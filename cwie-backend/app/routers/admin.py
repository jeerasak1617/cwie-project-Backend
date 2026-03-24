"""
Admin API - จัดการ Users, อนุมัติ/ปฏิเสธ, ดูข้อมูลทั้งหมด
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import User, UserRole, UserStatus

router = APIRouter(prefix="/admin", tags=["👑 Admin"])

admin_only = require_roles(["admin"])


# ==================== Dashboard ====================

@router.get("/dashboard", summary="Dashboard สรุปข้อมูล")
async def dashboard(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    """สรุปจำนวน user แยกตาม role และ status"""
    total = db.query(User).filter(User.deleted_at.is_(None)).count()
    pending = db.query(User).filter(User.status == UserStatus.pending, User.deleted_at.is_(None)).count()
    active = db.query(User).filter(User.status == UserStatus.active, User.deleted_at.is_(None)).count()

    # นับแยก role
    role_counts = {}
    for role in UserRole:
        count = db.query(User).filter(User.sys_role == role, User.deleted_at.is_(None)).count()
        role_counts[role.value] = count

    return {
        "total_users": total,
        "pending_approval": pending,
        "active_users": active,
        "by_role": role_counts,
    }


# ==================== จัดการ Users ====================

@router.get("/users", summary="ดู Users ทั้งหมด (filter ได้)")
async def list_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    """ดูรายชื่อ user ทั้งหมด พร้อม filter และ pagination"""
    q = db.query(User).filter(User.deleted_at.is_(None))

    if role:
        q = q.filter(User.sys_role == role)
    if status:
        q = q.filter(User.status == status)
    if search:
        q = q.filter(
            (User.first_name_th.ilike(f"%{search}%")) |
            (User.last_name_th.ilike(f"%{search}%")) |
            (User.student_code.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "users": [
            {
                "id": u.id,
                "sys_role": u.sys_role.value if u.sys_role else None,
                "status": u.status.value,
                "first_name_th": u.first_name_th,
                "last_name_th": u.last_name_th,
                "student_code": u.student_code,
                "email": u.email,
                "phone": u.phone,
                "position": u.position,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}", summary="ดูข้อมูล User คนเดียว")
async def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    return {
        "id": user.id,
        "line_user_id": user.line_user_id,
        "sys_role": user.sys_role.value if user.sys_role else None,
        "status": user.status.value,
        "student_code": user.student_code,
        "employee_code": user.employee_code,
        "prefix_th": user.prefix_th,
        "first_name_th": user.first_name_th,
        "last_name_th": user.last_name_th,
        "email": user.email,
        "phone": user.phone,
        "mobile": user.mobile,
        "position": user.position,
        "expertise": user.expertise,
        "department_id": user.department_id,
        "company_id": user.company_id,
        "photo_url": user.photo_url,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
        "rejection_reason": user.rejection_reason,
    }


# ==================== อนุมัติ / ปฏิเสธ ====================

@router.post("/users/{user_id}/approve", summary="อนุมัติ User")
async def approve_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    if user.status != UserStatus.pending:
        raise HTTPException(400, f"ไม่สามารถอนุมัติได้ สถานะปัจจุบัน: {user.status.value}")

    user.status = UserStatus.active
    user.approved_by_user_id = admin.id
    user.approved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": f"อนุมัติ {user.first_name_th} {user.last_name_th} สำเร็จ"}


@router.post("/users/{user_id}/reject", summary="ปฏิเสธ User")
async def reject_user(
    user_id: int,
    reason: str = "ข้อมูลไม่ถูกต้อง",
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    if user.status != UserStatus.pending:
        raise HTTPException(400, f"ไม่สามารถปฏิเสธได้ สถานะปัจจุบัน: {user.status.value}")

    user.status = UserStatus.rejected
    user.rejection_reason = reason
    user.approved_by_user_id = admin.id
    user.approved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": f"ปฏิเสธ {user.first_name_th} {user.last_name_th}"}


@router.post("/users/{user_id}/deactivate", summary="ระงับ User")
async def deactivate_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    user.status = UserStatus.inactive
    db.commit()
    return {"success": True, "message": "ระงับผู้ใช้งานสำเร็จ"}


@router.delete("/users/{user_id}", summary="ลบ User (soft delete)")
async def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    user.deleted_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ลบผู้ใช้งานสำเร็จ"}
