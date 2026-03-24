"""
CWIE System - Main Application
ระบบฝึกประสบการณ์วิชาชีพและสหกิจศึกษา
มหาวิทยาลัยราชภัฏจันทรเกษม
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, admin, student, advisor, supervisor, master_data

app = FastAPI(
    title="CWIE System API",
    description="ระบบฝึกประสบการณ์วิชาชีพและสหกิจศึกษา - Backend API",
    version="2.0.0",
    docs_url="/docs",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
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
