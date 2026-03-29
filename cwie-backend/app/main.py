"""
CWIE System - Main Application
ระบบฝึกประสบการณ์วิชาชีพและสหกิจศึกษา
มหาวิทยาลัยราชภัฏจันทรเกษม
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, admin, student, advisor, supervisor, master_data

# Import models เพื่อให้ SQLAlchemy รู้จักทุกตาราง
from app.models import user as _models  # noqa: F401

app = FastAPI(
    title="CWIE System API",
    description="ระบบฝึกประสบการณ์วิชาชีพและสหกิจศึกษา - Backend API",
    version="2.0.0",
    docs_url="/docs",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ลงทะเบียน Routers ทั้งหมด
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)
app.include_router(student.router, prefix=settings.API_PREFIX)
app.include_router(advisor.router, prefix=settings.API_PREFIX)
app.include_router(supervisor.router, prefix=settings.API_PREFIX)
app.include_router(master_data.router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """สร้างตารางทั้งหมดอัตโนมัติเมื่อ server เริ่มทำงาน"""
    print("🔧 กำลังตรวจสอบและสร้างตารางที่ขาด...")
    Base.metadata.create_all(bind=engine)
    print("✅ ตารางพร้อมใช้งาน")


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "🎓 CWIE System API v2.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth",
            "admin": "/api/v1/admin",
            "student": "/api/v1/student",
            "advisor": "/api/v1/advisor",
            "supervisor": "/api/v1/supervisor",
            "master": "/api/v1/master",
        },
    }
