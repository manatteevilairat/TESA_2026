"""
shared/mock_generator.py
สคริปต์จำลองการส่งข้อมูล (Mock Generator) เสมือนจริงจากทั้ง ESP32 และ Raspberry Pi 5
สามารถรันส่งเข้า MQTT Broker หรือรันแบบ Standalone Print เพื่อทดสอบระบบได้ทันที
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
import random
import json
import argparse
from shared.schemas import SensorData, VisionData, DefectCounts

MQTT_BROKER_DEFAULT = "localhost"
MQTT_PORT_DEFAULT = 1883
TOPIC_SENSOR = "tgr2026/coffee/{batch_id}/sensing"
TOPIC_VISION = "tgr2026/coffee/{batch_id}/vision"


def generate_mock_sensor(batch_id: str) -> SensorData:
    """จำลองข้อมูลเซ็นเซอร์ความชื้นและอุณหภูมิจาก ESP32"""
    # จำลองความชื้นกาแฟระหว่าง 10.5% - 13.5% (มาตรฐานกาแฟแห้ง)
    moisture = round(random.uniform(10.5, 13.5), 1)
    temp = round(random.uniform(27.0, 34.0), 1)
    humidity = round(random.uniform(55.0, 75.0), 1)
    
    status = "DRYING_NORMAL"
    if moisture > 12.5:
        status = "MOISTURE_HIGH"
    elif moisture < 11.0:
        status = "DRYING_COMPLETE"

    return SensorData(
        device_id="esp32_sensing_01",
        batch_id=batch_id,
        timestamp=time.time(),
        moisture_pct=moisture,
        ambient_temp_c=temp,
        ambient_humidity_pct=humidity,
        status=status,
    )


def generate_mock_vision(batch_id: str) -> VisionData:
    """จำลองผลการตรวจจับภาพเมล็ดกาแฟจาก Raspberry Pi 5"""
    sample_count = 100
    black_beans = random.randint(0, 3)
    sour_beans = random.randint(0, 2)
    mold_beans = random.randint(0, 1)
    broken_beans = random.randint(1, 5)
    unripe_beans = random.randint(0, 2)

    total_defects = black_beans + sour_beans + mold_beans + broken_beans + unripe_beans
    defect_rate = round((total_defects / sample_count) * 100, 1)

    if defect_rate <= 3.0 and mold_beans == 0:
        grade = "FINE_ROBUSTA"
    elif defect_rate <= 6.0:
        grade = "PREMIUM"
    elif defect_rate <= 12.0:
        grade = "COMMERCIAL_GRADE"
    else:
        grade = "REJECT"

    return VisionData(
        device_id="rpi5_vision_01",
        batch_id=batch_id,
        timestamp=time.time(),
        sample_count=sample_count,
        defects=DefectCounts(
            black_beans=black_beans,
            sour_beans=sour_beans,
            mold_beans=mold_beans,
            broken_beans=broken_beans,
            unripe_beans=unripe_beans,
        ),
        defect_rate_pct=defect_rate,
        primary_grade=grade,
    )


def run_generator(batch_id: str, interval: float = 3.0, broker: str = MQTT_BROKER_DEFAULT, dry_run: bool = False):
    print(f"🚀 เริ่มต้นการจำลองข้อมูลสำหรับ Batch: {batch_id}")
    client = None

    if not dry_run:
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mock_generator")
            client.connect(broker, MQTT_PORT_DEFAULT, 60)
            client.loop_start()
            print(f"✅ เชื่อมต่อ MQTT Broker สำเร็จที่ {broker}:{MQTT_PORT_DEFAULT}")
        except Exception as e:
            print(f"⚠️ ไม่สามารถต่อ MQTT Broker ({e}) -> สลับเป็นโหมด Dry-run แสดงผลหน้าจอ")
            dry_run = True

    try:
        round_count = 0
        while True:
            round_count += 1
            sensor_data = generate_mock_sensor(batch_id)
            vision_data = generate_mock_vision(batch_id)

            sensor_payload = sensor_data.model_dump_json(indent=2)
            vision_payload = vision_data.model_dump_json(indent=2)

            if dry_run or client is None:
                print(f"\n--- [รอบที่ {round_count}] ข้อมูลจำลอง ---")
                print(f"📡 [ESP32 Sensing]: ความชื้น = {sensor_data.moisture_pct}%, อุณหภูมิ = {sensor_data.ambient_temp_c}°C, สถานะ = {sensor_data.status}")
                print(f"📷 [RPi 5 Vision ]: เกรด = {vision_data.primary_grade}, Defect Rate = {vision_data.defect_rate_pct}%, รา = {vision_data.defects.mold_beans} เมล็ด")
            else:
                s_topic = TOPIC_SENSOR.format(batch_id=batch_id)
                v_topic = TOPIC_VISION.format(batch_id=batch_id)
                client.publish(s_topic, sensor_payload)
                client.publish(v_topic, vision_payload)
                print(f"[{time.strftime('%X')}] 📤 ส่งข้อมูล MQTT: {s_topic} และ {v_topic}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 หยุดการจำลองข้อมูล")
        if client:
            client.loop_stop()
            client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Data Generator สำหรับ TGR2026")
    parser.add_argument("--batch", type=str, default="CPN-2026-B001", help="รหัส Batch กาแฟ")
    parser.add_argument("--interval", type=float, default=2.5, help="ความถี่ในการส่งข้อมูล (วินาที)")
    parser.add_argument("--broker", type=str, default="localhost", help="IP หรือ Hostname ของ MQTT Broker")
    parser.add_argument("--dry-run", action="store_true", help="รันแบบไม่ส่ง MQTT (แสดงผลหน้าจออย่างเดียว)")
    args = parser.parse_args()

    run_generator(batch_id=args.batch, interval=args.interval, broker=args.broker, dry_run=args.dry_run)
