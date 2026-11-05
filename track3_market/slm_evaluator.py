"""
market_platform/slm_evaluator.py
โมดูลเรียกใช้งาน Local SLM (Ollama qwen2.5:1.5b)
ทำหน้าที่วิเคราะห์คุณภาพเมล็ดกาแฟโรบัสตาชุมพร, สรุป Cupping Notes, และคำนวณราคาแนะนำ
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
from typing import Optional
from shared.schemas import SensorData, VisionData, SLMEvaluation

OLLAMA_MODEL_DEFAULT = "qwen2.5:1.5b"


def evaluate_coffee_quality(
    batch_id: str,
    sensor: Optional[SensorData] = None,
    vision: Optional[VisionData] = None,
    model_name: str = OLLAMA_MODEL_DEFAULT
) -> SLMEvaluation:
    """
    ส่งข้อมูล Sensor และ Vision ให้ Local SLM วิเคราะห์และส่งคืนเป็น Structured JSON
    """
    import time
    start_time = time.time()
    moisture = sensor.moisture_pct if sensor else 11.5
    temp = sensor.ambient_temp_c if sensor else 30.0
    defect_rate = vision.defect_rate_pct if vision else 5.0
    mold_count = vision.defects.mold_beans if vision else 0
    vision_grade = vision.primary_grade if vision else "PREMIUM"

    prompt = f"""คุณเป็นผู้เชี่ยวชาญด้านมาตรฐานกาแฟโรบัสตาชุมพร (Chumphon Fine Robusta Specialist)
ประเมินผลผลิตกาแฟชุด {batch_id}:
- ความชื้นเมล็ด: {moisture}% (มาตรฐานส่งออก 10.5%-12.5%)
- อุณหภูมิตาก: {temp}°C
- ข้อบกพร่อง: {defect_rate}%
- เชื้อรา: {mold_count} เมล็ด
- เกรดจากกล้อง: {vision_grade}

จงประเมินและตอบกลับเฉพาะ JSON ก้อนเดียวสั้นกระชับ:
{{
  "evaluated_grade": "ชุมพร ไฟน์โรบัสตา หรือ เกรดพรีเมียม หรือ เกรดพาณิชย์",
  "cupping_notes": "คำอธิบายกลิ่นรสและบอดี้สั้นๆ ไม่เกิน 2 ประโยค",
  "roast_recommendation": "Medium Roast (คั่วกลาง) หรือ Dark Roast (คั่วเข้ม)",
  "suggested_price_thb_per_kg": 280.0,
  "traceability_summary": "สรุปข้อมูลการรับรองสำหรับผู้ซื้อสั้นๆ ไม่เกิน 2 ประโยค"
}}
หมายเหตุ: ตอบเป็น JSON เท่านั้น suggested_price_thb_per_kg เป็นตัวเลขราคาจริง (150-450) ห้ามตอบ 0"""

    # ลองเรียก Ollama
    try:
        import ollama
        import re
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "repeat_penalty": 1.2, "num_predict": 400},
        )
        content = response["message"]["content"].strip()
        
        # ดึงส่วน JSON ออกมาจากคำตอบ
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        clean_json = json_match.group(0) if json_match else content
        
        parsed = json.loads(clean_json)
        price = float(parsed.get("suggested_price_thb_per_kg", 220.0))
        if price <= 0:
            price = 220.0

        latency = round(time.time() - start_time, 2)
        return SLMEvaluation(
            batch_id=batch_id,
            evaluated_grade=parsed.get("evaluated_grade", "Chumphon Fine Robusta"),
            cupping_notes=parsed.get("cupping_notes", "บอดี้เข้มข้น โทนช็อกโกแลต คาราเมลและถั่ว"),
            roast_recommendation=parsed.get("roast_recommendation", "Medium Roast (คั่วกลาง)"),
            suggested_price_thb_per_kg=price,
            traceability_summary=parsed.get("traceability_summary", "ผ่านการตรวจสอบความชื้นและตำหนิตามเกณฑ์ Fine Robusta"),
            engine_used=f"Ollama ({model_name})",
            latency_seconds=latency,
        )
    except Exception as e:
        # Fallback อัจฉริยะหาก Ollama ยังไม่ได้เปิด service
        print(f"⚠️ [SLM Notice] ไม่สามารถติดต่อ Ollama ({e}) -> ใช้งาน Fallback Heuristic Engine")
        latency = round(time.time() - start_time, 3)
        
        # กฎ Heuristic จำลองผลลัพธ์
        if moisture <= 12.0 and defect_rate <= 3.5 and mold_count == 0:
            grade = "ชุมพร ไฟน์โรบัสตา (Chumphon Fine Robusta)"
            notes = "เมล็ดสมบูรณ์สูงมาก ปราศจากเชื้อรา ความชื้นอยู่ในเกณฑ์เหมาะสม อโรม่าหอมสะอาด โทนช็อกโกแลตและเครื่องเทศหวาน"
            roast = "Medium Roast (คั่วกลาง ดึงความหวานธรรมชาติ)"
            price = 350.0
            summary = "กาแฟระดับ Specialty Fine Robusta ชุมพร ตรวจสอบย้อนกลับได้ 100% เหมาะสำหรับโรงคั่วที่เน้น Single Origin"
        elif defect_rate <= 7.0 and mold_count == 0:
            grade = "ชุมพร โรบัสตา พรีเมียม (Chumphon Robusta Premium)"
            notes = "เมล็ดส่วนใหญ่ได้มาตรฐาน ความชื้นควบคุมได้ดี มีเมล็ดแตกหักเล็กน้อย บอดี้แน่น เหมาะกับการทำเอสเปรสโซเบลนด์"
            roast = "Medium-Dark Roast (คั่วกลางค่อนเข้ม)"
            price = 220.0
            summary = "เกรดคุณภาพสูงสำหรับร้านกาแฟพิเศษ คัดสรรจากแหล่งปลูกที่มีการควบคุมการตากแห้งอย่างเป็นระบบ"
        else:
            grade = "กาแฟโรบัสตาเกรดพาณิชย์ทั่วไป (Commercial Grade)"
            notes = "พบอัตราเมล็ดมีตำหนิสูงกว่าเกณฑ์พรีเมียม ควรนำไปคัดแยกซ้ำก่อนเข้าสู่กระบวนการคั่ว"
            roast = "Dark Roast (คั่วเข้ม)"
            price = 145.0
            summary = "เกรดพาณิชย์มาตรฐาน เหมาะสำหรับอุตสาหกรรมแปรรูปกาแฟสำเร็จรูป"

        return SLMEvaluation(
            batch_id=batch_id,
            evaluated_grade=grade,
            cupping_notes=notes,
            roast_recommendation=roast,
            suggested_price_thb_per_kg=price,
            traceability_summary=summary,
            engine_used="Fallback Heuristic Engine",
            latency_seconds=latency,
        )


if __name__ == "__main__":
    from shared.mock_generator import generate_mock_sensor, generate_mock_vision
    batch = "CPN-2026-TEST"
    s = generate_mock_sensor(batch)
    v = generate_mock_vision(batch)
    result = evaluate_coffee_quality(batch, s, v)
    print("✨ ผลการประเมินจาก SLM Engine:")
    print(result.model_dump_json(indent=2))
