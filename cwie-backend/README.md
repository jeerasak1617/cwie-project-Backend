# 🎓 CWIE Backend API

ระบบฝึกประสบการณ์วิชาชีพและสหกิจศึกษา - มหาวิทยาลัยราชภัฏจันทรเกษม

## 📁 โครงสร้าง

```
cwie-backend/
├── app/
│   ├── main.py              ← จุดเริ่มต้น FastAPI
│   ├── core/
│   │   ├── config.py        ← ตั้งค่า (DB, LINE, JWT)
│   │   ├── database.py      ← เชื่อม PostgreSQL
│   │   └── security.py      ← JWT + Password + สิทธิ์
│   ├── models/
│   │   └── user.py          ← ตาราง 45 ตาราง (ตรง ERD)
│   ├── services/
│   │   └── line_login.py    ← LINE OAuth
│   └── routers/
│       ├── auth.py          ← 🔐 Login, LINE, ลงทะเบียน
│       ├── admin.py         ← 👑 อนุมัติ user, dashboard
│       ├── student.py       ← 🎓 เช็คชื่อ, บันทึกรายวัน
│       └── master_data.py   ← 📋 จังหวัด, คณะ, บริษัท
├── .env.example
├── requirements.txt
└── README.md
```

## 🚀 วิธีติดตั้ง + รัน (ทำครั้งเดียว)

### 1. เช็ค Python

```powershell
python --version
```

ถ้าไม่มี → โหลดที่ https://www.python.org/downloads/
(ติ๊ก ☑ Add Python to PATH ตอนติดตั้ง)

### 2. เตรียมโปรเจค

```powershell
# แตก zip แล้ว cd เข้าไป
cd D:\cwie-project\cwie-backend

# สร้างไฟล์ .env
copy .env.example .env

# แก้ .env ใส่ค่าจริง (เปิดด้วย notepad หรือ VS Code)
notepad .env
```

### 3. ติดตั้ง packages

```powershell
pip install -r requirements.txt
```

### 4. รัน

```powershell
uvicorn app.main:app --reload --port 8000
```

### 5. ทดสอบ

เปิด browser → http://localhost:8000/docs

---

## 📋 API Endpoints ทั้งหมด

### 🔐 Auth (`/api/v1/auth`)

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| POST | `/auth/login` | Admin login |
| GET | `/auth/line/login` | ขอ LINE URL |
| GET | `/auth/line/callback` | LINE callback |
| POST | `/auth/select-role` | เลือก role |
| POST | `/auth/register/student` | ลงทะเบียนนักศึกษา |
| POST | `/auth/register/advisor` | ลงทะเบียนอาจารย์ |
| POST | `/auth/register/supervisor` | ลงทะเบียนพี่เลี้ยง |
| GET | `/auth/me` | ดูข้อมูลตัวเอง |

### 👑 Admin (`/api/v1/admin`)

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/admin/dashboard` | สรุปจำนวน user |
| GET | `/admin/users` | ดู user ทั้งหมด (filter ได้) |
| GET | `/admin/users/{id}` | ดู user คนเดียว |
| POST | `/admin/users/{id}/approve` | อนุมัติ user |
| POST | `/admin/users/{id}/reject` | ปฏิเสธ user |
| POST | `/admin/users/{id}/deactivate` | ระงับ user |
| DELETE | `/admin/users/{id}` | ลบ user |

### 🎓 นักศึกษา (`/api/v1/student`)

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/student/profile` | ดูข้อมูลส่วนตัว |
| PUT | `/student/profile` | แก้ไขข้อมูล |
| GET | `/student/internship` | ดูข้อมูลฝึกงาน |
| POST | `/student/attendance/check-in` | เช็คชื่อเข้างาน |
| POST | `/student/attendance/check-out` | เช็คชื่อออกงาน |
| GET | `/student/attendance` | ดูประวัติเช็คชื่อ |
| POST | `/student/daily-log` | เขียนบันทึกรายวัน |
| GET | `/student/daily-logs` | ดูบันทึกทั้งหมด |
| PUT | `/student/daily-log/{id}` | แก้ไขบันทึก |
| POST | `/student/leave-request` | ส่งคำขอลา |
| GET | `/student/leave-requests` | ดูคำขอลา |

### 📋 ข้อมูลพื้นฐาน (`/api/v1/master`)

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/master/provinces` | จังหวัด |
| GET | `/master/districts/{province_id}` | อำเภอ |
| GET | `/master/subdistricts/{district_id}` | ตำบล |
| GET | `/master/faculties` | คณะ |
| GET | `/master/departments/{faculty_id}` | สาขา |
| GET | `/master/semesters` | ภาคเรียน |
| GET | `/master/semesters/current` | ภาคเรียนปัจจุบัน |
| GET | `/master/companies` | บริษัท (ค้นหาได้) |
| GET | `/master/companies/{id}` | ข้อมูลบริษัท |
| GET | `/master/business-types` | ประเภทธุรกิจ |
| GET | `/master/student-types` | ประเภทนักศึกษา |
| GET | `/master/skill-types` | ประเภททักษะ |
| GET | `/master/leave-types` | ประเภทการลา |
