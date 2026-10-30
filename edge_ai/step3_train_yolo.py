"""
edge_ai/step3_train_yolo.py
ก้าวที่ 3: สั่ง Train โมเดล YOLOv8n และ Export เป็น ONNX สำหรับ Raspberry Pi 5
หัวข้อ:
1. การโหลด Pre-trained Weights (YOLOv8n ขนาดจิ๋ว 6 MB)
2. การสั่ง Train ด้วยไฟล์ data.yaml
3. การแปลงโมเดล (Export) เป็นฟอร์แมต .onnx เพื่อนำไปรันบน CPU RPi 5
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = ROOT_DIR / "edge_ai" / "sample_dataset" / "data.yaml"

print("=" * 60)
print("🎓 ก้าวที่ 3: ฝึกสอนโมเดล AI (YOLO Training & ONNX Export)")
print("=" * 60)

# 1. นำเข้าไลบรารี Ultralytics
from ultralytics import YOLO

# 2. โหลดโมเดลตั้งต้น (Base Pre-trained Model)
# เลือกรุ่น 'n' (Nano) ซึ่งเป็นรุ่นที่เล็กและเร็วที่สุด เหมาะกับ CPU ของ Raspberry Pi 5
print("1. กำลังโหลด Base Model: yolov8n.pt (~6.2 MB)...")
model = YOLO("yolov8n.pt")

# 3. สั่ง Train โมเดล
# พารามิเตอร์สำคัญ:
# - data: path ของไฟล์ data.yaml
# - epochs: จำนวนรอบการเรียนรู้ (ในการแข่งจริงใช้ 30-50 รอบ แต่ที่นี่ลอง 1 รอบเพื่อดูขั้นตอน)
# - imgsz: ขนาดภาพที่ย่อส่งเข้าโมเดล (มาตรฐานคือ 640)
# - device: 'mps' (GPU ของ Mac) หรือ 'cpu'
print("\n2. เริ่มต้นกระบวนการ Train (Fine-tuning)...")
results = model.train(
    data=str(DATA_YAML),
    epochs=1,          # รอบการทดสอบ
    imgsz=320,         # ขนาดภาพย่อเพื่อความรวดเร็ว
    batch=1,
    device="cpu",      # รันบน CPU จำลองสภาพ RPi 5
    project="edge_ai/runs",
    name="coffee_yolo",
    exist_ok=True
)

print("\n3. การ Train เสร็จสมบูรณ์! ผลลัพธ์และกราฟจะถูกบันทึกไว้ที่ edge_ai/runs/coffee_yolo/")

# 4. Export โมเดลเป็น .onnx (ขั้นตอนสำคัญที่สุดสำหรับ Raspberry Pi 5)
# ทำไมต้องแปลงเป็น ONNX?
# เพราะไฟล์ PyTorch (.pt) เดิมจะกินแรมเยอะและรันบน CPU ช้า
# เมื่อแปลงเป็น ONNX จะตัด Overhead ของ Python ออก ทำให้รันบน CPU RPi 5 ได้ลื่นไหลขึ้น 2-3 เท่า!
print("\n4. กำลังแปลงโมเดล (Export) เป็น .onnx สำหรับนำไปเสียบบน RPi 5...")
onnx_path = model.export(format="onnx", imgsz=320, dynamic=False)

print(f"\n🎉 สำเร็จแล้ว! คุณได้ไฟล์โมเดล AI สำหรับนำไปใช้บน Raspberry Pi 5:")
print(f"   📁 {onnx_path}")
print("=" * 60)
