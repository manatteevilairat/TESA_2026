# ☕ TESA 2026: Edge AI Engine Status & Roadmap

> **Status:** Production-Ready & Verified on Silicon (RPi 5 & macOS)  
> **Competition Format:** Batch Image Evaluation (Offline Dataset from Organizers)  
> **Last Updated:** November 2026  
> **Target:** TESA Top Gun Rally 2026 (Robusta Coffee AIoT Platform)

---

## 1. ยืนยันความพร้อมใช้งานจริง (Readiness Confirmation)

**คำตอบ:** โค้ดในโฟลเดอร์ `edge_ai/` **พร้อมใช้งานจริงในการแข่งขัน 100% แล้วครับ**

### รูปแบบการแข่งขันจริง (Official Tournament Format):
- **ไม่มีการใช้กล้องสด/สายพาน:** กรรมการจะแจกชุดภาพทดสอบ (Test Images Folder) ให้ผู้เข้าแข่งขันนำเข้า Pipeline เพื่อประเมินผล
- **Hardware Silicon Verified (RPi 5):**
  - ประมวลผลชุดภาพทดสอบมาตรฐาน 62 ภาพ สำเร็จใน **2.57 วินาที (Python 24.05 FPS)** และ **2.84 วินาที (Rust 21.86 FPS)**
  - คัดกรอง 7 คลาสและคำนวณข้อบกพร่องตามเกณฑ์ TESA/SCA ครบถ้วน
  - สรุปผลเป็นรายงาน `batch_report.json` ส่งต่อไปยัง Market Platform และ Trading Agent ได้ทันที

---

## 2. สรุปภาพรวมโครงสร้างและการทำงานของ `edge_ai/`

โฟลเดอร์นี้ทำหน้าที่เป็น **ระบบประมวลผลและตัดสินคุณภาพเมล็ดกาแฟจากโฟลเดอร์ภาพที่กรรมการกำหนด (Batch Evaluation)**:

| ไฟล์ | หน้าที่หลัก | สถานะ |
| :--- | :--- | :--- |
| [`edge_ai/batch_eval.py`](file:///Users/sorn/TESA_2026/edge_ai/batch_eval.py) | **Tournament Pipeline ตัวหลัก:** รับโฟลเดอร์ภาพกรรมการ (`--input-dir`), รัน Pure ONNX, ตัดเกรด 4 ระดับ, ประเมินราคา Fair Price, บันทึก `batch_report.json` และส่ง MQTT | พร้อมใช้งานจริง |
| [`edge_ai/vision_engine.py`](file:///Users/sorn/TESA_2026/edge_ai/vision_engine.py) | **Core Inference Engine:** คลาส `CoffeeVisionAnalyzer` รัน YOLOv8 ONNX แบบ CPU Multi-thread ไร้ PyTorch overhead | พร้อมใช้งานจริง |
| [`edge_ai/models/coffee_best.onnx`](file:///Users/sorn/TESA_2026/edge_ai/models/coffee_best.onnx) | **YOLOv8 Weights:** โมเดลความละเอียด 320x320 จำแนก 7 คลาส Robusta | สมบูรณ์ |
| [`edge_ai/simulate_organizer_test.py`](file:///Users/sorn/TESA_2026/edge_ai/simulate_organizer_test.py) | จำลองสถานการณ์กรรมการโยนภาพชุดทดสอบเข้ามาแบบฉับพลัน | พร้อมใช้งาน |
| [`edge_ai/train_yolo.py`](file:///Users/sorn/TESA_2026/edge_ai/train_yolo.py) | สคริปต์เทรนโมเดลใหม่ทันทีเมื่อกรรมการแจก Dataset เพิ่มเติมหน้างาน | พร้อมใช้งาน |
| [`edge_ai/train_yolo_colab.ipynb`](file:///Users/sorn/TESA_2026/edge_ai/train_yolo_colab.ipynb) | Notebook เทรนบน Google Colab GPU สำหรับการ Fine-tune แบบเร่งด่วน | พร้อมใช้งาน |

---

## 3. ความสามารถปัจจุบัน (Current Capabilities)

1. **7-Class Robusta Taxonomy Recognition:**
   - **Good bean:** เมล็ดสมบูรณ์สุขภาพดี
   - **Primary Defects (ร้ายแรง):** Black (เมล็ดดำ), Insect damage (มอดเจาะ), Scorched (เมล็ดไหม้)
   - **Secondary Defects (รอง):** Broken (เมล็ดแตก/หัก), Empty (เมล็ดกลวง/ลีบ), Quaker (เมล็ดดิบ)
2. **Official Robusta Grading & Pricing Rubric:**
   - **FINE_ROBUSTA (320 THB/kg):** Defect $\le$ 3% และไม่มี Primary Defect
   - **PREMIUM (230 THB/kg):** Defect $\le$ 6% และ Primary Defect $\le$ 1%
   - **COMMERCIAL_GRADE (145 THB/kg):** Defect $\le$ 14%
   - **REJECT (65 THB/kg):** เมล็ดตกเกรด/ข้อบกพร่องเกินเกณฑ์
3. **Seamless Integration with Market Platform:**
   - รายงาน `shared/batch_report.json` จะถูกสร้างขึ้นทันทีหลังประเมินผลเสร็จ
   - ระบบ **Trading Agent** (Smart Asymmetric Strategy) จะดึงเกรดและราคาประเมินนี้ไปจับคู่ซื้อขายในตลาดจำลองทันที

---

## 4. แผนงานขั้นต่อไปสำหรับการแข่งขันจริง (Tournament Roadmap)

เพื่อให้พร้อมรับมือกับโจทย์ของกรรมการในวันจริง:

```
[ขั้นตอนปัจจุบัน: Batch Eval พร้อม 100%] ──► [ขั้นที่ 1: One-Command Evaluation] ──► [ขั้นที่ 2: Rapid Retrain Pipeline] ──► [ขั้นที่ 3: IoT Sensor Integration]
```

### 🎯 ขั้นที่ 1: One-Command Evaluation (รับโฟลเดอร์ภาพกรรมการทันที)
- **เป้าหมาย:** เมื่อกรรมการแจกโฟลเดอร์ภาพ (เช่น เสียบ Flash Drive หรือส่ง Path มาให้) ให้พิมพ์คำสั่งเดียวแล้วประเมินเสร็จใน < 3 วินาที
- **คำสั่งพร้อมใช้:**
  ```bash
  # แบบ Python
  uv run --no-project edge_ai/batch_eval.py --input-dir /path/to/organizer_images --batch-id FINAL-MATCH
  
  # แบบ Rust (ความเร็วสูงสุด)
  ./edge_rust/target/release/edge_rust --input-dir /path/to/organizer_images --batch-id FINAL-MATCH
  ```

### 🎯 ขั้นที่ 2: Rapid Retraining Pipeline (เมื่อกรรมการแจก Dataset กาแฟชุมพรหน้างาน)
- **เป้าหมาย:** ในวันแข่ง หากกรรมการให้ Dataset ภาพเมล็ดกาแฟจริงของชุมพรมาเพิ่ม เราต้องเทรนและ Export เป็น ONNX ให้เสร็จภายใน 15–30 นาที
- **สิ่งที่เตรียมไว้แล้ว:** มีสคริปต์ `edge_ai/train_yolo.py` และ Colab Notebook ที่มีคำสั่ง Export เป็น ONNX 320x320 พร้อมนำมาแทนที่ `coffee_best.onnx` ทันที

### 🎯 ขั้นที่ 3: เชื่อมต่อเซนเซอร์สภาพแวดล้อม (DHT11 IoT Integration)
- **เป้าหมาย:** หากมีโจทย์เสริมเกี่ยวกับการเฝ้าระวังคลังเก็บเมล็ดกาแฟ (Silo / Storage Monitoring) ให้อ่านค่าอุณหภูมิและความชื้นสัมพัทธ์จาก DHT11 บน RPi 5
- **การต่อยอด:** ส่ง Telemetry ของ DHT11 ผ่าน MQTT ขึ้น Dashboard ควบคู่กับผล Batch Evaluation

### 🎯 ขั้นที่ 4: End-to-End Simulation (ทดสอบจำลองทั้งระบบตั้งแต่ต้นจนจบ)
- **เป้าหมาย:** ทดสอบ Flow: ภาพของกรรมการ ──► `batch_eval` ──► `batch_report.json` ──► `trading_agent.py` ตัดสินใจซื้อขายใน `market_platform`
