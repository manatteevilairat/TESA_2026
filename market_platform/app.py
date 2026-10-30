"""
market_platform/app.py
Next-Gen Market Platform: แพลตฟอร์มตลาดซื้อขายกาแฟโรบัสตาชุมพรสู่ตลาดยุคใหม่
รันด้วย Streamlit: รองรับทั้งมุมมองเกษตรกร (Supplier), ผู้ซื้อ (Buyer), และ Live Monitor
"""

import sys
import os
from pathlib import Path

# เพิ่ม Root Directory เข้า sys.path เพื่อให้ Streamlit หาโมดูล shared เจอเสมอ
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import time
from shared.schemas import CoffeeBatchRecord, SensorData, VisionData, DefectCounts, SLMEvaluation
from shared.mock_generator import generate_mock_sensor, generate_mock_vision
from market_platform.slm_evaluator import evaluate_coffee_quality
import json

DB_FILE = ROOT_DIR / "shared" / "live_db.json"

def resolve_vision_path(v_dict: dict) -> dict:
    """Remaps remote RPi Linux paths to local workspace paths if needed."""
    url = v_dict.get("image_annotated_url")
    if url and not os.path.exists(url):
        if "/home/admin/TESA_2026/" in url:
            rel = url.replace("/home/admin/TESA_2026/", "")
            mac_p = ROOT_DIR / rel
            if mac_p.exists():
                v_dict["image_annotated_url"] = str(mac_p)
            elif (ROOT_DIR / "runs" / "batch_eval_output").exists():
                v_dict["image_annotated_url"] = str(ROOT_DIR / "runs" / "batch_eval_output")
            else:
                v_dict["image_annotated_url"] = str(ROOT_DIR / "shared" / "latest_vision.jpg")
        elif (ROOT_DIR / "runs" / "batch_eval_output").exists():
            v_dict["image_annotated_url"] = str(ROOT_DIR / "runs" / "batch_eval_output")
    return v_dict

def save_live_database():
    """บันทึก session state ปัจจุบันกลับลง live_db.json เพื่อไม่ให้ข้อมูลหาย"""
    if DB_FILE.exists() and "batches" in st.session_state:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for b_id, b_obj in st.session_state.batches.items():
                data["batches"][b_id] = b_obj.model_dump()
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def sync_live_database():
    """โหลดข้อมูลล่าสุดที่ถูกส่งผ่าน MQTT จาก live_db.json"""
    history = []
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                live_batches = data.get("batches", {})
                history = data.get("history", [])
                
                for b_id, b_data in live_batches.items():
                    if b_data.get("latest_vision"):
                        b_data["latest_vision"] = resolve_vision_path(b_data["latest_vision"])
                    if b_id in st.session_state.batches:
                        if b_data.get("latest_sensor"):
                            st.session_state.batches[b_id].latest_sensor = SensorData(**b_data["latest_sensor"])
                        if b_data.get("latest_vision"):
                            st.session_state.batches[b_id].latest_vision = VisionData(**b_data["latest_vision"])
                    else:
                        st.session_state.batches[b_id] = CoffeeBatchRecord(**b_data)
        except Exception as e:
            pass
    return history

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="Chumphon Robusta Next-Gen Market",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# จัดการ State เก็บข้อมูล Lot กาแฟ
if "batches" not in st.session_state:
    # สร้างข้อมูลตั้งต้น 2 Batches (โหลดค่า Static เบื้องต้น เพื่อให้หน้าเว็บเปิดได้ทันทีโดยไม่ติดบล็อก)
    b1 = CoffeeBatchRecord(
        batch_id="CPN-2026-B001",
        farmer_name="ลุงประสิทธิ์ สวนกาแฟเขาทะลุ",
        origin="ต.เขาทะลุ อ.สวี จ.ชุมพร",
        process_type="Natural Dry Process",
        latest_sensor=SensorData(
            batch_id="CPN-2026-B001",
            moisture_pct=11.2,
            ambient_temp_c=29.5,
            ambient_humidity_pct=62.0,
            status="DRYING_NORMAL"
        ),
        latest_vision=VisionData(
            batch_id="CPN-2026-B001",
            sample_count=100,
            defects=DefectCounts(black_beans=0, mold_beans=0, broken_beans=2, sour_beans=0),
            defect_rate_pct=2.0,
            primary_grade="FINE_ROBUSTA"
        ),
        slm_eval=SLMEvaluation(
            batch_id="CPN-2026-B001",
            evaluated_grade="ชุมพร ไฟน์โรบัสตา (Chumphon Fine Robusta)",
            cupping_notes="เมล็ดสมบูรณ์สูง ปราศจากเชื้อรา ความชื้นอยู่ในเกณฑ์เหมาะสม อโรม่าหอมสะอาด โทนช็อกโกแลตและเครื่องเทศหวาน",
            roast_recommendation="Medium Roast (คั่วกลาง)",
            suggested_price_thb_per_kg=380.0,
            traceability_summary="กาแฟระดับ Specialty Fine Robusta ชุมพร ตรวจสอบย้อนกลับได้ 100%",
            engine_used="Ollama (qwen2.5:1.5b)",
            latency_seconds=1.85,
        ),
        asking_price_thb_per_kg=380.0,
        is_listed_for_sale=True
    )

    st.session_state.batches = {
        "CPN-2026-B001": b1
    }

# ซิงค์ข้อมูลล่าสุดจาก live_db.json ทุกครั้งที่หน้ารัน
recent_history = sync_live_database()

# Sidebar: สถานะระบบและการซิงค์
with st.sidebar:
    st.header("⚙️ การเชื่อมต่อเครือข่าย")
    st.success("🟢 **MQTT Broker:** `localhost:1883` (ONLINE)")
    st.info("🤖 **Local SLM:** `qwen2.5:1.5b` (GPU Metal)")
    if st.button("🔄 ซิงค์ข้อมูลจาก MQTT เดี๋ยวนี้", use_container_width=True):
        recent_history = sync_live_database()
        st.toast("ซิงค์ข้อมูลล่าสุดสำเร็จ!")
        st.rerun()

    st.divider()
    st.caption("TESA Top Gun Rally 2026 — Live Telemetry Engine")

# Header หลัก
st.title("☕ Chumphon Robusta AIoT Next-Gen Market")
st.caption("ระบบประเมินคุณภาพกาแฟอัจฉริยะ (AIoT + Local SLM) เพื่อการซื้อขายที่โปร่งใสและเพิ่มมูลค่าผลผลิต")

tab_farmer, tab_buyer, tab_monitor, tab_track3 = st.tabs([
    "👨‍🌾 1. ฝั่งเกษตรกร (Supplier Portal)",
    "🛒 2. ตลาดซื้อขายกาแฟ (Buyer Marketplace)",
    "📡 3. ตรวจสอบระบบ (Live System Telemetry)",
    "🤖 4. ซ้อมแข่ง AI Trading Agent (Track 3 Simulator)"
])

# ----------------- TAB 1: FARMER VIEW -----------------
with tab_farmer:
    st.subheader("📋 จัดการและประเมินคุณภาพชุดผลผลิต (Batch Management)")
    
    col_input, col_action = st.columns([2, 1])
    with col_input:
        current_batch_id = st.selectbox(
            "เลือก Batch กาแฟที่กำลังดำเนินการ:",
            options=list(st.session_state.batches.keys()) + ["+ สร้าง Batch ใหม่..."]
        )

    if current_batch_id == "+ สร้าง Batch ใหม่...":
        new_id = f"CPN-2026-B{len(st.session_state.batches)+1:03d}"
        f_name = st.text_input("ชื่อเกษตรกร / วิสาหกิจ:", "กลุ่มวิสาหกิจชุมชนกาแฟชุมพร")
        f_origin = st.text_input("แหล่งปลูก:", "อ.ท่าแซะ จ.ชุมพร")
        if st.button("บันทึกและเริ่มติดตาม"):
            st.session_state.batches[new_id] = CoffeeBatchRecord(
                batch_id=new_id,
                farmer_name=f_name,
                origin=f_origin,
                process_type="Natural Dry Process"
            )
            st.success(f"สร้าง Batch {new_id} สำเร็จ!")
            st.rerun()
    else:
        batch: CoffeeBatchRecord = st.session_state.batches[current_batch_id]
        
        st.markdown(f"**แหล่งปลูก:** {batch.origin} | **เกษตรกร:** {batch.farmer_name} | **กระบวนการ:** {batch.process_type}")
        
        col1, col2 = st.columns(2)
        
        # กล่องข้อมูล ESP32
        with col1:
            st.info("📡 **ข้อมูลกายภาพจาก ESP32 (Sensing Node)**")
            if batch.latest_sensor:
                s = batch.latest_sensor
                m_col, t_col, h_col = st.columns(3)
                m_col.metric("ความชื้นเมล็ด", f"{s.moisture_pct}%")
                t_col.metric("อุณหภูมิตาก", f"{s.ambient_temp_c} °C")
                h_col.metric("ความชื้นอากาศ", f"{s.ambient_humidity_pct}%")
                st.caption(f"สถานะ: `{s.status}` | อัปเดตล่าสุด: {time.strftime('%X', time.localtime(s.timestamp))}")
            else:
                st.write("ยังไม่มีข้อมูลเซ็นเซอร์")
                
            if st.button("🔄 จำลองอ่านค่าเซ็นเซอร์ใหม่ (Simulate ESP32)", key=f"btn_s_{current_batch_id}"):
                batch.latest_sensor = generate_mock_sensor(current_batch_id)
                st.rerun()

        # กล่องข้อมูล Raspberry Pi 5
        with col2:
            st.info("📷 **ผลการตรวจสอบภาพจาก Raspberry Pi 5 (Vision Node)**")
            if batch.latest_vision:
                v = batch.latest_vision
                g_col, d_col, mld_col = st.columns(3)
                g_col.metric("เกรดเบื้องต้น", v.primary_grade)
                d_col.metric("อัตราตำหนิ", f"{v.defect_rate_pct}%")
                mld_col.metric("เมล็ดขึ้นรา", f"{v.defects.mold_beans} เมล็ด")
                st.caption(f"สุ่มตรวจ: {v.sample_count} เมล็ด | ดำ: {v.defects.black_beans} | รา: {v.defects.mold_beans} | แตก: {v.defects.broken_beans} | ดิบ: {v.defects.unripe_beans}")
                
                # แสดงภาพผลการตรวจจับพร้อม Bounding Box
                if v.image_annotated_url and os.path.exists(v.image_annotated_url):
                    if os.path.isdir(v.image_annotated_url):
                        batch_imgs = sorted(list(Path(v.image_annotated_url).glob("*.jpg")))
                        if batch_imgs:
                            st.caption(f"📁 พบภาพผลการตรวจจับในชุดนี้ทั้งหมด {len(batch_imgs)} รูป")
                            sel_idx = st.slider("เลื่อนเพื่อตรวจดูภาพเมล็ดแต่ละภาพ:", min_value=1, max_value=len(batch_imgs), value=1, key=f"sl_{current_batch_id}")
                            active_img_path = str(batch_imgs[sel_idx - 1])
                            st.image(active_img_path, caption=f"📷 [{sel_idx}/{len(batch_imgs)}] {batch_imgs[sel_idx - 1].name}", use_container_width=True)
                        else:
                            st.info("ไม่พบไฟล์รูปภาพในโฟลเดอร์ผลการประเมิน")
                    else:
                        st.image(v.image_annotated_url, caption="📷 ภาพถ่ายเมล็ดกาแฟพร้อมกรอบวิเคราะห์ตำหนิ (Vision Feed)", use_container_width=True)
            else:
                st.write("ยังไม่มีข้อมูลผลตรวจภาพ")
                
            if st.button("📸 รันสแกนภาพเมล็ดด้วย Vision Engine", key=f"btn_v_{current_batch_id}"):
                import importlib
                import edge_ai.vision_engine as ve
                import cv2
                importlib.reload(ve)
                analyzer = ve.CoffeeVisionAnalyzer()
                feed = ve.RealTestImageFeed()
                if feed.images:
                    current_idx = st.session_state.get("feed_index", 0)
                    next_idx = (current_idx + 1) % len(feed.images)
                    st.session_state["feed_index"] = next_idx
                    sample_img = cv2.imread(str(feed.images[next_idx]))
                else:
                    sample_img, _ = feed.next_frame()
                v_data, _ = analyzer.process_image(sample_img, current_batch_id)
                batch.latest_vision = v_data
                save_live_database()
                st.rerun()

        st.divider()

        # ผลประเมินจาก Local SLM
        st.subheader("🤖 การประเมินคุณภาพเชิงลึกด้วย Local SLM (Ollama qwen2.5:1.5b)")
        if st.button("🧠 สั่ง AI วิเคราะห์เกรดและประเมินราคา (Evaluate with SLM)"):
            with st.spinner("Local SLM กำลังวิเคราะห์ข้อมูลกายภาพและตำหนิเมล็ด..."):
                batch.slm_eval = evaluate_coffee_quality(current_batch_id, batch.latest_sensor, batch.latest_vision)
                if batch.asking_price_thb_per_kg is None:
                    batch.asking_price_thb_per_kg = batch.slm_eval.suggested_price_thb_per_kg
            st.success("ประเมินผลสำเร็จ!")

        if batch.slm_eval:
            se = batch.slm_eval
            res_box = st.container(border=True)
            
            # แสดง Badge ตรวจสอบสถานะว่าใช้ Ollama จริงหรือไม่
            if "Ollama" in se.engine_used:
                res_box.success(f"🟢 **ประมวลผลด้วย AI จริง:** `{se.engine_used}` (ใช้เวลา `{se.latency_seconds}` วินาที)")
            else:
                res_box.warning(f"⚠️ **ประมวลผลด้วย:** `{se.engine_used}` (โหมดสำรอง)")

            res_box.markdown(f"### 🏆 เกรดที่ประเมิน: **{se.evaluated_grade}**")
            res_box.write(f"**Cupping & Profile Notes:** {se.cupping_notes}")
            res_box.write(f"**คำแนะนำการคั่ว:** {se.roast_recommendation}")
            res_box.write(f"**ราคาแนะนำตลาด:** `{se.suggested_price_thb_per_kg}` บาท/กก.")
            res_box.info(f"**ใบรับรองย้อนกลับ (Traceability Certificate):** {se.traceability_summary}")

            col_price, col_submit = st.columns([2, 1])
            with col_price:
                price_input = st.number_input(
                    "ระบุราคาขายจริง (บาท/กก.):",
                    value=float(batch.asking_price_thb_per_kg or se.suggested_price_thb_per_kg),
                    step=10.0
                )
                batch.asking_price_thb_per_kg = price_input
            with col_submit:
                st.write("")
                st.write("")
                if st.button("🚀 เปิดขายในตลาด Next-Gen Market", type="primary"):
                    batch.is_listed_for_sale = True
                    st.success(f"นำ Batch {current_batch_id} ขึ้นวางจำหน่ายแล้ว!")

# ----------------- TAB 2: BUYER MARKETPLACE -----------------
with tab_buyer:
    st.subheader("🛒 ตลาดซื้อขายกาแฟโรบัสตาพรีเมียม (Chumphon Certified Marketplace)")
    st.caption("เลือกซื้อเมล็ดกาแฟที่ผ่านการตรวจสอบย้อนกลับ (Traceability) และรับรองคุณภาพด้วยระบบ AIoT")

    listed_batches = [b for b in st.session_state.batches.values() if b.is_listed_for_sale]
    
    if not listed_batches:
        st.warning("ขณะนี้ยังไม่มีผลผลิตเปิดวางขาย กรุณาเปิดขายจากฝั่งเกษตรกรก่อน")
    else:
        for b in listed_batches:
            with st.container(border=True):
                col_info, col_buy = st.columns([3, 1])
                with col_info:
                    st.markdown(f"### 🏷️ รหัสสินค้า: **{b.batch_id}** — *{b.origin}*")
                    st.write(f"👨‍🌾 **ผู้ผลิต:** {b.farmer_name} | **กระบวนการ:** {b.process_type}")
                    
                    if b.slm_eval:
                        st.markdown(f"**เกรดที่ได้รับการรับรอง:** :green[{b.slm_eval.evaluated_grade}]")
                        st.caption(f"☕ {b.slm_eval.cupping_notes}")
                        st.caption(f"🔥 ระดับคั่วที่แนะนำ: {b.slm_eval.roast_recommendation}")
                    
                    # ข้อมูลทางเทคนิค
                    m_val = f"{b.latest_sensor.moisture_pct}%" if b.latest_sensor else "N/A"
                    d_val = f"{b.latest_vision.defect_rate_pct}%" if b.latest_vision else "N/A"
                    st.markdown(f"📊 **ข้อมูลตรวจสอบย้อนกลับ:** ความชื้นเมล็ด = `{m_val}` | อัตราตำหนิ = `{d_val}` | เชื้อรา = `0`")

                with col_buy:
                    st.metric("ราคาขาย", f"{b.asking_price_thb_per_kg:,.0f} ฿/กก.")
                    if st.button(f"🛒 สั่งซื้อทันที", key=f"buy_{b.batch_id}", type="primary"):
                        st.balloons()
                        st.success(f"ทำรายการสั่งซื้อ Batch {b.batch_id} สำเร็จ! ข้อมูลธุรกรรมถูกบันทึกเรียบร้อย")

# ----------------- TAB 3: SYSTEM TELEMETRY -----------------
with tab_monitor:
    st.subheader("📡 Real-time Hardware & Telemetry Status")
    st.write("ตรวจสอบความพร้อมของอุปกรณ์ในเครือข่าย AIoT และท่อส่งข้อมูล MQTT")
    
    t1, t2, t3 = st.columns(3)
    t1.metric("MQTT Broker (Port 1883)", "ONLINE", delta="Localhost")
    t2.metric("จำนวนชุดกาแฟ (Batches)", len(st.session_state.batches))
    t3.metric("ข้อความที่บันทึกแล้ว", f"{len(recent_history)} Packets")

    st.markdown("#### 📥 ประวัติข้อความ MQTT ล่าสุด (Incoming Packets Stream)")
    if recent_history:
        df_hist = pd.DataFrame(recent_history)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีข้อความส่งเข้ามาจาก MQTT Broker (ทดลองรัน backend_service.py และ mock_generator.py เพื่อส่งข้อมูล)")

    st.markdown("#### 🗺️ แผนผังการเชื่อมโยงระบบ (System Topology)")
    st.code(
        """
  [ESP32 Sensing Node] ──(MQTT Pub)──► Topic: tgr2026/coffee/{batch_id}/sensing
  [RPi 5 Vision Node ] ──(MQTT Pub)──► Topic: tgr2026/coffee/{batch_id}/vision
                                           │
                                           ▼
                             [Mosquitto MQTT Broker (1883)]
                                           │
                                           ▼
                          [Backend Service (Data Fusion)]
                                           │
                                           ▼
                           [shared/live_db.json (Storage)]
                                           │
                                           ▼
                       [Streamlit UI + Local SLM Evaluator]
        """,
        language="text"
    )

# ----------------- TAB 4: TRACK 3 NEXT-GEN MARKET AGENT -----------------
with tab_track3:
    st.subheader("🤖 ซ้อมแข่ง AI Trading Agent (Track 3: The Next-Gen Market)")
    st.caption("จำลองกลไกการแข่งขันวันที่ 18 และ 20 พ.ย. — ให้ AI Agent ซื้อขายอัตโนมัติด้วยกลยุทธ์ Blind Bidding")

    with st.expander("📖 สรุปกติกาการแข่งขัน Track 3 จาก Pre-camp", expanded=False):
        st.markdown("""
        * **เป้าหมาย:** ทำหน้าที่เป็นผู้ขายเมล็ดกาแฟโรบัสตา โดยให้ Python AI Agent เป็นคนตัดสินใจเสนอขายผ่าน REST API
        * **ระบบเสนอขายแบบปิดซอง (Blind Bidding):** แต่ละรอบ Agent ต้องเลือก **ล็อตที่จะขาย + ผู้ซื้อเป้าหมาย + ราคาเสนอขาย**
        * **เกณฑ์การให้คะแนน (Value Surplus Score):** คิดจากความคุ้มค่าของการขายเทียบกับมูลค่าแท้จริงของกาแฟล็อตนั้น  
          $$\\text{Surplus Score} = \\frac{\\text{ราคาขายจริง} - \\text{มูลค่าแท้จริง}}{\\text{มูลค่าแท้จริง}} \\times 100\\%$$
          *(ล็อตคุณภาพต่ำ ถ้าตั้งราคาฉลาดและจับคู่โรงงานถูก ก็สามารถชนะได้)*
        """)

    col_buyers, col_market_actions = st.columns([1, 1])

    with col_buyers:
        st.markdown("#### 🏢 กลุ่มผู้ซื้อในตลาด (Buyer Profiles)")
        st.info("""
        **1. Chumphon Craft Roastery (Specialty)**
        * ต้องการ: ข้อบกพร่อง $\\le 5.0\\%$, ความชื้น $10.0 - 12.5\\%$
        * งบประมาณสูงสุด: **360 ฿/กก.**
        
        **2. Southern Roasting & Blending Co. (Commercial)**
        * ต้องการ: ข้อบกพร่อง $\\le 14.0\\%$, ความชื้น $9.5 - 13.5\\%$
        * งบประมาณสูงสุด: **220 ฿/กก.**
        
        **3. Chumphon Agro-Instant Corp. (Instant / Byproduct)**
        * ต้องการ: ข้อบกพร่อง $\\le 40.0\\%$, กาแฟแตก/ไหม้/กะลา
        * งบประมาณสูงสุด: **130 ฿/กก.**
        """)

    with col_market_actions:
        st.markdown("#### ⚙️ การตั้งค่ากลยุทธ์ของ Agent (Agent Strategy)")
        strategy_mode = st.radio(
            "เลือกอัลกอริทึมการคำนวณราคาปิดซอง:",
            [
                "🏆 Smart Asymmetric (กลยุทธ์แชมป์: ปรับกำไรตามเกรดกาแฟ)",
                "🔄 Adaptive Feedback (ปรับตัวอัตโนมัติ: ชนะขยับขึ้น แพ้ถอยลง)",
                "📊 Fixed Margin (กำหนด % กำไรคงที่ทุกเกรด)"
            ],
            index=0
        )

        fixed_slider_val = 16.0
        if "Fixed" in strategy_mode:
            fixed_slider_val = st.slider("เป้าหมายกำไรส่วนเกิน (Target Surplus Margin %):", min_value=5.0, max_value=35.0, value=18.0, step=1.0)
            st.caption(f"Agent จะเสนอราคาบวก +{fixed_slider_val}% เท่ากันทุกเกรดกาแฟ")
        elif "Asymmetric" in strategy_mode:
            st.info("💡 **หลักการ:** กาแฟเกรดต่ำ (Reject) โรงงาน Instant มีงบสูง เราบวกกำไรได้ถึง **+28%** สร้าง Surplus มหาศาล ส่วนกาแฟ Specialty บวกแบบรัดกุม **+12%** เพื่อกันหลุดงบ")
        else:
            st.info("💡 **หลักการ:** เริ่มต้นที่ +16% หากรอบที่แล้วชนะจะปรับขึ้นทีละ +1.5% หากแพ้หรือโดนตัดราคาจะถอยลง -3.0% ทันที")

        if "agent_history" not in st.session_state:
            st.session_state.agent_history = []
        if "agent_total_surplus" not in st.session_state:
            st.session_state.agent_total_surplus = 0.0
        if "agent_total_revenue" not in st.session_state:
            st.session_state.agent_total_revenue = 0.0
        if "adaptive_margin_val" not in st.session_state:
            st.session_state.adaptive_margin_val = 0.16

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            run_btn = st.button("🚀 สั่ง AI Agent ทำงาน 1 รอบ (Look -> Think -> Act)", type="primary", use_container_width=True)
        with col_btn2:
            if st.button("🔄 รีเซ็ตการแข่งขัน", use_container_width=True):
                st.session_state.agent_history = []
                st.session_state.agent_total_surplus = 0.0
                st.session_state.agent_total_revenue = 0.0
                st.session_state.adaptive_margin_val = 0.16
                st.rerun()

        if run_btn:
            # 3 sample lots of varying quality
            sample_lots = [
                {
                    "lot_id": "LOT-A (Fine)",
                    "type": "fine",
                    "defect": 2.5,
                    "moisture": 11.2,
                    "intrinsic": 310.0,
                    "target_buyer": "Chumphon Craft Roastery",
                    "buyer_id": "buyer_specialty",
                    "max_budget": 360.0
                },
                {
                    "lot_id": "LOT-B (Commercial)",
                    "type": "commercial",
                    "defect": 8.5,
                    "moisture": 12.0,
                    "intrinsic": 150.0,
                    "target_buyer": "Southern Roasting Co.",
                    "buyer_id": "buyer_commercial",
                    "max_budget": 220.0
                },
                {
                    "lot_id": "LOT-C (Reject/Off-grade)",
                    "type": "reject",
                    "defect": 24.0,
                    "moisture": 13.8,
                    "intrinsic": 70.0,
                    "target_buyer": "Chumphon Agro-Instant Corp.",
                    "buyer_id": "buyer_instant",
                    "max_budget": 130.0
                }
            ]

            round_num = len(st.session_state.agent_history) + 1
            round_bids = []

            for lot in sample_lots:
                # คำนวณ Margin ตาม Strategy ที่เลือก
                if "Asymmetric" in strategy_mode:
                    if lot["type"] == "fine":
                        markup = 1.12
                    elif lot["type"] == "commercial":
                        markup = 1.18
                    else:
                        markup = 1.28
                elif "Adaptive" in strategy_mode:
                    markup = 1.0 + st.session_state.adaptive_margin_val
                else:
                    markup = 1.0 + (fixed_slider_val / 100.0)

                proposed_price = round(min(lot["intrinsic"] * markup, lot["max_budget"] * 0.96), 1)

                # จำลองการแข่งขันในตลาด (คู่แข่งเสนอราคา 1.05 - 1.25 เท่าของราคากลาง)
                import random
                competing_bid = lot["intrinsic"] * random.uniform(1.05, 1.25)
                won = (proposed_price <= lot["max_budget"]) and (proposed_price <= competing_bid * 1.08)

                profit = round(proposed_price - lot["intrinsic"], 1) if won else 0.0
                surplus_pct = round((profit / lot["intrinsic"]) * 100, 1) if won else 0.0

                if won:
                    st.session_state.agent_total_revenue += proposed_price
                    st.session_state.agent_total_surplus += surplus_pct
                    if "Adaptive" in strategy_mode:
                        st.session_state.adaptive_margin_val = min(0.30, st.session_state.adaptive_margin_val + 0.015)
                else:
                    if "Adaptive" in strategy_mode:
                        st.session_state.adaptive_margin_val = max(0.06, st.session_state.adaptive_margin_val - 0.03)

                status_reason = "ชนะประมูล (ได้ราคาสูงสุดที่ไม่หลุดเพดาน)" if won else f"แพ้ประมูล (คู่แข่งตัดราคาที่ {competing_bid:.1f} ฿)"

                round_bids.append({
                    "ล็อต": lot["lot_id"],
                    "ผู้ซื้อเป้าหมาย": lot["target_buyer"],
                    "มูลค่าแท้จริง": f"{lot['intrinsic']:.1f} ฿",
                    "ราคาที่เราเสนอ": f"{proposed_price:.1f} ฿",
                    "ผลการประมูล": "✅ ชนะ (WON)" if won else "❌ แพ้ (UNDERBID)",
                    "คะแนน Surplus %": f"+{surplus_pct:.1f}%" if won else "0.0%",
                    "หมายเหตุ": status_reason
                })

            st.session_state.agent_history.append({
                "round": round_num,
                "strategy": strategy_mode.split("(")[0].strip(),
                "bids": round_bids
            })
            st.toast("AI Agent ตัดสินใจและส่งข้อเสนอขายสำเร็จ!")

    st.divider()

    # แสดงผลคะแนนสะสม
    m1, m2, m3 = st.columns(3)
    m1.metric("รอบการแข่งขันที่เล่นแล้ว", f"{len(st.session_state.agent_history)} รอบ")
    m2.metric("รายได้สะสมทั้งหมด (Total Revenue)", f"{st.session_state.agent_total_revenue:,.1f} ฿")
    m3.metric("คะแนนความคุ้มค่าสะสม (Surplus Score)", f"{st.session_state.agent_total_surplus:,.1f} %", delta="Value Efficiency")

    if st.session_state.agent_history:
        st.markdown("#### 📜 บันทึกประวัติการตัดสินใจของ AI Agent แต่ละรอบ")
        for h in reversed(st.session_state.agent_history):
            with st.container(border=True):
                st.markdown(f"**รอบที่ {h['round']}** (Round {h['round']})")
                df_bids = pd.DataFrame(h["bids"])
                st.dataframe(df_bids, use_container_width=True, hide_index=True)

