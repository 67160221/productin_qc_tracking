<div align="center">

# TRACK-PRO

### QC & Production Tracking System

ระบบติดตามงานผลิตและมาตรฐาน QC สำหรับโรงงาน Die-Casting
เชื่อมโยงข้อมูลระหว่าง **ลูกค้า/ผู้จัดซื้อ** และ **ผู้จัดการโรงงาน**

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)

</div>

---

## สารบัญ

- [ภาพรวมระบบ](#ภาพรวมระบบ)
- [สถาปัตยกรรม](#สถาปัตยกรรม)
- [Technology Stack](#technology-stack)
- [โครงสร้างโปรเจกต์](#โครงสร้างโปรเจกต์)
- [เริ่มต้นใช้งาน](#เริ่มต้นใช้งาน)
- [ข้อมูลตัวอย่าง (Auto Seed)](#ข้อมูลตัวอย่าง-auto-seed)
- [บัญชีผู้ใช้ทดสอบ](#บัญชีผู้ใช้ทดสอบ)
- [หน้าจอการใช้งาน](#หน้าจอการใช้งาน)
- [API Reference](#api-reference)
- [ตัวแปรแวดล้อม](#ตัวแปรแวดล้อม)
- [การพัฒนา](#การพัฒนา)
- [ข้อจำกัดที่ทราบ](#ข้อจำกัดที่ทราบ)

---

## ภาพรวมระบบ

TRACK-PRO คือระบบติดตามสถานะงานผลิตชิ้นงาน **Die-Casting** ตั้งแต่ต้นจนจบกระบวนการ ประกอบด้วย:

| โมดูล | รายละเอียด |
|---|---|
| **Authentication** | เข้าสู่ระบบด้วย username/password (ลงทะเบียนผ่าน API ได้) |
| **Dashboard** | ติดตามความคืบหน้าการฉีดขึ้นรูป (Shot Count), Yield Rate และสถานะสายการผลิต |
| **Post-Processing** | ติดตามขั้นตอนหลังการหล่อ 4 ขั้นตอน (Casting → CNC → CMM/X-Ray → Coating) |
| **QC Report** | รายงานผลตรวจสอบคุณภาพ (spec / actual / PASS-FAIL) และวิธีสุ่มตัวอย่าง |
| **Logistics** | ข้อมูลการจัดส่ง ทะเบียนรถ สถานะคนขับ และลิงก์ GPS |
| **Edge Case Simulator** | จำลองสถานการณ์ผิดปกติ (เน็ตหลุด, เครื่องพัง, ของเสียวิกฤต) จากหน้า Dashboard |

---

## สถาปัตยกรรม

### 1) สถาปัตยกรรมปัจจุบัน (as-is)

ระบบรันด้วย Docker Compose 4 containers: `frontend` (Nginx), `backend` (FastAPI), `db` (PostgreSQL) และ `cloudflared` (Cloudflare Tunnel)
โดย backend เป็น FastAPI ตัวเดียวที่แบ่งเป็น module (Auth, Jobs, Post-Processing, QC, Logistics)

![Current architecture](docs/architecture/current-architecture.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
    U["Users<br/>Client / Factory Manager<br/>(Web Browser)"]
    subgraph DC["Docker Compose network"]
        CF["cloudflared<br/>Cloudflare Tunnel"]
        FE["frontend<br/>Nginx :80<br/>static HTML + reverse proxy"]
        BE["backend<br/>FastAPI + Uvicorn :8000"]
        DB[("db<br/>PostgreSQL 15 :5432<br/>volume: postgres_data")]
    end
    U -- "HTTP :80" --> FE
    U -- "HTTPS public URL" --> CF
    CF --> FE
    FE -- "/api/* proxy" --> BE
    BE -- "SQLAlchemy / psycopg2" --> DB
```

</details>

### 2) Microservices Architecture (target)

แผนแยก backend ตัวเดียวออกเป็น 5 services ตามขอบเขตของ endpoint ที่มีอยู่แล้ว โดยแต่ละ service มี container และฐานข้อมูลของตัวเอง
มี API Gateway (Nginx) เป็นจุดเข้าเดียว ส่วน IoT Gateway เป็นแผนพัฒนาต่อ

![Microservices architecture](docs/architecture/microservices-architecture.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TB
    B["Web Browser<br/>Customer / Factory Manager"]
    IOT["IoT Gateway (planned)"]
    GW["API Gateway - Nginx<br/>Static UI + routing /api/v1/*"]
    B --> GW
    IOT -.-> GW
    GW -- "/api/v1/auth/*" --> AUTH["Auth Service"]
    GW -- "/api/v1/jobs/*" --> JOB["Job and Dashboard Service"]
    GW -- "/jobs/id/post-processing" --> PP["Post-Processing Service"]
    GW -- "/jobs/id/qc-report" --> QC["QC Service"]
    GW -- "/jobs/id/logistics" --> LG["Logistics Service"]
    AUTH --> D1[("users_db")]
    JOB --> D2[("jobs_db")]
    PP --> D3[("tracking_db")]
    QC --> D4[("qc_db")]
    LG --> D5[("logistics_db")]
```

</details>

**การแบ่ง service ตาม endpoint และตารางที่มีอยู่ในโค้ดปัจจุบัน**

| Service | Endpoint (ปัจจุบัน) | ตารางที่รับผิดชอบ |
|---|---|---|
| Auth Service | `POST /v1/auth/login`, `POST /v1/auth/register` | `users` |
| Job & Dashboard Service | `GET /v1/jobs/{id}/dashboard`, `POST /v1/jobs/{id}/edge-case`, `POST /v1/jobs/{id}/concession`, `POST /v1/jobs` | `job_orders` |
| Post-Processing Service | `GET /v1/jobs/{id}/post-processing` | `post_processing_steps` |
| QC Service | `GET /v1/jobs/{id}/qc-report` | `qc_reports`, `qc_report_items` |
| Logistics Service | `GET /v1/jobs/{id}/logistics` | `logistics` |

> **หมายเหตุ:** สถานะปัจจุบันของโค้ดคือ modular monolith (ทุก service อยู่ใน backend container เดียว และใช้ PostgreSQL database เดียว)
> แผนภาพที่ 2 คือสถาปัตยกรรมเป้าหมายที่ออกแบบต่อยอดจากโครงสร้างเดิม

---

## Technology Stack

![Technology stack diagram](docs/architecture/tech-stack-diagram.svg)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TB
    L1["<b>Presentation</b><br/>HTML5 · Tailwind CSS (CDN) · Vanilla JavaScript (Fetch API) · Google Fonts · localStorage"]
    L2["<b>Web Server / Gateway</b><br/>Nginx (alpine) · static files · reverse proxy /api/*"]
    L3["<b>Application</b><br/>Python 3.11 · FastAPI · Uvicorn · Pydantic v2 · SQLAlchemy · CORS Middleware"]
    L4["<b>Data</b><br/>PostgreSQL 15 · psycopg2-binary · Docker Volume · seed.py"]
    L5["<b>DevOps / Infrastructure</b><br/>Docker · Docker Compose · cloudflared (Cloudflare Tunnel) · .env · GitHub"]
    L1 --> L2 --> L3 --> L4
    L5 -. hosts .-> L2
    L5 -. hosts .-> L3
    L5 -. hosts .-> L4
```

</details>

ไฟล์ภาพทั้งหมดอยู่ที่ [`docs/architecture/`](docs/architecture/) (SVG และ PNG)

---

## โครงสร้างโปรเจกต์

```
productin_qc_tracking-main/
├── README.md
├── docs/
│   └── architecture/
│       ├── current-architecture.svg / .png
│       ├── microservices-architecture.svg / .png
│       └── tech-stack-diagram.svg / .png
└── Web Application Development/
    ├── backend/
    │   ├── main.py            # FastAPI app, endpoints, lifespan (รอ DB -> สร้างตาราง -> seed)
    │   ├── models.py          # SQLAlchemy models (User, JobOrder, QCReport ฯลฯ)
    │   ├── schemas.py         # Pydantic request/response schemas
    │   ├── database.py        # การเชื่อมต่อฐานข้อมูลและ session
    │   ├── seed.py            # ข้อมูลตัวอย่าง (เรียกอัตโนมัติตอน backend เริ่ม)
    │   ├── requirements.txt   # Python dependencies
    │   └── Dockerfile
    ├── frontend/
    │   ├── login.html         # หน้าเข้าสู่ระบบ
    │   ├── dashboard.html     # แดชบอร์ดหลัก + Edge Case Simulator
    │   ├── tracking.html      # ติดตามขั้นตอนหลังการหล่อ
    │   ├── qc-report.html     # รายงาน QC และข้อมูลจัดส่ง
    │   ├── default.conf       # Nginx config (reverse proxy /api)
    │   └── Dockerfile
    ├── docker-compose.yml
    ├── .env / .env.example
    └── login.html, dashboard.html, tracking.html, qc-report.html
                               # สำเนา HTML ที่อยู่นอกโฟลเดอร์ frontend/ (Docker ไม่ได้ใช้ไฟล์เหล่านี้)
```

---

## เริ่มต้นใช้งาน

### สิ่งที่ต้องมี

- [Docker](https://www.docker.com/) และ [Docker Compose](https://docs.docker.com/compose/)

### ขั้นตอนการรัน

```bash
# 1) เข้าไปในโฟลเดอร์ที่มี docker-compose.yml
cd "Web Application Development"

# 2) ต้องมีไฟล์ .env (ถ้ายังไม่มี ให้คัดลอกจากตัวอย่างแล้วแก้ค่าตามต้องการ)
#    macOS / Linux / Git Bash:
[ -f .env ] || cp .env.example .env
#    Windows (CMD):  if not exist .env copy .env.example .env

# 3) สั่งรันทั้งระบบ (Database + Backend + Frontend + Tunnel)
docker compose up --build

# 4) เปิดเบราว์เซอร์ไปที่
#    http://localhost
```

ในการรันครั้งแรก backend จะรอให้ฐานข้อมูลพร้อม สร้างตารางให้เอง และ **seed ข้อมูลตัวอย่างอัตโนมัติ** ใช้งานได้ทันทีโดยไม่ต้องรันคำสั่งเพิ่ม
(ดูรายละเอียดที่หัวข้อ [ข้อมูลตัวอย่าง](#ข้อมูลตัวอย่าง-auto-seed))

### ตรวจสอบว่าระบบเชื่อมต่อฐานข้อมูลสำเร็จ

```bash
curl http://localhost/api/v1/health
```

```json
{ "status": "ok", "database": "connected", "job_orders": 1 }
```

### เปิดใช้งานผ่าน URL สาธารณะ (Cloudflare Tunnel)

container `cloudflared` จะสร้าง URL ชั่วคราว (`https://xxxx.trycloudflare.com`) ให้อัตโนมัติ ดู URL ได้จาก log:

```bash
docker compose logs cloudflared
```

### หยุดการทำงาน

```bash
docker compose down          # หยุดและลบ container (ข้อมูลใน volume ยังอยู่)
docker compose down -v       # หยุดและลบข้อมูลใน volume ด้วย (รันครั้งต่อไปจะ seed ใหม่)
```

---

## ข้อมูลตัวอย่าง (Auto Seed)

ทุกครั้งที่ backend เริ่มทำงาน จะรัน `seed.py` โดยอัตโนมัติ และสร้างข้อมูลต่อไปนี้ **เฉพาะที่ยังไม่มี**:

| ข้อมูล | รายละเอียด |
|---|---|
| Users | 2 บัญชี (ลูกค้า 1, ผู้จัดการโรงงาน 1) — ดู[บัญชีผู้ใช้ทดสอบ](#บัญชีผู้ใช้ทดสอบ) |
| Job Order | `Z-2046` — Die-Casting Part, เป้าหมาย 5,000 shots (ทำแล้ว 3,250), Yield Rate 98.4% |
| Post-Processing | 4 ขั้นตอน (Casting Done ✔, CNC & Deburring ⏳, CMM & X-Ray, Coating) |
| QC Report | `QC-99823` พร้อมผลตรวจ 3 รายการ (Outer Dia., Thickness, X-Ray Scan) |
| Logistics | ใบส่งของ `DO-2026-0718` พร้อมข้อมูลรถและลิงก์ GPS |

- **Idempotent:** รีสตาร์ทกี่ครั้งก็ไม่สร้างข้อมูลซ้ำ และไม่เขียนทับข้อมูลที่ถูกแก้ไขไปแล้ว (เช่น สถานะที่เปลี่ยนจาก Edge Case Simulator)
- **ปิดการ seed:** ตั้งค่า `SEED_ON_STARTUP=false` ใน `.env`
- **รันด้วยมือ:** `docker compose exec backend python seed.py`
- **เริ่มใหม่ทั้งหมด:** `docker compose down -v && docker compose up --build`

---

## บัญชีผู้ใช้ทดสอบ

| บทบาท | Username | Password |
|---|---|---|
| ลูกค้า / ผู้จัดซื้อ | `Jeab@company.com` | `Jeab` |
| ผู้จัดการโรงงาน | `admin@factory.com` | `password123` |

> บัญชีเหล่านี้สำหรับทดสอบเท่านั้น สำหรับการใช้งานจริงต้องเปลี่ยนรหัสผ่านและเพิ่มการเข้ารหัส (ดู[ข้อจำกัดที่ทราบ](#ข้อจำกัดที่ทราบ))

---

## หน้าจอการใช้งาน

| หน้า | ไฟล์ | คำอธิบาย |
|---|---|---|
| เข้าสู่ระบบ | `login.html` | เลือกบทบาท กรอก username/password แล้วรับ token |
| แดชบอร์ดหลัก | `dashboard.html` | Timeline, Shot Count, Yield Rate, สถานะ Defect, ปุ่ม Edge Case Simulator |
| ขั้นตอนหลังการหล่อ | `tracking.html` | Stepper แสดงความคืบหน้า 4 ขั้นตอน |
| รายงาน QC & จัดส่ง | `qc-report.html` | เอกสาร QC ดิจิทัล + สถานะโลจิสติกส์ |

---

## API Reference

เรียกผ่าน Nginx ที่ `http://localhost/api/v1/...` (Nginx ตัดคำนำหน้า `/api` แล้วส่งต่อไปที่ backend เป็น `/v1/...`)
backend ไม่เปิดพอร์ตออกภายนอกใน Docker Compose

### Authentication

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| `POST` | `/v1/auth/login` | เข้าสู่ระบบด้วย username/password (บทบาทอ่านจากฐานข้อมูล) |
| `POST` | `/v1/auth/register` | ลงทะเบียนผู้ใช้ใหม่ (username ซ้ำจะได้ 400) |

### Job Orders

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| `GET` | `/v1/jobs/{job_id}/dashboard` | ข้อมูลแดชบอร์ดของ Job Order |
| `POST` | `/v1/jobs/{job_id}/edge-case` | จำลองสถานการณ์ `case_type`: `normal`, `iot_loss`, `breakdown` |
| `POST` | `/v1/jobs/{job_id}/concession` | บันทึกการตัดสินใจกรณีพบของเสีย (`action_selected`) |
| `POST` | `/v1/jobs` | สร้าง Job Order ใหม่ |

> ปุ่ม "ของเสียวิกฤต (Defect Warning)" บนหน้า Dashboard ไม่เรียก `/edge-case` แต่เปิดหน้าต่างให้เลือกการตัดสินใจ แล้วส่งไปที่ `/concession`

### Post-Processing, QC & Logistics

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| `GET` | `/v1/jobs/{job_id}/post-processing` | รายการขั้นตอนหลังการหล่อ (เรียงตาม `step_no`) |
| `GET` | `/v1/jobs/{job_id}/qc-report` | รายงานผลตรวจสอบคุณภาพ |
| `GET` | `/v1/jobs/{job_id}/logistics` | ข้อมูลการจัดส่งและ GPS |

> ถ้า Job ไม่มีข้อมูลในตารางเหล่านี้ endpoint จะตอบข้อมูลตัวอย่างค่าเริ่มต้นกลับไป (fallback) ส่วน `dashboard` จะตอบ `404` ถ้าไม่พบ Job Order

### System

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| `GET` | `/v1/health` | ตรวจสอบการเชื่อมต่อฐานข้อมูล และจำนวน Job Order |

<details>
<summary><b>ตัวอย่าง Request/Response — POST /v1/auth/login</b></summary>

**Request**
```json
{
  "role": "manager",
  "username": "admin@factory.com",
  "password": "password123"
}
```

**Response**
```json
{
  "access_token": "mock-jwt-token-admin@factory.com-2026",
  "token_type": "bearer",
  "role": "manager"
}
```
</details>

---

## ตัวแปรแวดล้อม

กำหนดในไฟล์ `.env` (ตัวอย่างอยู่ใน `.env.example`) ซึ่ง `docker-compose.yml` และ backend อ่านค่าจากไฟล์นี้

| ตัวแปร | ใช้โดย | คำอธิบาย |
|---|---|---|
| `POSTGRES_USER` | db | ผู้ใช้ฐานข้อมูล |
| `POSTGRES_PASSWORD` | db | รหัสผ่านฐานข้อมูล |
| `POSTGRES_DB` | db | ชื่อฐานข้อมูล |
| `DATABASE_URL` | backend | Connection string เช่น `postgresql://USER:PASSWORD@db:5432/DB_NAME` |
| `SEED_ON_STARTUP` | backend | (ไม่บังคับ) ค่าเริ่มต้น `true` — ตั้งเป็น `false` เพื่อปิดการ seed อัตโนมัติ |

> ค่า `USER` / `PASSWORD` / `DB_NAME` ใน `DATABASE_URL` ต้องตรงกับ `POSTGRES_*`
> สำหรับการใช้งานจริง (Production) ควรเปลี่ยนรหัสผ่านทั้งหมด และไม่ควร commit ไฟล์ `.env` ขึ้น repository

---

## การพัฒนา

### รัน Backend แยกเพื่อพัฒนา (Hot Reload)

```bash
cd "Web Application Development/backend"
pip install -r requirements.txt
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/DB_NAME"
uvicorn main:app --reload --port 8000
```

เมื่อรันแยก จะเปิด Swagger UI ได้ที่ `http://localhost:8000/docs` และเรียก API ที่ `http://localhost:8000/v1/...` (ไม่มีคำนำหน้า `/api`)

### เทคโนโลยีที่ใช้

- **Backend**: Python 3.11 · FastAPI · Uvicorn · SQLAlchemy · Pydantic v2 · psycopg2
- **Frontend**: HTML5 · Tailwind CSS (CDN) · Vanilla JavaScript (Fetch API)
- **Database**: PostgreSQL 15
- **Infrastructure**: Docker Compose · Nginx (reverse proxy) · Cloudflare Tunnel (cloudflared)

---

## ข้อจำกัดที่ทราบ

รายการนี้ระบุตามสถานะจริงของโค้ดปัจจุบัน เพื่อให้ผู้ตรวจสอบและผู้พัฒนาต่อทราบ

- **การยืนยันตัวตน:** รหัสผ่านถูกเก็บเป็น plain text ในฐานข้อมูล และ token เป็นค่าจำลอง (`mock-jwt-token-...`) ที่ backend ไม่ได้ตรวจสอบในแต่ละ request
- **บทบาทผู้ใช้:** field `role` ที่ส่งมาตอน login ไม่ได้ถูกตรวจ backend ใช้ role จากฐานข้อมูล และยังไม่มีการจำกัดสิทธิ์ตาม role
- **Job Order ตายตัว:** หน้าเว็บผูกกับ Job `Z-2046` (ยังไม่มีหน้าเลือก/สร้าง Job)
- **ข้อมูล QC / Logistics / Post-Processing:** API มีเฉพาะการอ่าน (`GET`) ข้อมูลเพิ่มผ่าน seed หรือฐานข้อมูลโดยตรง
- **Edge Case Simulator:** เป็นการจำลองสถานะโดยแก้ข้อมูลใน `job_orders` ไม่ได้เชื่อมกับอุปกรณ์ IoT จริง
- **Microservices:** ปัจจุบันเป็น modular monolith ส่วน microservices เป็นสถาปัตยกรรมเป้าหมายตามหัวข้อ[สถาปัตยกรรม](#สถาปัตยกรรม)

---

<div align="center">

Made for **Die-Casting QC Platform**

</div>
