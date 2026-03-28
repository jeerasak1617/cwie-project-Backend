"""
Advisor API (อาจารย์นิเทศก์)
- ดูรายชื่อนักศึกษาที่ดูแล
- ตรวจบันทึกรายวัน + comment
- จัดตารางนิเทศ + บันทึกผลนิเทศ
- อนุมัติเอกสาร / คำขอลา
- ประเมินนักศึกษา
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
    LeaveRequest, AdvisorVisitSchedule, SupervisionVisit,
    Evaluation, MonthlySummary, ApprovalStatus, EvaluationType,
    DocumentStatus, InternshipExperience,
)

router = APIRouter(prefix="/advisor", tags=["👨‍🏫 อาจารย์นิเทศก์"])

advisor_only = require_roles(["advisor"])


# ==================== Dashboard ====================

@router.get("/dashboard", summary="Dashboard อาจารย์")
async def dashboard(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    """สรุปข้อมูลนักศึกษาที่ดูแล"""
    internships = db.query(Internship).filter(Internship.user_adv_id == user.id).all()
    total = len(internships)

    # นับบันทึกรายวันที่ยังไม่ตรวจ
    pending_logs = 0
    for i in internships:
        count = db.query(DailyLog).filter(
            DailyLog.internship_id == i.id,
            DailyLog.advisor_comment.is_(None),
        ).count()
        pending_logs += count

    # นับคำขอลาที่รออนุมัติ
    pending_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.approved_by_user_id.is_(None),
        LeaveRequest.status == ApprovalStatus.pending,
        LeaveRequest.internship_id.in_([i.id for i in internships]),
    ).count() if internships else 0

    return {
        "total_students": total,
        "pending_daily_logs": pending_logs,
        "pending_leave_requests": pending_leaves,
        "internship_ids": [i.id for i in internships],
    }


# ==================== นักศึกษาที่ดูแล ====================

@router.get("/students", summary="ดูรายชื่อนักศึกษาที่ดูแล")
async def list_students(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    internships = db.query(Internship).filter(Internship.user_adv_id == user.id).all()
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
            "company_id": i.company_id,
            "start_date": i.start_date.isoformat() if i.start_date else None,
            "end_date": i.end_date.isoformat() if i.end_date else None,
            "completed_hours": float(i.completed_hours or 0),
            "required_hours": i.required_hours,
            "status_id": i.status_id,
        })
    return {"students": result}


@router.get("/students/{internship_id}", summary="ดูรายละเอียดนักศึกษา")
async def get_student_detail(internship_id: int, db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลการฝึกงานหรือไม่ใช่นักศึกษาที่ดูแล")

    student = db.query(User).filter(User.id == internship.user_std_id).first()
    total_logs = db.query(DailyLog).filter(DailyLog.internship_id == internship_id).count()
    reviewed_logs = db.query(DailyLog).filter(
        DailyLog.internship_id == internship_id, DailyLog.advisor_comment.isnot(None)
    ).count()
    total_attendance = db.query(AttendanceRecord).filter(
        AttendanceRecord.internship_id == internship_id
    ).count()

    # ดึงชื่อบริษัท
    company_name = None
    if internship.company_id:
        from app.models.user import Company
        company = db.query(Company).filter(Company.id == internship.company_id).first()
        if company:
            company_name = company.name_th or company.name_en

    # ดึง semester
    semester_label = None
    if internship.semester_id:
        from app.models.user import Semester
        sem = db.query(Semester).filter(Semester.id == internship.semester_id).first()
        if sem:
            semester_label = f"เทอม {sem.term}/{sem.year}"

    return {
        "internship": {
            "id": internship.id,
            "internship_code": internship.internship_code,
            "start_date": internship.start_date.isoformat() if internship.start_date else None,
            "end_date": internship.end_date.isoformat() if internship.end_date else None,
            "required_hours": internship.required_hours,
            "completed_hours": float(internship.completed_hours or 0),
            "company_id": internship.company_id,
            "company_name": company_name,
            "job_title": internship.job_title,
            "semester": semester_label,
        },
        "student": {
            "id": student.id,
            "student_code": student.student_code,
            "full_name": f"{student.first_name_th} {student.last_name_th}",
            "email": student.email,
            "phone": student.phone,
        } if student else None,
        "summary": {
            "total_daily_logs": total_logs,
            "reviewed_daily_logs": reviewed_logs,
            "total_attendance_days": total_attendance,
        },
    }


# ==================== ตรวจบันทึกรายวัน ====================

@router.get("/daily-logs/{internship_id}", summary="ดูบันทึกรายวันของนักศึกษา")
async def list_student_daily_logs(
    internship_id: int,
    reviewed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(DailyLog).filter(DailyLog.internship_id == internship_id)
    if reviewed is True:
        q = q.filter(DailyLog.advisor_comment.isnot(None))
    elif reviewed is False:
        q = q.filter(DailyLog.advisor_comment.is_(None))

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


@router.post("/daily-logs/{log_id}/review", summary="ตรวจ + comment บันทึกรายวัน")
async def review_daily_log(
    log_id: int,
    comment: str,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "ไม่พบบันทึก")

    internship = db.query(Internship).filter(
        Internship.id == log.internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    log.advisor_comment = comment
    log.advisor_reviewed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ตรวจบันทึกรายวันสำเร็จ"}


# ==================== อนุมัติคำขอลา ====================

@router.get("/leave-requests", summary="ดูคำขอลาทั้งหมดของนักศึกษาที่ดูแล")
async def list_leave_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship_ids = [i.id for i in db.query(Internship).filter(Internship.user_adv_id == user.id).all()]
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
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leaves
        ],
    }





# ==================== ตารางนิเทศ ====================

@router.post("/visit-schedule", summary="สร้างตารางนิเทศ")
async def create_visit_schedule(
    internship_id: int,
    semester_id: int,
    scheduled_date: str,
    scheduled_time: Optional[str] = None,
    visit_number: int = 1,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    from datetime import time as time_type
    sched_time = None
    if scheduled_time:
        parts = scheduled_time.split(":")
        sched_time = time_type(int(parts[0]), int(parts[1]))

    schedule = AdvisorVisitSchedule(
        user_adv_id=user.id,
        internship_id=internship_id,
        semester_id=semester_id,
        scheduled_date=date.fromisoformat(scheduled_date),
        scheduled_time=sched_time,
        visit_number=visit_number,
        notes=notes,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {"success": True, "id": schedule.id, "message": "สร้างตารางนิเทศสำเร็จ"}


@router.get("/visit-schedules", summary="ดูตารางนิเทศทั้งหมด")
async def list_visit_schedules(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    schedules = db.query(AdvisorVisitSchedule).filter(
        AdvisorVisitSchedule.user_adv_id == user.id
    ).order_by(AdvisorVisitSchedule.scheduled_date.desc()).all()

    return {
        "schedules": [
            {
                "id": s.id,
                "internship_id": s.internship_id,
                "scheduled_date": s.scheduled_date.isoformat() if s.scheduled_date else None,
                "scheduled_time": s.scheduled_time.strftime("%H:%M") if s.scheduled_time else None,
                "visit_number": s.visit_number,
                "status_id": s.status_id,
                "notes": s.notes,
            }
            for s in schedules
        ],
    }


# ==================== บันทึกผลนิเทศ ====================

@router.post("/visit-report", summary="บันทึกผลนิเทศ")
async def create_visit_report(
    internship_id: int,
    visit_date: str,
    visit_number: int = 1,
    schedule_id: Optional[int] = None,
    work_observed: Optional[str] = None,
    student_performance: Optional[str] = None,
    student_attitude: Optional[str] = None,
    work_environment: Optional[str] = None,
    strengths: Optional[str] = None,
    improvements_needed: Optional[str] = None,
    issues_found: Optional[str] = None,
    solutions_suggested: Optional[str] = None,
    recommendations: Optional[str] = None,
    supervisor_feedback: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    visit = SupervisionVisit(
        schedule_id=schedule_id,
        user_adv_id=user.id,
        internship_id=internship_id,
        visit_date=date.fromisoformat(visit_date),
        visit_number=visit_number,
        work_observed=work_observed,
        student_performance=student_performance,
        student_attitude=student_attitude,
        work_environment=work_environment,
        strengths=strengths,
        improvements_needed=improvements_needed,
        issues_found=issues_found,
        solutions_suggested=solutions_suggested,
        recommendations=recommendations,
        supervisor_feedback=supervisor_feedback,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return {"success": True, "id": visit.id, "message": "บันทึกผลนิเทศสำเร็จ"}


@router.get("/visit-reports", summary="ดูผลนิเทศทั้งหมด")
async def list_visit_reports(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    visits = db.query(SupervisionVisit).filter(
        SupervisionVisit.user_adv_id == user.id
    ).order_by(SupervisionVisit.visit_date.desc()).all()

    return {
        "reports": [
            {
                "id": v.id,
                "internship_id": v.internship_id,
                "visit_date": v.visit_date.isoformat() if v.visit_date else None,
                "visit_number": v.visit_number,
                "student_performance": v.student_performance,
                "strengths": v.strengths,
                "improvements_needed": v.improvements_needed,
                "recommendations": v.recommendations,
            }
            for v in visits
        ],
    }


@router.get("/visit-reports/{internship_id}", summary="ดูผลนิเทศของนักศึกษาเฉพาะคน")
async def get_student_visit_reports(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    visits = db.query(SupervisionVisit).filter(
        SupervisionVisit.internship_id == internship_id,
        SupervisionVisit.user_adv_id == user.id,
    ).order_by(SupervisionVisit.visit_number).all()

    return {
        "reports": [
            {
                "id": v.id,
                "visit_number": v.visit_number,
                "visit_date": v.visit_date.isoformat() if v.visit_date else None,
                "work_observed": v.work_observed,
                "student_performance": v.student_performance,
                "issues_found": v.issues_found,
                "solutions_suggested": v.solutions_suggested,
                "recommendations": v.recommendations,
                "supervisor_feedback": v.supervisor_feedback,
            }
            for v in visits
        ],
    }


# ==================== ประเมินนักศึกษา ====================

@router.post("/evaluation", summary="ประเมินนักศึกษา (40 คะแนน)")
async def create_evaluation(
    internship_id: int,
    scores: Optional[str] = None,
    total_score: float = 0,
    strengths: Optional[str] = None,
    weaknesses: Optional[str] = None,
    suggestions: Optional[str] = None,
    overall_comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    # เช็คว่าประเมินไปแล้วหรือยัง
    existing = db.query(Evaluation).filter(
        Evaluation.internship_id == internship_id,
        Evaluation.evaluation_type == EvaluationType.advisor,
        Evaluation.evaluator_user_id == user.id,
    ).first()
    if existing:
        raise HTTPException(409, "ประเมินนักศึกษาคนนี้ไปแล้ว")

    import json
    scores_json = json.loads(scores) if scores else None

    evaluation = Evaluation(
        internship_id=internship_id,
        evaluation_type=EvaluationType.advisor,
        evaluatee_user_id=internship.user_std_id,
        evaluator_user_id=user.id,
        scores=scores_json,
        total_score=total_score,
        max_possible_score=40,
        percentage=round((total_score / 40) * 100, 2) if total_score else 0,
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
async def list_evaluations(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    evals = db.query(Evaluation).filter(
        Evaluation.evaluator_user_id == user.id,
        Evaluation.evaluation_type == EvaluationType.advisor,
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
                "submitted_at": e.submitted_at.isoformat() if e.submitted_at else None,
            }
            for e in evals
        ],
    }


@router.get("/evaluation/{internship_id}", summary="ดูคะแนนประเมินทั้งหมดของนักศึกษา (อาจารย์เห็นทั้งหมด)")
async def get_all_evaluations_for_student(
    internship_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    """อาจารย์เห็นคะแนนทั้งหมด: ของตัวเอง + ของบริษัท"""
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    # ดึงทุก evaluation ของ internship นี้
    evals = db.query(Evaluation).filter(Evaluation.internship_id == internship_id).all()

    result = {}
    for e in evals:
        eval_type = e.evaluation_type.value if e.evaluation_type else "unknown"
        import json
        result[eval_type] = {
            "id": e.id,
            "evaluation_type": eval_type,
            "total_score": float(e.total_score) if e.total_score else 0,
            "max_possible_score": float(e.max_possible_score) if e.max_possible_score else 0,
            "scores": e.scores if isinstance(e.scores, dict) else (json.loads(e.scores) if isinstance(e.scores, str) else {}),
            "strengths": e.strengths,
            "weaknesses": e.weaknesses,
            "overall_comment": e.overall_comment,
            "submitted_at": e.submitted_at.isoformat() if e.submitted_at else None,
        }

    return {"evaluations": result}


# ==================== ดูการเข้างาน ====================

@router.get("/attendance/{internship_id}", summary="ดูสถิติเข้างานของนักศึกษา")
async def get_student_attendance(
    internship_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(AttendanceRecord).filter(AttendanceRecord.internship_id == internship_id)
    if month and year:
        q = q.filter(
            extract("month", AttendanceRecord.date) == month,
            extract("year", AttendanceRecord.date) == year,
        )

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
    user: User = Depends(advisor_only),
):
    internship = db.query(Internship).filter(
        Internship.id == internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(404, "ไม่พบข้อมูลหรือไม่ใช่นักศึกษาที่ดูแล")

    q = db.query(InternshipExperience).filter(InternshipExperience.internship_id == internship_id)
    if reviewed is True:
        q = q.filter(InternshipExperience.advisor_comment.isnot(None))
    elif reviewed is False:
        q = q.filter(InternshipExperience.advisor_comment.is_(None))

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
    user: User = Depends(advisor_only),
):
    exp = db.query(InternshipExperience).filter(InternshipExperience.id == experience_id).first()
    if not exp:
        raise HTTPException(404, "ไม่พบข้อมูลประสบการณ์")

    internship = db.query(Internship).filter(
        Internship.id == exp.internship_id, Internship.user_adv_id == user.id
    ).first()
    if not internship:
        raise HTTPException(403, "ไม่ใช่นักศึกษาที่ดูแล")

    exp.advisor_comment = comment
    exp.advisor_reviewed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "ตรวจประสบการณ์สำเร็จ"}


# ==================== โปรไฟล์อาจารย์ ====================

@router.get("/profile", summary="ดูโปรไฟล์อาจารย์")
async def get_advisor_profile(db: Session = Depends(get_db), user: User = Depends(advisor_only)):
    return {
        "id": user.id,
        "prefix_th": user.prefix_th,
        "first_name_th": user.first_name_th,
        "last_name_th": user.last_name_th,
        "first_name_en": user.first_name_en,
        "last_name_en": user.last_name_en,
        "email": user.email,
        "phone": user.phone,
        "mobile": user.mobile,
        "department_id": user.department_id,
        "photo_url": user.photo_url,
    }


@router.put("/profile", summary="แก้ไขโปรไฟล์อาจารย์")
async def update_advisor_profile(
    phone: Optional[str] = None,
    mobile: Optional[str] = None,
    email: Optional[str] = None,
    department_id: Optional[int] = None,
    prefix_th: Optional[str] = None,
    photo_url: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    if phone is not None: user.phone = phone
    if mobile is not None: user.mobile = mobile
    if email is not None: user.email = email
    if department_id is not None: user.department_id = department_id
    if prefix_th is not None: user.prefix_th = prefix_th
    if photo_url is not None: user.photo_url = photo_url
    db.commit()
    return {"success": True, "message": "อัปเดตโปรไฟล์สำเร็จ"}


@router.post("/profile/upload-photo", summary="อัปโหลดรูปโปรไฟล์อาจารย์")
async def upload_advisor_photo(
    data: dict,
    db: Session = Depends(get_db),
    user: User = Depends(advisor_only),
):
    photo_url = data.get("photo_url")
    if not photo_url:
        raise HTTPException(400, "ไม่มีข้อมูลรูปภาพ")
    user.photo_url = photo_url
    db.commit()
    return {"success": True, "message": "อัปโหลดรูปสำเร็จ"}
