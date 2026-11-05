# 🏆 Ultimate Pre-Camp Preparation Checklist: TESA Top Gun Rally 2026
**"เตรียมพร้อมแบบสุดทางเพื่อชัยชนะ: Zero to Ready ก่อนถึงค่ายชุมพร"**

เอกสารนี้รวบรวมทุกมิติการเตรียมตัว ทั้งเชิงเทคนิค (Code Boilerplate, Data Contract, Offline Cache), ฮาร์ดแวร์ (Network Fallback), และยุทธวิธีหน้างาน (Hackathon Tactics) เพื่อให้ทีมมีความพร้อม 80-90% ก่อนวันแข่งจริง

---

## 📌 สารบัญยุทธศาสตร์ 6 มิติ
1. [มิติที่ 1: สัญญาข้อมูลกลาง (Data Contract & System Protocols)](#1-data-contract--system-protocols)
2. [มิติที่ 2: งานฝั่ง Embedded & Sensor (ESP32)](#2-embedded--sensor-esp32)
3. [มิติที่ 3: งานฝั่ง Edge AI & Computer Vision (Raspberry Pi 5)](#3-edge-ai--computer-vision-raspberry-pi-5)
4. [มิติที่ 4: งานฝั่ง Intelligence & Market (Local SLM + Streamlit/FastAPI)](#4-intelligence--market-local-slm--platform)
5. [มิติที่ 5: การเอาตัวรอดแบบ Offline 100% & เครือข่าย (DevOps & Networking)](#5-offline-resilience--networking)
6. [มิติที่ 6: ยุทธวิธีการแข่งขันและการนำเสนอ (Competition Tactics & Demo)](#6-competition-tactics--presentation)

---

## 1. Data Contract & System Protocols
> **เป้าหมาย:** ทุกคนเขียนโค้ดได้ทันทีโดยไม่ต้องรอฮาร์ดแวร์จริง ด้วยการล็อกโครงสร้างข้อมูลและสร้างตัวจำลองข้อมูล (Mock Generators)

- [ ] **กำหนด MQTT Topics ให้ชัดเจนทั้งระบบ:**
  * `tgr2026/coffee/{batch_id}/sensing` (ข้อมูลเซ็นเซอร์จาก ESP32)
  * `tgr2026/coffee/{batch_id}/vision` (ข้อมูลภาพคัดเกรดจาก RPi 5)
  * `tgr2026/coffee/{batch_id}/market` (คำสั่งซื้อขาย / อัปเดตราคา)
  * `tgr2026/system/heartbeat` (สถานะอุปกรณ์ออนไลน์)

- [ ] **ล็อกโครงสร้าง JSON Payload (Data Schema):**
  * **Payload จาก ESP32 (Sensing):**
    ```json
    {
      "device_id": "esp32_node_01",
      "batch_id": "CPN-2026-B001",
      "timestamp": 1731657600,
      "moisture_pct": 11.8,
      "ambient_temp_c": 28.5,
      "ambient_humidity_pct": 65.2,
      "status": "DRYING_NORMAL"
    }
    ```
  * **Payload จาก Raspberry Pi 5 (Vision):**
    ```json
    {
      "device_id": "rpi5_vision_01",
      "batch_id": "CPN-2026-B001",
      "timestamp": 1731657605,
      "sample_count": 50,
      "defects": {
        "black_beans": 1,
        "sour_beans": 0,
        "mold_beans": 0,
        "broken_beans": 2
      },
      "defect_rate_pct": 6.0,
      "primary_grade": "GRADE_1",
      "image_annotated_url": "/static/annotated/B001.jpg"
    }
    ```

- [ ] **เขียนสคริปต์ Mock Data Generators (Python):**
  * สคริปต์ยิงข้อมูลจำลองเข้า MQTT ทุกๆ 2 วินาที เพื่อให้ฝั่ง Backend/Dashboard เขียนโค้ดเชื่อมต่อได้ตั้งแต่วันนี้

---

## 2. Embedded & Sensor (ESP32)
> **เป้าหมาย:** โค้ดบน ESP32 ต้องเสถียร ไม่แฮงก์ ไม่หลุด Wi-Fi และอ่านค่าแม่นยำ

- [ ] **สร้าง PlatformIO Boilerplate Template:**
  * ใช้ **FreeRTOS Tasks** แยกการทำงาน:
    * Task 1: อ่านเซ็นเซอร์และประมวลผล (Core 1)
    * Task 2: จัดการ Wi-Fi, MQTT และส่งข้อมูล (Core 0)
  * มีระบบ **Watchdog Timer (WDT)** และ **Auto-reconnect Wi-Fi/MQTT** แบบไม่บล็อกการทำงาน (Non-blocking loop)
  * มีระบบ **NTP Time Sync** ดึงเวลาสากลมาแนบใน Timestamp

- [ ] **เตรียม Library & Calibration Filter:**
  * อัลกอริทึมกรองสัญญาณ: **Moving Average** หรือ **Median Filter** เพื่อตัดค่าแกว่ง (Spike) ของเซ็นเซอร์
  * ฟังก์ชันแปลงค่า ADC เป็นค่าความชื้นสัมพัทธ์ (Linear Interpolation / Polynomial Calibration)
  * ลง Library สำหรับเซ็นเซอร์ที่พบบ่อยในงานเกษตรไว้ล่วงหน้า:
    * เซ็นเซอร์อุณหภูมิ/ความชื้น: `DHT22`, `SHT30/31`, `BME280`
    * เซ็นเซอร์วัดความชื้นดิน/เมล็ดแบบ Capacitive / Resistive
    * เซ็นเซอร์น้ำหนัก: `HX711` (Load cell)
    * เซ็นเซอร์สี: `TCS34725`

- [ ] **เตรียมฮาร์ดแวร์อะไหล่สำรอง:**
  * บอร์ด ESP32 สำรอง 2-3 บอร์ด (เช็กพอร์ต Micro-USB หรือ Type-C ให้แน่ใจ)
  * Breadboard, ชุดสาย Jumper (ช-ช, ช-ญ, ญ-ญ) 100+ เส้น
  * ตัวต้านทาน 4.7kΩ / 10kΩ (สำหรับ Pull-up I2C/OneWire) และ Capacitor 100uF (กรองไฟเลี้ยง)

---

## 3. Edge AI & Computer Vision (Raspberry Pi 5)
> **เป้าหมาย:** รันโมเดลคัดแยกเมล็ดกาแฟบน CPU RPi 5 ได้เฟรมเรต $\ge$ 15-20 FPS โดยไม่ต้องมี AI HAT+

- [ ] **เตรียม Pipeline เทรนโมเดลบน Google Colab ล่วงหน้า:**
  * ทำ Template Jupyter Notebook สำหรับเทรน **YOLOv8n (Nano)** หรือ **YOLO11n**:
    * สคริปต์ดาวน์โหลด Dataset จาก Roboflow (ค้นหาคีย์เวิร์ด: `coffee-beans-defect`, `coffee-cherry-ripeness`)
    * คำสั่งเทรน 50-100 Epochs ด้วย GPU T4 ฟรี (ใช้เวลาไม่เกิน 15 นาที)
    * คำสั่ง Export ออกเป็น **ONNX** และ **TFLite (INT8 Quantization)**

- [ ] **เตรียม Inference Script บน Raspberry Pi 5 (Python):**
  * เขียนสคริปต์กล้อง Multi-threaded (แยก Thread อ่านภาพจากกล้อง กับ Thread ทำนายผล AI เพื่อลดอาการ Latency)
  * ใช้ **ONNX Runtime (with CPUExecutionProvider)** รันโมเดล `.onnx` แบบเปิด Multi-threads (`session_options.intra_op_num_threads = 4`)
  * เขียนระบบวาด Bounding Box + นับจำนวนประเภทข้อบกพร่อง (Defect Counter) แบบอัตโนมัติ

- [ ] **เตรียม Fallback: Classical Computer Vision (OpenCV):**
  * สคริปต์คัดแยกเมล็ดแบบไม่ต้องใช้ Deep Learning (เผื่อโจทย์หน้างานมีเวลาน้อยมาก):
    * แปลง Color Space เป็น **HSV / LAB** เพื่อคัดแยกเมล็ดเขียว (ดิบ), แดง (สุก), ดำ (เน่า)
    * ฟังก์ชัน `cv2.findContours` + `cv2.contourArea` สำหรับคัดแยกเมล็ดแตกหักหรือวัดขนาดเมล็ด (Bean Size Grading)

- [ ] **เตรียมสภาพแวดล้อมบน RPi 5:**
  * Flash OS 64-bit ใส่ MicroSD Card ความเร็วสูง (A2 / V30)
  * ติดตั้ง `opencv-python`, `onnxruntime`, `paho-mqtt`, `picamera2` พร้อมทดสอบเปิดกล้องสำเร็จ

---

## 4. Intelligence & Market (Local SLM + Platform)
> **เป้าหมาย:** มีหน้าเว็บตลาดที่สวยงาม พร้อมฟีเจอร์ AI สรุปเกรดและราคาที่เรียกปุ๊บตอบปั๊บ 100% ไม่พัง

- [ ] **เตรียม Local SLM Engine (Ollama):**
  * ติดตั้ง Ollama และ Pull โมเดลเก็บไว้ในเครื่อง:
    ```bash
    ollama pull qwen2.5:1.5b
    ```
  * ทดสอบความเร็วในการตอบสนองบนเครื่องโน้ตบุ๊ก (ต้องสร้างข้อความได้ภายใน 2-4 วินาที)

- [ ] **เตรียม Prompt Templates & Structured Outputs (JSON Mode):**
  * ออกแบบ Prompt ให้โมเดลรับข้อมูล (ความชื้น, สถิติเมล็ดเสีย) แล้วบังคับให้โมเดลตอบกลับมาเป็น **Valid JSON** เท่านั้น (ป้องกันโค้ดพังเวลา Parse)
  * ตัวอย่าง Prompt สรุป Cupping & Market Pricing:
    ```python
    prompt = """คุณเป็นผู้เชี่ยวชาญด้านกาแฟโรบัสตาชุมพร
    ข้อมูลผลผลิต:
    - ความชื้น: {moisture}%
    - เปอร์เซ็นต์เมล็ดชำรุด: {defects}%
    จงประเมิน:
    1. เกรดกาแฟ (Specialty / Grade 1 / Commercial)
    2. คำแนะนำในการคั่ว (Light / Medium / Dark Roast)
    3. ราคาแนะนำต่อกิโลกรัม (บาท)
    ตอบเป็นรูปแบบ JSON: {"grade": "...", "roast_recommendation": "...", "suggested_price": 0, "summary": "..."}"""
    ```

- [ ] **เตรียมโครงสร้างเว็บตลาด (Next-Gen Market Platform Boilerplate):**
  * แนะนำใช้ **Streamlit** (พัฒนาเร็วและเสร็จทันภายในเวลาแข่งขัน 4 ชม.):
    * **หน้า 1: Supplier / Farmer View:** อัปโหลด Batch, ดูคะแนนคุณภาพจาก AI, แดชบอร์ดดูกราฟความชื้นย้อนหลัง, กด "เปิดขายในตลาด"
    * **หน้า 2: Buyer / Roaster View:** หน้า Marketplace แสดงรายการกาแฟที่ผ่านการตรวจสอบ (Traceability Card) มีรูปถ่ายยืนยัน พร้อมปุ่ม "สั่งซื้อ / เสนอราคา (Bidding)"
    * **หน้า 3: Live System Integration Monitor:** แดชบอร์ดแสดงสถานะฮาร์ดแวร์แบบ Real-time (ESP32 Online / RPi Camera Active / MQTT Message Counter)

---

## 5. Offline Resilience & Networking (กันตาย 100%)
> **เป้าหมาย:** ระบบต้องทำงานได้โดยไม่ต้องพึ่งพาระบบอินเทอร์เน็ตของสถานที่แข่งขัน

- [ ] **เราเตอร์ Wi-Fi พกพา (Dedicated Wi-Fi 6 Router):**
  * นำเราเตอร์ Wi-Fi ตัวเล็กของทีมไปเอง (ตั้งค่า SSID และ Password ล่วงหน้า)
  * ตั้งค่า Static IP ให้บอร์ด RPi 5 และเครื่องโน้ตบุ๊กหลัก
  * ฝังค่า Wi-Fi นี้ลงในโค้ด ESP32 และ RPi 5 ตั้งแต่วันนี้ (เมื่อถึงหน้างาน เสียบปลั๊กเราเตอร์ ทุกบอร์ดจะเกาะกลุ่มคุยกันได้ทันทีแม้อินเทอร์เน็ตภายนอกจะล่ม)

- [ ] **ดาวน์โหลด Python Wheels & Packages เก็บไว้ Offline:**
  * ป้องกันปัญหา `pip install` ไม่ผ่านหน้างานเนื่องจากเน็ตค่ายตัดหรือล่ม:
    ```bash
    pip download -r requirements.txt -d ./offline_packages
    # เวลาติดตั้งหน้างาน: pip install --no-index --find-links=./offline_packages -r requirements.txt
    ```

- [ ] **Local MQTT Broker:**
  * รัน Mosquitto ในเครื่องคอมพิวเตอร์หลัก หรือเปิดบน Raspberry Pi 5
  * แก้ไข `mosquitto.conf` ให้รองรับ:
    ```conf
    listener 1883
    allow_anonymous true
    ```

- [ ] **สาย LAN สำรอง & สิทธิ์ Direct Access:**
  * ตั้งค่าเครื่องโน้ตบุ๊กให้สามารถเชื่อมต่อ Raspberry Pi 5 ผ่านสาย LAN ตรงด้วย Hostname (เช่น `ssh pi@raspberrypi.local` หรือ Subnet 192.168.137.x)

---

## 6. Competition Tactics & Presentation
> **เป้าหมาย:** แปลงผลงานทางวิศวกรรมให้เป็นคะแนนสูงสุดต่อหน้าคณะกรรมการ

- [ ] **เตรียมสไลด์นำเสนอ (Presentation Deck Template) ล่วงหน้า:**
  * เตรียมโครงสร้างสไลด์ 5–7 หน้าไว้ก่อนแข่ง:
    1. **Cover & Team Intro:** ชื่อทีม และบทบาทสมาชิก
    2. **Problem & Pain Points:** สรุปปัญหาห่วงโซ่คุณค่ากาแฟโรบัสตาชุมพร (อ้างอิงจากโจทย์)
    3. **System Architecture:** แผนภาพสถาปัตยกรรม 4 เลเยอร์ (Sensing $\rightarrow$ Vision $\rightarrow$ MQTT $\rightarrow$ SLM Market)
    4. **Technical Innovations:** ความแม่นยำของโมเดล Vision, การออกแบบ Data Fusion, การใช้ SLM
    5. **Business Impact & Sustainability:** แพลตฟอร์มนี้ช่วยเพิ่มรายได้ให้เกษตรกรและสร้างความโปร่งใสอย่างไร
    6. **Live Demo Walkthrough:** วิดีโอสำรองขั้นตอนการทำงาน

- [ ] **บันทึกวิดีโอ Backup Demo ล่วงหน้า (กฎเหล็ก Demo กันตาย):**
  * คืนวันที่ 20 พ.ย. เมื่อระบบทำงานร่วมกันได้สำเร็จ **ให้อัดคลิปวิดีโอหน้าจอและถ่ายคลิปการทำงานจริงของฮาร์ดแวร์เก็บไว้ในสไลด์ทันที**
  * หากวัน Live Demo เกิดเหตุสุดวิสัย (สายหลุด, เซ็นเซอร์ช็อต, Wi-Fi ดับ) สามารถเปิดคลิปสาธิตให้กรรมการดูได้ทันทีโดยไม่เสียคะแนน

- [ ] **ซ้อมทำ Mock Challenge 4 ชั่วโมง (Dry Run):**
  * นัดทีมจำลองการแข่ง 1 วันเต็ม: เริ่ม 13:00 น. แจกโจทย์สมมุติ $\rightarrow$ บังคับปิดงานและสาธิตในเวลา 17:00 น. เพื่อวัดว่าสมาชิกติดคอขวด (Bottleneck) ที่จุดไหน

---

## 📅 ตารางแผนงานเตรียมตัวนับถอยหลังสู่ค่าย (Roadmap)

| สัปดาห์ | แผนงานหลักที่ต้องทำให้เสร็จ |
| :--- | :--- |
| **สัปดาห์ที่ 1**<br/>*(22 - 27 ต.ค.)* | • เข้าร่วม Pre-Camp Training (เสาร์ที่ 24 ต.ค.)<br/>• สร้าง Data Contract (JSON Schema & Topics)<br/>• ติดตั้ง Ollama (`qwen2.5:1.5b`) และทดสอบเขียน Prompt ให้ตอบ JSON<br/>• เซ็ตอัปบอร์ด ESP32 และ RPi 5 ให้เชื่อมต่อ MQTT Broker ได้สำเร็จ |
| **สัปดาห์ที่ 2**<br/>*(28 ต.ค. - 5 พ.ย.)* | • เตรียม Colab Notebook สำหรับเทรน YOLOv8n และหาชุดภาพเมล็ดกาแฟมาทดลอง<br/>• พัฒนาโครงสร้างเว็บ Next-Gen Market Platform (Streamlit) หน้าเกษตรกรและผู้ซื้อ<br/>• เขียนสคริปต์วัดค่าเซ็นเซอร์และฟิลเตอร์กรองสัญญาณบน ESP32 |
| **สัปดาห์ที่ 3**<br/>*(6 - 13 พ.ย.)* | • **Integration Test:** เชื่อมทุกอย่างเข้าด้วยกัน (จำลองการยิงข้อมูลเซ็นเซอร์ + ภาพ + SLM + หน้าเว็บ)<br/>• ซ้อมแข่งเสมือนจริง 4 ชม. (Dry Run) 1 รอบ<br/>• บรรจุอุปกรณ์, ซื้อปลั๊กพ่วง, เซ็ตเราเตอร์ Wi-Fi พกพา และดาวน์โหลด Offline Packages |
| **15 พ.ย. 2569** | เดินทางถึง มจล. ชุมพร $\rightarrow$ ลงทะเบียน $\rightarrow$ พร้อมลุย 100%! |
