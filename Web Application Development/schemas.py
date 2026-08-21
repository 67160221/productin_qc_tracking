from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    role: str       # 'client' หรือ 'manager'
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class DefectStatus(BaseModel):
    icon: str
    title: str
    desc: str

class DashboardResponse(BaseModel):
    job_name: str
    kickoff_date: str
    eta_text: str
    current_shots: int
    target_shots: int = 5000
    progress_percent: float
    yield_rate: float
    status: str
    defect_status: Optional[DefectStatus] = None

    model_config = ConfigDict(from_attributes=True)

class ProcessStep(BaseModel):
    step_no: int
    name: str
    desc: str
    status: str  # 'completed', 'in_progress', 'pending'

    model_config = ConfigDict(from_attributes=True)

class PostProcessingResponse(BaseModel):
    job_code: str
    steps: List[ProcessStep]

class QCItemResult(BaseModel):
    item: str
    spec: str
    actual: str
    result: str  # 'PASS' หรือ 'FAIL'

class QCReportResponse(BaseModel):
    report_no: str
    inspection_date: str
    product_part: str
    sampling_method: str
    auditor: str
    results: List[QCItemResult]

class LogisticsResponse(BaseModel):
    delivery_note: str
    package_info: str
    destination: str
    vehicle_plate: str
    driver_status: str
    gps_url: str

class EdgeCaseRequest(BaseModel):
    case_type: str  # 'normal', 'iot_loss', 'breakdown', 'high_defect'

class ConcessionRequest(BaseModel):
    action_selected: str

class JobCreate(BaseModel):
    job_code: str          # เช่น "Z-2046"
    job_name: str          # เช่น "Die-Casting Part #Z-2046"
    kickoff_date: str      # เช่น "2026-07-18"
    eta_text: str          # เช่น "22 กรกฎาคม 2026"
    status: str            # เช่น "กำลังดำเนินการผลิต"
    target_shots: int = 5000
    current_shots: int = 0
    yield_rate: float = 100.0
    defect_icon: Optional[str] = "✔️"
    defect_title: Optional[str] = "พารามิเตอร์ปกติ"
    defect_desc: Optional[str] = "อยู่ในเกณฑ์ควบคุม"