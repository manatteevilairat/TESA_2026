"""
market_platform/trading_agent.py - Autonomous AI Trading Agent for TESA 2026 Next-Gen Market
Implements the official Track 3 Agent architecture:
1. LOOK (ดู) : Queries market API for active round, buyer constraints, and current inventory.
2. THINK (คิด): Evaluates intrinsic lot values, matches lots to optimal buyers, and computes strategic bid prices.
3. ACT (ทำ)   : Submits blind bids via REST POST, inspects win/loss feedback, and adapts margins.

Includes 3 selectable strategies:
- 'asymmetric' (Champion): Tailored margins by grade (high markup on cheap beans, safe markup on premium beans).
- 'adaptive'   : Online learning ratchet (increases margin on win, decreases on loss/underbid).
- 'fixed'      : Static markup ratio.
Pure English interface without emojis.
"""

import sys
import time
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.config import MARKET_API_PORT

DEFAULT_API_BASE = f"http://127.0.0.1:{MARKET_API_PORT}"


class CoffeeTradingAgent:
    def __init__(
        self,
        api_base: str = DEFAULT_API_BASE,
        strategy: str = "asymmetric",
        base_margin_pct: float = 16.0
    ):
        self.api_base = api_base.rstrip("/")
        self.strategy = strategy.lower()
        self.base_margin_pct = base_margin_pct
        self.current_adaptive_margin = base_margin_pct / 100.0
        self.bid_history: List[Dict[str, Any]] = []
        self.cleared_price_ratios: List[float] = []

    def look(self) -> Dict[str, Any]:
        """Queries market status and available inventory via REST API."""
        try:
            status_res = requests.get(f"{self.api_base}/api/market/status", timeout=3.0)
            status_res.raise_for_status()
            market_status = status_res.json()

            inventory_res = requests.get(f"{self.api_base}/api/market/inventory", timeout=3.0)
            inventory_res.raise_for_status()
            inventory = inventory_res.json()

            return {
                "market": market_status,
                "inventory": inventory.get("available_lots", [])
            }
        except Exception as e:
            print(f"Error querying market API: {e}")
            return {"market": None, "inventory": []}

    def select_best_buyer(self, lot: Dict[str, Any], buyers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Filters buyers by quality and moisture, selecting the highest paying viable buyer."""
        defect = lot["defect_rate_pct"]
        moisture = lot["moisture_pct"]

        eligible = [
            b for b in buyers
            if defect <= b["max_defect_rate"] and b["moisture_min"] <= moisture <= b["moisture_max"]
        ]
        if not eligible:
            # Fallback for extreme defect / off-grade beans to instant processors
            eligible = [b for b in buyers if "instant" in b["buyer_id"]]

        if not eligible:
            return None
        return max(eligible, key=lambda b: b["budget_max_thb"])

    def calculate_asymmetric_bid(self, lot: Dict[str, Any], buyer: Dict[str, Any]) -> float:
        """
        TESA Champion Pricing:
        - Low intrinsic lots (Off-grade / Reject < 100 THB): High markup (25-35%), captures huge surplus score safely.
        - Commercial lots (100 - 200 THB): Moderate markup (16-20%).
        - Premium / Fine Robusta (> 200 THB): Tight markup (10-14%) to prevent budget overflow and underbidding.
        """
        intrinsic = lot["intrinsic_value_thb"]
        budget = buyer["budget_max_thb"]
        headroom_ratio = budget / max(1.0, intrinsic)

        if intrinsic < 100.0:
            target_multiplier = min(1.30, headroom_ratio * 0.92)
        elif intrinsic < 200.0:
            target_multiplier = min(1.18, headroom_ratio * 0.95)
        else:
            target_multiplier = min(1.12, headroom_ratio * 0.96)

        # Calibrate with observed competitor clearing prices if available
        if self.cleared_price_ratios:
            recent_avg = sum(self.cleared_price_ratios[-4:]) / len(self.cleared_price_ratios[-4:])
            target_multiplier = min(target_multiplier, recent_avg * 1.05)

        proposed_price = intrinsic * target_multiplier
        return round(min(proposed_price, budget * 0.97), 2)

    def calculate_adaptive_bid(self, lot: Dict[str, Any], buyer: Dict[str, Any]) -> float:
        """Online adaptive pricing: Ratchets up on win, backs off on loss."""
        intrinsic = lot["intrinsic_value_thb"]
        budget = buyer["budget_max_thb"]
        multiplier = 1.0 + self.current_adaptive_margin
        proposed_price = intrinsic * multiplier
        return round(min(proposed_price, budget * 0.96), 2)

    def calculate_fixed_bid(self, lot: Dict[str, Any], buyer: Dict[str, Any]) -> float:
        """Static markup bidding."""
        intrinsic = lot["intrinsic_value_thb"]
        budget = buyer["budget_max_thb"]
        multiplier = 1.0 + (self.base_margin_pct / 100.0)
        proposed_price = intrinsic * multiplier
        return round(min(proposed_price, budget * 0.96), 2)

    def think(self, market_status: Dict[str, Any], available_lots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Matches available lots to best buyers and computes strategic blind bids."""
        if not market_status or not available_lots:
            return []

        buyers = market_status.get("buyers", [])
        bids = []

        for lot in available_lots:
            buyer = self.select_best_buyer(lot, buyers)
            if not buyer:
                continue

            if self.strategy == "asymmetric":
                final_price = self.calculate_asymmetric_bid(lot, buyer)
            elif self.strategy == "adaptive":
                final_price = self.calculate_adaptive_bid(lot, buyer)
            else:
                final_price = self.calculate_fixed_bid(lot, buyer)

            # Check if buyer budget is physically lower than lot intrinsic cost
            if buyer["budget_max_thb"] < lot["intrinsic_value_thb"]:
                # Cannot sell with profit to this buyer; cap at budget ceiling to avoid instant rejection
                final_price = round(buyer["budget_max_thb"] * 0.98, 2)
            else:
                # Ensure minimum viable trade with positive margin
                final_price = max(final_price, round(lot["intrinsic_value_thb"] * 1.02, 2))
                final_price = min(final_price, round(buyer["budget_max_thb"] * 0.98, 2))

            bids.append({
                "lot_id": lot["lot_id"],
                "buyer_id": buyer["buyer_id"],
                "bid_price_thb": final_price
            })

        return bids

    def act(self, bids: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Submits blind bids to market API and processes round results."""
        if not bids:
            print("No bids to submit in this round.")
            return None

        try:
            res = requests.post(f"{self.api_base}/api/market/bid", json=bids, timeout=4.0)
            res.raise_for_status()
            round_result = res.json()
            self.bid_history.append(round_result)

            # Update Adaptive Learning Parameters from Round Feedback
            for item in round_result.get("results", []):
                reason = item.get("reason", "")
                intrinsic = item.get("intrinsic_value_thb", 1.0)

                # Parse competitor market clearing price
                if "market cleared at" in reason:
                    match = re.search(r"market cleared at ([\d\.]+) THB", reason)
                    if match and intrinsic > 0:
                        cleared_val = float(match.group(1))
                        self.cleared_price_ratios.append(cleared_val / intrinsic)

                # Adjust adaptive margin
                if self.strategy == "adaptive":
                    if item.get("won", False):
                        self.current_adaptive_margin = min(0.30, self.current_adaptive_margin + 0.015)
                    else:
                        self.current_adaptive_margin = max(0.06, self.current_adaptive_margin - 0.03)

            return round_result
        except Exception as e:
            print(f"Failed to submit bids: {e}")
            return None

    def step(self) -> Optional[Dict[str, Any]]:
        """Executes one complete Look -> Think -> Act agent cycle."""
        perception = self.look()
        market = perception.get("market")
        lots = perception.get("inventory", [])

        if not market or not market.get("is_active"):
            print("Market is currently closed or inactive.")
            return None

        round_num = market.get("current_round")
        print(f"\n--- AI Agent Cycle [Round {round_num} | Strategy: {self.strategy.upper()}] ---")
        print(f"Available Lots in Inventory: {len(lots)}")
        for lot in lots:
            print(f"  Lot {lot['lot_id']:<14} | Defect: {lot['defect_rate_pct']:>4.1f}% | Moisture: {lot['moisture_pct']:>4.1f}% | Fair Value: {lot['intrinsic_value_thb']:>6.1f} THB")

        bids = self.think(market, lots)
        print(f"Generated {len(bids)} strategic blind bids:")
        for b in bids:
            print(f"  Target: {b['buyer_id']:<20} | Lot: {b['lot_id']:<14} | Proposed Bid: {b['bid_price_thb']:>6.1f} THB")

        outcome = self.act(bids)
        if outcome:
            won_count = outcome.get("bids_won", 0)
            total = outcome.get("bids_submitted", 0)
            print(f"Round Resolution: {won_count}/{total} Bids Won!")
            for r in outcome.get("results", []):
                status_str = "ACCEPTED" if r["won"] else "REJECTED"
                print(f"  [{status_str:<8}] Lot: {r['lot_id']:<12} | Bid: {r['bid_price_thb']:>6.1f} THB | Surplus: {r.get('surplus_ratio_pct', 0.0):>5.1f}% ({r['reason']})")
        return outcome

    def advance_simulation(self):
        """Helper to advance round on mock server."""
        try:
            requests.post(f"{self.api_base}/api/market/resolve_round", timeout=2.0)
        except Exception:
            pass


def run_tournament(api_base: str, strategy: str = "asymmetric", rounds: int = 5):
    print("=" * 65)
    print("   Starting TESA 2026 Next-Gen Market Autonomous Tournament")
    print(f"   API Target : {api_base}")
    print(f"   Strategy   : {strategy.upper()}")
    print(f"   Max Rounds : {rounds}")
    print("=" * 65)

    agent = CoffeeTradingAgent(api_base=api_base, strategy=strategy)

    for r in range(1, rounds + 1):
        outcome = agent.step()
        if not outcome:
            break
        time.sleep(1.0)
        agent.advance_simulation()

    # Final Scoreboard
    try:
        score_res = requests.get(f"{api_base}/api/market/scoreboard", timeout=3.0)
        if score_res.ok:
            board = score_res.json()
            print("\n" + "=" * 65)
            print("                   FINAL TOURNAMENT SCORECARD")
            print("=" * 65)
            print(f"Total Revenue Generated    : {board['total_revenue_thb']:>8.2f} THB")
            print(f"Total Intrinsic Lot Value  : {board['total_intrinsic_value_thb']:>8.2f} THB")
            print(f"Overall Value Surplus Score: {board['overall_surplus_score']:>8.2f}%")
            print("=" * 65)
    except Exception as e:
        print(f"Failed to fetch final scoreboard: {e}")


def get_strategic_bid(
    lot: Dict[str, Any],
    buyer: Dict[str, Any],
    strategy: str = "asymmetric",
    cleared_ratios: Optional[List[float]] = None
) -> float:
    """
    1-Line Drop-In Strategic Bidding Calculator for Competition Day.
    Designed for zero-friction integration with the organizer's starter agent on Nov 18.

    Usage:
        from track3_market.trading_agent import get_strategic_bid
        bid_price = get_strategic_bid(lot, buyer, strategy="asymmetric")
    """
    intrinsic = float(
        lot.get("intrinsic_value_thb") or
        lot.get("cost_basis_thb") or
        lot.get("reserve_price") or
        lot.get("price") or 100.0
    )
    budget = float(
        buyer.get("budget_max_thb") or
        buyer.get("max_price") or
        buyer.get("budget") or 250.0
    )
    headroom_ratio = budget / max(1.0, intrinsic)

    if strategy == "asymmetric":
        if intrinsic < 100.0:
            target_multiplier = min(1.30, headroom_ratio * 0.92)
        elif intrinsic < 200.0:
            target_multiplier = min(1.18, headroom_ratio * 0.95)
        else:
            target_multiplier = min(1.12, headroom_ratio * 0.96)
    elif strategy == "adaptive":
        target_multiplier = 1.16
    else:  # fixed
        target_multiplier = 1.10

    if cleared_ratios:
        recent_avg = sum(cleared_ratios[-4:]) / len(cleared_ratios[-4:])
        target_multiplier = min(target_multiplier, recent_avg * 1.05)

    proposed = intrinsic * target_multiplier
    # Safety Bounds: Never exceed buyer budget ceiling, never bid below cost basis
    if budget < intrinsic:
        return round(budget * 0.98, 2)
    return round(min(max(proposed, intrinsic * 1.02), budget * 0.98), 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TGR2026 AI Coffee Trading Agent")
    parser.add_argument("--api", type=str, default=DEFAULT_API_BASE, help="Market API server URL")
    parser.add_argument("--strategy", type=str, default="asymmetric", choices=["asymmetric", "adaptive", "fixed"], help="Bidding strategy")
    parser.add_argument("--rounds", type=int, default=4, help="Number of simulated tournament rounds")
    args = parser.parse_args()

    run_tournament(api_base=args.api, strategy=args.strategy, rounds=args.rounds)
