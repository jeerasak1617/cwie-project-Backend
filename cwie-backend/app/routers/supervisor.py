"""
Supervisor API (พี่เลี้ยง/ผู้ดูแลในสถานประกอบการ)
- ดูรายชื่อนักศึกษาฝึกงาน
- ตรวจบันทึกรายวัน + comment
- อนุมัติการเข้างาน / คำขอลา / ออกนอกสถานที่
- ประเมินนักศึกษา (50 คะแนน)
- อนุมัติแผนฝึกงาน
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.core.database import get_db
from app.core.security import require_roles
from app.models.user import (
    User, UserRole, Internship, DailyLog, AttendanceRecord,
    LeaveRequest, InternshipPlan, OffSiteRecord, MonthlySummary,
    Evaluation, ApprovalStatus, EvaluationType, DocumentStatus,
    InternshipExperience,
)

router = APIRouter(prefix="/supervisor", tags=["🏢 พี่เลี้ยง"])

supervisor_only = require_roles(["supervisor"])


# ==================== Dashboard ====================

@router.get("/dashboard", summary="Dashboard พี่เลี้ยง")
async def dashboard(db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    internships = db.query(Internship).filter(Internship.user_sup_id == user.id).all()
    total = len(internships)

    pending_logs = 0
    pending_attendance = 0
    for i in internships:
        pending_logs += db.query(DailyLog).filter(
            DailyLog.internship_id == i.id,
            DailyLog.supervisor_comment.is_(None),
        ).count()
        pending_attendance += db.query(AttendanceRecord).filter(
            AttendanceRecord.internship_id == i.id,
            AttendanceRecord.supervisor_approved.is_(None),
        ).count()

    pending_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.status == ApprovalStatus.pending,
        LeaveRequest.internship_id.in_([i.id for i in internships]),
    ).count() if internships else 0

    return {
        "total_students": total,
        "pending_daily_logs": pending_logs,
        "pending_attendance_approvals": pending_attendance,
        "pending_leave_requests": pending_leaves,
    }


# ==================== นักศึกษาฝึกงาน ====================

@router.get("/students", summary="ดูรายชื่อนักศึกษาที่ดูแล")
async def list_students(db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    internships = db.query(Internship).filter(Internship.user_sup_id == user.id).all()
    result = []
    for i in internships:
        student = db.query(User).filter(User.id == i.user_std_id).first()
        if not student:
            continue
        result.append({
            "internship_id": i.id,
            "student_id": student.id,
            "student_code": student.student_code,
            "full_name": f"{student.first_name_th} {student.last_name_th}",
            "job_title": i.job_title,
            "department": i.department,
            "start_date": i.start_date.isoformat() if i.start_date else None,
            "end_date": i.end_date.isoformat() if i.end_date else None,
            "completed_hours": float(i.completed_hours or 0),
            "required_hours": i.required_hours,
        })
    return {"students": result}


# ==================== ตรวจบันทึกรายวัน ====================

@router.get("/daily-logs/{internship_id}", summary="ดูบันทึกรายวันของนักศึกษา")
async def list_daily_logs(
    internship_id: int,
    reviewed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(DailyLog).filter(DailyLog.internship_id == internship_id)
    if reviewed is True:
        q = q.filter(DailyLog.supervisor_comment.isnot(None))
    elif reviewed is False:
        q = q.filter(DailyLog.supervisor_comment.is_(None))

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
                "status_id": l.status_id,
            }
            for l in logs
        ],
    }


@router.post("/daily-logs/{log_id}/review", summary="ตรวจ + comment บันทึกรายวัน")
async def review_daily_log(
    log_id: int,
    comment: str,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "ไม่พบบันทึก")

    internship = db.query(Internship).filter(
        Internship.id == log.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    log.supervisor_comment = comment
    log.supervisor_reviewed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ตรวจบันทึกรายวันสำเร็จ"}


# ==================== อนุมัติการเข้างาน ====================

@router.get("/attendance/{internship_id}", summary="ดูการเข้างานของนักศึกษา")
async def list_attendance(
    internship_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
    pending_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(AttendanceRecord).filter(AttendanceRecord.internship_id == internship_id)
    if month and year:
        q = q.filter(
            extract("month", AttendanceRecord.date) == month,
            extract("year", AttendanceRecord.date) == year,
        )
    if pending_only:
        q = q.filter(AttendanceRecord.supervisor_approved.is_(None))

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
                "supervisor_approved": r.supervisor_approved,
                "supervisor_comment": r.supervisor_comment,
            }
            for r in records
        ],
    }


@router.post("/attendance/{record_id}/approve", summary="อนุมัติการเข้างาน")
async def approve_attendance(
    record_id: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "ไม่พบข้อมูลเข้างาน")

    internship = db.query(Internship).filter(
        Internship.id == record.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    record.supervisor_approved = True
    record.supervisor_approved_at = datetime.utcnow()
    record.supervisor_comment = comment
    db.commit()
    return {"success": True, "message": "อนุมัติการเข้างานสำเร็จ"}


@router.post("/attendance/batch-approve", summary="อนุมัติการเข้างานหลายรายการ")
async def batch_approve_attendance(
    record_ids: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    ids = [int(x.strip()) for x in record_ids.split(",") if x.strip()]
    approved_count = 0

    for rid in ids:
        record = db.query(AttendanceRecord).filter(AttendanceRecord.id == rid).first()
        if not record:
            continue
        internship = db.query(Internship).filter(
            Internship.id == record.internship_id, Internship.user_sup_id == user.id
        ).first()
        if not internship:
            continue
        record.supervisor_approved = True
        record.supervisor_approved_at = datetime.utcnow()
        record.supervisor_comment = comment
        approved_count += 1

    db.commit()
    return {"success": True, "approved_count": approved_count, "message": f"อนุมัติ {approved_count} รายการ"}


# ==================== อนุมัติคำขอลา ====================

@router.get("/leave-requests", summary="ดูคำขอลาทั้งหมด")
async def list_leave_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship_ids = [i.id for i in db.query(Internship).filter(Internship.user_sup_id == user.id).all()]
    if not internship_ids:
        return {"requests": []}

    q = db.query(LeaveRequest).filter(LeaveRequest.internship_id.in_(internship_ids))
    if status:
        q = q.filter(LeaveRequest.status == status)

    leaves = q.order_by(LeaveRequest.created_at.desc()).all()
    return {
        "requests": [
            {
                "id": l.id,
                "internship_id": l.internship_id,
                "user_std_id": l.user_std_id,
                "leave_type_id": l.leave_type_id,
                "start_date": l.start_date.isoformat(),
                "end_date": l.end_date.isoformat(),
                "total_days": float(l.total_days) if l.total_days else None,
                "reason": l.reason,
                "status": l.status.value if l.status else None,
            }
            for l in leaves
        ],
    }


@router.post("/leave-requests/{leave_id}/approve", summary="อนุมัติคำขอลา")
async def approve_leave(leave_id: int, db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(404, "ไม่พบคำขอลา")
    internship = db.query(Internship).filter(
        Internship.id == leave.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    leave.status = ApprovalStatus.approved
    leave.approved_by_user_id = user.id
    leave.approved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "อนุมัติคำขอลาสำเร็จ"}


@router.post("/leave-requests/{leave_id}/reject", summary="ปฏิเสธคำขอลา")
async def reject_leave(
    leave_id: int, reason: str = "ไม่อนุมัติ",
    db: Session = Depends(get_db), user: User = Depends(supervisor_only),
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(404, "ไม่พบคำขอลา")
    internship = db.query(Internship).filter(
        Internship.id == leave.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    leave.status = ApprovalStatus.rejected
    leave.rejection_reason = reason
    leave.approved_by_user_id = user.id
    leave.approved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ปฏิเสธคำขอลา"}


# ==================== อนุมัติออกนอกสถานที่ ====================

@router.get("/off-site/{internship_id}", summary="ดูคำขอออกนอกสถานที่")
async def list_off_site(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    records = db.query(OffSiteRecord).filter(
        OffSiteRecord.internship_id == internship_id
    ).order_by(OffSiteRecord.off_site_date.desc()).all()

    return {
        "records": [
            {
                "id": r.id,
                "off_site_date": r.off_site_date.isoformat() if r.off_site_date else None,
                "destination": r.destination,
                "purpose": r.purpose,
                "departure_time": r.departure_time.strftime("%H:%M") if r.departure_time else None,
                "return_time": r.return_time.strftime("%H:%M") if r.return_time else None,
                "approved_by_user_id": r.approved_by_user_id,
            }
            for r in records
        ],
    }


@router.post("/off-site/{record_id}/approve", summary="อนุมัติออกนอกสถานที่")
async def approve_off_site(record_id: int, db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    record = db.query(OffSiteRecord).filter(OffSiteRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "ไม่พบข้อมูล")
    internship = db.query(Internship).filter(
        Internship.id == record.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    record.approved_by_user_id = user.id
    record.approved_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "อนุมัติออกนอกสถานที่สำเร็จ"}


# ==================== อนุมัติแผนฝึกงาน ====================

@router.get("/plans/{internship_id}", summary="ดูแผนฝึกงานของนักศึกษา")
async def list_internship_plans(
    internship_id: int, db: Session = Depends(get_db), user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    plans = db.query(InternshipPlan).filter(
        InternshipPlan.internship_id == internship_id
    ).order_by(InternshipPlan.week_number).all()

    return {
        "plans": [
            {
                "id": p.id,
                "week_number": p.week_number,
                "task_name": p.task_name,
                "task_description": p.task_description,
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "planned_hours": p.planned_hours,
                "actual_hours": float(p.actual_hours) if p.actual_hours else None,
                "completion_percentage": p.completion_percentage,
                "supervisor_approved": p.supervisor_approved,
                "supervisor_comment": p.supervisor_comment,
            }
            for p in plans
        ],
    }


@router.post("/plans/{plan_id}/approve", summary="อนุมัติแผนฝึกงาน")
async def approve_plan(
    plan_id: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    plan = db.query(InternshipPlan).filter(InternshipPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "ไม่พบแผนฝึกงาน")
    internship = db.query(Internship).filter(
        Internship.id == plan.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    plan.supervisor_approved = True
    plan.supervisor_comment = comment
    db.commit()
    return {"success": True, "message": "อนุมัติแผนฝึกงานสำเร็จ"}


# ==================== สรุปรายเดือน ====================

@router.post("/monthly-summary/{internship_id}/sign", summary="ลงนามสรุปรายเดือน")
async def sign_monthly_summary(
    internship_id: int,
    year: int,
    month: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    summary = db.query(MonthlySummary).filter(
        MonthlySummary.internship_id == internship_id,
        MonthlySummary.year == year,
        MonthlySummary.month == month,
    ).first()
    if not summary:
        raise HTTPException(404, "ไม่พบสรุปรายเดือน")

    summary.supervisor_signed = True
    summary.supervisor_signed_at = datetime.utcnow()
    summary.supervisor_comment = comment
    db.commit()
    return {"success": True, "message": "ลงนามสรุปรายเดือนสำเร็จ"}


# ==================== ประเมินนักศึกษา ====================

@router.post("/evaluation", summary="ประเมินนักศึกษา (50 คะแนน)")
async def create_evaluation(
    internship_id: int,
    scores: Optional[str] = None,
    total_score: float = 0,
    strengths: Optional[str] = None,
    weaknesses: Optional[str] = None,
    suggestions: Optional[str] = None,
    overall_comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    existing = db.query(Evaluation).filter(
        Evaluation.internship_id == internship_id,
        Evaluation.evaluation_type == EvaluationType.supervisor,
        Evaluation.evaluator_user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(409, "ประเมินนักศึกษาคนนี้ไปแล้ว")

    import json
    scores_json = json.loads(scores) if scores else None

    evaluation = Evaluation(
        internship_id=internship_id,
        evaluation_type=EvaluationType.supervisor,
        evaluatee_user_id=internship.user_std_id,
        evaluator_user_id=user.id,
        scores=scores_json,
        total_score=total_score,
        max_possible_score=50,
        percentage=round((total_score / 50) * 100, 2) if total_score else 0,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        overall_comment=overall_comment,
        status=DocumentStatus.submitted,
        submitted_at=datetime.utcnow(),
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return {"success": True, "id": evaluation.id, "message": "ประเมินนักศึกษาสำเร็จ"}


@router.get("/evaluations", summary="ดูผลประเมินทั้งหมดที่เคยให้")
async def list_evaluations(db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    evals = db.query(Evaluation).filter(
        Evaluation.evaluator_user_id == user.id,
        Evaluation.evaluation_type == EvaluationType.supervisor,
    ).order_by(Evaluation.created_at.desc()).all()

    return {
        "evaluations": [
            {
                "id": e.id,
                "internship_id": e.internship_id,
                "evaluatee_user_id": e.evaluatee_user_id,
                "total_score": float(e.total_score) if e.total_score else None,
                "max_possible_score": float(e.max_possible_score) if e.max_possible_score else None,
                "percentage": float(e.percentage) if e.percentage else None,
                "overall_comment": e.overall_comment,
                "status": e.status.value if e.status else None,
            }
            for e in evals
        ],
    }


# ==================== ตรวจประสบการณ์ ====================

@router.get("/experiences/{internship_id}", summary="ดูประสบการณ์ของนักศึกษา")
async def list_student_experiences(
    internship_id: int,
    reviewed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(InternshipExperience).filter(InternshipExperience.internship_id == internship_id)
    if reviewed is True:
        q = q.filter(InternshipExperience.supervisor_comment.isnot(None))
    elif reviewed is False:
        q = q.filter(InternshipExperience.supervisor_comment.is_(None))

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


@router.post("/experiences/{experience_id}/review", summary="ตรวจ + comment ประสบการณ์")
async def review_experience(
    experience_id: int,
    comment: str,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    exp = db.query(InternshipExperience).filter(InternshipExperience.id == experience_id).first()
    if not exp:
        raise HTTPException(404, "ไม่พบข้อมูลประสบการณ์")

    internship = db.query(Internship).filter(
        Internship.id == exp.internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    exp.supervisor_comment = comment
    exp.supervisor_reviewed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ตรวจประสบการณ์สำเร็จ"}

# ==================== เพิ่มนักศึกษาที่ดูแล (ยึดจากบริษัทเดียวกัน) ====================
# เพิ่มโค้ดนี้ต่อท้ายไฟล์ supervisor.py

@router.get("/unassigned-students", summary="ดูนักศึกษาที่ฝึกบริษัทเดียวกันแต่ยังไม่มีพี่เลี้ยง")
async def list_unassigned_students(db: Session = Depends(get_db), user: User = Depends(supervisor_only)):
    """ดึงนักศึกษาที่ฝึกในบริษัทเดียวกับ supervisor แต่ยังไม่มีพี่เลี้ยง (user_sup_id is NULL)"""
    # หา company_id ของ supervisor
    company_id = user.company_id

    q = db.query(Internship).filter(Internship.user_sup_id.is_(None))
    # ถ้า supervisor มี company_id ให้กรองเฉพาะบริษัทเดียวกัน
    if company_id:
        q = q.filter(Internship.company_id == company_id)

    internships = q.all()
    result = []
    for i in internships:
        student = db.query(User).filter(User.id == i.user_std_id).first()
        if not student:
            continue
        result.append({
            "internship_id": i.id,
            "student_id": student.id,
            "student_code": student.student_code,
            "full_name": f"{student.first_name_th or ''} {student.last_name_th or ''}".strip(),
            "email": student.email,
            "department_id": student.department_id,
            "company_id": i.company_id,
            "start_date": i.start_date.isoformat() if i.start_date else None,
        })
    return {"students": result}


@router.post("/assign-student", summary="เลือกนักศึกษาเข้ามาดูแล")
async def assign_student(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    """Supervisor เลือก assign ตัวเองเป็นพี่เลี้ยงของ internship นี้"""
    internship = db.query(Internship).filter(Internship.id == internship_id).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลการฝึกงาน")

    # เช็คว่าบริษัทตรงกันไหม
    if user.company_id and internship.company_id and user.company_id != internship.company_id:
        raise HTTPException(403, "นักศึกษาคนนี้ไม่ได้ฝึกในบริษัทของคุณ")

    if internship.user_sup_id and internship.user_sup_id != user.id:
        raise HTTPException(409, "นักศึกษาคนนี้มีพี่เลี้ยงดูแลอยู่แล้ว")

    internship.user_sup_id = user.id
    db.commit()
    return {"success": True, "message": "เพิ่มนักศึกษาในรายชื่อที่ดูแลสำเร็จ"}


@router.post("/unassign-student", summary="ถอนนักศึกษาออกจากรายชื่อ")
async def unassign_student(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(supervisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_sup_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    internship.user_sup_id = None
    db.commit()
    return {"success": True, "message": "ถอนนักศึกษาออกจากรายชื่อสำเร็จ"}
