"""
SQLAlchemy Models - ตรงกับ ERD Version 2.0 (45 ตาราง)
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Enum, DateTime, Date, Time,
    ForeignKey, Boolean, Numeric, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base


# ==================== Enums ====================

class UserRole(str, enum.Enum):
    student = "student"
    advisor = "advisor"
    supervisor = "supervisor"
    admin = "admin"

class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    inactive = "inactive"
    rejected = "rejected"

class BioGender(str, enum.Enum):
    male = "male"
    female = "female"

class SkillLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"

class StudyProgramType(str, enum.Enum):
    regular = "regular"
    part_time = "part_time"

class EvaluationType(str, enum.Enum):
    supervisor = "supervisor"
    advisor = "advisor"
    orientation = "orientation"
    debriefing = "debriefing"

class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    revision = "revision"

class DocumentStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


# ==================== MASTER DATA - ADDRESS ====================

class Province(Base):
    __tablename__ = "provinces"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    geography_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class Subdistrict(Base):
    __tablename__ = "subdistricts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    postal_code = Column(String(5))
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== MASTER DATA - ORGANIZATION ====================

class Faculty(Base):
    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(150), nullable=False)
    name_en = Column(String(150))
    dean_name = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(150), nullable=False)
    name_en = Column(String(150))
    degree_name_th = Column(String(100))
    degree_name_en = Column(String(100))
    program_years = Column(Integer, default=4)
    internship_hours = Column(Integer, default=450)
    coop_hours = Column(Integer, default=720)
    pre_internship_hours = Column(Integer, default=90)
    program_chair_user_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class StudentType(Base):
    __tablename__ = "student_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class SkillType(Base):
    __tablename__ = "skill_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    description = Column(Text)
    icon = Column(String(50))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class BusinessType(Base):
    __tablename__ = "business_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Semester(Base):
    __tablename__ = "semesters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    term = Column(Integer, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    internship_start = Column(Date)
    internship_end = Column(Date)
    registration_start = Column(Date)
    registration_end = Column(Date)
    orientation_date = Column(Date)
    debriefing_date = Column(Date)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("year", "term"),)


# ==================== ADDRESSES ====================

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    address_type = Column(String(20), default="home")
    address_line = Column(Text)
    building_name = Column(String(100))
    building_no = Column(String(20))
    floor = Column(String(10))
    room_no = Column(String(20))
    moo = Column(String(10))
    village = Column(String(100))
    soi = Column(String(100))
    road = Column(String(100))
    subdistrict_id = Column(Integer, ForeignKey("subdistricts.id"))
    district_id = Column(Integer, ForeignKey("districts.id"))
    province_id = Column(Integer, ForeignKey("provinces.id"))
    postal_code = Column(String(5))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    google_map_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== COMPANIES ====================

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tax_id = Column(String(13), unique=True)
    name_th = Column(String(255), nullable=False)
    name_en = Column(String(255))
    business_type_id = Column(Integer, ForeignKey("business_types.id"))
    phone = Column(String(20))
    fax = Column(String(20))
    email = Column(String(100))
    website = Column(String(255))
    description = Column(Text)
    employee_count = Column(Integer)
    established_year = Column(Integer)
    logo_url = Column(Text)
    org_chart_url = Column(Text)
    welfare_info = Column(Text)
    address_id = Column(Integer, ForeignKey("addresses.id"))
    is_mou_partner = Column(Boolean, default=False)
    mou_start_date = Column(Date)
    mou_end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    verified_at = Column(DateTime)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class CompanyContact(Base):
    __tablename__ = "company_contacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    contact_type = Column(String(20), default="primary")
    prefix = Column(String(20))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    position = Column(String(100))
    department = Column(String(100))
    phone = Column(String(20))
    mobile = Column(String(20))
    email = Column(String(100))
    line_id = Column(String(50))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class CompanyPosition(Base):
    __tablename__ = "company_positions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    position_name = Column(String(150), nullable=False)
    department = Column(String(100))
    job_description = Column(Text)
    requirements = Column(Text)
    slots_available = Column(Integer, default=1)
    slots_filled = Column(Integer, default=0)
    allowance = Column(Numeric(10, 2))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== USERS ====================

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Authentication
    line_user_id = Column(String(50), unique=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(255))

    # System
    sys_role = Column(Enum(UserRole, name="user_role"))
    status = Column(Enum(UserStatus, name="user_status"), default=UserStatus.pending)

    # IDs
    student_code = Column(String(20), unique=True)
    employee_code = Column(String(20))

    # Thai Name
    prefix_th = Column(String(30))
    first_name_th = Column(String(100))
    middle_name_th = Column(String(100))
    last_name_th = Column(String(100))

    # English Name
    prefix_en = Column(String(30))
    first_name_en = Column(String(100))
    middle_name_en = Column(String(100))
    last_name_en = Column(String(100))

    # Personal Info
    id_card_number = Column(String(13))
    birth_date = Column(Date)
    bio_gender = Column(Enum(BioGender, name="bio_gender"))
    nationality = Column(String(50), default="ไทย")
    race = Column(String(50), default="ไทย")
    religion = Column(String(50))
    marital_status = Column(String(20))
    military_status = Column(String(50))

    # Contact
    phone = Column(String(20))
    mobile = Column(String(20))
    email = Column(String(100))
    line_id = Column(String(50))
    facebook = Column(String(100))

    # Photos
    photo_url = Column(Text)
    id_card_photo_url = Column(Text)

    # Education (Student)
    study_program_type = Column(Enum(StudyProgramType, name="study_program_type"), default=StudyProgramType.regular)
    admission_year = Column(Integer)
    expected_graduation_year = Column(Integer)
    gpa = Column(Numeric(3, 2))
    gpax = Column(Numeric(3, 2))
    total_credits = Column(Integer, default=0)
    advisor_user_id = Column(Integer, ForeignKey("users.id"))

    # Position (Staff)
    position = Column(String(100))
    expertise = Column(Text)

    # Foreign Keys
    student_type_id = Column(Integer, ForeignKey("student_types.id"))
    department_id = Column(Integer, ForeignKey("departments.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    current_address_id = Column(Integer, ForeignKey("addresses.id"))
    permanent_address_id = Column(Integer, ForeignKey("addresses.id"))

    # Approval
    approved_by_user_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)

    # System
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)


# ==================== USER EXTENDED ====================

class UserHealthInfo(Base):
    __tablename__ = "user_health_info"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    height = Column(Numeric(5, 2))
    weight = Column(Numeric(5, 2))
    blood_group = Column(String(5))
    chronic_disease = Column(Text, default="ไม่มี")
    allergies = Column(Text)
    medications = Column(Text)
    disabilities = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserEmergencyContact(Base):
    __tablename__ = "user_emergency_contacts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contact_name = Column(String(100), nullable=False)
    relationship = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    mobile = Column(String(20))
    address = Column(Text)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserFamily(Base):
    __tablename__ = "user_families"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    relation_type = Column(String(20), nullable=False)
    prefix = Column(String(20))
    first_name = Column(String(100))
    last_name = Column(String(100))
    age = Column(Integer)
    occupation = Column(String(100))
    workplace = Column(String(255))
    phone = Column(String(20))
    income = Column(Numeric(12, 2))
    is_alive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserEducationHistory(Base):
    __tablename__ = "user_education_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(String(50), nullable=False)
    institution_name = Column(String(255), nullable=False)
    faculty = Column(String(150))
    major = Column(String(150))
    country = Column(String(50), default="ไทย")
    start_year = Column(Integer)
    end_year = Column(Integer)
    gpa = Column(Numeric(3, 2))
    degree_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserWorkProfile(Base):
    __tablename__ = "user_work_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_workplace = Column(String(255))
    current_position = Column(String(100))
    work_phone = Column(String(20))
    work_start_date = Column(Date)
    monthly_income = Column(Numeric(12, 2))
    work_experience_years = Column(Integer)
    work_experience_detail = Column(Text)
    personality = Column(Text)
    hobbies = Column(Text)
    special_talents = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserSkill(Base):
    __tablename__ = "user_skills"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skill_type_id = Column(Integer, ForeignKey("skill_types.id"))
    skill_name = Column(String(100), nullable=False)
    skill_level = Column(Enum(SkillLevel, name="skill_level"))
    certificate_name = Column(String(255))
    certificate_url = Column(Text)
    issued_date = Column(Date)
    expiry_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserJobInterest(Base):
    __tablename__ = "user_job_interests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_title = Column(String(150), nullable=False)
    job_category = Column(String(100))
    description = Column(Text)
    preferred_location = Column(String(100))
    expected_salary = Column(Numeric(12, 2))
    priority = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class UserActivity(Base):
    __tablename__ = "user_activities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String(50))
    activity_name = Column(String(255), nullable=False)
    organization = Column(String(255))
    description = Column(Text)
    activity_date = Column(Date)
    end_date = Column(Date)
    location = Column(String(255))
    certificate_url = Column(Text)
    hours = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== INTERNSHIPS ====================

class InternshipStatus(Base):
    __tablename__ = "internship_statuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    color = Column(String(7))
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Internship(Base):
    __tablename__ = "internships"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_code = Column(String(20), unique=True)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_adv_id = Column(Integer, ForeignKey("users.id"))
    user_sup_id = Column(Integer, ForeignKey("users.id"))
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company_position_id = Column(Integer, ForeignKey("company_positions.id"))
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    required_hours = Column(Integer, default=450)
    completed_hours = Column(Numeric(7, 2), default=0)
    pre_training_hours = Column(Numeric(5, 2), default=0)
    job_title = Column(String(150))
    job_description = Column(Text)
    department = Column(String(100))
    status_id = Column(Integer, ForeignKey("internship_statuses.id"))
    orientation_attended = Column(Boolean, default=False)
    orientation_date = Column(Date)
    debriefing_attended = Column(Boolean, default=False)
    debriefing_date = Column(Date)
    final_grade = Column(String(5))
    final_score = Column(Numeric(5, 2))
    passed = Column(Boolean)
    remarks = Column(Text)
    cancellation_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class InternshipPlan(Base):
    __tablename__ = "internship_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    week_number = Column(Integer)
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text)
    location = Column(String(255))
    start_date = Column(Date)
    end_date = Column(Date)
    planned_hours = Column(Integer)
    actual_hours = Column(Numeric(5, 2))
    completion_percentage = Column(Integer, default=0)
    supervisor_approved = Column(Boolean, default=False)
    supervisor_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class InternshipRegistration(Base):
    __tablename__ = "internship_registrations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    company_position_id = Column(Integer, ForeignKey("company_positions.id"))
    resume_url = Column(Text)
    transcript_url = Column(Text)
    recommendation_letter_url = Column(Text)
    advisor_status = Column(Enum(ApprovalStatus, name="approval_status"), default=ApprovalStatus.pending)
    advisor_user_id = Column(Integer, ForeignKey("users.id"))
    advisor_approved_at = Column(DateTime)
    advisor_comment = Column(Text)
    department_status = Column(Enum(ApprovalStatus, name="approval_status", create_type=False), default=ApprovalStatus.pending)
    department_user_id = Column(Integer, ForeignKey("users.id"))
    department_approved_at = Column(DateTime)
    department_comment = Column(Text)
    company_status = Column(Enum(ApprovalStatus, name="approval_status", create_type=False), default=ApprovalStatus.pending)
    company_approved_at = Column(DateTime)
    company_comment = Column(Text)
    final_status = Column(Enum(ApprovalStatus, name="approval_status", create_type=False), default=ApprovalStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_std_id", "semester_id"),)


# ==================== ATTENDANCE ====================

class AttendanceStatus(Base):
    __tablename__ = "attendance_statuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    color = Column(String(7))
    counts_as_present = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    max_days_per_semester = Column(Integer)
    requires_document = Column(Boolean, default=False)
    requires_approval = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkSchedule(Base):
    __tablename__ = "work_schedules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    break_start = Column(Time)
    break_end = Column(Time)
    is_working_day = Column(Boolean, default=True)
    late_threshold_minutes = Column(Integer, default=15)
    early_leave_threshold_minutes = Column(Integer, default=15)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("internship_id", "day_of_week"),)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    total_days = Column(Numeric(3, 1))
    reason = Column(Text, nullable=False)
    attachment_url = Column(Text)
    attachment_name = Column(String(255))
    status = Column(Enum(ApprovalStatus, name="approval_status", create_type=False), default=ApprovalStatus.pending)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in_time = Column(Time)
    check_in_latitude = Column(Numeric(10, 8))
    check_in_longitude = Column(Numeric(11, 8))
    check_in_photo_url = Column(Text)
    check_in_device_info = Column(Text)
    check_out_time = Column(Time)
    check_out_latitude = Column(Numeric(10, 8))
    check_out_longitude = Column(Numeric(11, 8))
    check_out_photo_url = Column(Text)
    check_out_device_info = Column(Text)
    scheduled_hours = Column(Numeric(4, 2))
    hours_worked = Column(Numeric(4, 2))
    overtime_hours = Column(Numeric(4, 2), default=0)
    late_minutes = Column(Integer, default=0)
    early_leave_minutes = Column(Integer, default=0)
    status_id = Column(Integer, ForeignKey("attendance_statuses.id"))
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id"))
    supervisor_approved = Column(Boolean)
    supervisor_approved_at = Column(DateTime)
    supervisor_comment = Column(Text)
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("internship_id", "date"),)

class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    working_days = Column(Integer, default=0)
    present_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    leave_days = Column(Numeric(3, 1), default=0)
    holiday_days = Column(Integer, default=0)
    scheduled_hours = Column(Numeric(6, 2), default=0)
    actual_hours = Column(Numeric(6, 2), default=0)
    overtime_hours = Column(Numeric(6, 2), default=0)
    total_late_minutes = Column(Integer, default=0)
    student_signed = Column(Boolean, default=False)
    student_signed_at = Column(DateTime)
    supervisor_signed = Column(Boolean, default=False)
    supervisor_signed_at = Column(DateTime)
    supervisor_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("internship_id", "year", "month"),)

class OffSiteRecord(Base):
    __tablename__ = "off_site_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    attendance_id = Column(Integer, ForeignKey("attendance_records.id"), nullable=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    off_site_date = Column(Date, nullable=False)
    departure_time = Column(Time)
    return_time = Column(Time)
    destination = Column(String(255), nullable=False)
    destination_detail = Column(Text)
    destination_latitude = Column(Numeric(10, 8))
    destination_longitude = Column(Numeric(11, 8))
    purpose = Column(Text, nullable=False)
    accompany_person = Column(String(100))
    transportation = Column(String(50))
    approved_by_user_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== DAILY LOGS ====================

class DailyLogStatus(Base):
    __tablename__ = "daily_log_statuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    color = Column(String(7))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyLog(Base):
    __tablename__ = "daily_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    log_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    hours_spent = Column(Numeric(4, 2))
    activities = Column(Text, nullable=False)
    learnings = Column(Text)
    problems = Column(Text)
    solutions = Column(Text)
    problem_resolved = Column(Boolean, default=False)
    consulted_supervisor = Column(Boolean, default=False)
    consulted_advisor = Column(Boolean, default=False)
    felt_overloaded = Column(Boolean, default=False)
    photo_urls = Column(JSON)
    supervisor_comment = Column(Text)
    supervisor_reviewed_at = Column(DateTime)
    advisor_comment = Column(Text)
    advisor_reviewed_at = Column(DateTime)
    status_id = Column(Integer, ForeignKey("daily_log_statuses.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("internship_id", "log_date"),)


# ==================== VISITS ====================

class VisitStatus(Base):
    __tablename__ = "visit_statuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    color = Column(String(7))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class SatisfactionLevel(Base):
    __tablename__ = "satisfaction_levels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    score = Column(Integer)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdvisorVisitSchedule(Base):
    __tablename__ = "advisor_visit_schedules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_adv_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time)
    estimated_duration_minutes = Column(Integer, default=60)
    visit_number = Column(Integer, default=1)
    rescheduled_from_id = Column(Integer, ForeignKey("advisor_visit_schedules.id"))
    reschedule_reason = Column(Text)
    status_id = Column(Integer, ForeignKey("visit_statuses.id"))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class SupervisionVisit(Base):
    __tablename__ = "supervision_visits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("advisor_visit_schedules.id"))
    user_adv_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    visit_date = Column(Date, nullable=False)
    arrival_time = Column(Time)
    departure_time = Column(Time)
    visit_number = Column(Integer, default=1)
    work_observed = Column(Text)
    student_performance = Column(Text)
    student_attitude = Column(Text)
    work_environment = Column(Text)
    strengths = Column(Text)
    improvements_needed = Column(Text)
    issues_found = Column(Text)
    solutions_suggested = Column(Text)
    recommendations = Column(Text)
    supervisor_feedback = Column(Text)
    supervisor_concerns = Column(Text)
    student_satisfaction_id = Column(Integer, ForeignKey("satisfaction_levels.id"))
    company_satisfaction_id = Column(Integer, ForeignKey("satisfaction_levels.id"))
    overall_satisfaction_id = Column(Integer, ForeignKey("satisfaction_levels.id"))
    photo_urls = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== EVALUATIONS ====================

class EvaluationCriteria(Base):
    __tablename__ = "evaluation_criteria"
    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_type = Column(Enum(EvaluationType, name="evaluation_type"), nullable=False)
    code = Column(String(20), nullable=False)
    name_th = Column(String(255), nullable=False)
    name_en = Column(String(255))
    description = Column(Text)
    max_score = Column(Numeric(5, 2), nullable=False)
    weight = Column(Numeric(5, 2), default=1)
    parent_id = Column(Integer, ForeignKey("evaluation_criteria.id"))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("evaluation_type", "code"),)

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    evaluation_type = Column(Enum(EvaluationType, name="evaluation_type", create_type=False), nullable=False)
    evaluatee_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    evaluator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scores = Column(JSON)
    total_score = Column(Numeric(5, 2))
    max_possible_score = Column(Numeric(5, 2))
    percentage = Column(Numeric(5, 2))
    grade = Column(String(5))
    strengths = Column(Text)
    weaknesses = Column(Text)
    suggestions = Column(Text)
    overall_comment = Column(Text)
    status = Column(Enum(DocumentStatus, name="document_status"), default=DocumentStatus.draft)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("internship_id", "evaluation_type", "evaluator_user_id"),)

class StudentSummary(Base):
    __tablename__ = "student_summaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), unique=True, nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    knowledge_gained = Column(Text)
    skills_gained = Column(Text)
    attitudes_gained = Column(Text)
    best_experience = Column(Text)
    challenges_faced = Column(Text)
    how_overcame = Column(Text)
    recommendations_for_students = Column(Text)
    recommendations_for_company = Column(Text)
    recommendations_for_university = Column(Text)
    future_career_plan = Column(Text)
    will_apply_for_job = Column(Boolean)
    status = Column(Enum(DocumentStatus, name="document_status", create_type=False), default=DocumentStatus.draft)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== DOCUMENTS ====================

class DocumentType(Base):
    __tablename__ = "document_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name_th = Column(String(150), nullable=False)
    name_en = Column(String(150))
    description = Column(Text)
    template_url = Column(Text)
    requires_student_signature = Column(Boolean, default=False)
    requires_advisor_signature = Column(Boolean, default=False)
    requires_supervisor_signature = Column(Boolean, default=False)
    requires_department_signature = Column(Boolean, default=False)
    requires_company_signature = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)
    submission_deadline_days = Column(Integer)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_number = Column(String(50), unique=True)
    internship_id = Column(Integer, ForeignKey("internships.id"))
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    file_url = Column(Text)
    file_name = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(50))
    issued_date = Column(Date)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(DocumentStatus, name="document_status", create_type=False), default=DocumentStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class DocumentSignature(Base):
    __tablename__ = "document_signatures"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    signer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    signer_role = Column(String(50), nullable=False)
    signature_url = Column(Text)
    signature_date = Column(Date)
    signature_ip = Column(String(45))
    status = Column(Enum(ApprovalStatus, name="approval_status", create_type=False), default=ApprovalStatus.pending)
    comment = Column(Text)
    rejected_reason = Column(Text)
    sign_order = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("document_id", "signer_role"),)


# ==================== NOTIFICATIONS ====================

class NotificationType(Base):
    __tablename__ = "notification_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name_th = Column(String(100), nullable=False)
    name_en = Column(String(100))
    template_th = Column(Text)
    template_en = Column(Text)
    icon = Column(String(50))
    color = Column(String(7))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_type_id = Column(Integer, ForeignKey("notification_types.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(Text)
    reference_type = Column(String(50))
    reference_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    sent_via_line = Column(Boolean, default=False)
    sent_via_email = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== INTERNSHIP EXPERIENCE ====================

class InternshipExperience(Base):
    __tablename__ = "internship_experiences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    internship_id = Column(Integer, ForeignKey("internships.id"), nullable=False)
    user_std_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    experience_date = Column(Date, nullable=False)
    topic = Column(String(255), nullable=False)
    description = Column(Text)
    skills_learned = Column(Text)
    challenges = Column(Text)
    solutions = Column(Text)
    outcomes = Column(Text)
    supervisor_comment = Column(Text)
    supervisor_reviewed_at = Column(DateTime)
    advisor_comment = Column(Text)
    advisor_reviewed_at = Column(DateTime)
    status = Column(Enum(DocumentStatus, name="document_status", create_type=False), default=DocumentStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ==================== AUDIT LOG ====================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    table_name = Column(String(100))
    record_id = Column(Integer)
    old_values = Column(JSON)
    new_values = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
