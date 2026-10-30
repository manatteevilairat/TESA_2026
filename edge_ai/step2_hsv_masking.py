"""
edge_ai/step2_hsv_masking.py
ก้าวที่ 2: การแยกสีผลผลิตด้วย HSV Color Space & Color Masking
หัวข้อ:
1. การแปลงภาพจาก BGR เป็น HSV ด้วย cv2.cvtColor()
2. การสร้างแถบช่วงสี (Lower & Upper Bounds)
3. การสกัดเฉพาะสีที่ต้องการด้วย cv2.inRange() ได้ภาพ Mask (ขาว-ดำ)
"""

import cv2
import numpy as np
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
INPUT_IMAGE = CURRENT_DIR / "my_first_beans.jpg"

print("=" * 60)
print("🎓 ก้าวที่ 2: การแยกสีผลผลิตด้วย HSV (Color Masking)")
print("=" * 60)

# 1. โหลดภาพจากก้าวที่ 1 เข้ามา
if not INPUT_IMAGE.exists():
    print("❌ ไม่พบไฟล์ my_first_beans.jpg กรุณารัน step1_intro.py ก่อนครับ")
    exit(1)

image_bgr = cv2.imread(str(INPUT_IMAGE))

# 2. แปลงภาพจากระบบสี BGR เป็น HSV
image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
print("1. แปลงภาพ BGR -> HSV สำเร็จ!")

# -------------------------------------------------------------
# 3. กำหนดช่วงสีที่ต้องการตรวจจับ (Color Boundaries)
# -------------------------------------------------------------
# [Hue (0-179), Saturation (0-255), Value (0-255)]

# ก. สีเขียวของเมล็ดดิบ (Hue อยู่ระหว่าง 35 ถึง 85)
lower_green = np.array([35, 50, 50])
upper_green = np.array([85, 255, 255])

# ข. สีแดงของเมล็ดสุก (ใน HSV สีแดงจะอยู่ที่ 0-10 และ 160-179)
lower_red1 = np.array([0, 70, 50])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 70, 50])
upper_red2 = np.array([179, 255, 255])

# ค. สีดำของเมล็ดเน่า/ตำหนิ (วัดจากความสว่าง Value ต่ำมาก โดยไม่สน Hue)
lower_black = np.array([0, 0, 0])
upper_black = np.array([179, 255, 50])

# -------------------------------------------------------------
# 4. สร้างแผ่นกรองสี (Masking) ด้วย cv2.inRange()
# -------------------------------------------------------------
# ผลลัพธ์ที่ได้จะเป็นภาพขาว-ดำ:
# - สีขาว (255) = พิกเซลที่อยู่ในช่วงสีที่เราตามหา
# - สีดำ (0)   = พิกเซลอื่นๆ ที่ไม่ใช่สีนั้น

# ก. สกัดเมล็ดดิบ (สีเขียว)
mask_green = cv2.inRange(image_hsv, lower_green, upper_green)

# ข. สกัดเมล็ดสุก (สีแดง: ต้องรวม 2 ช่วงเข้าด้วยกัน)
mask_red_part1 = cv2.inRange(image_hsv, lower_red1, upper_red1)
mask_red_part2 = cv2.inRange(image_hsv, lower_red2, upper_red2)
mask_red = cv2.bitwise_or(mask_red_part1, mask_red_part2)

# ค. สกัดเมล็ดดำ (Black bean)
mask_black = cv2.inRange(image_hsv, lower_black, upper_black)

# -------------------------------------------------------------
# 5. นับจำนวนพิกเซลสีขาวเพื่อพิสูจน์ว่าคอมพิวเตอร์เจอจริงไหม
# -------------------------------------------------------------
green_pixels = cv2.countNonZero(mask_green)
red_pixels   = cv2.countNonZero(mask_red)
black_pixels = cv2.countNonZero(mask_black)

print("2. ผลการตรวจจับพื้นที่สี (Pixel Count):")
print(f"   🟢 เมล็ดดิบ (Green Mask) : พบ {green_pixels} พิกเซล")
print(f"   🔴 เมล็ดสุก (Red Mask)   : พบ {red_pixels} พิกเซล")
print(f"   ⚫ เมล็ดดำ (Black Mask)  : พบ {black_pixels} พิกเซล\n")

# -------------------------------------------------------------
# 6. บันทึกภาพ Mask ทั้ง 3 ใบออกมาดู
# -------------------------------------------------------------
cv2.imwrite(str(CURRENT_DIR / "mask_green.jpg"), mask_green)
cv2.imwrite(str(CURRENT_DIR / "mask_red.jpg"), mask_red)
cv2.imwrite(str(CURRENT_DIR / "mask_black.jpg"), mask_black)

# นำภาพ Mask มารวมกับภาพจริงให้เห็นชัดๆ (Bitwise AND)
ripe_isolated = cv2.bitwise_and(image_bgr, image_bgr, mask=mask_red)
cv2.imwrite(str(CURRENT_DIR / "ripe_only.jpg"), ripe_isolated)

print("3. บันทึกภาพผลลัพธ์แยกสีเรียบร้อยแล้ว:")
print(f"   - mask_green.jpg (แผ่นกรองเมล็ดดิบ)")
print(f"   - mask_red.jpg   (แผ่นกรองเมล็ดสุก)")
print(f"   - mask_black.jpg (แผ่นกรองเมล็ดดำ)")
print(f"   - ripe_only.jpg  (ภาพเมล็ดสุกที่ถูกตัดพื้นหลังออกหมดแล้ว)")
print("=" * 60)
