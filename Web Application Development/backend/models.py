from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base  # ตรวจสอบว่ามี Import Base แล้ว

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="client")


class JobOrder(Base):
    __tablename__ = "job_orders"

    job_code = Column(String, primary_key=True, index=True)  # เช่น "Z-2046"
    job_name = Column(String, nullable=False)
    kickoff_date = Column(String, nullable=False)
    eta_text = Column(String, nullable=False)
    status = Column(String, nullable=False)
    target_shots = Column(Integer, default=5000)
    current_shots = Column(Integer, default=0)
    yield_rate = Column(Float, default=100.0)
    defect_icon = Column(String, default="✔️")
    defect_title = Column(String, default="พารามิเตอร์ปกติ")
    defect_desc = Column(String, default="อยู่ในเกณฑ์ควบคุม")

    steps = relationship("PostProcessingStep", back_populates="job", cascade="all, delete-orphan")
    qc_report = relationship("QCReport", back_populates="job", uselist=False, cascade="all, delete-orphan")
    logistics = relationship("Logistics", back_populates="job", uselist=False, cascade="all, delete-orphan")


class PostProcessingStep(Base):
    __tablename__ = "post_processing_steps"

    id = Column(Integer, primary_key=True, index=True)
    job_code = Column(String, ForeignKey("job_orders.job_code"), nullable=False)
    step_no = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)  # 'completed' | 'in_progress' | 'pending'
    desc = Column(String, nullable=False)

    job = relationship("JobOrder", back_populates="steps")


class QCReport(Base):
    __tablename__ = "qc_reports"

    id = Column(Integer, primary_key=True, index=True)
    job_code = Column(String, ForeignKey("job_orders.job_code"), unique=True, nullable=False)
    report_no = Column(String, nullable=False)
    inspection_date = Column(String, nullable=False)
    product_part = Column(String, nullable=False)
    sampling_method = Column(String, nullable=False)
    auditor = Column(String, nullable=False)

    job = relationship("JobOrder", back_populates="qc_report")
    # ชื่อ attribute ต้องเป็น "results" ให้ตรงกับ schemas.QCReportResponse.results
    results = relationship("QCReportItem", back_populates="report", cascade="all, delete-orphan")


class QCReportItem(Base):
    __tablename__ = "qc_report_items"

    id = Column(Integer, primary_key=True, index=True)
    qc_report_id = Column(Integer, ForeignKey("qc_reports.id"), nullable=False)
    item = Column(String, nullable=False)
    spec = Column(String, nullable=False)
    actual = Column(String, nullable=False)
    result = Column(String, nullable=False)  # 'PASS' | 'FAIL'

    report = relationship("QCReport", back_populates="results")


class Logistics(Base):
    __tablename__ = "logistics"

    id = Column(Integer, primary_key=True, index=True)
    job_code = Column(String, ForeignKey("job_orders.job_code"), unique=True, nullable=False)
    delivery_note = Column(String, nullable=False)
    package_info = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    vehicle_plate = Column(String, nullable=False)
    driver_status = Column(String, nullable=False)
    gps_url = Column(String, nullable=False)

    job = relationship("JobOrder", back_populates="logistics")
