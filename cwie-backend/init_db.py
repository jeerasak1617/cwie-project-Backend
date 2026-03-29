"""
init_db.py — สร้างตารางทั้งหมด + seed ข้อมูลเริ่มต้น
วิธีใช้: python init_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine, Base, SessionLocal
from app.models.user import *           # import ทุก Model
from app.core.security import hash_password

def create_tables():
    print("🔧 กำลังสร้างตารางทั้งหมด...")
    Base.metadata.create_all(bind=engine)
    print("✅ สร้างตารางสำเร็จ!")

def seed_data():
    db = SessionLocal()
    try:
        # ===== เช็คว่ามีข้อมูลแล้วหรือยัง =====
        if db.query(User).first():
            print("⚠️  มีข้อมูลอยู่แล้ว ข้ามขั้นตอน seed")
            return

        print("🌱 กำลัง seed ข้อมูลเริ่มต้น...")

        # ===== 1. Semester =====
        sem = Semester(year=2568, term=1, is_current=True)
        db.add(sem)
        db.flush()

        # ===== 2. Faculty & Department =====
        fac = Faculty(code="SCI", name_th="คณะวิทยาศาสตร์", name_en="Faculty of Science")
        db.add(fac)
        db.flush()

        dept = Department(
            faculty_id=fac.id, code="CS", name_th="วิทยาการคอมพิวเตอร์",
            name_en="Computer Science", internship_hours=450
        )
        db.add(dept)
        db.flush()

        # ===== 3. Internship Status =====
        statuses = [
            InternshipStatus(code="registered", name_th="ลงทะเบียนแล้ว", sort_order=1),
            InternshipStatus(code="training", name_th="กำลังฝึกงาน", sort_order=2),
            InternshipStatus(code="completed", name_th="ฝึกงานครบ", sort_order=3),
        ]
        db.add_all(statuses)
        db.flush()
        training_status = statuses[1]

        # ===== 4. Company =====
        company = Company(
            name_th="บริษัท ทดสอบ จำกัด", name_en="Test Company Co., Ltd.",
            phone="02-111-2222", email="test@company.com", is_active=True
        )
        db.add(company)
        db.flush()

        # ===== 5. Users =====
        # Admin
        admin = User(
            username="admin01", password_hash=hash_password("1234"),
            sys_role=UserRole.admin, status=UserStatus.active,
            prefix_th="นาย", first_name_th="แอดมิน", last_name_th="ระบบ",
            email="admin@cwie.ac.th"
        )
        db.add(admin)

        # Supervisor (พี่เลี้ยง)
        supervisor = User(
            username="supervisor01", password_hash=hash_password("1234"),
            sys_role=UserRole.supervisor, status=UserStatus.active,
            prefix_th="คุณ", first_name_th="วิชัย", last_name_th="เก่งกาจ",
            email="supervisor@company.com", company_id=company.id,
            position="หัวหน้าแผนก IT"
        )
        db.add(supervisor)

        # Advisor (อาจารย์)
        advisor = User(
            username="advisor01", password_hash=hash_password("1234"),
            sys_role=UserRole.advisor, status=UserStatus.active,
            prefix_th="ดร.", first_name_th="สมชาย", last_name_th="ใจดี",
            email="advisor@cwie.ac.th", department_id=dept.id,
            employee_code="ADV001"
        )
        db.add(advisor)

        # Students
        students_data = [
            ("6311202375", "ธนัญญา", "กิ่งนาค"),
            ("6510001234", "นักศึกษา", "ทดสอบ"),
            ("6611505915", "จิรศักดิ์", "มกราโชติ"),
            ("6611507812", "อัครินทร์", "ยอดรัก"),
        ]
        student_users = []
        for scode, fname, lname in students_data:
            s = User(
                username=scode, password_hash=hash_password("1234"),
                sys_role=UserRole.student, status=UserStatus.active,
                student_code=scode,
                prefix_th="นาย" if fname != "ธนัญญา" else "นางสาว",
                first_name_th=fname, last_name_th=lname,
                email=f"{scode}@std.cwie.ac.th",
                department_id=dept.id, advisor_user_id=None,
            )
            db.add(s)
            student_users.append(s)

        db.flush()

        # set advisor for students
        for s in student_users:
            s.advisor_user_id = advisor.id

        # ===== 6. Internships =====
        # เฉพาะ ธนัญญา เป็นคนที่ supervisor เลือกแล้ว (user_sup_id = supervisor)
        # คนอื่นๆ user_sup_id = None (ต้องรอบริษัทเพิ่ม)
        from datetime import date
        internships = []
        for i, s in enumerate(student_users):
            intern = Internship(
                internship_code=f"INT-2568-{i+1:03d}",
                user_std_id=s.id,
                user_adv_id=advisor.id,
                user_sup_id=supervisor.id if s.student_code == "6311202375" else None,
                company_id=company.id,
                semester_id=sem.id,
                start_date=date(2025, 6, 1),
                end_date=date(2025, 10, 31),
                required_hours=450,
                completed_hours=0,
                status_id=training_status.id,
                job_title="นักพัฒนาซอฟต์แวร์",
            )
            db.add(intern)
            internships.append(intern)

        db.commit()
        print(f"✅ Seed สำเร็จ!")
        print(f"   - Admin: admin01 / 1234")
        print(f"   - Supervisor: supervisor01 / 1234")
        print(f"   - Advisor: advisor01 / 1234")
        print(f"   - Students: 6311202375, 6510001234, 6611505915, 6611507812 / 1234")
        print(f"   - บริษัท: {company.name_th}")
        print(f"   - Internships: {len(internships)} รายการ")
        print(f"   ⚠️  เฉพาะ 6311202375 ธนัญญา ที่ถูก assign ให้ supervisor แล้ว")
        print(f"   ⚠️  คนอื่นต้องกด 'เพิ่มนักศึกษา' ในหน้าบริษัท")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    seed_data()
