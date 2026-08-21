from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db, engine

# สั่งให้ SQLAlchemy สร้างตารางใน Database อัตโนมัติ (หากยังไม่มี)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TRACK-PRO API Systems", version="1.0.0")

# อนุญาตให้ Frontend (CORS) เรียกใช้งานได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ENDPOINTS ====================

# 1. AUTHENTICATION
@app.post("/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="กรุณากรอกข้อมูลให้ครบถ้วน")
    
    # ตรวจสอบว่า Username ซ้ำในฐานข้อมูลหรือไม่
    existing_user = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail=f"ชื่อผู้ใช้งาน '{payload.username}' มีอยู่ในระบบแล้ว"
        )
    
    # สร้างและบันทึกผู้ใช้ใหม่ลงฐานข้อมูล PostgreSQL
    new_user = models.User(
        username=payload.username,
        password=payload.password,
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "message": "ลงทะเบียนผู้ใช้งานสำเร็จ",
        "username": new_user.username,
        "role": new_user.role
    }

@app.post("/v1/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="กรุณากรอกข้อมูลให้ครบถ้วน")
    
    # ค้นหาผู้ใช้งานและรหัสผ่านจาก Database
    user = db.query(models.User).filter(
        models.User.username == payload.username,
        models.User.password == payload.password
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    
    return {
        "access_token": f"mock-jwt-token-{user.username}-2026",
        "token_type": "bearer",
        "role": user.role
    }

# 2. MAIN DASHBOARD & REALTIME IOT (index.html)
@app.get("/v1/jobs/{job_id}/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard_data(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.JobOrder).filter(models.JobOrder.job_code == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล Job Order")
    
    progress_percent = round((job.current_shots / job.target_shots) * 100, 1) if job.target_shots else 0.0
    
    return {
        "job_name": job.job_name,
        "kickoff_date": job.kickoff_date,
        "eta_text": job.eta_text,
        "current_shots": job.current_shots,
        "target_shots": job.target_shots,
        "progress_percent": progress_percent,
        "yield_rate": job.yield_rate,
        "status": job.status,
        "defect_status": {
            "icon": job.defect_icon or "✔️",
            "title": job.defect_title or "พารามิเตอร์ปกติ",
            "desc": job.defect_desc or "อยู่ในเกณฑ์ควบคุม"
        }
    }

@app.post("/v1/jobs/{job_id}/edge-case")
def trigger_edge_case(job_id: str, payload: schemas.EdgeCaseRequest, db: Session = Depends(get_db)):
    job = db.query(models.JobOrder).filter(models.JobOrder.job_code == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล Job Order")

    case_type = payload.case_type
    
    if case_type == "normal":
        job.status = "กำลังดำเนินการผลิต"
        job.eta_text = "22 กรกฎาคม 2026 (ตามกำหนดเดิม)"
        job.defect_icon = "✔️"
        job.defect_title = "พารามิเตอร์ปกติ"
        job.defect_desc = "อัตราการเกิดฟองอากาศอยู่ในเกณฑ์ยอมรับได้"
    elif case_type == "iot_loss":
        job.status = "OFFLINE"
        job.eta_text = "ตรวจสอบไม่ได้ชั่วคราว"
    elif case_type == "breakdown":
        job.status = "Paused / Under Maintenance"
        job.eta_text = "25 กรกฎาคม 2026 (ล่าช้าจากเครื่องจักรขัดข้อง)"
        job.defect_icon = "🔧"
        job.defect_title = "สายการผลิตหยุดชะงัก"
        job.defect_desc = "กำลังปิดปรับปรุงแม่พิมพ์กระทันหัน"
    
    db.commit()
    return {"message": f"จำลองสถานการณ์ {case_type} สำเร็จ"}

@app.post("/v1/jobs/{job_id}/concession")
def record_concession(job_id: str, payload: schemas.ConcessionRequest, db: Session = Depends(get_db)):
    job = db.query(models.JobOrder).filter(models.JobOrder.job_code == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูล Job Order")

    job.defect_icon = "❌"
    job.defect_title = "รอการประมวลผลงานแก้"
    job.defect_desc = f"คำสั่งล่าสุด: {payload.action_selected}"
    
    db.commit()
    return {"message": "บันทึกการตัดสินใจสำเร็จ", "action": payload.action_selected}

# 3. POST-PROCESSING TRACKING (tracking.html)
@app.get("/v1/jobs/{job_id}/post-processing")
def get_post_processing_steps(job_id: str, db: Session = Depends(get_db)):
    steps = db.query(models.PostProcessingStep).filter(models.PostProcessingStep.job_code == job_id).all()
    
    if not steps:
        return {
            "job_id": job_id,
            "steps": [
                {"step_no": 1, "name": "หล่อจริงชิ้นงานเสร็จสิ้น (Casting Done)", "status": "completed", "desc": "ชิ้นงานถูกสแกนออกจากไลน์เครื่องฉีดกะที่ 1"},
                {"step_no": 2, "name": "แผนกเจาะเซาะร่องตัดแต่งผิว (CNC & Deburring)", "status": "in_progress", "desc": "กำลังเก็บรายละเอียดและขัดครีบส่วนเกิน 1,240 ชิ้น"},
                {"step_no": 3, "name": "ทดสอบมิติและโครงสร้างภายใน (CMM & X-Ray)", "status": "pending", "desc": "รอคิวส่งเข้าห้องแล็บวัดพิกัดและสแกนรอยร้าว"},
                {"step_no": 4, "name": "กระบวนการชุบเคลือบผิว (Coating)", "status": "pending", "desc": "ขั้นตอนสุดท้ายก่อนย้ายส่งคลังสินค้า"}
            ]
        }
    
    return {"job_id": job_id, "steps": steps}

# 4. QC REPORT & LOGISTICS (qc-report.html)
@app.get("/v1/jobs/{job_id}/qc-report", response_model=schemas.QCReportResponse)
def get_qc_report(job_id: str, db: Session = Depends(get_db)):
    report = db.query(models.QCReport).filter(models.QCReport.job_code == job_id).first()
    
    if not report:
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
    return report

@app.get("/v1/jobs/{job_id}/logistics", response_model=schemas.LogisticsResponse)
def get_logistics_info(job_id: str, db: Session = Depends(get_db)):
    logistics = db.query(models.Logistics).filter(models.Logistics.job_code == job_id).first()
    
    if not logistics:
        return {
            "delivery_note": "DO-2026-0718",
            "package_info": "12 กล่องใหญ่ (ยกลังพัลเลต์)",
            "destination": "นิคมอุตสาหกรรมบางปู จ.สมุทรปราการ",
            "vehicle_plate": "8x-xxxx กทม.",
            "driver_status": "กำลังเดินทางมุ่งหน้านิคมฯ",
            "gps_url": "https://maps.google.com"
        }
    return logistics

@app.post("/v1/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
    existing_job = db.query(models.JobOrder).filter(models.JobOrder.job_code == payload.job_code).first()
    if existing_job:
        raise HTTPException(
            status_code=400, 
            detail=f"Job Order รหัส '{payload.job_code}' มีอยู่ในระบบแล้ว"
        )
    
    new_job = models.JobOrder(
        job_code=payload.job_code,
        job_name=payload.job_name,
        kickoff_date=payload.kickoff_date,
        eta_text=payload.eta_text,
        status=payload.status,
        target_shots=payload.target_shots,
        current_shots=payload.current_shots,
        yield_rate=payload.yield_rate,
        defect_icon=payload.defect_icon,
        defect_title=payload.defect_title,
        defect_desc=payload.defect_desc
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return {
        "message": "เพิ่มข้อมูล Job Order สำเร็จ",
        "data": new_job
    }