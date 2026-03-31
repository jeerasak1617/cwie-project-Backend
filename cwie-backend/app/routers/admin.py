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


@router.put("/users/{user_id}", summary="แก้ไขข้อมูล User (กำหนดบริษัท/สาขา)")
async def update_user(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(404, "ไม่พบผู้ใช้งาน")
    if "company_id" in data and data["company_id"]:
        user.company_id = int(data["company_id"])
    if "department_id" in data and data["department_id"]:
        user.department_id = int(data["department_id"])
    if "position" in data:
        user.position = data["position"]
    db.commit()
    return {"success": True, "message": "อัปเดตข้อมูลสำเร็จ"}


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

# ==================== จัดการภาคเรียน ====================

@router.get("/semesters", summary="ดูภาคเรียนทั้งหมด")
async def list_semesters(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Semester
    semesters = db.query(Semester).order_by(Semester.year.desc(), Semester.term.desc()).all()
    return {
        "semesters": [
            {
                "id": s.id,
                "term": s.term,
                "year": s.year,
                "start_date": s.start_date.isoformat() if s.start_date else None,
                "end_date": s.end_date.isoformat() if s.end_date else None,
                "internship_start": s.internship_start.isoformat() if s.internship_start else None,
                "internship_end": s.internship_end.isoformat() if s.internship_end else None,
                "is_current": s.is_current,
            }
            for s in semesters
        ],
    }


@router.post("/semesters", summary="สร้างภาคเรียนใหม่")
async def create_semester(
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import Semester
    from datetime import date as dt_date

    term = data.get("term")
    year = data.get("year")
    if not term or not year:
        raise HTTPException(400, "กรุณาระบุ term และ year")

    term = int(term)
    year = int(year)

    existing = db.query(Semester).filter(Semester.term == term, Semester.year == year).first()
    if existing:
        raise HTTPException(400, f"ภาคเรียน {term}/{year} มีอยู่แล้ว")

    sem = Semester(
        term=term,
        year=year,
        start_date=dt_date.fromisoformat(data["start_date"]) if data.get("start_date") else None,
        end_date=dt_date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
        internship_start=dt_date.fromisoformat(data["internship_start"]) if data.get("internship_start") else None,
        internship_end=dt_date.fromisoformat(data["internship_end"]) if data.get("internship_end") else None,
        is_current=data.get("is_current", False),
    )

    # ถ้าตั้ง is_current → ยกเลิก current ตัวอื่นทั้งหมด
    if sem.is_current:
        db.query(Semester).filter(Semester.is_current == True).update({"is_current": False})

    db.add(sem)
    db.commit()
    db.refresh(sem)
    return {"success": True, "id": sem.id, "message": f"สร้างภาคเรียน {term}/{year} สำเร็จ"}


@router.put("/semesters/{semester_id}", summary="แก้ไขภาคเรียน")
async def update_semester(
    semester_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import Semester
    from datetime import date as dt_date

    sem = db.query(Semester).filter(Semester.id == semester_id).first()
    if not sem:
        raise HTTPException(404, "ไม่พบภาคเรียน")

    if "term" in data: sem.term = int(data["term"])
    if "year" in data: sem.year = int(data["year"])
    if "start_date" in data: sem.start_date = dt_date.fromisoformat(data["start_date"]) if data["start_date"] else None
    if "end_date" in data: sem.end_date = dt_date.fromisoformat(data["end_date"]) if data["end_date"] else None
    if "internship_start" in data: sem.internship_start = dt_date.fromisoformat(data["internship_start"]) if data["internship_start"] else None
    if "internship_end" in data: sem.internship_end = dt_date.fromisoformat(data["internship_end"]) if data["internship_end"] else None
    if "is_current" in data:
        if data["is_current"]:
            db.query(Semester).filter(Semester.is_current == True, Semester.id != semester_id).update({"is_current": False})
        sem.is_current = data["is_current"]

    db.commit()
    return {"success": True, "message": "อัปเดตภาคเรียนสำเร็จ"}


@router.delete("/semesters/{semester_id}", summary="ลบภาคเรียน")
async def delete_semester(semester_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Semester
    sem = db.query(Semester).filter(Semester.id == semester_id).first()
    if not sem:
        raise HTTPException(404, "ไม่พบภาคเรียน")
    db.delete(sem)
    db.commit()
    return {"success": True, "message": "ลบภาคเรียนสำเร็จ"}


@router.put("/internships/update-hours", summary="อัปเดตชั่วโมงฝึกงานทั้งหมดจาก 560 เป็น 450")
async def update_all_internship_hours(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Internship
    count = db.query(Internship).filter(Internship.required_hours == 560).update({"required_hours": 450})
    db.commit()
    return {"success": True, "updated_count": count, "message": f"อัปเดต {count} รายการจาก 560 → 450 ชม."}

# ==================== จัดการบริษัท ====================

@router.get("/companies", summary="ดูบริษัททั้งหมด")
async def list_companies(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import Company
    q = db.query(Company).filter(Company.is_active == True)
    if search:
        q = q.filter(Company.name_th.ilike(f"%{search}%") | Company.name_en.ilike(f"%{search}%"))
    total = q.count()
    companies = q.order_by(Company.name_th).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "companies": [
            {"id": c.id, "name_th": c.name_th, "name_en": c.name_en, "phone": c.phone, "email": c.email, "is_active": c.is_active}
            for c in companies
        ],
        "total": total,
    }


@router.post("/companies", summary="เพิ่มบริษัทใหม่")
async def create_company(data: dict, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Company
    company = Company(
        name_th=data.get("name_th", ""),
        name_en=data.get("name_en", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        description=data.get("description", ""),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"success": True, "id": company.id, "message": f"เพิ่มบริษัท '{company.name_th}' สำเร็จ"}


@router.put("/companies/{company_id}", summary="แก้ไขบริษัท")
async def update_company(company_id: int, data: dict, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "ไม่พบบริษัท")
    if "name_th" in data: company.name_th = data["name_th"]
    if "name_en" in data: company.name_en = data["name_en"]
    if "phone" in data: company.phone = data["phone"]
    if "email" in data: company.email = data["email"]
    if "description" in data: company.description = data["description"]
    db.commit()
    return {"success": True, "message": "อัปเดตบริษัทสำเร็จ"}


@router.delete("/companies/{company_id}", summary="ลบบริษัท")
async def delete_company(company_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Company
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, "ไม่พบบริษัท")
    company.is_active = False
    db.commit()
    return {"success": True, "message": "ลบบริษัทสำเร็จ"}


# ==================== Admin ประเมิน (ปฐมนิเทศ + ปัจฉิมนิเทศ) ====================

@router.get("/internships", summary="ดู internship ทั้งหมด")
async def list_internships(db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Internship, Company
    internships = db.query(Internship).order_by(Internship.id.desc()).all()
    result = []
    for i in internships:
        student = db.query(User).filter(User.id == i.user_std_id).first()
        company = db.query(Company).filter(Company.id == i.company_id).first() if i.company_id else None
        result.append({
            "id": i.id,
            "internship_code": i.internship_code,
            "student_name": f"{student.first_name_th} {student.last_name_th}" if student else "-",
            "student_code": student.student_code if student else "-",
            "company_name": company.name_th if company else "-",
            "start_date": i.start_date.isoformat() if i.start_date else None,
            "end_date": i.end_date.isoformat() if i.end_date else None,
            "orientation_attended": i.orientation_attended,
            "debriefing_attended": i.debriefing_attended,
        })
    return {"internships": result}


@router.post("/evaluation", summary="Admin ให้คะแนนปฐมนิเทศ/ปัจฉิมนิเทศ")
async def admin_evaluate(
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import Evaluation, EvaluationType, ApprovalStatus, Internship
    internship_id = data.get("internship_id")
    eval_type = data.get("evaluation_type")  # "orientation" or "debriefing"
    score = data.get("score", 0)
    comment = data.get("comment", "")

    if eval_type not in ["orientation", "debriefing"]:
        raise HTTPException(400, "evaluation_type ต้องเป็น orientation หรือ debriefing")
    if score < 0 or score > 5:
        raise HTTPException(400, "คะแนนต้องอยู่ระหว่าง 0-5")

    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลการฝึกงาน")

    # เช็คว่าประเมินไปแล้วหรือยัง
    existing = db.query(Evaluation).filter(
        Evaluation.internship_id == internship_id,
        Evaluation.evaluation_type == eval_type,
    ).first()

    if existing:
        existing.total_score = score
        existing.overall_comment = comment
        existing.submitted_at = datetime.utcnow()
    else:
        ev = Evaluation(
            internship_id=internship_id,
            evaluatee_user_id=internship.user_std_id,
            evaluator_user_id=admin.id,
            evaluation_type=eval_type,
            total_score=score,
            max_possible_score=5,
            overall_comment=comment,
            status=ApprovalStatus.approved,
            submitted_at=datetime.utcnow(),
        )
        db.add(ev)

    # อัปเดต internship
    if eval_type == "orientation":
        internship.orientation_attended = score > 0
    else:
        internship.debriefing_attended = score > 0

    db.commit()
    return {"success": True, "message": f"ให้คะแนน{'ปฐมนิเทศ' if eval_type == 'orientation' else 'ปัจฉิมนิเทศ'}สำเร็จ"}


@router.get("/evaluation/{internship_id}", summary="ดูคะแนน Admin ที่ให้ไว้")
async def get_admin_evaluations(internship_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Evaluation
    evals = db.query(Evaluation).filter(
        Evaluation.internship_id == internship_id,
        Evaluation.evaluation_type.in_(["orientation", "debriefing"]),
    ).all()
    result = {}
    for e in evals:
        result[e.evaluation_type.value] = {
            "score": float(e.total_score) if e.total_score else 0,
            "comment": e.overall_comment,
        }
    return {"evaluations": result}
@router.put("/internships/{internship_id}/assign", summary="assign")
async def assign_internship(
    internship_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import Internship
    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(404, "not found")
    if "user_adv_id" in data and data["user_adv_id"]:
        internship.user_adv_id = int(data["user_adv_id"])
    if "user_sup_id" in data and data["user_sup_id"]:
        internship.user_sup_id = int(data["user_sup_id"])
    db.commit()
    return {"success": True, "message": "ok"}


# ==================== จัดการการฝึกงาน (ใหม่) ====================

@router.get("/internships/{internship_id}", summary="ดูรายละเอียดการฝึกงานของนักศึกษา")
async def get_internship_detail(internship_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    from app.models.user import Internship, Company, AttendanceRecord, DailyLog, InternshipExperience, Evaluation, Semester
    from sqlalchemy import func as sqlfunc

    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลการฝึกงาน")

    student = db.query(User).filter(User.id == internship.user_std_id).first()
    advisor = db.query(User).filter(User.id == internship.user_adv_id).first() if internship.user_adv_id else None
    supervisor = db.query(User).filter(User.id == internship.user_sup_id).first() if internship.user_sup_id else None
    company = db.query(Company).filter(Company.id == internship.company_id).first() if internship.company_id else None
    semester = db.query(Semester).filter(Semester.id == internship.semester_id).first() if internship.semester_id else None

    # ชั่วโมงจริง
    actual_hours = float(db.query(sqlfunc.coalesce(sqlfunc.sum(AttendanceRecord.hours_worked), 0)).filter(
        AttendanceRecord.internship_id == internship_id
    ).scalar() or 0)

    # นับต่างๆ
    total_attendance = db.query(AttendanceRecord).filter(AttendanceRecord.internship_id == internship_id).count()
    total_logs = db.query(DailyLog).filter(DailyLog.internship_id == internship_id).count()
    total_experiences = db.query(InternshipExperience).filter(InternshipExperience.internship_id == internship_id).count()
    total_evaluations = db.query(Evaluation).filter(Evaluation.internship_id == internship_id).count()

    return {
        "internship": {
            "id": internship.id,
            "internship_code": internship.internship_code,
            "start_date": internship.start_date.isoformat() if internship.start_date else None,
            "end_date": internship.end_date.isoformat() if internship.end_date else None,
            "required_hours": internship.required_hours,
            "completed_hours": actual_hours,
            "job_title": internship.job_title,
            "department": internship.department,
            "status_id": internship.status_id,
            "cancellation_reason": internship.cancellation_reason,
            "remarks": internship.remarks,
            "semester": f"เทอม {semester.term}/{semester.year}" if semester else None,
        },
        "student": {
            "id": student.id,
            "student_code": student.student_code,
            "full_name": f"{student.prefix_th or ''} {student.first_name_th} {student.last_name_th}".strip(),
            "email": student.email,
            "phone": student.phone or student.mobile,
            "department_id": student.department_id,
            "gpa": float(student.gpa) if student.gpa else None,
        } if student else None,
        "advisor": {
            "id": advisor.id,
            "full_name": f"{advisor.prefix_th or ''} {advisor.first_name_th} {advisor.last_name_th}".strip(),
        } if advisor else None,
        "supervisor": {
            "id": supervisor.id,
            "full_name": f"{supervisor.prefix_th or ''} {supervisor.first_name_th} {supervisor.last_name_th}".strip(),
        } if supervisor else None,
        "company": {
            "id": company.id,
            "name_th": company.name_th,
        } if company else None,
        "summary": {
            "total_attendance_days": total_attendance,
            "total_daily_logs": total_logs,
            "total_experiences": total_experiences,
            "total_evaluations": total_evaluations,
        },
    }


@router.post("/internships/{internship_id}/cancel", summary="ยกเลิกการฝึกงาน + ลบข้อมูลทั้งหมด")
async def cancel_internship(
    internship_id: int,
    data: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    from app.models.user import (
        Internship, InternshipStatus, AttendanceRecord, DailyLog,
        InternshipExperience, InternshipPlan, OffSiteRecord, LeaveRequest,
        MonthlySummary, Evaluation
    )
    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลการฝึกงาน")

    reason = data.get("reason", "ยกเลิกโดย Admin")

    # ลบข้อมูลที่เกี่ยวข้องทั้งหมด
    db.query(AttendanceRecord).filter(AttendanceRecord.internship_id == internship_id).delete()
    db.query(DailyLog).filter(DailyLog.internship_id == internship_id).delete()
    db.query(InternshipExperience).filter(InternshipExperience.internship_id == internship_id).delete()
    db.query(InternshipPlan).filter(InternshipPlan.internship_id == internship_id).delete()
    db.query(OffSiteRecord).filter(OffSiteRecord.internship_id == internship_id).delete()
    db.query(LeaveRequest).filter(LeaveRequest.internship_id == internship_id).delete()
    db.query(MonthlySummary).filter(MonthlySummary.internship_id == internship_id).delete()
    db.query(Evaluation).filter(Evaluation.internship_id == internship_id).delete()

    # ลบ internship
    student_id = internship.user_std_id
    db.delete(internship)
    db.commit()

    return {
        "success": True,
        "student_id": student_id,
        "message": f"ยกเลิกการฝึกงานและลบข้อมูลทั้งหมดสำเร็จ เหตุผล: {reason}",
    }


