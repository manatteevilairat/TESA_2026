"""
shared/schemas.py - TESA Top Gun Rally 2026 Data Contract
สัญญาข้อมูลกลาง (Data Contract) กำหนดโครงสร้างข้อมูล JSON สำหรับทุก Node ในระบบ
"""

from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field
import time


class SensorData(BaseModel):
    """Payload จากบอร์ด ESP32 (Sensing Node)"""
    device_id: str = Field(default="esp32_sensing_01", description="ID ของบอร์ด ESP32")
    batch_id: str = Field(..., description="รหัสชุดการผลิตกาแฟ เช่น CPN-2026-B001")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp (วินาที)")
    moisture_pct: float = Field(..., ge=0.0, le=100.0, description="ความชื้นเมล็ดกาแฟ (%)")
    ambient_temp_c: float = Field(..., description="อุณหภูมิสิ่งแวดล้อม (°C)")
    ambient_humidity_pct: float = Field(..., ge=0.0, le=100.0, description="ความชื้นสัมพัทธ์ในอากาศ (%)")
    status: Literal["DRYING_NORMAL", "MOISTURE_HIGH", "DRYING_COMPLETE", "ALERT"] = "DRYING_NORMAL"


class DefectCounts(BaseModel):
    """Coffee bean defect statistics mapped to SCA & Robusta standards."""
    black_beans: int = Field(default=0, ge=0, description="Black bean defect (Primary defect)")
    sour_beans: int = Field(default=0, ge=0, description="Sour / fermented bean defect")
    mold_beans: int = Field(default=0, ge=0, description="Mold bean defect (Toxin hazard)")
    broken_beans: int = Field(default=0, ge=0, description="Broken / chipped bean defect")
    unripe_beans: int = Field(default=0, ge=0, description="Unripe / Quaker bean defect")
    insect_beans: int = Field(default=0, ge=0, description="Insect damage / borer beetle hole")
    empty_beans: int = Field(default=0, ge=0, description="Empty / floater bean defect")
    scorched_beans: int = Field(default=0, ge=0, description="Scorched / sun-burnt bean defect")


class VisionData(BaseModel):
    """Payload จากบอร์ด Raspberry Pi 5 (Vision Node)"""
    device_id: str = Field(default="rpi5_vision_01", description="ID ของ Raspberry Pi 5")
    batch_id: str = Field(..., description="รหัสชุดการผลิตกาแฟ")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp")
    sample_count: int = Field(..., gt=0, description="จำนวนเมล็ดกาแฟในตัวอย่างที่ส่องตรวจ")
    defects: DefectCounts = Field(default_factory=DefectCounts)
    defect_rate_pct: float = Field(..., ge=0.0, le=100.0, description="เปอร์เซ็นต์ข้อบกพร่องโดยรวม (%)")
    primary_grade: Literal["FINE_ROBUSTA", "PREMIUM", "COMMERCIAL_GRADE", "REJECT"] = "COMMERCIAL_GRADE"
    image_annotated_url: Optional[str] = None
    image_base64: Optional[str] = None


class SLMEvaluation(BaseModel):
    """ผลการประเมินคุณภาพเชิงลึกจาก Local SLM (Ollama qwen2.5:1.5b)"""
    batch_id: str
    evaluated_grade: str = Field(..., description="เกรดที่ SLM ประเมิน (เช่น Chumphon Fine Robusta, Grade 1)")
    cupping_notes: str = Field(..., description="คำอธิบายลักษณะกลิ่นรสและโปรไฟล์ทางกายภาพ")
    roast_recommendation: str = Field(..., description="ระดับการคั่วที่แนะนำ (Light / Medium / Dark Roast)")
    suggested_price_thb_per_kg: float = Field(..., gt=0, description="ราคาแนะนำขายต่อกิโลกรัม (บาท)")
    traceability_summary: str = Field(..., description="สรุปข้อมูลรับรองย้อนกลับสำหรับผู้ซื้อ (Buyer Summary)")
    engine_used: str = Field(default="Ollama (qwen2.5:1.5b)", description="เอนจินที่ใช้ประมวลผล")
    latency_seconds: float = Field(default=0.0, description="เวลาที่ใช้ในการประมวลผล (วินาที)")


class CoffeeBatchRecord(BaseModel):
    """ข้อมูลชุดรวม (Data Fusion) สำหรับนำขึ้น Next-Gen Market"""
    batch_id: str
    farmer_name: str = "เกษตรกรชุมพรวิสาหกิจชุมชน"
    origin: str = "อ.สวี จ.ชุมพร"
    process_type: str = "Dry Process (Natural)"
    latest_sensor: Optional[SensorData] = None
    latest_vision: Optional[VisionData] = None
    slm_eval: Optional[SLMEvaluation] = None
    asking_price_thb_per_kg: Optional[float] = None
    is_listed_for_sale: bool = False
