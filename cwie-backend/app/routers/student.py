"""
Student API - บันทึกรายวัน, เช็คชื่อเข้า-ออก, ดูข้อมูลการฝึกงาน
"""
from datetime import datetime, date, time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import (
    User, Internship, DailyLog, AttendanceRecord,
    LeaveRequest, InternshipPlan, OffSiteRecord, InternshipExperience, UserRole
)

router = APIRouter(prefix="/student", tags=["🎓 นักศึกษา"])

student_only = require_roles(["student"])


# ==================== ข้อมูลส่วนตัว ====================

@router.get("/profile", summary="ดูข้อมูลส่วนตัว")
async def get_profile(db: Session = Depends(get_db), user: User = Depends(student_only)):
    return {
        "id": user.id,
        "student_code": user.student_code,
        "prefix_th": user.prefix_th,
        "first_name_th": user.first_name_th,
        "last_name_th": user.last_name_th,
        "email": user.email,
        "phone": user.phone,
        "mobile": user.mobile,
        "gpa": float(user.gpa) if user.gpa else None,
        "department_id": user.department_id,
        "photo_url": user.photo_url,
    }


@router.put("/profile", summary="แก้ไขข้อมูลส่วนตัว")
async def update_profile(
    phone: Optional[str] = None,
    mobile: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    if phone is not None: user.phone = phone
    if mobile is not None: user.mobile = mobile
    if email is not None: user.email = email
    db.commit()
    return {"success": True, "message": "อัปเดตข้อมูลสำเร็จ"}


# ==================== การฝึกงาน ====================

@router.get("/internship", summary="ดูข้อมูลการฝึกงาน")
async def get_internship(db: Session = Depends(get_db), user: User = Depends(student_only)):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"message": "ยังไม่มีข้อมูลการฝึกงาน"}
    return {
        "id": internship.id,
        "internship_code": internship.internship_code,
        "company_id": internship.company_id,
        "start_date": internship.start_date.isoformat() if internship.start_date else None,
        "end_date": internship.end_date.isoformat() if internship.end_date else None,
        "required_hours": internship.required_hours,
        "completed_hours": float(internship.completed_hours or 0),
        "job_title": internship.job_title,
        "status_id": internship.status_id,
    }


# ==================== เช็คชื่อ (Attendance) ====================

@router.post("/attendance/check-in", summary="เช็คชื่อเข้างาน")
async def check_in(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    today = date.today()
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.internship_id == internship.id,
        AttendanceRecord.date == today,
    ).first()
    if existing and existing.check_in_time:
        raise HTTPException(400, "เช็คชื่อเข้างานวันนี้แล้ว")

    if existing:
        existing.check_in_time = datetime.now().time()
        existing.check_in_latitude = latitude
        existing.check_in_longitude = longitude
    else:
        record = AttendanceRecord(
            internship_id=internship.id,
            user_std_id=user.id,
            date=today,
            check_in_time=datetime.now().time(),
            check_in_latitude=latitude,
            check_in_longitude=longitude,
        )
        db.add(record)

    db.commit()
    return {"success": True, "message": f"เช็คชื่อเข้างานสำเร็จ เวลา {datetime.now().strftime('%H:%M')}"}


@router.post("/attendance/check-out", summary="เช็คชื่อออกงาน")
async def check_out(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    today = date.today()
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.internship_id == internship.id,
        AttendanceRecord.date == today,
    ).first()
    if not record or not record.check_in_time:
        raise HTTPException(400, "ยังไม่ได้เช็คชื่อเข้างานวันนี้")
    if record.check_out_time:
        raise HTTPException(400, "เช็คชื่อออกงานวันนี้แล้ว")

    now = datetime.now()
    record.check_out_time = now.time()
    record.check_out_latitude = latitude
    record.check_out_longitude = longitude

    # คำนวณชั่วโมงทำงาน
    check_in = datetime.combine(today, record.check_in_time)
    check_out = datetime.combine(today, now.time())
    hours = (check_out - check_in).total_seconds() / 3600
    record.hours_worked = round(hours, 2)

    db.commit()
    return {"success": True, "message": f"เช็คชื่อออกงานสำเร็จ ทำงาน {hours:.1f} ชม."}


@router.get("/attendance", summary="ดูประวัติเช็คชื่อ")
async def list_attendance(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"records": []}

    q = db.query(AttendanceRecord).filter(AttendanceRecord.internship_id == internship.id)
    if month and year:
        from sqlalchemy import extract
        q = q.filter(extract("month", AttendanceRecord.date) == month, extract("year", AttendanceRecord.date) == year)
    records = q.order_by(AttendanceRecord.date.desc()).all()

    return {
        "records": [
            {
                "id": r.id,
                "date": r.date.isoformat(),
                "check_in_time": r.check_in_time.strftime("%H:%M") if r.check_in_time else None,
                "check_out_time": r.check_out_time.strftime("%H:%M") if r.check_out_time else None,
                "hours_worked": float(r.hours_worked) if r.hours_worked else None,
                "late_minutes": r.late_minutes,
                "status_id": r.status_id,
            }
            for r in records
        ]
    }


# ==================== บันทึกรายวัน (Daily Log) ====================

@router.post("/daily-log", summary="เขียนบันทึกรายวัน")
async def create_daily_log(
    log_date: str,
    activities: str,
    learnings: Optional[str] = None,
    problems: Optional[str] = None,
    solutions: Optional[str] = None,
    hours_spent: Optional[float] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    log_date_parsed = date.fromisoformat(log_date)
    existing = db.query(DailyLog).filter(
        DailyLog.internship_id == internship.id, DailyLog.log_date == log_date_parsed
    ).first()
    if existing:
        raise HTTPException(409, "บันทึกวันนี้มีอยู่แล้ว ใช้ PUT เพื่อแก้ไข")

    log = DailyLog(
        internship_id=internship.id, user_std_id=user.id,
        log_date=log_date_parsed, activities=activities,
        learnings=learnings, problems=problems, solutions=solutions,
        hours_spent=hours_spent,
    )
    db.add(log); db.commit(); db.refresh(log)
    return {"success": True, "id": log.id, "message": "บันทึกรายวันสำเร็จ"}


@router.get("/daily-logs", summary="ดูบันทึกรายวันทั้งหมด")
async def list_daily_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"total": 0, "logs": []}

    q = db.query(DailyLog).filter(DailyLog.internship_id == internship.id)
    total = q.count()
    logs = q.order_by(DailyLog.log_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "logs": [
            {
                "id": l.id,
                "log_date": l.log_date.isoformat(),
                "activities": l.activities,
                "learnings": l.learnings,
                "problems": l.problems,
                "solutions": l.solutions,
                "hours_spent": float(l.hours_spent) if l.hours_spent else None,
                "supervisor_comment": l.supervisor_comment,
                "advisor_comment": l.advisor_comment,
                "status_id": l.status_id,
            }
            for l in logs
        ],
    }


@router.put("/daily-log/{log_id}", summary="แก้ไขบันทึกรายวัน")
async def update_daily_log(
    log_id: int,
    activities: Optional[str] = None,
    learnings: Optional[str] = None,
    problems: Optional[str] = None,
    solutions: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    log = db.query(DailyLog).filter(DailyLog.id == log_id, DailyLog.user_std_id == user.id).first()
    if not log:
        raise HTTPException(404, "ไม่พบบันทึก")
    if activities is not None: log.activities = activities
    if learnings is not None: log.learnings = learnings
    if problems is not None: log.problems = problems
    if solutions is not None: log.solutions = solutions
    db.commit()
    return {"success": True, "message": "แก้ไขบันทึกสำเร็จ"}


# ==================== ลาหยุด ====================

@router.post("/leave-request", summary="ส่งคำขอลา")
async def create_leave_request(
    leave_type_id: int,
    start_date: str,
    end_date: str,
    reason: str,
    total_days: float = 1,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    leave = LeaveRequest(
        internship_id=internship.id, user_std_id=user.id,
        leave_type_id=leave_type_id,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        total_days=total_days, reason=reason,
    )
    db.add(leave); db.commit(); db.refresh(leave)
    return {"success": True, "id": leave.id, "message": "ส่งคำขอลาสำเร็จ"}


@router.get("/leave-requests", summary="ดูคำขอลาทั้งหมด")
async def list_leave_requests(db: Session = Depends(get_db), user: User = Depends(student_only)):
    leaves = db.query(LeaveRequest).filter(LeaveRequest.user_std_id == user.id).order_by(LeaveRequest.id.desc()).all()
    return {
        "requests": [
            {
                "id": l.id,
                "leave_type_id": l.leave_type_id,
                "start_date": l.start_date.isoformat(),
                "end_date": l.end_date.isoformat(),
                "total_days": float(l.total_days) if l.total_days else None,
                "reason": l.reason,
                "status": l.status.value if l.status else None,
            }
            for l in leaves
        ]
    }


# ==================== แผนฝึกงาน (Internship Plan) ====================

@router.post("/internship-plan", summary="สร้างแผนฝึกงาน")
async def create_internship_plan(
    task_name: str,
    start_date: str,
    end_date: str,
    week_number: Optional[int] = None,
    task_description: Optional[str] = None,
    location: Optional[str] = None,
    planned_hours: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    plan = InternshipPlan(
        internship_id=internship.id,
        week_number=week_number,
        task_name=task_name,
        task_description=task_description,
        location=location,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        planned_hours=planned_hours,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"success": True, "id": plan.id, "message": "สร้างแผนฝึกงานสำเร็จ"}


@router.get("/internship-plans", summary="ดูแผนฝึกงานทั้งหมด")
async def list_internship_plans(
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"plans": []}

    plans = db.query(InternshipPlan).filter(
        InternshipPlan.internship_id == internship.id
    ).order_by(InternshipPlan.week_number, InternshipPlan.start_date).all()

    return {
        "plans": [
            {
                "id": p.id,
                "week_number": p.week_number,
                "task_name": p.task_name,
                "task_description": p.task_description,
                "location": p.location,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "planned_hours": p.planned_hours,
                "actual_hours": float(p.actual_hours) if p.actual_hours else None,
                "completion_percentage": p.completion_percentage,
                "supervisor_approved": p.supervisor_approved,
                "supervisor_comment": p.supervisor_comment,
            }
            for p in plans
        ]
    }


@router.put("/internship-plan/{plan_id}", summary="แก้ไขแผนฝึกงาน")
async def update_internship_plan(
    plan_id: int,
    task_name: Optional[str] = None,
    task_description: Optional[str] = None,
    location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    planned_hours: Optional[int] = None,
    actual_hours: Optional[float] = None,
    completion_percentage: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    plan = db.query(InternshipPlan).filter(
        InternshipPlan.id == plan_id, InternshipPlan.internship_id == internship.id
    ).first()
    if not plan:
        raise HTTPException(404, "ไม่พบแผนฝึกงาน")

    if task_name is not None: plan.task_name = task_name
    if task_description is not None: plan.task_description = task_description
    if location is not None: plan.location = location
    if start_date is not None: plan.start_date = date.fromisoformat(start_date)
    if end_date is not None: plan.end_date = date.fromisoformat(end_date)
    if planned_hours is not None: plan.planned_hours = planned_hours
    if actual_hours is not None: plan.actual_hours = actual_hours
    if completion_percentage is not None: plan.completion_percentage = completion_percentage
    db.commit()
    return {"success": True, "message": "แก้ไขแผนฝึกงานสำเร็จ"}


# ==================== บันทึกประสบการณ์ (Experience) ====================

@router.post("/experience", summary="บันทึกประสบการณ์ฝึกงาน")
async def create_experience(
    experience_date: str,
    topic: str,
    description: Optional[str] = None,
    skills_learned: Optional[str] = None,
    challenges: Optional[str] = None,
    solutions: Optional[str] = None,
    outcomes: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    exp = InternshipExperience(
        internship_id=internship.id,
        user_std_id=user.id,
        experience_date=date.fromisoformat(experience_date),
        topic=topic,
        description=description,
        skills_learned=skills_learned,
        challenges=challenges,
        solutions=solutions,
        outcomes=outcomes,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"success": True, "id": exp.id, "message": "บันทึกประสบการณ์สำเร็จ"}


@router.get("/experiences", summary="ดูประสบการณ์ทั้งหมด")
async def list_experiences(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"total": 0, "experiences": []}

    q = db.query(InternshipExperience).filter(InternshipExperience.internship_id == internship.id)
    total = q.count()
    exps = q.order_by(InternshipExperience.experience_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "experiences": [
            {
                "id": e.id,
                "experience_date": e.experience_date.isoformat(),
                "topic": e.topic,
                "description": e.description,
                "skills_learned": e.skills_learned,
                "challenges": e.challenges,
                "solutions": e.solutions,
                "outcomes": e.outcomes,
                "supervisor_comment": e.supervisor_comment,
                "advisor_comment": e.advisor_comment,
                "status": e.status.value if e.status else None,
            }
            for e in exps
        ],
    }


@router.put("/experience/{experience_id}", summary="แก้ไขประสบการณ์")
async def update_experience(
    experience_id: int,
    topic: Optional[str] = None,
    description: Optional[str] = None,
    skills_learned: Optional[str] = None,
    challenges: Optional[str] = None,
    solutions: Optional[str] = None,
    outcomes: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    exp = db.query(InternshipExperience).filter(
        InternshipExperience.id == experience_id, InternshipExperience.user_std_id == user.id
    ).first()
    if not exp:
        raise HTTPException(404, "ไม่พบข้อมูลประสบการณ์")

    if topic is not None: exp.topic = topic
    if description is not None: exp.description = description
    if skills_learned is not None: exp.skills_learned = skills_learned
    if challenges is not None: exp.challenges = challenges
    if solutions is not None: exp.solutions = solutions
    if outcomes is not None: exp.outcomes = outcomes
    db.commit()
    return {"success": True, "message": "แก้ไขประสบการณ์สำเร็จ"}


# ==================== ออกนอกสถานที่ (Off-Site) ====================

@router.post("/off-site-request", summary="ขอออกนอกสถานที่")
async def create_off_site_request(
    off_site_date: str,
    destination: str,
    purpose: str,
    departure_time: Optional[str] = None,
    return_time: Optional[str] = None,
    destination_detail: Optional[str] = None,
    accompany_person: Optional[str] = None,
    transportation: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        raise HTTPException(400, "ยังไม่มีข้อมูลการฝึกงาน")

    parsed_date = date.fromisoformat(off_site_date)

    # หา attendance record ของวันนั้น (ถ้ามี)
    attendance = db.query(AttendanceRecord).filter(
        AttendanceRecord.internship_id == internship.id,
        AttendanceRecord.date == parsed_date,
    ).first()
    attendance_id = attendance.id if attendance else None

    from datetime import time as time_type
    dep_time = None
    ret_time = None
    if departure_time:
        parts = departure_time.split(":")
        dep_time = time_type(int(parts[0]), int(parts[1]))
    if return_time:
        parts = return_time.split(":")
        ret_time = time_type(int(parts[0]), int(parts[1]))

    record = OffSiteRecord(
        attendance_id=attendance_id or 0,
        internship_id=internship.id,
        user_std_id=user.id,
        off_site_date=parsed_date,
        departure_time=dep_time,
        return_time=ret_time,
        destination=destination,
        destination_detail=destination_detail,
        purpose=purpose,
        accompany_person=accompany_person,
        transportation=transportation,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "id": record.id, "message": "ส่งคำขอออกนอกสถานที่สำเร็จ"}


@router.get("/off-site-requests", summary="ดูคำขอออกนอกสถานที่ทั้งหมด")
async def list_off_site_requests(
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
):
    internship = db.query(Internship).filter(Internship.user_std_id == user.id).order_by(Internship.id.desc()).first()
    if not internship:
        return {"records": []}

    records = db.query(OffSiteRecord).filter(
        OffSiteRecord.internship_id == internship.id
    ).order_by(OffSiteRecord.off_site_date.desc()).all()

    return {
        "records": [
            {
                "id": r.id,
                "off_site_date": r.off_site_date.isoformat(),
                "destination": r.destination,
                "destination_detail": r.destination_detail,
                "purpose": r.purpose,
                "departure_time": r.departure_time.strftime("%H:%M") if r.departure_time else None,
                "return_time": r.return_time.strftime("%H:%M") if r.return_time else None,
                "accompany_person": r.accompany_person,
                "transportation": r.transportation,
                "approved_by_user_id": r.approved_by_user_id,
            }
            for r in records
        ]
    }
