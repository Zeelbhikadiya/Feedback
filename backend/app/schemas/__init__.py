from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models import (
    CampaignMode,
    CampaignStatus,
    CommentRule,
    IdentityMode,
    RankDirection,
    UserRole,
)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithUser(Token):
    user: "UserOut"


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.EMPLOYEE
    department_id: Optional[int] = None
    employee_code: Optional[str] = None
    is_leader: bool = False
    locale: str = "en"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_leader: Optional[bool] = None
    locale: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    department_id: Optional[int] = None
    employee_code: Optional[str] = None
    is_active: bool
    is_leader: bool
    locale: str

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str
    code: Optional[str] = None


class DepartmentOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    name: str
    department_id: Optional[int] = None
    member_ids: list[int] = []


class GroupOut(BaseModel):
    id: int
    name: str
    department_id: Optional[int] = None
    member_ids: list[int] = []

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    name: str
    mode: CampaignMode
    department_id: Optional[int] = None
    target_user_id: Optional[int] = None
    group_head_id: Optional[int] = None
    employee_group_id: Optional[int] = None
    participant_ids: list[int] = []
    grade_employee_ids: list[int] = []
    identity_mode: IdentityMode = IdentityMode.NAMED
    comment_rule: CommentRule = CommentRule.OPTIONAL
    rank_direction: RankDirection = RankDirection.ONE_IS_BEST
    result_visibility: str = "management_only"
    allow_employee_results: bool = False
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    reminder_enabled: bool = True
    publish: bool = False


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    identity_mode: Optional[IdentityMode] = None
    comment_rule: Optional[CommentRule] = None
    rank_direction: Optional[RankDirection] = None
    result_visibility: Optional[str] = None
    allow_employee_results: Optional[bool] = None
    reminder_enabled: Optional[bool] = None
    participant_ids: Optional[list[int]] = None
    grade_employee_ids: Optional[list[int]] = None
    target_user_id: Optional[int] = None
    group_head_id: Optional[int] = None


class CampaignOut(BaseModel):
    id: int
    name: str
    mode: CampaignMode
    status: CampaignStatus
    department_id: Optional[int] = None
    target_user_id: Optional[int] = None
    group_head_id: Optional[int] = None
    employee_group_id: Optional[int] = None
    identity_mode: IdentityMode
    comment_rule: CommentRule
    rank_direction: RankDirection
    result_visibility: str
    allow_employee_results: bool
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    reminder_enabled: bool
    locked_settings: bool
    participant_count: int = 0
    submitted_count: int = 0
    target_name: Optional[str] = None
    group_head_name: Optional[str] = None
    department_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PollSubmit(BaseModel):
    score: int = Field(ge=1, le=10)
    comment: Optional[str] = None


class GradeRankItem(BaseModel):
    employee_id: int
    rank: int = Field(ge=1)


class GradeSave(BaseModel):
    ranks: list[GradeRankItem]
    finalize: bool = False


class PollResultOut(BaseModel):
    campaign_id: int
    invited: int
    submitted: int
    pending: int
    response_rate: float
    average_score: Optional[float]
    median_score: Optional[float]
    distribution: dict[int, int]
    star_average: Optional[float]
    comment_count: int
    theme_summary: Optional[dict[str, Any]] = None
    ai_summary: Optional[str] = None
    comments: list[dict[str, Any]] = []


class GradeResultOut(BaseModel):
    campaign_id: int
    is_final: bool
    ranked_count: int
    total_required: int
    rank_direction: RankDirection
    ranking: list[dict[str, Any]]
    reopened_note: Optional[str] = None


class DashboardOut(BaseModel):
    active: list[CampaignOut]
    scheduled: list[CampaignOut]
    recently_closed: list[CampaignOut]
    totals: dict[str, int]


class TrendPoint(BaseModel):
    campaign_id: int
    campaign_name: str
    average_score: Optional[float]
    response_count: int
    captured_at: datetime


class SSOConfigOut(BaseModel):
    enabled: bool
    discovery_url: Optional[str] = None
    client_id: Optional[str] = None


TokenWithUser.model_rebuild()
