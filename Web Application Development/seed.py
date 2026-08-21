from database import SessionLocal, engine
import models

# สร้างตารางถ้ายังไม่มี
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# ลิสต์ User ที่ต้องการสร้าง
initial_users = [
    models.User(username="admin@factory.com", password="password123", role="manager"),
    models.User(username="Jeab@company.com", password="Jeab", role="client")
]

for user in initial_users:
    # ตรวจสอบไม่ให้สร้างซ้ำ
    exists = db.query(models.User).filter(models.User.username == user.username).first()
    if not exists:
        db.add(user)

db.commit()
db.close()
print("สร้างบัญชีผู้ใช้เริ่มต้นเรียบร้อยแล้ว!")