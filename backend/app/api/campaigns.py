from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, joinedload

from app.core.audit import write_audit
from app.core.security import CAMPAIGN_CREATOR_ROLES, MANAGEMENT_ROLES, get_current_user, require_roles
from app.database import get_db
from app.models import (
    Campaign,
    CampaignMode,
    CampaignParticipant,
    CampaignStatus,
    CampaignTrendSnapshot,
    GradeTarget,
    IdentityMode,
    PollResponse,
    User,
    UserRole,
)
from app.schemas import (
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    DashboardOut,
    GradeResultOut,
    GradeSave,
    PollResultOut,
    PollSubmit,
    TrendPoint,
)
from app.services.campaigns import (
    apply_grade_ranks,
    available_ranks,
    build_grade_results,
    build_poll_results,
    campaign_to_out,
    get_or_create_grade_submission,
    refresh_poll_analysis,
    sync_campaign_status,
    validate_poll_submit,
)
from app.services.exports import (
    build_ics,
    export_grade_excel,
    export_grade_pdf,
    export_poll_excel,
    export_poll_pdf,
)
from app.services.notifications import campaign_open_message, log_notification, reminder_message

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _get_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = (
        db.query(Campaign)
        .options(
            joinedload(Campaign.participants).joinedload(CampaignParticipant.user),
            joinedload(Campaign.poll_responses).joinedload(PollResponse.respondent),
            joinedload(Campaign.grade_targets).joinedload(GradeTarget.employee),
            joinedload(Campaign.grade_submission),
            joinedload(Campaign.target_user),
            joinedload(Campaign.group_head),
            joinedload(Campaign.department),
        )
        .filter(Campaign.id == campaign_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    sync_campaign_status(campaign)
    return campaign


def _can_manage(user: User) -> bool:
    return user.role in MANAGEMENT_ROLES


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    status: CampaignStatus | None = None,
    mode: CampaignMode | None = None,
    department_id: int | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Campaign).options(
        joinedload(Campaign.participants),
        joinedload(Campaign.target_user),
        joinedload(Campaign.group_head),
        joinedload(Campaign.department),
        joinedload(Campaign.grade_targets),
        joinedload(Campaign.grade_submission),
    )
    if status:
        q = q.filter(Campaign.status == status)
    if mode:
        q = q.filter(Campaign.mode == mode)
    if department_id:
        q = q.filter(Campaign.department_id == department_id)

    campaigns = q.order_by(Campaign.created_at.desc()).all()
    for c in campaigns:
        sync_campaign_status(c)
    db.commit()

    if mine or user.role in (UserRole.EMPLOYEE, UserRole.GROUP_HEAD):
        filtered = []
        for c in campaigns:
            if c.mode == CampaignMode.POLL and any(p.user_id == user.id for p in c.participants):
                filtered.append(c)
            elif c.mode == CampaignMode.GRADE and c.group_head_id == user.id:
                filtered.append(c)
            elif _can_manage(user) or user.role == UserRole.RESULT_VIEWER:
                filtered.append(c)
        campaigns = filtered
    elif user.role == UserRole.RESULT_VIEWER:
        campaigns = [c for c in campaigns if c.status in (CampaignStatus.ANALYSIS_READY, CampaignStatus.CLOSED, CampaignStatus.ARCHIVED)]

    return [CampaignOut(**campaign_to_out(c)) for c in campaigns]


@router.post("", response_model=CampaignOut)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES)),
):
    if payload.mode == CampaignMode.POLL and not payload.target_user_id:
        raise HTTPException(status_code=400, detail="Poll campaigns require a target leader")
    if payload.mode == CampaignMode.GRADE and not payload.group_head_id:
        raise HTTPException(status_code=400, detail="Grade campaigns require a group head")
    if payload.mode == CampaignMode.GRADE and not payload.grade_employee_ids:
        raise HTTPException(status_code=400, detail="Grade campaigns require employees to rank")

    status = CampaignStatus.DRAFT
    if payload.publish and payload.start_at and payload.end_at:
        now = datetime.utcnow()
        if now < payload.start_at:
            status = CampaignStatus.SCHEDULED
        elif payload.start_at <= now <= payload.end_at:
            status = CampaignStatus.OPEN
        else:
            status = CampaignStatus.CLOSED

    campaign = Campaign(
        name=payload.name,
        mode=payload.mode,
        status=status,
        department_id=payload.department_id,
        target_user_id=payload.target_user_id,
        group_head_id=payload.group_head_id,
        employee_group_id=payload.employee_group_id,
        identity_mode=payload.identity_mode,
        comment_rule=payload.comment_rule,
        rank_direction=payload.rank_direction,
        result_visibility=payload.result_visibility,
        allow_employee_results=payload.allow_employee_results,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reminder_enabled=payload.reminder_enabled,
        created_by_id=user.id,
        locked_settings=payload.publish,
    )
    db.add(campaign)
    db.flush()

    if payload.mode == CampaignMode.POLL:
        for uid in payload.participant_ids:
            emp = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
            if emp:
                db.add(CampaignParticipant(campaign_id=campaign.id, user_id=uid))
    else:
        for uid in payload.grade_employee_ids:
            emp = db.query(User).filter(User.id == uid, User.is_active.is_(True)).first()
            if emp:
                db.add(GradeTarget(campaign_id=campaign.id, employee_id=uid))

    write_audit(db, actor_id=user.id, action="create_campaign", entity_type="campaign", entity_id=campaign.id, detail=campaign.name)
    db.commit()
    campaign = _get_campaign(db, campaign.id)
    return CampaignOut(**campaign_to_out(campaign))


@router.get("/dashboard", response_model=DashboardOut)
def management_dashboard(db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES, UserRole.RESULT_VIEWER))):
    campaigns = db.query(Campaign).options(
        joinedload(Campaign.participants),
        joinedload(Campaign.target_user),
        joinedload(Campaign.group_head),
        joinedload(Campaign.department),
        joinedload(Campaign.grade_targets),
        joinedload(Campaign.grade_submission),
    ).all()
    for c in campaigns:
        sync_campaign_status(c)
    db.commit()
    active = [c for c in campaigns if c.status == CampaignStatus.OPEN]
    scheduled = [c for c in campaigns if c.status == CampaignStatus.SCHEDULED]
    recently_closed = [
        c for c in campaigns if c.status in (CampaignStatus.CLOSED, CampaignStatus.ANALYSIS_READY)
    ][:10]
    return DashboardOut(
        active=[CampaignOut(**campaign_to_out(c)) for c in active],
        scheduled=[CampaignOut(**campaign_to_out(c)) for c in scheduled],
        recently_closed=[CampaignOut(**campaign_to_out(c)) for c in recently_closed],
        totals={
            "active": len(active),
            "scheduled": len(scheduled),
            "closed": len(recently_closed),
            "all": len(campaigns),
        },
    )


@router.get("/trends/{leader_id}", response_model=list[TrendPoint])
def leader_trends(leader_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES, UserRole.RESULT_VIEWER))):
    snaps = (
        db.query(CampaignTrendSnapshot)
        .filter(CampaignTrendSnapshot.target_user_id == leader_id)
        .order_by(CampaignTrendSnapshot.captured_at)
        .all()
    )
    out = []
    for s in snaps:
        camp = db.query(Campaign).filter(Campaign.id == s.campaign_id).first()
        out.append(
            TrendPoint(
                campaign_id=s.campaign_id,
                campaign_name=camp.name if camp else f"Campaign {s.campaign_id}",
                average_score=s.average_score,
                response_count=s.response_count,
                captured_at=s.captured_at,
            )
        )
    return out


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    db.commit()
    return CampaignOut(**campaign_to_out(campaign))


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES)),
):
    campaign = _get_campaign(db, campaign_id)
    if campaign.locked_settings and campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.SCHEDULED):
        # only limited fields after open — handled by explicit admin endpoints
        raise HTTPException(status_code=400, detail="Campaign settings are locked after open. Use admin reopen/close actions.")
    data = payload.model_dump(exclude_unset=True)
    participant_ids = data.pop("participant_ids", None)
    grade_employee_ids = data.pop("grade_employee_ids", None)
    for k, v in data.items():
        setattr(campaign, k, v)
    if participant_ids is not None and campaign.mode == CampaignMode.POLL and campaign.status == CampaignStatus.DRAFT:
        campaign.participants.clear()
        db.flush()
        for uid in participant_ids:
            db.add(CampaignParticipant(campaign_id=campaign.id, user_id=uid))
    if grade_employee_ids is not None and campaign.mode == CampaignMode.GRADE and campaign.status == CampaignStatus.DRAFT:
        campaign.grade_targets.clear()
        db.flush()
        for uid in grade_employee_ids:
            db.add(GradeTarget(campaign_id=campaign.id, employee_id=uid))
    write_audit(db, actor_id=user.id, action="update_campaign", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return CampaignOut(**campaign_to_out(_get_campaign(db, campaign_id)))


@router.post("/{campaign_id}/publish", response_model=CampaignOut)
def publish_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    if not campaign.start_at or not campaign.end_at:
        raise HTTPException(status_code=400, detail="Start and end time required")
    campaign.locked_settings = True
    sync_campaign_status(campaign)
    if campaign.status == CampaignStatus.DRAFT:
        campaign.status = CampaignStatus.SCHEDULED if datetime.utcnow() < campaign.start_at else CampaignStatus.OPEN
    write_audit(db, actor_id=user.id, action="publish_campaign", entity_type="campaign", entity_id=campaign.id)
    if campaign.status == CampaignStatus.OPEN:
        for p in campaign.participants:
            subj, body = campaign_open_message(campaign.name, campaign.end_at)
            log_notification(db, subject=subj, body=body, user_id=p.user_id, campaign_id=campaign.id)
            p.notified_open = True
    db.commit()
    return CampaignOut(**campaign_to_out(_get_campaign(db, campaign_id)))


@router.post("/{campaign_id}/close", response_model=CampaignOut)
def close_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    campaign.status = CampaignStatus.ANALYSIS_READY
    campaign.end_at = datetime.utcnow()
    if campaign.mode == CampaignMode.POLL:
        refresh_poll_analysis(db, campaign)
    write_audit(db, actor_id=user.id, action="close_campaign", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return CampaignOut(**campaign_to_out(_get_campaign(db, campaign_id)))


@router.post("/{campaign_id}/archive", response_model=CampaignOut)
def archive_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    campaign.status = CampaignStatus.ARCHIVED
    write_audit(db, actor_id=user.id, action="archive_campaign", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return CampaignOut(**campaign_to_out(campaign))


@router.post("/{campaign_id}/duplicate", response_model=CampaignOut)
def duplicate_campaign(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*CAMPAIGN_CREATOR_ROLES))):
    src = _get_campaign(db, campaign_id)
    now = datetime.utcnow()
    clone = Campaign(
        name=f"{src.name} (Copy)",
        mode=src.mode,
        status=CampaignStatus.DRAFT,
        department_id=src.department_id,
        target_user_id=src.target_user_id,
        group_head_id=src.group_head_id,
        employee_group_id=src.employee_group_id,
        identity_mode=src.identity_mode,
        comment_rule=src.comment_rule,
        rank_direction=src.rank_direction,
        result_visibility=src.result_visibility,
        allow_employee_results=src.allow_employee_results,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=8),
        reminder_enabled=src.reminder_enabled,
        created_by_id=user.id,
        locked_settings=False,
    )
    db.add(clone)
    db.flush()
    for p in src.participants:
        db.add(CampaignParticipant(campaign_id=clone.id, user_id=p.user_id))
    for t in src.grade_targets:
        db.add(GradeTarget(campaign_id=clone.id, employee_id=t.employee_id))
    write_audit(db, actor_id=user.id, action="duplicate_campaign", entity_type="campaign", entity_id=clone.id)
    db.commit()
    return CampaignOut(**campaign_to_out(_get_campaign(db, clone.id)))


@router.post("/{campaign_id}/poll", response_model=dict)
def submit_poll(
    campaign_id: int,
    payload: PollSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.POLL:
        raise HTTPException(status_code=400, detail="Not a poll campaign")
    sync_campaign_status(campaign)
    if campaign.status != CampaignStatus.OPEN:
        raise HTTPException(status_code=400, detail="Campaign is not open for submissions")
    participant = next((p for p in campaign.participants if p.user_id == user.id), None)
    if not participant:
        raise HTTPException(status_code=403, detail="You are not a participant in this campaign")
    existing = next((r for r in campaign.poll_responses if r.respondent_id == user.id), None)
    if existing and not existing.is_reopened:
        raise HTTPException(status_code=400, detail="You already submitted a response")
    try:
        validate_poll_submit(campaign, payload.comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    anon_token = None
    if campaign.identity_mode == IdentityMode.STRICT_ANONYMOUS:
        anon_token = secrets.token_hex(16)

    if existing and existing.is_reopened:
        existing.score = payload.score
        existing.comment = None if campaign.comment_rule.value == "disabled" else payload.comment
        existing.is_reopened = False
        existing.submitted_at = datetime.utcnow()
        existing.anonymous_token = anon_token
    else:
        db.add(
            PollResponse(
                campaign_id=campaign.id,
                respondent_id=user.id,
                score=payload.score,
                comment=None if campaign.comment_rule.value == "disabled" else payload.comment,
                anonymous_token=anon_token,
            )
        )
    participant.has_submitted = True
    write_audit(db, actor_id=user.id, action="submit_poll", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return {"ok": True, "message": "Response submitted"}


@router.get("/{campaign_id}/poll/mine")
def my_poll_status(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    participant = next((p for p in campaign.participants if p.user_id == user.id), None)
    response = next((r for r in campaign.poll_responses if r.respondent_id == user.id), None)
    return {
        "is_participant": bool(participant),
        "has_submitted": bool(participant and participant.has_submitted),
        "can_edit": bool(response and response.is_reopened),
        "identity_mode": campaign.identity_mode,
        "comment_rule": campaign.comment_rule,
        "target_name": campaign.target_user.full_name if campaign.target_user else None,
        "status": campaign.status,
        "end_at": campaign.end_at,
    }


@router.post("/{campaign_id}/grade", response_model=GradeResultOut)
def save_grade(
    campaign_id: int,
    payload: GradeSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.GRADE:
        raise HTTPException(status_code=400, detail="Not a grade campaign")
    sync_campaign_status(campaign)
    if campaign.status != CampaignStatus.OPEN:
        raise HTTPException(status_code=400, detail="Campaign is not open")
    if campaign.group_head_id != user.id and user.role != UserRole.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail="Only the assigned Group Head can rank")
    submission = get_or_create_grade_submission(db, campaign)
    required = {t.employee_id for t in campaign.grade_targets}
    try:
        apply_grade_ranks(
            db,
            submission,
            [{"employee_id": r.employee_id, "rank": r.rank} for r in payload.ranks],
            required,
            payload.finalize,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    write_audit(
        db,
        actor_id=user.id,
        action="finalize_grade" if payload.finalize else "save_grade_draft",
        entity_type="campaign",
        entity_id=campaign.id,
    )
    if payload.finalize:
        campaign.status = CampaignStatus.ANALYSIS_READY
    db.commit()
    return GradeResultOut(**build_grade_results(db, _get_campaign(db, campaign_id)))


@router.get("/{campaign_id}/grade", response_model=dict)
def get_grade_workspace(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.GRADE:
        raise HTTPException(status_code=400, detail="Not a grade campaign")
    if (
        campaign.group_head_id != user.id
        and not _can_manage(user)
        and user.role != UserRole.RESULT_VIEWER
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    result = build_grade_results(db, campaign)
    employees = [
        {"id": t.employee_id, "full_name": t.employee.full_name if t.employee else ""}
        for t in campaign.grade_targets
    ]
    return {
        **result,
        "employees": employees,
        "available_ranks": available_ranks(campaign),
        "rank_direction_label": "Rank 1 = Highest / Best"
        if campaign.rank_direction.value == "one_is_best"
        else "Rank 1 = Lowest",
        "status": campaign.status,
    }


@router.get("/{campaign_id}/results/poll", response_model=PollResultOut)
def poll_results(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.POLL:
        raise HTTPException(status_code=400, detail="Not a poll campaign")
    if not _can_view_results(user, campaign):
        raise HTTPException(status_code=403, detail="Not authorized to view results")
    include_ids = campaign.identity_mode == IdentityMode.NAMED and _can_manage(user)
    if campaign.status in (CampaignStatus.CLOSED, CampaignStatus.ANALYSIS_READY, CampaignStatus.ARCHIVED):
        if not campaign.theme_summary:
            refresh_poll_analysis(db, campaign)
            db.commit()
    return PollResultOut(**build_poll_results(db, campaign, include_identities=include_ids))


@router.get("/{campaign_id}/results/grade", response_model=GradeResultOut)
def grade_results(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.GRADE:
        raise HTTPException(status_code=400, detail="Not a grade campaign")
    if not _can_view_results(user, campaign):
        raise HTTPException(status_code=403, detail="Not authorized")
    return GradeResultOut(**build_grade_results(db, campaign))


@router.post("/{campaign_id}/analyze")
def run_analysis(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode != CampaignMode.POLL:
        raise HTTPException(status_code=400, detail="Analysis is for poll campaigns")
    refresh_poll_analysis(db, campaign)
    write_audit(db, actor_id=user.id, action="run_analysis", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return {"ok": True, "ai_summary": campaign.ai_summary, "theme_summary": campaign.theme_summary}


@router.post("/{campaign_id}/reopen-response/{user_id}")
def reopen_response(
    campaign_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    campaign = _get_campaign(db, campaign_id)
    response = next((r for r in campaign.poll_responses if r.respondent_id == user_id), None)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    response.is_reopened = True
    participant = next((p for p in campaign.participants if p.user_id == user_id), None)
    if participant:
        participant.has_submitted = False
    if campaign.status in (CampaignStatus.CLOSED, CampaignStatus.ANALYSIS_READY):
        campaign.status = CampaignStatus.OPEN
    write_audit(db, actor_id=actor.id, action="reopen_response", entity_type="poll_response", entity_id=response.id)
    db.commit()
    return {"ok": True}


@router.post("/{campaign_id}/reopen-grade")
def reopen_grade(campaign_id: int, db: Session = Depends(get_db), actor: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    if not campaign.grade_submission:
        raise HTTPException(status_code=404, detail="No grade submission")
    campaign.grade_submission.is_final = False
    campaign.grade_submission.is_draft = True
    campaign.status = CampaignStatus.OPEN
    write_audit(db, actor_id=actor.id, action="reopen_grade", entity_type="campaign", entity_id=campaign.id)
    db.commit()
    return {"ok": True}


@router.get("/{campaign_id}/export/{fmt}")
def export_campaign(campaign_id: int, fmt: str, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES, UserRole.RESULT_VIEWER))):
    campaign = _get_campaign(db, campaign_id)
    if campaign.mode == CampaignMode.POLL:
        result = build_poll_results(db, campaign, include_identities=campaign.identity_mode == IdentityMode.NAMED)
        if fmt == "xlsx":
            data = export_poll_excel(campaign, result)
            return Response(
                data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="poll_{campaign.id}.xlsx"'},
            )
        if fmt == "pdf":
            data = export_poll_pdf(campaign, result)
            return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="poll_{campaign.id}.pdf"'})
    else:
        result = build_grade_results(db, campaign)
        if fmt == "xlsx":
            data = export_grade_excel(campaign, result)
            return Response(
                data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="grade_{campaign.id}.xlsx"'},
            )
        if fmt == "pdf":
            data = export_grade_pdf(campaign, result)
            return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="grade_{campaign.id}.pdf"'})
    raise HTTPException(status_code=400, detail="Format must be pdf or xlsx")


@router.get("/{campaign_id}/calendar.ics")
def calendar_ics(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    campaign = _get_campaign(db, campaign_id)
    content = build_ics(campaign)
    return Response(content, media_type="text/calendar", headers={"Content-Disposition": f'attachment; filename="campaign_{campaign.id}.ics"'})


@router.get("/{campaign_id}/pending")
def pending_participants(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    """List pending without revealing anonymous answers."""
    campaign = _get_campaign(db, campaign_id)
    pending = []
    for p in campaign.participants:
        if not p.has_submitted:
            pending.append({"user_id": p.user_id, "full_name": p.user.full_name if p.user else None, "email": p.user.email if p.user else None})
    return {"campaign_id": campaign.id, "pending_count": len(pending), "pending": pending}


@router.post("/{campaign_id}/remind")
def send_reminders(campaign_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*MANAGEMENT_ROLES))):
    campaign = _get_campaign(db, campaign_id)
    count = 0
    for p in campaign.participants:
        if not p.has_submitted:
            subj, body = reminder_message(campaign.name, campaign.end_at)
            log_notification(db, subject=subj, body=body, user_id=p.user_id, campaign_id=campaign.id)
            p.notified_reminder = True
            count += 1
    write_audit(db, actor_id=user.id, action="send_reminders", entity_type="campaign", entity_id=campaign.id, detail=str(count))
    db.commit()
    return {"ok": True, "reminders": count}


def _can_view_results(user: User, campaign: Campaign) -> bool:
    if user.role in MANAGEMENT_ROLES or user.role == UserRole.RESULT_VIEWER:
        return True
    if campaign.allow_employee_results and campaign.status in (
        CampaignStatus.ANALYSIS_READY,
        CampaignStatus.CLOSED,
        CampaignStatus.ARCHIVED,
    ):
        if campaign.mode == CampaignMode.POLL and any(p.user_id == user.id for p in campaign.participants):
            return True
        if campaign.mode == CampaignMode.GRADE and campaign.group_head_id == user.id:
            return True
    return False
