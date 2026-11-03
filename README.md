# ☕ Chumphon Robusta AIoT Platform toward The Next-Gen Market
### TESA Top Gun Rally 2026 (TGR2026) · สจล. วิทยาเขตชุมพรเขตรอุดมศักดิ์

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/Package%20Manager-uv-DE5FE9?logo=astral&logoColor=white)](https://astral.sh/uv)
[![Hardware](https://img.shields.io/badge/Target%20Hardware-Raspberry%20Pi%205-C51A4A?logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Inference Engine](https://img.shields.io/badge/Inference-Pure%20ONNX%20Runtime%20CPU-005CED?logo=onnx&logoColor=white)](https://onnxruntime.ai/)
[![Protocol](https://img.shields.io/badge/Telemetry-MQTT%20Mosquitto-3C5280?logo=eclipsemosquitto&logoColor=white)](https://mosquitto.org/)
[![UI Platform](https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Market API](https://img.shields.io/badge/Market%20API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

แพลตฟอร์ม AIoT ครบวงจรสำหรับยกระดับห่วงโซ่คุณค่ากาแฟโรบัสตาชุมพร เชื่อมโยงตั้งแต่การตรวจวัดสภาพแวดล้อมทางกายภาพ (Track 1: ESP32), การคัดเกรดตำหนิเมล็ดกาแฟด้วย Computer Vision บน Edge Hardware (Track 2: Raspberry Pi 5), ไปจนถึงระบบตลาดซื้อขายอัตโนมัติด้วย AI Trading Agent แบบปิดซองประมูล (Track 3: The Next-Gen Market)

---

## 🗺️ สถาปัตยกรรมระบบรวม (End-to-End System Architecture)

```
[ Track 1 : ESP32 Sensing Node ]          [ Track 2 : Edge AI on RPi 5 ]
   - ความชื้นเมล็ดกาแฟ (%)                    - 7-Class Robusta YOLOv8n ONNX
   - อุณหภูมิ & ความชื้นอากาศ                - Zero-Torch CPU Multi-threading (24 FPS)
          │                                                │
          ▼                                                ▼
   (MQTT Telemetry)                                (MQTT Telemetry)
   tgr2026/coffee/{batch}/sensing                  tgr2026/coffee/{batch}/vision
          │                                                │
          └───────────────────────┬────────────────────────┘
                                  ▼
                    [ Mosquitto MQTT Broker (1883) ]
                                  │
                                  ▼
                   [ Backend Data Fusion Engine ]
                   (shared/live_db.json Storage)
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼                                               ▼
[ Streamlit Web Platform ]                    [ Track 3 : AI Trading Agent ]
 - 👨‍🌾 ผู้ผลิต: ตรวจผลภาพ & เซ็นเซอร์           - กลยุทธ์ประมูลปิดซอง (Blind Bidding)
 - 🛒 ตลาด: รับรองย้อนกลับ (Traceability)      - Smart Asymmetric + Adaptive Learning
 - 🤖 Local SLM: Cupping Notes & ราคาแนะนำ    - เชื่อมต่อ REST API กลาง
```

---

## 🏆 จุดเด่นสำคัญของแต่ละ Track (Key Highlights)

### 🟢 Track 1: ESP32 Sensing Node (`esp32_firmware/`)
* **ฮาร์ดแวร์:** ESP32 เชื่อมต่อ Wi-Fi และส่งข้อมูลผ่าน MQTT JSON Telemetry
* **ฟังก์ชันการทำงาน:** อ่านค่า Analog (ADC), ควบคุม PWM, กรองสัญญาณ และคำนวณสอบเทียบ (Calibration) ความชื้นเมล็ดกาแฟตามมาตรฐานการส่งออก ($10.5\% - 12.5\%$)

### 🟢 Track 2: Edge AI on Raspberry Pi 5 (`edge_ai/`)
* **โมเดล AI:** YOLOv8n fine-tuned บน 7 คลาสทางการของ สจล. ชุมพร (`Good bean`, `Black`, `Broken`, `Empty`, `Insect damage`, `Quaker`, `Scorched`)
* **Zero-Torch Pure ONNX Runtime:** ออกแบบให้รันตรงบน CPU Multi-threading (4 Threads) โดยไม่ต้องติดตั้ง PyTorch หรือ CUDA ให้หนักเครื่อง
* **สคริปต์ Batch Evaluation (`batch_eval.py`):** ประมวลผลโฟลเดอร์ภาพ Private Test Set ของกรรมการรวดเดียว ตีกรอบ นับเมล็ด คัดแยก Primary vs Secondary Defects และตัดเกรดกาแฟอัตโนมัติ (`Fine Robusta`, `Premium`, `Commercial`, `Reject`)
* **1-Click Remote Deployment (`deploy_to_rpi.py`):** สั่งยิงโมเดลและโค้ดเข้า Raspberry Pi 5 ผ่านเครือข่ายภายใน 2 วินาที

### 🟢 Track 3: The Next-Gen Market & AI Agent (`market_platform/`)
* **สถาปัตยกรรม Agent (ดู $\rightarrow$ คิด $\rightarrow$ ทำ):** ดึงข้อมูลความต้องการของผู้ซื้อในตลาด (Specialty Roaster, Commercial Factory, Instant Powder Processor) ผ่าน REST API
* **กลยุทธ์ประมูลแชมป์ (Smart Asymmetric + Adaptive):**
  * *กาแฟเกรดต่ำ (Reject/Off-grade):* งบโรงงาน Instant มีสูง ดันมาร์จิ้นได้ถึง $+25\% - 35\%$ เพื่อกอบโกยคะแนน Value Surplus
  * *กาแฟพรีเมียม (Fine Robusta):* เพดานงบโรงคั่วแคบ ตั้งราคาแบบรัดกุม $+10\% - 12\%$ เพื่อการันตีชนะประมูล
  * *Adaptive Learning:* ปรับลดราคาเมื่อโดนคู่แข่งตัดราคา และขยับขึ้นเมื่อชนะประมูล
* **Interactive Simulator:** มีแท็บซ้อมแข่งบน Streamlit Dashboard และสคริปต์ Benchmark แข่งจำลอง 150 แมตช์

---

## ⚡ ผลการทดสอบประสิทธิภาพจริง (Hardware & Benchmark Verification)

### 1. ความเร็วการรันโมเดล AI บน CPU ของ Raspberry Pi (ทดสอบกับภาพจริง 62 ภาพ)

| รายการทดสอบ | Raspberry Pi 4 (เดิม) | **Raspberry Pi 5 (ชิปใหม่)** | ผลการอัปเกรด |
| :--- | :---: | :---: | :---: |
| **ความเร็วเฉลี่ย (FPS)** | 6.63 FPS | **24.05 FPS** | 🚀 **เร็วขึ้น 3.6 เท่า** |
| **ความหน่วงต่อเฟรม (Latency)** | 150.74 ms | **41.58 ms** | ⏱️ ลดเวลาลงเหลือ 1 ใน 4 |
| **เวลาตรวจหมดทั้ง 62 รูป** | ~9.35 วินาที | **~2.57 วินาที** | 💨 Real-time บน CPU |
| **การใช้ทรัพยากร** | CPU 4 คอร์ | CPU 4 คอร์ | ไม่มี Torch/CUDA Bloat |

### 2. ผลการทดสอบกลยุทธ์ AI Agent ในตลาดประมูลจำลอง (Tournament 150 แมตช์)

| กลยุทธ์ (Bidding Strategy) | อัตราการชนะ (Win Rate) | กำไรเฉลี่ยต่อแมตช์ | คะแนน Surplus รวม |
| :--- | :---: | :---: | :---: |
| 1. Fixed Conservative (กำไร 8% คงที่) | 100.0% | 24.0% / match | 3,594.6% |
| 2. Fixed Aggressive (กำไร 24% คงที่) | 64.4% | 36.7% / match | 5,511.5% |
| 3. Adaptive Feedback (ปรับตามผลชนะ/แพ้) | 78.2% | 38.5% / match | 5,775.0% |
| **4. Smart Asymmetric (สูตรแชมป์ของเรา)** | **91.5%** | **42.8% / match** | **6,420.0% 🏆** |

---

## 📁 โครงสร้างไฟล์ในโปรเจกต์ (Clean Repository Structure)

```text
TESA_2026/
├── check_competition_readiness.py  # สคริปต์ตรวจความพร้อมทั้งระบบในคำสั่งเดียว
├── mosquitto.conf                   # ค่าคอนฟิก MQTT Broker สำหรับรับส่งข้อมูลในวง LAN
├── pyproject.toml                   # รายการ Dependencies หลักของโปรเจกต์
├── yolov8n.pt                       # สถาปัตยกรรมตั้งต้นสำหรับ Fine-tune หน้างาน
├── SYSTEM_OVERVIEW.md               # รายละเอียดเชิงลึกของระบบและข้อกำหนดทางเทคนิค
├── ULTIMATE_PREPARATION_CHECKLIST.md # เช็คลิสต์ตรวจสอบอุปกรณ์และการเตรียมความพร้อม
│
├── 📁 edge_ai/                      # โมดูล Edge AI สำหรับ Raspberry Pi
│   ├── batch_eval.py                # Pipeline สแกนตรวจภาพทั้งโฟลเดอร์ + ส่ง MQTT
│   ├── train_yolo.py                # สคริปต์เทรนโมเดลด่วนบน Mac/PC + Auto-export ONNX
│   ├── deploy_to_rpi.py             # เครื่องมือส่งโมเดลเข้าบอร์ด Pi ข้าม Wi-Fi ใน 2 วินาที
│   ├── vision_engine.py             # เอนจินประมวลผลภาพ 7 คลาสและคิดเกรด SCA
│   └── models/coffee_best.onnx      # โมเดล ONNX น้ำหนักเบาสำหรับรันบน Pi
│
├── 📁 market_platform/              # โมดูลตลาด Next-Gen Market และ Web Platform
│   ├── app.py                       # แดชบอร์ดหลัก 4 แท็บ (Streamlit)
│   ├── backend_service.py           # บริการ Data Fusion ดักฟัง MQTT บันทึกลง live_db
│   ├── trading_agent.py             # ตัวบอท AI แข่งขันประมูลปิดซองในตลาด
│   ├── strategy_benchmark.py        # สคริปต์รันทดสอบทัวร์นาเมนต์กลยุทธ์ 150 แมตช์
│   ├── mock_market_api.py           # เซิร์ฟเวอร์จำลองตลาดแข่งขัน REST API (FastAPI)
│   └── slm_evaluator.py             # เอนจิน SLM วิเคราะห์ Cupping Notes & ราคา
│
├── 📁 shared/                       # สัญญาข้อมูลกลาง (Data Contract)
│   ├── schemas.py                   # Pydantic Schemas กลางสำหรับทุก Node
│   ├── config.py                    # ตรวจจับ IP ในวง LAN อัตโนมัติและจัดการค่าคอนฟิก
│   └── live_db.json                 # ฐานข้อมูล JSON กลางสำหรับแลกเปลี่ยนข้อมูล
│
└── 📁 esp32_firmware/               # ซอร์สโค้ดเฟิร์มแวร์ ESP32 (PlatformIO)
    ├── platformio.ini               # การตั้งค่าบอร์ดและไลบรารี
    └── src/main.cpp                 # โค้ดอ่านเซ็นเซอร์ กรองสัญญาณ และเชื่อมต่อ MQTT
```

---

## 🚀 เริ่มต้นใช้งานอย่างรวดเร็ว (Quick Start)

### 1. ติดตั้งสภาพแวดล้อม (Environment Setup)
จัดการโปรเจกต์ด้วย [Astral `uv`](https://astral.sh/uv):
```bash
# โคลนโปรเจกต์
git clone https://github.com/manatteevilairat/TESA_2026.git
cd TESA_2026

# ซิงค์ Dependencies อัตโนมัติ
uv sync
```

### 2. ตรวจสอบความพร้อมของระบบทั้งหมด (1-Click Diagnostics)
```bash
uv run python check_competition_readiness.py
```

### 3. เปิดใช้งานแดชบอร์ดหลัก (Streamlit Platform)
```bash
# Terminal 1: เปิดบริการเชื่อมต่อข้อมูล MQTT Backend
uv run python market_platform/backend_service.py

# Terminal 2: เปิดหน้าเว็บแดชบอร์ด
uv run streamlit run market_platform/app.py
```
*เข้าใช้งานผ่านเบราว์เซอร์ที่ `http://localhost:8501`*

### 4. รัน Edge AI Batch Inspection บน Raspberry Pi 5
```bash
# บนบอร์ด Raspberry Pi 5
cd ~/TESA_2026
uv run --no-project edge_ai/batch_eval.py \
  --input-dir edge_ai/dataset/test/images \
  --batch-id CPN-RPI5-CHAMPION \
  --broker <IP_เครื่อง_MAC> \
  --publish-mqtt
```

### 5. ซ้อมแข่งขัน AI Trading Agent (Track 3)
```bash
# Terminal 1: เปิดเซิร์ฟเวอร์ตลาดจำลอง
uv run python market_platform/mock_market_api.py

# Terminal 2: ปล่อย AI Agent ลงแข่งประมูล 5 รอบด้วยกลยุทธ์ Asymmetric
uv run python market_platform/trading_agent.py --strategy asymmetric --rounds 5
```

---

## 👥 ผู้พัฒนา (Team Members)
* **มนัตถ์ธี ไวไลรัตน์ (Manattee Vilairat)** — มหาวิทยาลัยสงขลานครินทร์ (PSU) · `6810110275@psu.ac.th`
* โครงการแข่งขันระดมสมองระบบสมองกลฝังตัว **TESA Top Gun Rally ครั้งที่ 20 (2026)**
