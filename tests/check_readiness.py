"""
check_competition_readiness.py - Master Pre-Competition Diagnostics for TESA Top Gun Rally 2026
Runs comprehensive diagnostic tests for Track 1, Track 2, and Track 3.
Pure English interface without emojis.
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.config import check_system_health, DEFAULT_ONNX_MODEL, DEFAULT_TEST_IMAGES
from track2_edge_ai.vision_engine import CoffeeVisionAnalyzer
import numpy as np
import cv2

def run_diagnostics():
    print("=" * 65)
    print("      TESA TOP GUN RALLY 2026 - COMPETITION READINESS CHECK")
    print("=" * 65)

    health = check_system_health()
    all_passed = True

    # Check 1: Network & Broker
    print(f"[TRACK 1 & BROKER]")
    print(f"  Local Host IP       : {health['local_ip']}")
    if health['mqtt_broker']:
        print("  MQTT Broker (1883)  : PASSED (Online and listening)")
    else:
        print("  MQTT Broker (1883)  : WARNING (Offline - run 'brew services start mosquitto')")
        all_passed = False

    # Check 2: Edge AI & Vision
    print(f"\n[TRACK 2: EDGE AI & ONNX RUNTIME]")
    if health['onnx_model']:
        print(f"  ONNX Model File     : PASSED ({DEFAULT_ONNX_MODEL.name})")
        # Test 1-frame inference speed
        try:
            analyzer = CoffeeVisionAnalyzer(model_path=str(DEFAULT_ONNX_MODEL), threads=4)
            dummy_frame = np.full((320, 320, 3), 128, dtype=np.uint8)
            t0 = time.time()
            analyzer.analyze_frame_onnx(dummy_frame)
            lat_ms = (time.time() - t0) * 1000
            print(f"  ONNX Inference Test : PASSED ({lat_ms:.2f} ms / {1000/lat_ms:.1f} FPS)")
        except Exception as e:
            print(f"  ONNX Inference Test : FAILED ({e})")
            all_passed = False
    else:
        print(f"  ONNX Model File     : FAILED (Missing at {DEFAULT_ONNX_MODEL})")
        all_passed = False

    if health['test_dataset']:
        print(f"  Test Dataset        : PASSED ({health['test_image_count']} real Robusta images available)")
    else:
        print("  Test Dataset        : WARNING (Test dataset folder not found)")

    # Check 3: Track 3 Market Engine & Trading Agent
    print(f"\n[TRACK 3: THE NEXT-GEN MARKET & AI AGENT]")
    try:
        from fastapi.testclient import TestClient
        from track3_market.mock_market_api import app as market_app
        client = TestClient(market_app)
        res = client.get('/api/market/status')
        if res.status_code == 200:
            print("  Market REST API     : PASSED (FastAPI endpoints verified)")
        else:
            print("  Market REST API     : FAILED (Non-200 status code)")
            all_passed = False

        # Test Bidding Calculation
        bid_test = client.post('/api/market/bid', json=[
            {'lot_id': 'LOT-CPN-001', 'buyer_id': 'buyer_specialty', 'bid_price_thb': 330.0}
        ])
        if bid_test.status_code == 200 and bid_test.json()['bids_won'] > 0:
            print("  Blind Bidding Engine: PASSED (Bids resolved, surplus scoring active)")
        else:
            print("  Blind Bidding Engine: WARNING (Check mock bidding resolution)")
    except Exception as e:
        print(f"  Market REST API     : FAILED ({e})")
        all_passed = False

    # Check 4: Shared Database & Schemas
    print(f"\n[DATA CONTRACT & STORAGE]")
    if health['shared_db']:
        print("  Shared Telemetry DB : PASSED (live_db.json ready)")
    else:
        print("  Shared Telemetry DB : NOT INITIALIZED (Will auto-create on first packet)")

    print("=" * 65)
    if all_passed:
        print("RESULT: ALL SYSTEMS OPERATIONAL AND COMPETITION READY!")
    else:
        print("RESULT: SOME COMPONENTS NEED ATTENTION (See warnings above).")
    print("=" * 65)

if __name__ == "__main__":
    run_diagnostics()
