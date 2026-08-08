from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

app = FastAPI(title="TRACK-PRO API Systems", version="1.0.0")

# อนุญาตให้ Frontend (CORS) เรียกใช้งานได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== SCHEMAS ====================
class LoginRequest(BaseModel):
    role: str  # 'client' | 'manager'
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class EdgeCaseTrigger(BaseModel):
    case_type: str  # 'normal' | 'iot_loss' | 'breakdown' | 'high_defect'

class ConcessionDecision(BaseModel):
    action_selected: str  # 'Rework' | 'Accept with deviation'

class QualityItem(BaseModel):
    item: str
    spec: str
    actual: str
    result: str  # 'PASS' | 'FAIL'

# ==================== MOCK DATABASE ====================
db_job = {
    "job_id": "Z-2046",
    "job_name": "Die-Casting Part #Z-2046",
    "kickoff_date": "2026-07-18",
    "eta_text": "22 กรกฎาคม 2026 (ตามกำหนดเดิม)",
    "status": "กำลังดำเนินการผลิต",
    "target_shots": 5000,
    "current_shots": 1240,
    "yield_rate": 96.2,
    "defect_status": {
        "icon": "✔️",
        "title": "พารามิเตอร์ปกติ",
        "desc": "อัตราการเกิดฟองอากาศ (Porosity) อยู่ในเกณฑ์ควบคุม"
    }
}

# ==================== ENDPOINTS ====================

# 1. AUTHENTICATION
@app.post("/api/v1/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="กรุณากรอกข้อมูลให้ครบถ้วน")
    
    return {
        "access_token": "mock-jwt-token-track-pro-2026",
        "token_type": "bearer",
        "role": payload.role,
        "username": payload.username
    }

# 2. MAIN DASHBOARD & REALTIME IOT (index.html)
@app.get("/api/v1/jobs/{job_id}/dashboard")
def get_dashboard_data(job_id: str):
    if job_id != db_job["job_id"]:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล Job Order")
    
    progress_percent = round((db_job["current_shots"] / db_job["target_shots"]) * 100, 1)
    return {
        **db_job,
        "progress_percent": progress_percent
    }

@app.post("/api/v1/jobs/{job_id}/edge-case")
def trigger_edge_case(job_id: str, payload: EdgeCaseTrigger):
    case_type = payload.case_type
    
    if case_type == "normal":
        db_job["status"] = "กำลังดำเนินการผลิต"
        db_job["eta_text"] = "22 กรกฎาคม 2026 (ตามกำหนดเดิม)"
        db_job["defect_status"] = {"icon": "✔️", "title": "พารามิเตอร์ปกติ", "desc": "อัตราการเกิดฟองอากาศอยู่ในเกณฑ์ยอมรับได้"}
    elif case_type == "iot_loss":
        db_job["status"] = "OFFLINE"
        db_job["eta_text"] = "ตรวจสอบไม่ได้ชั่วคราว"
    elif case_type == "breakdown":
        db_job["status"] = "Paused / Under Maintenance"
        db_job["eta_text"] = "25 กรกฎาคม 2026 (ล่าช้าจากเครื่องจักรขัดข้อง)"
        db_job["defect_status"] = {"icon": "🔧", "title": "สายการผลิตหยุดชะงัก", "desc": "กำลังปิดปรับปรุงแม่พิมพ์กระทันหัน"}
    
    return {"message": f"จำลองสถานการณ์ {case_type} สำเร็จ", "current_state": db_job}

@app.post("/api/v1/jobs/{job_id}/concession")
def record_concession(job_id: str, payload: ConcessionDecision):
    db_job["defect_status"] = {
        "icon": "❌",
        "title": "รอการประมวลผลงานแก้",
        "desc": f"คำสั่งล่าสุด: {payload.action_selected}"
    }
    return {"message": "บันทึกการตัดสินใจสำเร็จ", "action": payload.action_selected}

# 3. POST-PROCESSING TRACKING (tracking.html)
@app.get("/api/v1/jobs/{job_id}/post-processing")
def get_post_processing_steps(job_id: str):
    return {
        "job_id": job_id,
        "steps": [
            {"step_no": 1, "name": "หล่อจริงชิ้นงานเสร็จสิ้น (Casting Done)", "status": "completed", "desc": "ชิ้นงานถูกสแกนออกจากไลน์เครื่องฉีดกะที่ 1"},
            {"step_no": 2, "name": "แผนกเจาะเซาะร่องตัดแต่งผิว (CNC & Deburring)", "status": "in_progress", "progress_percent": 50, "desc": "กำลังเก็บรายละเอียดและขัดครีบส่วนเกิน 1,240 ชิ้น"},
            {"step_no": 3, "name": "ทดสอบมิติและโครงสร้างภายใน (CMM & X-Ray)", "status": "pending", "desc": "รอคิวส่งเข้าห้องแล็บวัดพิกัดและสแกนรอยร้าว"},
            {"step_no": 4, "name": "กระบวนการชุบเคลือบผิว (Coating)", "status": "pending", "desc": "ขั้นตอนสุดท้ายก่อนย้ายส่งคลังสินค้า"}
        ]
    }

# 4. QC REPORT & LOGISTICS (qc-report.html)
@app.get("/api/v1/jobs/{job_id}/qc-report")
def get_qc_report(job_id: str):
    return {
        "report_no": "QC-99823",
        "inspection_date": "2026-07-18",
        "product_part": "Die-Casting Zinc Alloy Z-2046",
        "sampling_method": "MIL-STD-105E Level II",
        "auditor": "Somchai.W (Lead QC Auditor)",
        "results": [
            {"item": "Outer Dia.", "spec": "45.00 ±0.05", "actual": "45.02", "result": "PASS"},
            {"item": "Thickness", "spec": "12.50 ±0.02", "actual": "12.49", "result": "PASS"},
            {"item": "X-Ray Scan", "spec": "No Cracks", "actual": "Clear", "result": "PASS"}
        ]
    }

@app.get("/api/v1/jobs/{job_id}/logistics")
def get_logistics_info(job_id: str):
    return {
        "delivery_note": "DO-2026-0718",
        "package_info": "12 กล่องใหญ่ (ยกลังพัลเลต์)",
        "destination": "นิคมอุตสาหกรรมบางปู จ.สมุทรปราการ",
        "vehicle_plate": "8x-xxxx กทม.",
        "driver_status": "กำลังเดินทางมุ่งหน้านิคมฯ",
        "gps_url": "https://maps.google.com"
    }