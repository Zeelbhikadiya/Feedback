import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    SYSTEM_ADMIN = "system_admin"
    MANAGEMENT = "management"
    GROUP_HEAD = "group_head"
    EMPLOYEE = "employee"
    RESULT_VIEWER = "result_viewer"


class CampaignMode(str, enum.Enum):
    POLL = "poll"
    GRADE = "grade"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    ANALYSIS_READY = "analysis_ready"
    ARCHIVED = "archived"


class IdentityMode(str, enum.Enum):
    NAMED = "named"
    ANONYMOUS_RESULT = "anonymous_result"
    STRICT_ANONYMOUS = "strict_anonymous"


class CommentRule(str, enum.Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DISABLED = "disabled"


class RankDirection(str, enum.Enum):
    ONE_IS_BEST = "one_is_best"
    ONE_IS_LOWEST = "one_is_lowest"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="department")
    groups = relationship("EmployeeGroup", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    employee_code = Column(String(50), unique=True, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_leader = Column(Boolean, default=False)
    locale = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="users")
    poll_responses = relationship("PollResponse", back_populates="respondent", foreign_keys="PollResponse.respondent_id")
    grade_submissions = relationship("GradeSubmission", back_populates="group_head")


class EmployeeGroup(Base):
    __tablename__ = "employee_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="groups")
    members = relationship("EmployeeGroupMember", back_populates="group", cascade="all, delete-orphan")


class EmployeeGroupMember(Base):
    __tablename__ = "employee_group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("employee_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    group = relationship("EmployeeGroup", back_populates="members")
    user = relationship("User")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    mode = Column(Enum(CampaignMode), nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Poll: leader
    group_head_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Grade
    employee_group_id = Column(Integer, ForeignKey("employee_groups.id"), nullable=True)
    identity_mode = Column(Enum(IdentityMode), default=IdentityMode.NAMED, nullable=False)
    comment_rule = Column(Enum(CommentRule), default=CommentRule.OPTIONAL, nullable=False)
    rank_direction = Column(Enum(RankDirection), default=RankDirection.ONE_IS_BEST, nullable=False)
    result_visibility = Column(String(50), default="management_only")  # management_only | participants
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    reminder_enabled = Column(Boolean, default=True)
    allow_employee_results = Column(Boolean, default=False)
    ai_summary = Column(Text, nullable=True)
    theme_summary = Column(JSON, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    locked_settings = Column(Boolean, default=False)

    department = relationship("Department")
    target_user = relationship("User", foreign_keys=[target_user_id])
    group_head = relationship("User", foreign_keys=[group_head_id])
    employee_group = relationship("EmployeeGroup")
    created_by = relationship("User", foreign_keys=[created_by_id])
    participants = relationship("CampaignParticipant", back_populates="campaign", cascade="all, delete-orphan")
    poll_responses = relationship("PollResponse", back_populates="campaign", cascade="all, delete-orphan")
    grade_submission = relationship("GradeSubmission", back_populates="campaign", uselist=False, cascade="all, delete-orphan")
    grade_targets = relationship("GradeTarget", back_populates="campaign", cascade="all, delete-orphan")


class CampaignParticipant(Base):
    __tablename__ = "campaign_participants"
    __table_args__ = (UniqueConstraint("campaign_id", "user_id", name="uq_campaign_participant"),)

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    has_submitted = Column(Boolean, default=False)
    notified_open = Column(Boolean, default=False)
    notified_reminder = Column(Boolean, default=False)
    notified_final = Column(Boolean, default=False)

    campaign = relationship("Campaign", back_populates="participants")
    user = relationship("User")


class PollResponse(Base):
    __tablename__ = "poll_responses"
    __table_args__ = (UniqueConstraint("campaign_id", "respondent_id", name="uq_poll_response"),)

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    respondent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    is_reopened = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    # For strict anonymity: store response hash linkage separately conceptually
    anonymous_token = Column(String(64), nullable=True)

    campaign = relationship("Campaign", back_populates="poll_responses")
    respondent = relationship("User", foreign_keys=[respondent_id], back_populates="poll_responses")


class GradeTarget(Base):
    """Employees to be ranked in a grade campaign."""
    __tablename__ = "grade_targets"
    __table_args__ = (UniqueConstraint("campaign_id", "employee_id", name="uq_grade_target"),)

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    campaign = relationship("Campaign", back_populates="grade_targets")
    employee = relationship("User")


class GradeSubmission(Base):
    __tablename__ = "grade_submissions"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), unique=True, nullable=False)
    group_head_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_draft = Column(Boolean, default=True)
    is_final = Column(Boolean, default=False)
    submitted_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="grade_submission")
    group_head = relationship("User", back_populates="grade_submissions")
    ranks = relationship("GradeRank", back_populates="submission", cascade="all, delete-orphan")


class GradeRank(Base):
    __tablename__ = "grade_ranks"
    __table_args__ = (
        UniqueConstraint("submission_id", "employee_id", name="uq_grade_employee"),
        UniqueConstraint("submission_id", "rank", name="uq_grade_rank"),
    )

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("grade_submissions.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rank = Column(Integer, nullable=False)

    submission = relationship("GradeSubmission", back_populates="ranks")
    employee = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    actor = relationship("User")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    channel = Column(String(30), default="email")
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(30), default="logged")  # logged | sent | failed
    created_at = Column(DateTime, default=datetime.utcnow)


class CampaignTrendSnapshot(Base):
    """For trend comparison across repeated leader reviews."""
    __tablename__ = "campaign_trend_snapshots"

    id = Column(Integer, primary_key=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    average_score = Column(Float, nullable=True)
    response_count = Column(Integer, default=0)
    captured_at = Column(DateTime, default=datetime.utcnow)
