# ☕ TESA Top Gun Rally 2026 (TGR2026) Project Starter
**แพลตฟอร์ม AIoT เพื่อขับเคลื่อนกาแฟโรบัสตาชุมพรสู่ตลาดยุคใหม่**  
*(Chumphon Robusta AIoT Platform Toward The Next-Gen Market)*

โปรเจกต์นี้จัดการด้วย **Astral `uv`** (Python 3.12) โดยแบ่งโค้ดออกเป็น 4 ส่วนหลักตามสถาปัตยกรรมระบบ:

---

## 📂 โครงสร้างโปรเจกต์ (Project Structure)

```text
TESA_2026/
├── shared/                     # สัญญาข้อมูลกลาง (Data Contract) & ตัวจำลองข้อมูล
│   ├── schemas.py              # Pydantic models (SensorData, VisionData, SLMEvaluation)
│   └── mock_generator.py       # สคริปต์จำลอง ESP32 และ RPi 5 ส่งข้อมูลเข้า MQTT
├── market_platform/            # แพลตฟอร์มตลาด & บริการวิเคราะห์ด้วย Local SLM
│   ├── slm_evaluator.py        # เชื่อมต่อ Ollama (qwen2.5:1.5b) ประเมินเกรดและราคา
│   └── app.py                  # Next-Gen Market Dashboard (Streamlit)
├── edge_ai/                    # โค้ดกล้องและโมเดลสำหรับ Raspberry Pi 5
│   └── rpi_vision_pipeline.py  # Pipeline ตรวจนับตำหนิเมล็ดกาแฟบน CPU RPi 5
├── esp32_firmware/             # เฟิร์มแวร์ C/C++ สำหรับ ESP32 (PlatformIO)
│   ├── platformio.ini          # ค่าคอนฟิกบอร์ดและ Library (PubSubClient, ArduinoJson)
│   └── src/main.cpp            # โค้ดอ่านเซ็นเซอร์, กรองสัญญาณ, ส่ง MQTT
├── pyproject.toml              # การจัดการ Dependencies ด้วย uv
├── SYSTEM_OVERVIEW.md          # สรุปภาพรวมและแผนภาพสถาปัตยกรรมระบบ
└── ULTIMATE_PREPARATION_CHECKLIST.md # เช็กลิสต์เตรียมตัวระดับ Hardcore 6 มิติ
```

---

## 🚀 วิธีการทดสอบรันแต่ละส่วนด้วย `uv`

### 1. ทดสอบรันหน้าเว็บตลาด Next-Gen Market Platform (Streamlit)
```bash
uv run streamlit run market_platform/app.py
```
*เปิดเบราว์เซอร์ไปที่ `http://localhost:8501` เพื่อดูหน้าจอเกษตรกร (Supplier), ตลาดซื้อขาย (Buyer) และ System Telemetry*

### 2. ทดสอบ Local SLM Evaluator (Ollama qwen2.5:1.5b)
```bash
uv run python -m market_platform.slm_evaluator
```
*(หากยังไม่ได้เปิด Ollama ระบบจะสลับไปใช้ Heuristic Fallback อัตโนมัติ ทำให้ทดสอบได้ต่อเนื่องไม่สะดุด)*

### 3. เปิดบริการรับส่งและผสานข้อมูล (Backend Data Fusion Service)
```bash
uv run python -m market_platform.backend_service
```
*บริการนี้จะดักฟังข้อมูลเซ็นเซอร์และภาพจาก MQTT Broker แล้วผสานเข้าด้วยกันแบบ Real-time*

### 4. รันสคริปต์จำลองการส่งข้อมูล (Mock Data Generator)
```bash
# ส่งข้อมูลจำลองของ ESP32 และ RPi 5 เข้าสู่ MQTT Broker จริงทุก 3 วินาที
uv run python -m shared.mock_generator --broker localhost --interval 3.0 --batch CPN-2026-B002
```

### 5. ทดสอบ Pipeline บน Raspberry Pi 5
```bash
uv run python -m edge_ai.rpi_vision_pipeline --dry-run
```
