"""
market_platform/mock_market_api.py - TESA 2026 Next-Gen Market REST API Simulator
Simulates the official competition market environment for Track 3:
- Exposes REST API endpoints (GET / POST) with JSON payloads.
- Features diverse buyer profiles (Specialty Roaster, Commercial Factory, Instant Powder Processor).
- Implements Blind Bidding round resolution.
- Computes competition efficiency scores based on sale price relative to intrinsic lot value.
Pure English interface without emojis.
"""

import sys
import time
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
import uvicorn

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.config import MARKET_API_HOST, MARKET_API_PORT

app = FastAPI(title="TGR2026 Next-Gen Coffee Market Simulator", version="1.0.0")

class BuyerProfile(BaseModel):
    buyer_id: str
    name: str
    target_quality: str
    max_defect_rate: float
    moisture_min: float
    moisture_max: float
    budget_max_thb: float
    description: str

class CoffeeLot(BaseModel):
    lot_id: str
    defect_rate_pct: float
    moisture_pct: float
    primary_defects: int
    secondary_defects: int
    grade: str
    intrinsic_value_thb: float
    status: str = "AVAILABLE"  # AVAILABLE, SOLD, EXPIRED

class BidOffer(BaseModel):
    lot_id: str
    buyer_id: str
    bid_price_thb: float

class BidResult(BaseModel):
    lot_id: str
    buyer_id: str
    bid_price_thb: float
    intrinsic_value_thb: float
    won: bool
    reason: str
    profit_thb: float = 0.0
    surplus_ratio_pct: float = 0.0

BUYERS: Dict[str, BuyerProfile] = {
    "buyer_specialty": BuyerProfile(
        buyer_id="buyer_specialty",
        name="Chumphon Craft Roastery",
        target_quality="Specialty Fine Robusta",
        max_defect_rate=5.0,
        moisture_min=10.0,
        moisture_max=12.5,
        budget_max_thb=360.0,
        description="Premium micro-roastery seeking zero-defect beans with ideal moisture."
    ),
    "buyer_commercial": BuyerProfile(
        buyer_id="buyer_commercial",
        name="Southern Roasting & Blending Co.",
        target_quality="Commercial Grade Robusta",
        max_defect_rate=14.0,
        moisture_min=9.5,
        moisture_max=13.5,
        budget_max_thb=220.0,
        description="Commercial espresso blend factory accepting standard defects."
    ),
    "buyer_instant": BuyerProfile(
        buyer_id="buyer_instant",
        name="Chumphon Agro-Instant Corp.",
        target_quality="Processing Grade / Byproduct",
        max_defect_rate=40.0,
        moisture_min=8.0,
        moisture_max=15.0,
        budget_max_thb=130.0,
        description="Instant spray-dried coffee producer buying volume at low price."
    )
}

# Initial Inventory for Trading Simulation
INITIAL_LOTS = [
    CoffeeLot(
        lot_id="LOT-CPN-001",
        defect_rate_pct=2.4,
        moisture_pct=11.2,
        primary_defects=0,
        secondary_defects=2,
        grade="FINE_ROBUSTA",
        intrinsic_value_thb=310.0
    ),
    CoffeeLot(
        lot_id="LOT-CPN-002",
        defect_rate_pct=5.8,
        moisture_pct=11.8,
        primary_defects=1,
        secondary_defects=5,
        grade="PREMIUM",
        intrinsic_value_thb=215.0
    ),
    CoffeeLot(
        lot_id="LOT-CPN-003",
        defect_rate_pct=11.5,
        moisture_pct=12.2,
        primary_defects=3,
        secondary_defects=9,
        grade="COMMERCIAL_GRADE",
        intrinsic_value_thb=140.0
    ),
    CoffeeLot(
        lot_id="LOT-CPN-004",
        defect_rate_pct=26.0,
        moisture_pct=14.1,
        primary_defects=8,
        secondary_defects=18,
        grade="REJECT",
        intrinsic_value_thb=70.0
    )
]

market_state = {
    "current_round": 1,
    "max_rounds": 5,
    "is_active": True,
    "inventory": {lot.lot_id: lot.copy() for lot in INITIAL_LOTS},
    "history": [],
    "total_revenue": 0.0,
    "total_intrinsic_value": 0.0,
    "total_surplus_score": 0.0
}

@app.get("/")
def get_root():
    return {
        "service": "TGR2026 Next-Gen Market Simulator",
        "round": market_state["current_round"],
        "active": market_state["is_active"],
        "endpoints": ["/api/market/status", "/api/market/inventory", "/api/market/bid", "/api/market/resolve_round"]
    }

@app.get("/api/market/status")
def get_market_status():
    """Returns current market state and buyer demand constraints."""
    return {
        "current_round": market_state["current_round"],
        "max_rounds": market_state["max_rounds"],
        "is_active": market_state["is_active"],
        "buyers": list(BUYERS.values()),
        "round_timestamp": time.time()
    }

def sync_live_db_lots():
    """Dynamically integrates real fused lots from ESP32 + RPi5 in shared/live_db.json."""
    db_file = ROOT_DIR / "shared" / "live_db.json"
    if not db_file.exists():
        return
    try:
        with open(db_file, "r") as f:
            data = json.load(f)
        for batch_id, record in data.get("batches", {}).items():
            sensor = record.get("latest_sensor")
            vision = record.get("latest_vision")
            if sensor and vision:
                grade = vision.get("primary_grade", "COMMERCIAL_GRADE")
                price_map = {"FINE_ROBUSTA": 320.0, "PREMIUM": 230.0, "COMMERCIAL_GRADE": 145.0, "REJECT": 65.0}
                intrinsic = price_map.get(grade, 145.0)
                defects = vision.get("defects", {})
                pri = int(defects.get("black_beans", 0) + defects.get("mold_beans", 0))
                sec = int(defects.get("broken_beans", 0) + defects.get("unripe_beans", 0))
                
                # Insert or update into inventory if available
                if batch_id not in market_state["inventory"] or market_state["inventory"][batch_id].status == "AVAILABLE":
                    market_state["inventory"][batch_id] = CoffeeLot(
                        lot_id=batch_id,
                        defect_rate_pct=float(vision.get("defect_rate_pct", 10.0)),
                        moisture_pct=float(sensor.get("moisture_pct", 11.5)),
                        primary_defects=pri,
                        secondary_defects=sec,
                        grade=grade,
                        intrinsic_value_thb=intrinsic
                    )
    except Exception as e:
        print(f"Notice: Failed to sync live db lots: {e}")


@app.get("/api/market/inventory")
def get_inventory():
    """Returns seller's available inventory lots and their physical metrics."""
    sync_live_db_lots()
    available = [lot for lot in market_state["inventory"].values() if lot.status == "AVAILABLE"]
    return {
        "available_lots": available,
        "count": len(available)
    }

@app.post("/api/market/bid")
def submit_bid(offers: List[BidOffer]):
    """Receives agent blind bids for the current round."""
    if not market_state["is_active"]:
        raise HTTPException(status_code=400, detail="Market is closed")

    results: List[BidResult] = []

    for offer in offers:
        lot = market_state["inventory"].get(offer.lot_id)
        buyer = BUYERS.get(offer.buyer_id)

        if not lot or lot.status != "AVAILABLE":
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=0.0,
                won=False,
                reason="Lot not available or invalid"
            ))
            continue

        if not buyer:
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=False,
                reason="Buyer does not exist"
            ))
            continue

        # Check Buyer Quality Constraints
        if lot.defect_rate_pct > buyer.max_defect_rate:
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=False,
                reason=f"Defect rate ({lot.defect_rate_pct}%) exceeds buyer maximum ({buyer.max_defect_rate}%)"
            ))
            continue

        # Check Buyer Moisture Constraints
        if lot.moisture_pct < buyer.moisture_min or lot.moisture_pct > buyer.moisture_max:
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=False,
                reason=f"Moisture ({lot.moisture_pct}%) outside buyer window ({buyer.moisture_min}-{buyer.moisture_max}%)"
            ))
            continue

        # Check Price Ceiling & Simulated Market Competition
        # Buyer has a reservation ceiling, and competing agents submit bids within +-10% of fair value
        competing_bid = lot.intrinsic_value_thb * random.uniform(1.05, 1.25)
        if offer.bid_price_thb > buyer.budget_max_thb:
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=False,
                reason=f"Bid price ({offer.bid_price_thb:.1f} THB) exceeds buyer budget ({buyer.budget_max_thb:.1f} THB)"
            ))
        elif offer.bid_price_thb > competing_bid * 1.08:
            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=False,
                reason=f"Underbid by competitor in blind auction (market cleared at {competing_bid:.1f} THB)"
            ))
        else:
            # Won Bid!
            profit = round(offer.bid_price_thb - lot.intrinsic_value_thb, 2)
            surplus_ratio = round((profit / max(1.0, lot.intrinsic_value_thb)) * 100, 2)
            lot.status = "SOLD"

            market_state["total_revenue"] += offer.bid_price_thb
            market_state["total_intrinsic_value"] += lot.intrinsic_value_thb
            market_state["total_surplus_score"] += surplus_ratio

            results.append(BidResult(
                lot_id=offer.lot_id,
                buyer_id=offer.buyer_id,
                bid_price_thb=offer.bid_price_thb,
                intrinsic_value_thb=lot.intrinsic_value_thb,
                won=True,
                reason="Bid accepted by buyer",
                profit_thb=profit,
                surplus_ratio_pct=surplus_ratio
            ))

    round_record = {
        "round": market_state["current_round"],
        "timestamp": time.time(),
        "bids_submitted": len(offers),
        "bids_won": sum(1 for r in results if r.won),
        "results": [r.dict() for r in results]
    }
    market_state["history"].append(round_record)
    return round_record

@app.post("/api/market/resolve_round")
def resolve_round():
    """Advances market round and adds new incoming coffee lots."""
    if not market_state["is_active"]:
        return {"status": "MARKET_CLOSED"}

    market_state["current_round"] += 1

    if market_state["current_round"] > market_state["max_rounds"]:
        market_state["is_active"] = False

    # Simulate arrival of a new batch from farm drying
    new_lot_idx = len(market_state["inventory"]) + 1
    new_defect = round(random.uniform(2.0, 18.0), 1)
    new_moisture = round(random.uniform(10.2, 13.0), 1)
    new_intrinsic = round(max(50.0, 340.0 - (new_defect * 14.0)), 1)
    new_lot = CoffeeLot(
        lot_id=f"LOT-CPN-{new_lot_idx:03d}",
        defect_rate_pct=new_defect,
        moisture_pct=new_moisture,
        primary_defects=int(new_defect // 3),
        secondary_defects=int(new_defect),
        grade="FINE_ROBUSTA" if new_defect < 4 else ("COMMERCIAL_GRADE" if new_defect < 14 else "REJECT"),
        intrinsic_value_thb=new_intrinsic
    )
    market_state["inventory"][new_lot.lot_id] = new_lot

    return {
        "status": "ADVANCED",
        "new_round": market_state["current_round"],
        "is_active": market_state["is_active"],
        "new_lot_added": new_lot.lot_id
    }

@app.get("/api/market/scoreboard")
def get_scoreboard():
    """Returns official TESA competition performance metrics."""
    return {
        "current_round": market_state["current_round"],
        "is_active": market_state["is_active"],
        "total_revenue_thb": round(market_state["total_revenue"], 2),
        "total_intrinsic_value_thb": round(market_state["total_intrinsic_value"], 2),
        "overall_surplus_score": round(market_state["total_surplus_score"], 2),
        "history": market_state["history"]
    }

def run_server():
    print(f"Starting TESA 2026 Next-Gen Market Simulator on {MARKET_API_HOST}:{MARKET_API_PORT}")
    uvicorn.run(app, host=MARKET_API_HOST, port=MARKET_API_PORT, log_level="info")

if __name__ == "__main__":
    run_server()
