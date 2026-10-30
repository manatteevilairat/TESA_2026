"""
market_platform/backend_service.py
Backend Data Fusion Service:
- เชื่อมต่อ MQTT Broker (Mosquitto)
- ดักฟังข้อมูล Sensing (ESP32) และ Vision (RPi 5)
- รวมข้อมูล (Data Fusion) เข้ากับ Batch ID
- บันทึกสถานะลง shared/live_db.json เพื่อให้หน้าเว็บ Streamlit ดึงไปแสดงผลแบบ Real-time
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import paho.mqtt.client as mqtt
from shared.schemas import SensorData, VisionData, CoffeeBatchRecord
from shared.config import MQTT_BROKER_HOST, MQTT_BROKER_PORT
from market_platform.slm_evaluator import evaluate_coffee_quality

DB_FILE = ROOT_DIR / "shared" / "live_db.json"
MQTT_BROKER_DEFAULT = MQTT_BROKER_HOST
MQTT_PORT_DEFAULT = MQTT_BROKER_PORT


class BackendFusionEngine:
    def __init__(self, db_path: Path = DB_FILE):
        self.db_path = db_path
        self.batches = {}
        self.message_history = []
        self.load_database()

    def load_database(self):
        """โหลดข้อมูลเดิมจากไฟล์ JSON (ถ้ามี)"""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.batches = data.get("batches", {})
                    self.message_history = data.get("history", [])
                    print(f"📂 โหลดฐานข้อมูลสำเร็จ: {len(self.batches)} Batches")
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดในการอ่านฐานข้อมูล: {e}")

    def save_database(self):
        """บันทึกสถานะล่าสุดลงไฟล์ JSON แบบ Atomic write"""
        temp_path = self.db_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump({
                    "last_updated": time.time(),
                    "batches": self.batches,
                    "history": self.message_history[-30:] # เก็บ 30 ข้อความล่าสุด
                }, f, ensure_ascii=False, indent=2)
            temp_path.replace(self.db_path)
        except Exception as e:
            print(f"⚠️ ไม่สามารถบันทึกฐานข้อมูล: {e}")

    def process_sensor_message(self, batch_id: str, payload_dict: dict):
        sensor_obj = SensorData(**payload_dict)
        if batch_id not in self.batches:
            self.batches[batch_id] = CoffeeBatchRecord(
                batch_id=batch_id,
                latest_sensor=sensor_obj
            ).model_dump()
        else:
            self.batches[batch_id]["latest_sensor"] = sensor_obj.model_dump()

        print(f"📡 [Sensor Ingest] Batch {batch_id} | ความชื้น: {sensor_obj.moisture_pct}% | อุณหภูมิ: {sensor_obj.ambient_temp_c}°C")
        self.record_history("SENSOR", batch_id, f"ความชื้น {sensor_obj.moisture_pct}%, {sensor_obj.status}")
        self.save_database()

    def process_vision_message(self, batch_id: str, payload_dict: dict):
        vision_obj = VisionData(**payload_dict)

        # Handle base64 image transmission from remote RPi
        if vision_obj.image_base64:
            try:
                import base64
                img_bytes = base64.b64decode(vision_obj.image_base64)
                img_path = ROOT_DIR / "shared" / f"{batch_id}_vision.jpg"
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                vision_obj.image_annotated_url = str(img_path)
                with open(ROOT_DIR / "shared" / "latest_vision.jpg", "wb") as f:
                    f.write(img_bytes)
            except Exception as e:
                print(f"Warning: Failed to decode base64 image: {e}")
        elif vision_obj.image_annotated_url and not os.path.exists(vision_obj.image_annotated_url):
            # Remap remote Linux path (/home/admin/TESA_2026/...) to local Mac workspace
            rel = vision_obj.image_annotated_url.replace("/home/admin/TESA_2026/", "")
            mac_counterpart = ROOT_DIR / rel
            if mac_counterpart.exists():
                vision_obj.image_annotated_url = str(mac_counterpart)
            else:
                vision_obj.image_annotated_url = str(ROOT_DIR / "shared" / "latest_vision.jpg")

        if batch_id not in self.batches:
            self.batches[batch_id] = CoffeeBatchRecord(
                batch_id=batch_id,
                latest_vision=vision_obj
            ).model_dump()
        else:
            self.batches[batch_id]["latest_vision"] = vision_obj.model_dump()

        print(f"📷 [Vision Ingest] Batch {batch_id} | เกรด: {vision_obj.primary_grade} | ตำหนิ: {vision_obj.defect_rate_pct}%")
        self.record_history("VISION", batch_id, f"เกรด {vision_obj.primary_grade}, ตำหนิ {vision_obj.defect_rate_pct}%")
        self.save_database()

    def record_history(self, source: str, batch_id: str, summary: str):
        self.message_history.append({
            "time": time.strftime("%X"),
            "source": source,
            "batch_id": batch_id,
            "summary": summary
        })


def start_backend_service(broker: str = MQTT_BROKER_DEFAULT, port: int = MQTT_PORT_DEFAULT):
    engine = BackendFusionEngine()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"✅ Backend Service เชื่อมต่อ MQTT Broker [{broker}:{port}] สำเร็จ")
            # Subscribe ทุกหัวข้อของกาแฟ
            client.subscribe("tgr2026/coffee/+/sensing")
            client.subscribe("tgr2026/coffee/+/vision")
            print("🎧 กำลังดักฟัง Topics: tgr2026/coffee/+/sensing และ tgr2026/coffee/+/vision")
        else:
            print(f"❌ เชื่อมต่อ MQTT Broker ล้มเหลว (rc={rc})")

    def on_message(client, userdata, msg):
        topic = msg.topic
        payload_str = msg.payload.decode("utf-8")
        try:
            payload_data = json.loads(payload_str)
            parts = topic.split("/")
            # รูปแบบ: tgr2026 / coffee / {batch_id} / sensing|vision
            if len(parts) >= 4 and parts[1] == "coffee":
                batch_id = parts[2]
                msg_type = parts[3]
                if msg_type == "sensing":
                    engine.process_sensor_message(batch_id, payload_data)
                elif msg_type == "vision":
                    engine.process_vision_message(batch_id, payload_data)
        except Exception as e:
            print(f"⚠️ แปลงข้อความผิดพลาดจาก Topic {topic}: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="tgr2026_backend_fusion")
    client.on_connect = on_connect
    client.on_message = on_message

    print("🚀 กำลังเริ่มต้น Backend Data Fusion Service...")
    client.connect(broker, port, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 หยุดการทำงานของ Backend Service")
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TGR2026 Backend Data Fusion Service")
    parser.add_argument("--broker", type=str, default="localhost", help="MQTT Broker Host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
    args = parser.parse_args()

    start_backend_service(broker=args.broker, port=args.port)
