"""
Master Data API - ข้อมูลพื้นฐานที่ทุก role ใช้ร่วมกัน
จังหวัด/อำเภอ/ตำบล, คณะ/สาขา, บริษัท, ภาคเรียน
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import (
    Province, District, Subdistrict,
    Faculty, Department, Semester,
    Company, CompanyPosition, BusinessType,
    StudentType, SkillType, LeaveType,
    User,
)

router = APIRouter(prefix="/master", tags=["📋 ข้อมูลพื้นฐาน"])


# ==================== ที่อยู่ ====================

@router.get("/provinces", summary="จังหวัดทั้งหมด")
async def list_provinces(db: Session = Depends(get_db)):
    items = db.query(Province).order_by(Province.name_th).all()
    return [{"id": p.id, "code": p.code, "name_th": p.name_th} for p in items]


@router.get("/districts/{province_id}", summary="อำเภอในจังหวัด")
async def list_districts(province_id: int, db: Session = Depends(get_db)):
    items = db.query(District).filter(District.province_id == province_id).order_by(District.name_th).all()
    return [{"id": d.id, "code": d.code, "name_th": d.name_th} for d in items]


@router.get("/subdistricts/{district_id}", summary="ตำบลในอำเภอ")
async def list_subdistricts(district_id: int, db: Session = Depends(get_db)):
    items = db.query(Subdistrict).filter(Subdistrict.district_id == district_id).order_by(Subdistrict.name_th).all()
    return [{"id": s.id, "code": s.code, "name_th": s.name_th, "postal_code": s.postal_code} for s in items]


# ==================== คณะ / สาขา ====================

@router.get("/faculties", summary="คณะทั้งหมด")
async def list_faculties(db: Session = Depends(get_db)):
    items = db.query(Faculty).filter(Faculty.is_active == True).order_by(Faculty.name_th).all()
    return [{"id": f.id, "code": f.code, "name_th": f.name_th, "name_en": f.name_en} for f in items]


@router.get("/departments/{faculty_id}", summary="สาขาในคณะ")
async def list_departments(faculty_id: int, db: Session = Depends(get_db)):
    items = db.query(Department).filter(
        Department.faculty_id == faculty_id, Department.is_active == True
    ).order_by(Department.name_th).all()
    return [
        {
            "id": d.id, "code": d.code, "name_th": d.name_th, "name_en": d.name_en,
            "internship_hours": d.internship_hours, "coop_hours": d.coop_hours,
        }
        for d in items
    ]


# ==================== ภาคเรียน ====================

@router.get("/semesters", summary="ภาคเรียนทั้งหมด")
async def list_semesters(db: Session = Depends(get_db)):
    items = db.query(Semester).order_by(Semester.year.desc(), Semester.term.desc()).all()
    return [
        {
            "id": s.id, "year": s.year, "term": s.term, "is_current": s.is_current,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "internship_start": s.internship_start.isoformat() if s.internship_start else None,
            "internship_end": s.internship_end.isoformat() if s.internship_end else None,
            "registration_start": s.registration_start.isoformat() if s.registration_start else None,
            "registration_end": s.registration_end.isoformat() if s.registration_end else None,
        }
        for s in items
    ]


@router.get("/semesters/current", summary="ภาคเรียนปัจจุบัน")
async def current_semester(db: Session = Depends(get_db)):
    s = db.query(Semester).filter(Semester.is_current == True).first()
    if not s:
        raise HTTPException(404, "ยังไม่มีภาคเรียนปัจจุบัน")
    return {"id": s.id, "year": s.year, "term": s.term, "label": f"{s.term}/{s.year}"}


# ==================== บริษัท ====================

@router.get("/companies", summary="บริษัททั้งหมด")
async def list_companies(
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Company).filter(Company.is_active == True)
    if search:
        q = q.filter(
            (Company.name_th.ilike(f"%{search}%")) |
            (Company.name_en.ilike(f"%{search}%"))
        )
    total = q.count()
    items = q.order_by(Company.name_th).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "companies": [
            {
                "id": c.id, "name_th": c.name_th, "name_en": c.name_en,
                "phone": c.phone, "email": c.email, "website": c.website,
                "is_mou_partner": c.is_mou_partner,
            }
            for c in items
        ],
    }


@router.get("/companies/{company_id}", summary="ข้อมูลบริษัท")
async def get_company(company_id: int, db: Session = Depends(get_db)):
    c = db.query(Company).filter(Company.id == company_id).first()
    if not c:
        raise HTTPException(404, "ไม่พบบริษัท")
    positions = db.query(CompanyPosition).filter(
        CompanyPosition.company_id == company_id, CompanyPosition.is_active == True
    ).all()
    return {
        "id": c.id, "name_th": c.name_th, "name_en": c.name_en,
        "tax_id": c.tax_id, "phone": c.phone, "email": c.email, "website": c.website,
        "description": c.description, "employee_count": c.employee_count,
        "is_mou_partner": c.is_mou_partner, "logo_url": c.logo_url,
        "positions": [
            {
                "id": p.id, "position_name": p.position_name, "department": p.department,
                "slots_available": p.slots_available, "slots_filled": p.slots_filled,
                "allowance": float(p.allowance) if p.allowance else None,
            }
            for p in positions
        ],
    }


# ==================== อื่นๆ ====================

@router.get("/business-types", summary="ประเภทธุรกิจ")
async def list_business_types(db: Session = Depends(get_db)):
    items = db.query(BusinessType).order_by(BusinessType.sort_order).all()
    return [{"id": b.id, "code": b.code, "name_th": b.name_th} for b in items]


@router.get("/student-types", summary="ประเภทนักศึกษา")
async def list_student_types(db: Session = Depends(get_db)):
    items = db.query(StudentType).order_by(StudentType.sort_order).all()
    return [{"id": s.id, "code": s.code, "name_th": s.name_th} for s in items]


@router.get("/skill-types", summary="ประเภททักษะ")
async def list_skill_types(db: Session = Depends(get_db)):
    items = db.query(SkillType).order_by(SkillType.sort_order).all()
    return [{"id": s.id, "code": s.code, "name_th": s.name_th, "icon": s.icon} for s in items]

@router.get("/departments", summary="ดึงสาขาวิชาทั้งหมด")
async def get_all_departments(db: Session = Depends(get_db)):
    from app.models.user import Department
    depts = db.query(Department).all()
    return [{"id": d.id, "name_th": d.name_th, "name_en": getattr(d, 'name_en', None), "faculty_id": getattr(d, 'faculty_id', None)} for d in depts]


@router.get("/advisors", summary="ดึงรายชื่ออาจารย์ทั้งหมด")
async def get_all_advisors(db: Session = Depends(get_db)):
    from app.models.user import User, UserRole, UserStatus
    advisors = db.query(User).filter(User.sys_role == UserRole.advisor, User.status == UserStatus.active, User.deleted_at.is_(None)).all()
    return [{"id": a.id, "prefix_th": a.prefix_th, "first_name_th": a.first_name_th, "last_name_th": a.last_name_th, "department_id": a.department_id, "email": a.email} for a in advisors]

@router.get("/leave-types", summary="ประเภทการลา")
async def list_leave_types(db: Session = Depends(get_db)):
    items = db.query(LeaveType).order_by(LeaveType.sort_order).all()
    return [
        {"id": l.id, "code": l.code, "name_th": l.name_th, "max_days": l.max_days_per_semester}
        for l in items
    ]

