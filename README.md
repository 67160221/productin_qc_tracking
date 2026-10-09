# TRACK-PRO Match

แพลตฟอร์ม B2B จับคู่ **โรงหล่อโลหะ (die-casting)** ↔ **โรงงานกึ่งโลหะ / downstream** (CNC, อโนไดซ์, พ่นสี ฯลฯ)
แบบสองทาง — ฝั่งไหนก็ประกาศความต้องการ (RFQ) และเลือกคู่ค้าได้ เมื่อตกลงราคาแล้วระบบสร้าง **Job Order**
และส่งต่อเข้าระบบติดตามการผลิต / QC / โลจิสติกส์ของ TRACK-PRO ต่อทันที

> **สถานะ:** โค้ดผ่านการรีวิวและแก้ไขด้านความปลอดภัยแล้ว 2 รอบ (ดู [`docs/SECURITY-CHANGES.md`](docs/SECURITY-CHANGES.md))
> ชุดทดสอบฝั่ง backend (`pytest`) **เขียนไว้แล้วแต่ยังไม่เคยถูกรัน** — ให้รัน `pytest -v` และแก้ให้ผ่านก่อนใช้งานจริง
> ส่วนตรวจ frontend (XSS checker, smoke test) รันผ่านแล้ว

## สารบัญ

1. [ภาพรวมการทำงาน](#ภาพรวมการทำงาน)
2. [สถาปัตยกรรมและโครงสร้างโปรเจกต์](#สถาปัตยกรรมและโครงสร้างโปรเจกต์)
3. [เริ่มใช้งาน](#เริ่มใช้งาน)
4. [ตั้งค่า (.env)](#ตั้งค่า-env)
5. [บทบาทและสิทธิ์การมองเห็นข้อมูล](#บทบาทและสิทธิ์การมองเห็นข้อมูล)
6. [วงจรสถานะ](#วงจรสถานะ)
7. [อัลกอริทึมจับคู่](#อัลกอริทึมจับคู่)
8. [API](#api)
9. [ฐานข้อมูล: migration, สำรอง, กู้คืน](#ฐานข้อมูล-migration-สำรอง-กู้คืน)
10. [การทดสอบ](#การทดสอบ)
11. [ความปลอดภัย](#ความปลอดภัย)
12. [Checklist ก่อนขึ้น production](#checklist-ก่อนขึ้น-production)
13. [แก้ปัญหาที่พบบ่อย](#แก้ปัญหาที่พบบ่อย)

## ภาพรวมการทำงาน

```
สมัครองค์กร ──► ผู้ดูแลแพลตฟอร์มตรวจและ "ยืนยัน" ──► ล็อกอินได้
                                                          │
 ผู้ประกาศ (ผู้ซื้อ)                                       │            ผู้ถูกจับคู่ (ผู้ผลิต)
 ───────────────────                                       ▼            ─────────────────────
 เพิ่ม Capability ของตัวเอง (ให้ถูกค้นเจอ)        เพิ่ม Capability (process, วัสดุ, tolerance, กำลังผลิต)
 ประกาศ RFQ  ──► กด "ค้นหาคู่จับคู่" (run-match)
                    └─ ระบบให้คะแนน 0–100 พร้อมเหตุผล ──► เห็นใน "Match ที่เข้ามาหาฉัน" (incoming.html)
                                                          ตอบรับ / ปฏิเสธ (ครั้งเดียว)
                                                          ส่งใบเสนอราคา (ส่งใหม่ = แทนที่ใบเดิม)
 ดูใบเสนอราคา ──► ยืนยันใบที่เลือก ─────────────────────► ได้งาน
                    └─ สร้าง Job Order ──► Dashboard / Post-processing / QC Report / Logistics
                       (ใบอื่นถูกปฏิเสธ, Match อื่นถูกปิดอัตโนมัติ)
```

หน้าเว็บ (`frontend/`)

| หน้า | ใครใช้ | ทำอะไร |
|---|---|---|
| `login.html` | ทุกคน | เข้าสู่ระบบ / สมัครองค์กร (สมัครแล้วต้องรอยืนยัน) |
| `partners.html` | ผู้ประกาศ | โปรไฟล์ + Capability, ประกาศ RFQ, ค้นหาคู่, ดูใบเสนอราคาและยืนยัน |
| `incoming.html` | ผู้ถูกจับคู่ | Match ที่เข้ามา: ตอบรับ/ปฏิเสธ, ส่งใบเสนอราคา, ดูผล |
| `dashboard.html` | ผู้ซื้อ + ผู้ผลิตของ Job | ความคืบหน้า, Yield, สถานะ QC |
| `tracking.html` | เช่นเดียวกัน | ขั้นตอน Post-processing |
| `qc-report.html` | เช่นเดียวกัน | รายงาน QC + ข้อมูลขนส่ง |
| `admin.html` | ผู้ดูแลแพลตฟอร์ม | ยืนยัน / ยกเลิกการยืนยันองค์กร |

## สถาปัตยกรรมและโครงสร้างโปรเจกต์

```
Cloudflare Tunnel ─► nginx (frontend, 127.0.0.1:8080) ─► /api/ ─► FastAPI (backend:8000) ─► PostgreSQL
                      เสิร์ฟหน้าเว็บ + CSP/security headers        (ไม่เปิดพอร์ตออกนอก compose)
```

```
trackpro-match/
├── docker-compose.yml        db (+healthcheck) · backend · frontend · cloudflared
├── .env.example              ตัวอย่างค่าตั้ง (ห้ามใส่ความลับจริงในไฟล์นี้)
├── backend/
│   ├── main.py               endpoint ทั้งหมด + กติกาสิทธิ์/สถานะ
│   ├── models.py  schemas.py ตาราง / รูปแบบข้อมูลเข้า-ออก (+ validation, ความยาวสูงสุด)
│   ├── auth.py               bcrypt, JWT, require_platform_admin
│   ├── ratelimit.py          rate limiter ของ login/register
│   ├── matching.py           อัลกอริทึมจับคู่ (rule-based, อธิบายได้)
│   ├── seed.py               ข้อมูลตัวอย่างสำหรับ dev เท่านั้น
│   ├── create_platform_admin.py   สร้างผู้ดูแลแพลตฟอร์ม
│   └── tests/                pytest (SQLite ชั่วคราว)
├── frontend/                 HTML + common.js (helper: h(), escapeHtml(), safeUrl()) + default.conf (nginx)
├── db/migrations/            SQL สำหรับอัปเกรด DB เดิม
├── scripts/                  backup.sh · restore.sh · check_frontend_xss.py · smoke_frontend.js · test_common_js.js
└── docs/                     SECURITY-CHANGES.md · หน้า mock อ้างอิง
```

โครงสร้างข้อมูล

```
Organization (caster | finisher | both | platform)   ← platform = ผู้ดูแล สมัครเองไม่ได้ และไม่ถูกนำไปจับคู่
 ├─ User (role: admin | member, is_platform_admin)
 └─ Capability (process, material, min_tolerance_mm, max_part_weight_kg, capacity_per_month)
Requirement/RFQ (posted_by_org, seeking_org_type, status: open | matched | closed)
 └─ Match (candidate_org, score, reasons, status)      UNIQUE(requirement, candidate)
      └─ Quote (unit_price, currency, lead_time_days, terms, status)
JobOrder (requirement, buyer_org, supplier_org) ── PostProcessingStep / QCReport / Logistics
```

## เริ่มใช้งาน

ต้องมี Docker + Docker Compose

```bash
cp .env.example .env
# แก้ .env — ดูหัวข้อ "ตั้งค่า" (อย่างน้อย: POSTGRES_PASSWORD, JWT_SECRET_KEY, DATABASE_URL)

docker compose up --build

# 1) สร้างผู้ดูแลแพลตฟอร์ม (จำเป็น — ไม่มีคนนี้ = ไม่มีใครยืนยันองค์กรใหม่ได้)
docker compose exec -e ADMIN_EMAIL=you@company.com backend python create_platform_admin.py
#    ระบบจะถามรหัสผ่าน (อย่างน้อย 12 ตัวอักษร) แบบไม่แสดงบนจอ

# 2) (เฉพาะเครื่อง dev) ข้อมูลตัวอย่าง — ปฏิเสธการรันเมื่อ APP_ENV=production
docker compose exec -e APP_ENV=development -e SEED_PASSWORD='ตั้งเอง-12-ตัวขึ้นไป' backend python seed.py
```

เปิด `http://localhost:8080` → ล็อกอินด้วยบัญชีผู้ดูแล ระบบพาไป `admin.html` เพื่อยืนยันองค์กรที่สมัครเข้ามา
(องค์กรที่ยังไม่ยืนยัน ล็อกอินไม่ได้ และไม่ถูกนำไปจับคู่)

รันทดสอบโดยไม่ใช้ Docker: `cd backend && pip install -r requirements-dev.txt && pytest -v`

## ตั้งค่า (.env)

| ตัวแปร | จำเป็น | ความหมาย |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_DB` | ✓ | ชื่อผู้ใช้/ชื่อฐานข้อมูล |
| `POSTGRES_PASSWORD` | ✓ | สร้างด้วย `openssl rand -hex 24` (ใช้ hex เพื่อไม่ต้อง URL-encode) |
| `DATABASE_URL` | ✓ | `postgresql://USER:PASSWORD@db:5432/DB` — รหัสผ่านต้องตรงกับข้างบน |
| `JWT_SECRET_KEY` | ✓ | สร้างด้วย `openssl rand -hex 32` — ไม่ตั้ง = แอปไม่ยอมสตาร์ท |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | อายุ token (ค่าเริ่มต้น 480) |
| `CORS_ORIGINS` | ✓ | โดเมนที่อนุญาต คั่นด้วย `,` (ใส่เฉพาะที่ใช้จริง) |
| `CLOUDFLARE_TUNNEL_TOKEN` | production | token ของ Cloudflare Tunnel |
| `LOGIN_IP_LIMIT` | | login ต่อ IP ต่อนาที (20) |
| `LOGIN_FAILURE_LIMIT` | | ผิดกี่ครั้งต่อ (อีเมล+IP) ก่อนล็อก 15 นาที (5) |
| `REGISTER_IP_LIMIT` | | สมัครต่อ IP ต่อชั่วโมง (5) |
| `RATE_LIMIT_ENABLED` | | `false` = ปิด rate limit ทั้งหมด |

compose ตั้งค่าเอง: `APP_ENV=production` (กัน `seed.py`) และ `TRUST_PROXY_HEADERS=true`
(ให้ backend เชื่อ `X-Client-IP` ที่ nginx ใส่ให้ — **ห้ามเปิดถ้า backend เข้าถึงได้โดยตรงจากภายนอก**)

## บทบาทและสิทธิ์การมองเห็นข้อมูล

หลักการ: ล็อกอินแล้ว ≠ เห็นข้อมูลของทุกองค์กร ทุก endpoint ตรวจ "เป็นเจ้าของ/เป็นคู่สัญญา" ฝั่งเซิร์ฟเวอร์

| ข้อมูล | ผู้ประกาศ RFQ | ผู้ถูกจับคู่ (Match ยัง `proposed`/`accepted`) | ผู้ถูกจับคู่ที่ปฏิเสธ/แพ้ | องค์กรอื่น |
|---|---|---|---|---|
| รายละเอียด RFQ เต็ม (ชื่องาน, ชิ้นงาน, จำนวน) | ✓ | ✓ | ✗ (แบบย่อ) | ✗ (แบบย่อ, เฉพาะ RFQ ที่ยังเปิด) |
| รายการ Match ของ RFQ | ทุกราย | เฉพาะของตัวเอง | เฉพาะของตัวเอง | 404 |
| ใบเสนอราคาของ Match | ✓ | ✓ (ของตัวเอง) | ✓ (ของตัวเอง) | 404 |
| Job Order | ผู้ซื้อ | ผู้ผลิต | — | 403 |

- **แบบย่อ** (`visibility: "public"`) = process, วัสดุ, tolerance, พื้นที่, กำหนดส่ง, สถานะ — ไม่มีชื่อ RFQ ชื่อชิ้นงาน จำนวน และผู้ประกาศ
- **ผู้ดูแลแพลตฟอร์ม** (`is_platform_admin`) ใช้ได้เฉพาะ `/v1/admin/*` ตั้งได้ทางสคริปต์เท่านั้น ไม่มีทางตั้งผ่าน API
- **Admin ขององค์กร** แก้โปรไฟล์องค์กรได้ · **member** ใช้งานประจำวัน

## วงจรสถานะ

ทุกการเปลี่ยนสถานะถูกตรวจฝั่งเซิร์ฟเวอร์ ทำซ้ำหรือข้ามขั้นได้ `409`

```
Match      proposed ──ผู้ถูกจับคู่ตอบ (ครั้งเดียว)──► accepted | declined
           accepted ──ผู้ประกาศเลือกใบของคนอื่น──────► closed
Quote      pending  ──ผู้ประกาศยืนยัน──► accepted
                    ──ผู้ประกาศเลือกใบอื่น──► rejected
                    ──ผู้ถูกจับคู่ส่งใบใหม่──► superseded
Requirement open ──ยืนยันใบเสนอราคา──► matched   (และสร้าง Job Order 1 ใบเท่านั้น)
```

- ส่งใบเสนอราคาได้เมื่อ Match เป็น `accepted` และ RFQ ยัง `open`
- การยืนยันใบเสนอราคาล็อกแถว RFQ (`SELECT … FOR UPDATE` บน PostgreSQL) กันกดพร้อมกันแล้วได้ 2 Job
- `run-match` ซ้ำได้ปลอดภัย: อัปเดตคะแนน คงสถานะที่ผู้ถูกจับคู่ตอบไว้ และลบเฉพาะ Match ที่ยัง `proposed` ที่ไม่ผ่านเกณฑ์แล้ว

## อัลกอริทึมจับคู่

กฎล้วน อธิบายได้ (`backend/matching.py`) — เงื่อนไขบังคับ: องค์กร **verified**, ประเภทตรงที่มองหา (หรือ `both`),
มี Capability ที่ตรง process (และวัสดุ ถ้าระบุ) จากนั้นให้คะแนนรวม 100:

| ปัจจัย | คะแนนเต็ม | ที่มา |
|---|---|---|
| Tolerance | 25 | tolerance ที่ทำได้ดีที่สุดเทียบกับที่ต้องการ |
| ใบรับรอง | 15 | สัดส่วนใบรับรองที่ครบ |
| กำลังผลิตเหลือ | 15 | `capacity_per_month` เทียบจำนวนที่ต้องการ |
| พื้นที่ | 10 | จังหวัด/ภูมิภาคตรงกัน |
| ประวัติผลงาน | 35 | Yield เฉลี่ยจาก Job ที่เคยทำบนแพลตฟอร์มนี้ (องค์กรใหม่ได้ค่ากลาง) |

ทุกผลมี `reasons` เป็นข้อความอ่านได้ว่าทำไมได้คะแนนนี้

## API

Base path: `/api/v1` ผ่าน nginx (ตรงเข้า backend คือ `/v1`) · ยกเว้น `register`/`login` ต้องส่ง `Authorization: Bearer <token>`
เอกสาร Swagger (`/docs`) เปิดเฉพาะเมื่อ `APP_ENV` ไม่ใช่ `production` — compose ตั้งเป็น production จึงปิดไว้ (ไม่ให้ใครดู schema ผ่าน tunnel) ถ้าต้องการดูตอน dev ให้ override `APP_ENV` ของ backend

| Method + Path | สิทธิ์ | หน้าที่ |
|---|---|---|
| `POST /v1/auth/register` | สาธารณะ (rate limit) | สมัครองค์กร + ผู้ใช้แรก (admin) — `verified=false` |
| `POST /v1/auth/login` | สาธารณะ (rate limit) | คืน token; 403 ถ้าองค์กรยังไม่ verified |
| `GET/PATCH /v1/organizations/me` | login (PATCH: admin องค์กร) | โปรไฟล์องค์กร |
| `GET /v1/organizations/{id}` | login | โปรไฟล์องค์กรอื่น |
| `GET/POST /v1/organizations/me/capabilities` | login | ดู/เพิ่ม Capability |
| `DELETE /v1/capabilities/{id}` | เจ้าขององค์กร | ลบ Capability |
| `POST /v1/requirements` | login | ประกาศ RFQ |
| `GET /v1/requirements?mine_only=` | login | รายการ RFQ ที่เปิดอยู่ (เต็มสำหรับของตัวเอง/ที่ถูกจับคู่, ย่อสำหรับคนอื่น) |
| `GET /v1/requirements/{id}` | login | รายละเอียด (เต็ม/ย่อ ตามสิทธิ์) |
| `POST /v1/requirements/{id}/run-match` | ผู้ประกาศ | คำนวณ/อัปเดต Match |
| `GET /v1/requirements/{id}/matches` | ผู้ประกาศ (ทุกราย) / ผู้ถูกจับคู่ (ของตัวเอง) | ผล Match |
| `GET /v1/matches/incoming?status=` | login | Match ที่เข้ามาหาองค์กรฉัน |
| `POST /v1/matches/{id}/respond` | ผู้ถูกจับคู่ | `{"status": "accepted" \| "declined"}` ครั้งเดียว |
| `POST /v1/matches/{id}/quotes` | ผู้ถูกจับคู่ (Match accepted) | ส่งใบเสนอราคา |
| `GET /v1/matches/{id}/quotes` | สองฝ่ายของ Match | ดูใบเสนอราคา |
| `POST /v1/quotes/{id}/accept` | ผู้ประกาศ | ยืนยัน → สร้าง Job Order |
| `GET /v1/jobs`, `GET /v1/jobs/{code}/dashboard` | buyer/supplier ของ Job | ภาพรวมงาน |
| `GET /v1/jobs/{code}/post-processing` · `/qc-report` · `/logistics` | buyer/supplier | ติดตามผล |
| `POST /v1/jobs/{code}/edge-case` · `/concession` | buyer/supplier | **จำลอง**สถานการณ์ผิดปกติ (สำหรับ demo — ควรปิดใน production, ดูหัวข้อความปลอดภัย) |
| `GET /v1/admin/organizations?verified=` | ผู้ดูแลแพลตฟอร์ม | รายการองค์กร |
| `POST /v1/admin/organizations/{id}/verify` · `/unverify` | ผู้ดูแลแพลตฟอร์ม | ยืนยัน / ยกเลิก (token เดิมใช้ไม่ได้ทันที) |

รหัสที่พบบ่อย: `401` ไม่ได้ล็อกอิน/token หมดอายุ · `403` ไม่มีสิทธิ์ (การเขียน) · `404` ไม่พบ/ไม่ใช่ของคุณ (การอ่าน) ·
`409` สถานะไม่ถูกต้อง · `422` ข้อมูลไม่ผ่าน validation · `429` ถูกจำกัดอัตรา (ดู header `Retry-After`)

## ฐานข้อมูล: migration, สำรอง, กู้คืน

- **ติดตั้งใหม่** — แอปสร้างตารางเองตอนสตาร์ท (`create_all`) ไม่ต้องทำอะไร
- **อัปเกรด DB เดิม** (สร้างจากเวอร์ชันก่อนรอบรีวิว) — **ต้องรันก่อนสตาร์ทโค้ดใหม่** ไม่งั้นแอปพังเพราะขาดคอลัมน์ `users.is_platform_admin`
  ```bash
  ./scripts/backup.sh        # สำรองก่อนเสมอ (ลองกับสำเนาก่อนถ้าทำได้)
  docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < db/migrations/001_security_fixes.sql
  ```
  เพิ่มคอลัมน์, **รวม Match ที่ซ้ำ** (ย้าย Quote ไปที่แถวที่เก็บไว้ ไม่ทำให้ใบเสนอราคาหาย), เพิ่ม UNIQUE `(requirement_id, candidate_org_id)`
  — รันซ้ำได้ ทำงานใน transaction เดียว
- **สำรอง** — `./scripts/backup.sh` → `backups/trackpro_*.sql.gz` (เก็บ 14 วัน ปรับด้วย `KEEP_DAYS`, ที่เก็บด้วย `BACKUP_DIR`)
  ตั้ง cron เช่น `0 2 * * * /path/to/trackpro-match/scripts/backup.sh` แล้ว **คัดลอกไฟล์ออกนอกเครื่อง**
- **กู้คืน (ซ้อม)** — `./scripts/restore.sh backups/<ไฟล์>` กู้เข้า DB ชั่วคราว `trackpro_restore_test` แล้วแสดงจำนวนแถว
  ควรซ้อมอย่างน้อยหนึ่งครั้งก่อนใช้งานจริง · เขียนทับ DB จริง: `TARGET_DB=<ชื่อ DB> CONFIRM_OVERWRITE=yes ./scripts/restore.sh <ไฟล์>` (หยุด backend ก่อน)
- ยังไม่ใช้ Alembic: การเปลี่ยน schema ครั้งต่อไปให้เพิ่มไฟล์ `db/migrations/00N_*.sql` ตามลำดับ

## การทดสอบ

```bash
# Backend (pytest + SQLite ชั่วคราว; conftest บังคับ DATABASE_URL เองเพื่อไม่แตะ DB จริง)
cd backend && pip install -r requirements-dev.txt && pytest -v

# Frontend (ใช้แค่ Python 3 และ Node ไม่ต้องติดตั้งแพ็กเกจ)
python3 scripts/check_frontend_xss.py     # ต้องได้ "0 problem(s)"
node scripts/test_common_js.js            # escapeHtml / safeUrl / safeJobCode
node scripts/smoke_frontend.js            # รัน partners + incoming ด้วย DOM จำลอง ป้อน payload XSS
```

pytest ครอบคลุม: การเข้าถึงข้ามองค์กร (matches/quotes/requirement/jobs), วงจรสถานะ (respond→quote→accept, ยืนยันซ้ำ, ผู้แข่งขัน),
`run-match` ไม่สร้างซ้ำ, flow ยืนยันองค์กรและการเพิกถอน token, rate limit, หน้า "Match ที่เข้ามา", การ sanitize `gps_url`,
และตัวตรวจ XSS ฝั่ง frontend (รวมอยู่ใน pytest)

ที่ยังไม่มีการทดสอบอัตโนมัติ: `db/migrations/*.sql` (ต้องลองกับ PostgreSQL จริง), nginx config (`nginx -t`), การแสดงผลจริงในเบราว์เซอร์

## ความปลอดภัย

**มีแล้ว**
- รหัสผ่าน bcrypt, JWT จริงที่ตรวจทุก request (รวมตรวจว่าองค์กรยัง verified), role/องค์กรกำหนดฝั่งเซิร์ฟเวอร์
- แยกข้อมูลข้ามองค์กรทุก endpoint (ตารางในหัวข้อสิทธิ์), ตรวจสถานะทุกขั้น, ล็อกแถวตอนยืนยันใบเสนอราคา
- กัน XSS: ไม่ใส่ข้อมูลผู้ใช้เป็น HTML (`h()`/`textContent`/`escapeHtml`), ลิงก์ผ่าน `safeUrl`, backend กรอง `gps_url`, ตัวตรวจ static ใน CI
- Rate limit login/register + ล็อกเมื่อรหัสผิดซ้ำ + ตอบ/ใช้เวลาเท่ากันทั้งกรณี "ไม่มีผู้ใช้" และ "รหัสผิด"
- CSP + `X-Frame-Options` + `nosniff` + `Referrer-Policy` ใน nginx · CORS จำกัดโดเมน · DB ไม่เปิดพอร์ต · เข้าเว็บผ่าน Cloudflare Tunnel
- ไม่มีความลับหรือรหัสผ่านตายตัวในโค้ด (`seed.py` สุ่มรหัสผ่านและปฏิเสธการรันเมื่อ production)

**ข้อจำกัดที่ต้องรู้**
- **CSP ยังมี `'unsafe-inline'` ใน `script-src`** (หน้าใช้ inline script + Tailwind play-CDN) จึงไม่กัน inline script ที่ถูกฉีดเข้ามา
  แต่กันโหลดสคริปต์จากโดเมนอื่นและกันการส่ง token ออกไปเว็บอื่น · ถ้าหน้าเพี้ยนหลังเปิด CSP ให้ดู console แล้วปรับ `frontend/default.conf`
- **JWT เก็บใน `localStorage`** — ถ้ามี XSS หลุดจะถูกขโมยได้ ทางที่ดีกว่าคือ cookie `HttpOnly; Secure; SameSite` (ต้องแก้ auth + CSRF)
- **Rate limiter อยู่ในหน่วยความจำของโปรเซสเดียว** รีเซ็ตเมื่อ restart ใช้ได้กับ worker เดียว (ตาม compose) — ขยายหลาย worker ต้องย้ายไป Redis
  และควรตั้ง Cloudflare Rate Limiting / Turnstile ไว้ด้านหน้าด้วย (การล็อกต่อ อีเมล+IP กันได้เฉพาะ brute force จาก IP เดียว)
- `/auth/register` ยังบอกว่าอีเมลซ้ำ (user enumeration) — แก้ให้สิ้นเชิงต้องมีการยืนยันอีเมล
- **ยังไม่ได้แก้จากรายงานรีวิว:** H4 endpoint จำลอง `edge-case`/`concession` ที่ buyer/supplier เรียกได้และเขียนทับสถานะงานจริง ·
  H6 member เพิ่ม Capability ได้ · H8 `cloudflared:latest` ไม่ pin เวอร์ชัน และ backend รันเป็น root · H9 token อายุ 8 ชม. ไม่มีการเพิกถอนรายตัว (นอกจาก un-verify องค์กร)

## Checklist ก่อนขึ้น production

- [ ] **Rotate ความลับทั้งหมดที่เคยหลุดไปกับไฟล์ `.env` เดิม**: รหัส DB, `JWT_SECRET_KEY`, Cloudflare Tunnel token
- [ ] `pytest -v` ผ่านทั้งหมด และรันตัวตรวจ frontend ผ่าน
- [ ] DB เดิม: สำรอง → รัน `db/migrations/001_security_fixes.sql` → ตรวจจำนวนแถว
- [ ] สร้างผู้ดูแลแพลตฟอร์ม (`create_platform_admin.py`) และทดสอบยืนยัน/ยกเลิกองค์กรผ่าน `admin.html`
- [ ] ทดสอบข้ามองค์กรด้วยบัญชีจริง 2 บริษัท (ต้องไม่เห็นข้อมูลกัน)
- [ ] ตั้ง `CORS_ORIGINS` เป็นโดเมนจริงเท่านั้น (เอา `localhost` ออก)
- [ ] ตั้ง cron backup + คัดลอกออกนอกเครื่อง + **ซ้อมกู้คืนหนึ่งครั้ง**
- [ ] ตั้ง Cloudflare WAF / Rate Limiting Rule หน้า `/api/v1/auth/*`
- [ ] เปิดเว็บจริงดู browser console ว่า CSP ไม่บล็อกอะไรที่จำเป็น และตรวจ header ด้วย securityheaders.com
- [ ] pin เวอร์ชัน image (`cloudflared`, `postgres`), รัน `pip-audit` กับ `requirements.txt` ในเครื่องที่ต่อเน็ตได้
- [ ] ตัดสินใจเรื่อง H4 (ปิด endpoint จำลองใน production)
- [ ] แผน rollback: `docker compose down` + image เดิม; สงสัยข้อมูลรั่ว → เปลี่ยน `JWT_SECRET_KEY` (token ทุกใบหมดอายุทันที)

## แก้ปัญหาที่พบบ่อย

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| backend ไม่สตาร์ท: `JWT_SECRET_KEY is not set` | ยังไม่ตั้งใน `.env` — `openssl rand -hex 32` |
| backend error `column users.is_platform_admin does not exist` | DB เดิมยังไม่ผ่าน `001_security_fixes.sql` |
| สมัครแล้วล็อกอินไม่ได้ (403) | ปกติ — ต้องให้ผู้ดูแลยืนยันองค์กรที่ `admin.html` ก่อน |
| ไม่มีผู้ดูแลให้ยืนยัน | รัน `create_platform_admin.py` (ดูหัวข้อเริ่มใช้งาน) |
| ล็อกอินได้ `429` | ถูก rate limit — รอตาม `Retry-After` (หรือปรับค่าใน `.env`); ทุกคนถูกจำกัดพร้อมกัน = backend เห็น IP เดียว ตรวจว่า nginx ส่ง `X-Client-IP` และตั้ง `TRUST_PROXY_HEADERS=true` |
| หน้าเว็บไม่มีสไตล์/สคริปต์หลังเปิด CSP | ดู console; ถ้าเป็น Tailwind CDN ให้ผ่อน `script-src` ใน `frontend/default.conf` หรือ build Tailwind เอง |
| ผู้ถูกจับคู่ไม่เห็น RFQ | ต้องมี Capability ที่ตรง process/วัสดุ, องค์กร verified, และผู้ประกาศต้องกด "ค้นหาคู่จับคู่" |
| `seed.py` ปฏิเสธการรัน | ตั้งใจ — ใช้ได้เฉพาะ dev: `exec -e APP_ENV=development …` |
| `pytest` ล้มเพราะ import | รันจากโฟลเดอร์ `backend` และติดตั้ง `requirements-dev.txt` |
