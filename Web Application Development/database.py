import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. ดึง URL การเชื่อมต่อจากไฟล์ .env
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mysecretpassword@db:5432/webapp_db")

# 2. สร้าง Engine สำหรับสื่อสารกับ PostgreSQL
engine = create_engine(DATABASE_URL)

# 3. สร้าง Session Maker ไว้เปิด-ปิดการอ่านเขียนข้อมูล
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. สร้าง Base Class เพื่อให้ models.py นำไปใช้สืบทอดสร้างตาราง
Base = declarative_base()

# 5. ฟังก์ชัน Dependency สำหรับดึง DB Session ไปใช้ใน API (main.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()