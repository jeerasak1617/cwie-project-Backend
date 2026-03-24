"""
Auth API - Login, LINE Login, เลือก Role, ลงทะเบียน
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_roles
)
from app.models.user import User, UserRole, UserStatus
from app.services.line_login import line_login_service

router = APIRouter(prefix="/auth", tags=["🔐 Authentication"])

# เก็บ state ชั่วคราวสำหรับ LINE Login flow
pending_states: dict = {}


def _user_info(u: User) -> dict:
    name = None
    if u.first_name_th and u.last_name_th:
        parts = [u.prefix_th, u.first_name_th, u.last_name_th]
        name = " ".join(p for p in parts if p)
    return {
        "id": u.id,
        "sys_role": u.sys_role.value if u.sys_role else None,
        "status": u.status.value,
        "full_name": name,
        "photo_url": u.photo_url,
        "student_code": u.student_code,
        "email": u.email,
    }


# ==================== หน้า 1: Admin Login ====================

@router.post("/login", summary="Admin Login (username/password)")
async def admin_login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.deleted_at.is_(None)).first()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(401, "รหัสประจำตัวหรือรหัสผ่านไม่ถูกต้อง")
    if user.status != UserStatus.active:
        raise HTTPException(403, "บัญชีถูกระงับหรือรออนุมัติ")
    user.last_login_at = datetime.utcnow()
    db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.sys_role.value})
    return {"success": True, "access_token": token, "token_type": "bearer", "user": _user_info(user)}


# ==================== หน้า 2: LINE Login ====================

@router.get("/line/login", summary="ขอ LINE Login URL")
async def line_login():
    """Redirect ไปหน้า LINE Login"""
    if not settings.LINE_CHANNEL_ID:
        raise HTTPException(500, "ยังไม่ได้ตั้งค่า LINE Channel")
    url = line_login_service.get_login_url()
    return {"login_url": url}


@router.get("/line/callback", summary="LINE Login Callback")
async def line_callback(code: str = None, state: str = None, error: str = None, db: Session = Depends(get_db)):
    """LINE redirect กลับมาที่นี่พร้อม authorization code"""
    if error:
        # User กด cancel หรือ error จาก LINE
        return RedirectResponse(url="http://localhost:5173/login?error=line_cancelled")

    if not code:
        raise HTTPException(400, "ไม่ได้รับ authorization code จาก LINE")

    try:
        # 1. แลก code เป็น access token
        token_data = await line_login_service.get_access_token(code)
        access_token = token_data.get("access_token")

        # 2. ดึงโปรไฟล์จาก LINE
        profile = await line_login_service.get_profile(access_token)
        line_user_id = profile.get("userId")
        display_name = profile.get("displayName", "")
        picture_url = profile.get("pictureUrl", "")

        # 3. เช็คว่ามี user นี้ในระบบหรือยัง
        user = db.query(User).filter(User.line_user_id == line_user_id, User.deleted_at.is_(None)).first()

        if user:
            # มี user แล้ว → login เลย
            if user.status != UserStatus.active:
                return RedirectResponse(url="http://localhost:5173/pending-approval")

            user.last_login_at = datetime.utcnow()
            if picture_url:
                user.photo_url = picture_url
            db.commit()

            token = create_access_token({"sub": str(user.id), "role": user.sys_role.value})

            return RedirectResponse(url=f"http://localhost:5173/login?line_token={token}&role={user.sys_role.value}", status_code=302)
     
        else:
            # ยังไม่มี user → สร้าง registration token แล้วให้เลือก role
            reg_token = create_access_token(
                {"line_user_id": line_user_id, "display_name": display_name, "picture_url": picture_url, "type": "registration"},
                expires_delta=timedelta(hours=1)
            )
            return RedirectResponse(
                url=f"http://localhost:5173/select-role?token={reg_token}&name={display_name}"
            )

    except Exception as e:
        print(f"LINE Login Error: {e}")
        return RedirectResponse(url=f"http://localhost:5173/login?error=line_error")


# ==================== หน้า 3: เลือก Role ====================

@router.post("/select-role", summary="เลือก Role หลัง LINE Login")
async def select_role(role: str, token: str, db: Session = Depends(get_db)):
    """เลือก role (student/advisor/supervisor) หลังจาก LINE Login ครั้งแรก"""
    from app.core.security import decode_token
    payload = decode_token(token)
    if payload.get("type") != "registration":
        raise HTTPException(400, "Token ไม่ถูกต้อง")

    if role not in ["student", "advisor", "supervisor"]:
        raise HTTPException(400, "Role ไม่ถูกต้อง")

    return {
        "success": True,
        "message": f"เลือก role {role} สำเร็จ",
        "role": role,
        "token": token,
        "redirect": f"/register/{role}",
    }


# ==================== หน้า 4: ลงทะเบียน ====================

@router.post("/register/student", summary="ลงทะเบียนนักศึกษา")
async def register_student(
    token: str,
    first_name_th: str,
    last_name_th: str,
    student_code: str,
    email: str,
    prefix_th: Optional[str] = None,
    phone: Optional[str] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    from app.core.security import decode_token
    payload = decode_token(token)
    if payload.get("type") != "registration":
        raise HTTPException(400, "Token ไม่ถูกต้อง")

    # เช็คว่ารหัสนักศึกษาซ้ำไหม
    existing = db.query(User).filter(User.student_code == student_code, User.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(409, "รหัสนักศึกษานี้ลงทะเบียนแล้ว")

    user = User(
        line_user_id=payload.get("line_user_id"),
        username=student_code,
        password_hash=hash_password(student_code),  # รหัสผ่านเริ่มต้น = รหัสนักศึกษา
        sys_role=UserRole.student,
        status=UserStatus.pending,
        prefix_th=prefix_th,
        first_name_th=first_name_th,
        last_name_th=last_name_th,
        student_code=student_code,
        email=email,
        phone=phone,
        department_id=department_id,
        photo_url=payload.get("picture_url"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "ลงทะเบียนสำเร็จ รอ admin อนุมัติ", "user_id": user.id}


@router.post("/register/advisor", summary="ลงทะเบียนอาจารย์")
async def register_advisor(
    token: str,
    first_name_th: str,
    last_name_th: str,
    email: str,
    prefix_th: Optional[str] = None,
    phone: Optional[str] = None,
    department_id: Optional[int] = None,
    employee_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from app.core.security import decode_token
    payload = decode_token(token)
    if payload.get("type") != "registration":
        raise HTTPException(400, "Token ไม่ถูกต้อง")

    user = User(
        line_user_id=payload.get("line_user_id"),
        username=employee_code or email,
        password_hash=hash_password(email),
        sys_role=UserRole.advisor,
        status=UserStatus.pending,
        prefix_th=prefix_th,
        first_name_th=first_name_th,
        last_name_th=last_name_th,
        employee_code=employee_code,
        email=email,
        phone=phone,
        department_id=department_id,
        photo_url=payload.get("picture_url"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "ลงทะเบียนสำเร็จ รอ admin อนุมัติ", "user_id": user.id}


@router.post("/register/supervisor", summary="ลงทะเบียนพี่เลี้ยง")
async def register_supervisor(
    token: str,
    first_name_th: str,
    last_name_th: str,
    email: str,
    prefix_th: Optional[str] = None,
    phone: Optional[str] = None,
    company_id: Optional[int] = None,
    position: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from app.core.security import decode_token
    payload = decode_token(token)
    if payload.get("type") != "registration":
        raise HTTPException(400, "Token ไม่ถูกต้อง")

    user = User(
        line_user_id=payload.get("line_user_id"),
        username=email,
        password_hash=hash_password(email),
        sys_role=UserRole.supervisor,
        status=UserStatus.pending,
        prefix_th=prefix_th,
        first_name_th=first_name_th,
        last_name_th=last_name_th,
        email=email,
        phone=phone,
        company_id=company_id,
        position=position,
        photo_url=payload.get("picture_url"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "ลงทะเบียนสำเร็จ รอ admin อนุมัติ", "user_id": user.id}


# ==================== ดูข้อมูลตัวเอง ====================

@router.get("/me", summary="ดูข้อมูล User ปัจจุบัน")
async def get_me(user: User = Depends(get_current_user)):
    return _user_info(user)
