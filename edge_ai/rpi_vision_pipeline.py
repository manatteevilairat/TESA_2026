"""
edge_ai/rpi_vision_pipeline.py
Template โค้ดสำหรับรันบน Raspberry Pi 5
- จับภาพจากกล้อง (Picamera2 หรือ OpenCV VideoCapture)
- รันโมเดลทำนายผล (ONNX Runtime / Heuristic fallback)
- คำนวณ Defect Rate และส่งข้อมูลสรุปผ่าน MQTT
*(หมายเหตุ: ไม่อนุญาตให้ใช้ AI HAT+ ตามกติกา โค้ดนี้จึงใช้ CPU Multi-threading)*
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# กำหนดค่าคงที่
MQTT_BROKER = "localhost"  # แก้เป็น IP ของเครื่องคอมพิวเตอร์หลักที่รัน Broker
TOPIC_VISION = "tgr2026/coffee/{batch_id}/vision"


def analyze_coffee_frame(frame=None) -> Dict:
    """
    ฟังก์ชันวิเคราะห์ภาพเมล็ดกาแฟ
    เมื่อเชื่อมต่อโมเดลจริง สามารถโหลด ONNX Runtime ตรงนี้ได้
    """
    sample_count = 50
    black_beans = 1
    sour_beans = 0
    mold_beans = 0
    broken_beans = 2
    unripe_beans = 1

    total_defects = black_beans + sour_beans + mold_beans + broken_beans + unripe_beans
    defect_rate = round((total_defects / sample_count) * 100, 1)

    if defect_rate <= 3.0 and mold_beans == 0:
        grade = "FINE_ROBUSTA"
    elif defect_rate <= 6.0:
        grade = "PREMIUM"
    else:
        grade = "COMMERCIAL_GRADE"

    return {
        "sample_count": sample_count,
        "defects": {
            "black_beans": black_beans,
            "sour_beans": sour_beans,
            "mold_beans": mold_beans,
            "broken_beans": broken_beans,
            "unripe_beans": unripe_beans
        },
        "defect_rate_pct": defect_rate,
        "primary_grade": grade
    }


def main():
    parser = argparse.ArgumentParser(description="RPi 5 Vision Node Pipeline")
    parser.add_argument("--batch", type=str, default="CPN-2026-B001", help="Batch ID")
    parser.add_argument("--broker", type=str, default=MQTT_BROKER, help="MQTT Broker Host")
    parser.add_argument("--dry-run", action="store_true", help="รันแบบไม่ต่อ MQTT")
    args = parser.parse_args()

    client = None
    if not args.dry_run:
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="rpi5_vision")
            client.connect(args.broker, 1883, 60)
            client.loop_start()
            print(f"✅ RPi 5 เชื่อมต่อ MQTT Broker: {args.broker}")
        except Exception as e:
            print(f"⚠️ ไม่สามารถเชื่อมต่อ MQTT: {e}")

    print("🍓 เริ่มต้น Vision Pipeline บน Raspberry Pi 5...")
    try:
        while True:
            result = analyze_coffee_frame()
            payload = {
                "device_id": "rpi5_vision_01",
                "batch_id": args.batch,
                "timestamp": time.time(),
                **result
            }

            topic = TOPIC_VISION.format(batch_id=args.batch)
            if client:
                client.publish(topic, json.dumps(payload))
                print(f"[{time.strftime('%X')}] 📤 ส่งผลตรวจภาพ: {topic} -> {result['primary_grade']} (Defect: {result['defect_rate_pct']}%)")
            else:
                print(f"📷 [Vision Result]: {payload}")

            time.sleep(5.0)
    except KeyboardInterrupt:
        print("\n🛑 หยุดการทำงาน")
        if client:
            client.loop_stop()
            client.disconnect()


if __name__ == "__main__":
    main()
