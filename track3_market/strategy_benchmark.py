"""
market_platform/strategy_benchmark.py - TESA 2026 AI Agent Strategy Tournament & Optimizer
Compares 4 distinct algorithmic bidding strategies against market simulations:
1. FixedConservativeAgent   : Static low-margin (8-10%) guaranteed win strategy.
2. FixedAggressiveAgent     : Static high-margin (22-25%) high-risk strategy.
3. AdaptiveFeedbackAgent    : Dynamic margin adjusting on Win/Loss feedback.
4. SmartAsymmetricAgent     : Value-based asymmetric pricing (High margin on low-cost lots, tight margin on fine lots).
Outputs win rate, total revenue, and overall Value Surplus Score.
Pure English interface without emojis.
"""

import sys
import copy
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from track3_market.mock_market_api import BUYERS, CoffeeLot, INITIAL_LOTS

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.history: List[Dict[str, Any]] = []

    def select_buyer(self, lot: CoffeeLot, buyers: Dict[str, Any]) -> Optional[Any]:
        eligible = []
        for b in buyers.values():
            if lot.defect_rate_pct <= b.max_defect_rate and b.moisture_min <= lot.moisture_pct <= b.moisture_max:
                eligible.append(b)
        if not eligible:
            eligible = [b for b in buyers.values() if "instant" in b.buyer_id]
        if not eligible:
            return None
        return max(eligible, key=lambda b: b.budget_max_thb)

    def calculate_bid(self, lot: CoffeeLot, buyer: Any, round_num: int) -> float:
        raise NotImplementedError
]
    def record_feedback(self, result: Dict[str, Any]):
        self.history.append(result)


class FixedConservativeAgent(BaseAgent):
    """Bids with a fixed low margin (8%) to guarantee wins."""
    def calculate_bid(self, lot: CoffeeLot, buyer: Any, round_num: int) -> float:
        bid = lot.intrinsic_value_thb * 1.08
        return min(round(bid, 2), buyer.budget_max_thb * 0.98)


class FixedAggressiveAgent(BaseAgent):
    """Bids with a fixed high margin (24%) seeking maximum margin per trade."""
    def calculate_bid(self, lot: CoffeeLot, buyer: Any, round_num: int) -> float:
        bid = lot.intrinsic_value_thb * 1.24
        return min(round(bid, 2), buyer.budget_max_thb * 0.98)


class AdaptiveFeedbackAgent(BaseAgent):
    """Dynamically adjusts target margin up on wins and down on losses."""
    def __init__(self, name: str = "AdaptiveFeedbackAgent"):
        super().__init__(name)
        self.current_margin = 0.16

    def calculate_bid(self, lot: CoffeeLot, buyer: Any, round_num: int) -> float:
        bid = lot.intrinsic_value_thb * (1.0 + self.current_margin)
        return min(round(bid, 2), buyer.budget_max_thb * 0.96)

    def record_feedback(self, result: Dict[str, Any]):
        super().record_feedback(result)
        if result["won"]:
            # Gradual upward ratchet to capture more surplus
            self.current_margin = min(0.30, self.current_margin + 0.02)
        else:
            # Drop margin to restore win rate if underbid or rejected
            self.current_margin = max(0.06, self.current_margin - 0.035)


class SmartAsymmetricAgent(BaseAgent):
    """
    TESA Champion Strategy: Asymmetric Margin Allocation
    - Low Intrinsic Value lots (Reject/Off-grade): High surplus potential (up to 40-50% markup safely within instant budget).
    - High Intrinsic Value lots (Fine Robusta): Slim budget headroom (10-14% markup) to avoid underbidding or budget overflow.
    - Uses learned clearing prices from previous rounds to calibrate headroom.
    """
    def __init__(self, name: str = "SmartAsymmetricAgent"):
        super().__init__(name)
        self.cleared_price_ratios: List[float] = []

    def calculate_bid(self, lot: CoffeeLot, buyer: Any, round_num: int) -> float:
        intrinsic = lot.intrinsic_value_thb
        budget = buyer.budget_max_thb

        # Calculate max possible headroom up to buyer budget
        max_possible_ratio = budget / max(1.0, intrinsic)

        if intrinsic < 100.0:
            # Low value lot (e.g. 70 THB): High margin feasible (30-45%)
            target_markup = min(1.35, max_possible_ratio * 0.90)
        elif intrinsic < 200.0:
            # Medium commercial lot (e.g. 140 THB): Moderate margin (18-24%)
            target_markup = min(1.22, max_possible_ratio * 0.94)
        else:
            # Premium/Fine lot (e.g. 310 THB): Tight margin (10-15%)
            target_markup = min(1.14, max_possible_ratio * 0.96)

        # Incorporate historical cleared ratio calibration if available
        if self.cleared_price_ratios:
            avg_cleared = sum(self.cleared_price_ratios[-5:]) / len(self.cleared_price_ratios[-5:])
            safe_target = avg_cleared * 1.05  # Stay safely within 8% winning threshold
            target_markup = min(target_markup, safe_target)

        bid = intrinsic * target_markup
        return min(round(bid, 2), round(budget * 0.97, 2))

    def record_feedback(self, result: Dict[str, Any]):
        super().record_feedback(result)
        # Parse market clearing feedback if provided
        reason = result.get("reason", "")
        if "market cleared at" in reason:
            match = re.search(r"market cleared at ([\d\.]+) THB", reason)
            if match:
                cleared_val = float(match.group(1))
                intrinsic = result.get("intrinsic_value_thb", 1.0)
                if intrinsic > 0:
                    self.cleared_price_ratios.append(cleared_val / intrinsic)


def simulate_bid_evaluation(lot: CoffeeLot, buyer: Any, bid_price: float) -> Dict[str, Any]:
    """Simulates market auction logic matching mock_market_api."""
    if lot.defect_rate_pct > buyer.max_defect_rate:
        return {"won": False, "reason": "Defect exceeded", "profit": 0.0, "surplus_pct": 0.0}
    if lot.moisture_pct < buyer.moisture_min or lot.moisture_pct > buyer.moisture_max:
        return {"won": False, "reason": "Moisture outside window", "profit": 0.0, "surplus_pct": 0.0}

    competing_bid = lot.intrinsic_value_thb * random.uniform(1.05, 1.25)

    if bid_price > buyer.budget_max_thb:
        return {"won": False, "reason": "Exceeded budget", "profit": 0.0, "surplus_pct": 0.0}
    elif bid_price > competing_bid * 1.08:
        return {
            "won": False,
            "reason": f"Underbid by competitor in blind auction (market cleared at {competing_bid:.1f} THB)",
            "profit": 0.0,
            "surplus_pct": 0.0
        }
    else:
        profit = round(bid_price - lot.intrinsic_value_thb, 2)
        surplus_ratio = round((profit / max(1.0, lot.intrinsic_value_thb)) * 100, 2)
        return {
            "won": True,
            "reason": "Accepted",
            "profit": profit,
            "surplus_pct": surplus_ratio
        }


def run_benchmark(iterations: int = 100):
    print("=" * 70)
    print(f"   TESA 2026 AI TRADING AGENT TOURNAMENT BENCHMARK ({iterations} MATCHES)")
    print("=" * 70)

    agents = [
        FixedConservativeAgent("1. Fixed Conservative (8% Margin)"),
        FixedAggressiveAgent("2. Fixed Aggressive (24% Margin)"),
        AdaptiveFeedbackAgent("3. Adaptive Feedback (Dynamic Margin)"),
        SmartAsymmetricAgent("4. Smart Asymmetric (Value-Weighted Champion)")
    ]

    scores: Dict[str, Dict[str, float]] = {
        agent.name: {
            "bids_submitted": 0,
            "bids_won": 0,
            "total_revenue": 0.0,
            "total_intrinsic": 0.0,
            "total_profit": 0.0,
            "total_surplus_score": 0.0
        } for agent in agents
    }

    # Run tournament matches
    for match in range(iterations):
        # Generate random coffee lots for this match
        lots: List[CoffeeLot] = [
            CoffeeLot(
                lot_id="LOT-FINE",
                defect_rate_pct=random.uniform(1.5, 4.0),
                moisture_pct=random.uniform(10.5, 12.0),
                primary_defects=0,
                secondary_defects=random.randint(1, 3),
                grade="FINE_ROBUSTA",
                intrinsic_value_thb=random.uniform(290.0, 330.0)
            ),
            CoffeeLot(
                lot_id="LOT-COMMERCIAL",
                defect_rate_pct=random.uniform(6.0, 13.0),
                moisture_pct=random.uniform(10.0, 13.0),
                primary_defects=random.randint(1, 3),
                secondary_defects=random.randint(4, 9),
                grade="COMMERCIAL_GRADE",
                intrinsic_value_thb=random.uniform(130.0, 180.0)
            ),
            CoffeeLot(
                lot_id="LOT-OFFGRADE",
                defect_rate_pct=random.uniform(18.0, 35.0),
                moisture_pct=random.uniform(9.0, 14.5),
                primary_defects=random.randint(4, 10),
                secondary_defects=random.randint(10, 20),
                grade="REJECT",
                intrinsic_value_thb=random.uniform(60.0, 95.0)
            )
        ]

        # Each agent plays the exact same lots in this match
        for agent in agents:
            for lot in lots:
                buyer = agent.select_buyer(lot, BUYERS)
                if not buyer:
                    continue

                bid_price = agent.calculate_bid(lot, buyer, match + 1)
                eval_res = simulate_bid_evaluation(lot, buyer, bid_price)

                scores[agent.name]["bids_submitted"] += 1
                if eval_res["won"]:
                    scores[agent.name]["bids_won"] += 1
                    scores[agent.name]["total_revenue"] += bid_price
                    scores[agent.name]["total_intrinsic"] += lot.intrinsic_value_thb
                    scores[agent.name]["total_profit"] += eval_res["profit"]
                    scores[agent.name]["total_surplus_score"] += eval_res["surplus_pct"]

                eval_res["intrinsic_value_thb"] = lot.intrinsic_value_thb
                agent.record_feedback(eval_res)

    print(f"\n{'Strategy Name':<45} | {'Win Rate':<8} | {'Avg Surplus/Match':<18} | {'Total Surplus %':<15}")
    print("-" * 95)
    for name, s in scores.items():
        win_rate = (s["bids_won"] / max(1, s["bids_submitted"])) * 100
        avg_surplus_per_match = s["total_surplus_score"] / iterations
        total_surplus = s["total_surplus_score"]
        print(f"{name:<45} | {win_rate:>6.1f}% | {avg_surplus_per_match:>12.1f}%/match | {total_surplus:>14.1f}%")
    print("=" * 95)

if __name__ == "__main__":
    run_benchmark(iterations=150)
