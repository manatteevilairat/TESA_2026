"""
shared/config.py - Central Configuration and Network Discovery for TESA 2026
Provides dynamic local IP resolution, MQTT/REST endpoints, and environment settings.
"""

import os
import sys
import socket
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = ROOT_DIR / "shared"
TRACK1_DIR = ROOT_DIR / "track1_esp32"
TRACK2_DIR = ROOT_DIR / "track2_edge_ai"
EDGE_AI_DIR = TRACK2_DIR  # Alias for backward compatibility
MODELS_DIR = TRACK2_DIR / "models"
DATASET_DIR = TRACK2_DIR / "dataset"
TRACK3_DIR = ROOT_DIR / "track3_market"
MARKET_DIR = TRACK3_DIR  # Alias for backward compatibility

def get_local_ip() -> str:
    """Attempts to discover the machine's primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()

# Network Service Endpoints
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MARKET_API_HOST = os.getenv("MARKET_API_HOST", "0.0.0.0")
MARKET_API_PORT = int(os.getenv("MARKET_API_PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# Model Configuration
DEFAULT_ONNX_MODEL = MODELS_DIR / "coffee_best.onnx"
DEFAULT_TEST_IMAGES = DATASET_DIR / "test" / "images"

# Standard Coffee Taxonomy & Grading Constants
ROBUSTA_CLASSES = [
    "Black",
    "Broken",
    "Empty",
    "Good bean",
    "Insect damage",
    "Quaker",
    "Scorched"
]

PRIMARY_DEFECT_CLASSES = ["Black", "Insect damage", "Scorched"]
SECONDARY_DEFECT_CLASSES = ["Broken", "Empty", "Quaker"]

MOISTURE_TARGET_MIN = 10.0
MOISTURE_TARGET_MAX = 12.5

def check_system_health() -> Dict[str, Any]:
    """Inspects ports, files, and directories required for competition readiness."""
    health = {
        "local_ip": LOCAL_IP,
        "mqtt_broker": False,
        "onnx_model": DEFAULT_ONNX_MODEL.exists(),
        "test_dataset": DEFAULT_TEST_IMAGES.exists(),
        "test_image_count": 0,
        "shared_db": (SHARED_DIR / "live_db.json").exists()
    }

    # Test MQTT Broker port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((MQTT_BROKER_HOST, MQTT_BROKER_PORT))
        health["mqtt_broker"] = True
    except Exception:
        health["mqtt_broker"] = False
    finally:
        s.close()

    if health["test_dataset"]:
        health["test_image_count"] = len(list(DEFAULT_TEST_IMAGES.glob("*.jpg")))

    return health

if __name__ == "__main__":
    report = check_system_health()
    print("=== TESA 2026 System Diagnostics ===")
    print(f"Detected Host IP    : {report['local_ip']}")
    print(f"MQTT Broker Status  : {'ACTIVE' if report['mqtt_broker'] else 'DOWN'} ({MQTT_BROKER_HOST}:{MQTT_BROKER_PORT})")
    print(f"ONNX Model Found    : {'YES' if report['onnx_model'] else 'MISSING'} ({DEFAULT_ONNX_MODEL})")
    print(f"Test Dataset Found  : {'YES' if report['test_dataset'] else 'MISSING'} ({report['test_image_count']} images)")
    print(f"Shared Database     : {'READY' if report['shared_db'] else 'NOT INITIALIZED'}")
