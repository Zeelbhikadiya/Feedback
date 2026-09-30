"""Seed demo organization, users, and sample campaigns."""

from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    Campaign,
    CampaignMode,
    CampaignParticipant,
    CampaignStatus,
    CommentRule,
    Department,
    EmployeeGroup,
    EmployeeGroupMember,
    GradeTarget,
    IdentityMode,
    RankDirection,
    User,
    UserRole,
)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@company.local").first():
            print("Seed already applied.")
            return

        prod = Department(name="Production", code="PROD")
        hr = Department(name="Human Resources", code="HR")
        eng = Department(name="Engineering", code="ENG")
        db.add_all([prod, hr, eng])
        db.flush()

        def u(email, name, role, dept_id, leader=False, code=None):
            return User(
                email=email,
                full_name=name,
                hashed_password=hash_password("Password123!"),
                role=role,
                department_id=dept_id,
                is_leader=leader,
                employee_code=code,
                is_active=True,
            )

        admin = u("admin@company.local", "System Admin", UserRole.SYSTEM_ADMIN, hr.id, code="A001")
        mgmt = u("hr@company.local", "Priya Sharma", UserRole.MANAGEMENT, hr.id, code="H001")
        leader = u("leader@company.local", "Rahul Mehta", UserRole.EMPLOYEE, prod.id, leader=True, code="L001")
        ghead = u("grouphead@company.local", "Anita Desai", UserRole.GROUP_HEAD, prod.id, code="G001")
        viewer = u("viewer@company.local", "Results Viewer", UserRole.RESULT_VIEWER, hr.id, code="V001")
        employees = [
            u("e1@company.local", "Aman Patel", UserRole.EMPLOYEE, prod.id, code="E001"),
            u("e2@company.local", "Sneha Joshi", UserRole.EMPLOYEE, prod.id, code="E002"),
            u("e3@company.local", "Vikram Shah", UserRole.EMPLOYEE, prod.id, code="E003"),
            u("e4@company.local", "Neha Kapoor", UserRole.EMPLOYEE, prod.id, code="E004"),
            u("e5@company.local", "Rohan Gupta", UserRole.EMPLOYEE, eng.id, code="E005"),
        ]
        db.add_all([admin, mgmt, leader, ghead, viewer, *employees])
        db.flush()

        group = EmployeeGroup(name="Production Floor Team", department_id=prod.id, created_by_id=mgmt.id)
        db.add(group)
        db.flush()
        for emp in employees[:4]:
            db.add(EmployeeGroupMember(group_id=group.id, user_id=emp.id))

        now = datetime.utcnow()
        poll = Campaign(
            name="Production Leader Review - Q4",
            mode=CampaignMode.POLL,
            status=CampaignStatus.OPEN,
            department_id=prod.id,
            target_user_id=leader.id,
            identity_mode=IdentityMode.ANONYMOUS_RESULT,
            comment_rule=CommentRule.REQUIRED,
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=7),
            reminder_enabled=True,
            created_by_id=mgmt.id,
            locked_settings=True,
            allow_employee_results=False,
        )
        db.add(poll)
        db.flush()
        for emp in employees:
            db.add(CampaignParticipant(campaign_id=poll.id, user_id=emp.id))

        grade = Campaign(
            name="Production Team Ranking - Sept",
            mode=CampaignMode.GRADE,
            status=CampaignStatus.OPEN,
            department_id=prod.id,
            group_head_id=ghead.id,
            employee_group_id=group.id,
            identity_mode=IdentityMode.NAMED,
            rank_direction=RankDirection.ONE_IS_BEST,
            start_at=now - timedelta(hours=6),
            end_at=now + timedelta(days=5),
            reminder_enabled=True,
            created_by_id=mgmt.id,
            locked_settings=True,
        )
        db.add(grade)
        db.flush()
        for emp in employees[:4]:
            db.add(GradeTarget(campaign_id=grade.id, employee_id=emp.id))

        db.commit()
        print("Seed complete.")
        print("Login accounts (password: Password123!):")
        print("  admin@company.local       — System Admin")
        print("  hr@company.local          — Management/HR")
        print("  grouphead@company.local   — Group Head")
        print("  leader@company.local      — Leader (poll target)")
        print("  e1@company.local … e5     — Employees")
        print("  viewer@company.local      — Result Viewer")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
