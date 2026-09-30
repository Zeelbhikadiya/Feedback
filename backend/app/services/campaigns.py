from datetime import datetime
from statistics import median
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    Campaign,
    CampaignMode,
    CampaignParticipant,
    CampaignStatus,
    CampaignTrendSnapshot,
    CommentRule,
    GradeRank,
    GradeSubmission,
    GradeTarget,
    IdentityMode,
    PollResponse,
    User,
)
from app.services.ai_analysis import analyze_comments
from app.services.notifications import log_notification


def sync_campaign_status(campaign: Campaign, now: Optional[datetime] = None) -> CampaignStatus:
    now = now or datetime.utcnow()
    if campaign.status in (CampaignStatus.ARCHIVED, CampaignStatus.DRAFT):
        return campaign.status
    if campaign.status == CampaignStatus.ANALYSIS_READY:
        return campaign.status

    if campaign.start_at and campaign.end_at:
        if now < campaign.start_at:
            campaign.status = CampaignStatus.SCHEDULED
        elif campaign.start_at <= now <= campaign.end_at:
            if campaign.status != CampaignStatus.OPEN:
                campaign.status = CampaignStatus.OPEN
        elif now > campaign.end_at:
            if campaign.status == CampaignStatus.OPEN:
                campaign.status = CampaignStatus.CLOSED
            if campaign.status == CampaignStatus.CLOSED:
                campaign.status = CampaignStatus.ANALYSIS_READY
    return campaign.status


def campaign_to_out(c: Campaign) -> dict:
    submitted = sum(1 for p in c.participants if p.has_submitted)
    if c.mode == CampaignMode.GRADE and c.grade_submission and c.grade_submission.is_final:
        submitted = 1
    return {
        "id": c.id,
        "name": c.name,
        "mode": c.mode,
        "status": c.status,
        "department_id": c.department_id,
        "target_user_id": c.target_user_id,
        "group_head_id": c.group_head_id,
        "employee_group_id": c.employee_group_id,
        "identity_mode": c.identity_mode,
        "comment_rule": c.comment_rule,
        "rank_direction": c.rank_direction,
        "result_visibility": c.result_visibility,
        "allow_employee_results": c.allow_employee_results,
        "start_at": c.start_at,
        "end_at": c.end_at,
        "reminder_enabled": c.reminder_enabled,
        "locked_settings": c.locked_settings,
        "participant_count": len(c.participants) if c.mode == CampaignMode.POLL else len(c.grade_targets),
        "submitted_count": submitted if c.mode == CampaignMode.POLL else (1 if (c.grade_submission and c.grade_submission.is_final) else 0),
        "target_name": c.target_user.full_name if c.target_user else None,
        "group_head_name": c.group_head.full_name if c.group_head else None,
        "department_name": c.department.name if c.department else None,
        "created_at": c.created_at,
    }


def build_poll_results(db: Session, campaign: Campaign, include_identities: bool) -> dict[str, Any]:
    responses = campaign.poll_responses
    invited = len(campaign.participants)
    submitted = len(responses)
    pending = max(invited - submitted, 0)
    scores = [r.score for r in responses]
    distribution = {i: 0 for i in range(1, 11)}
    for s in scores:
        distribution[s] = distribution.get(s, 0) + 1
    avg = round(sum(scores) / len(scores), 2) if scores else None
    med = float(median(scores)) if scores else None
    comments_payload = []
    for r in responses:
        item: dict[str, Any] = {
            "id": r.id,
            "score": r.score,
            "comment": r.comment,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        }
        if include_identities and campaign.identity_mode == IdentityMode.NAMED:
            item["respondent_name"] = r.respondent.full_name if r.respondent else None
            item["respondent_id"] = r.respondent_id
        else:
            item["respondent_name"] = None
            item["respondent_id"] = None
        comments_payload.append(item)

    return {
        "campaign_id": campaign.id,
        "invited": invited,
        "submitted": submitted,
        "pending": pending,
        "response_rate": round((submitted / invited) * 100, 1) if invited else 0.0,
        "average_score": avg,
        "median_score": med,
        "distribution": distribution,
        "star_average": round((avg / 2), 2) if avg is not None else None,
        "comment_count": sum(1 for r in responses if r.comment),
        "theme_summary": campaign.theme_summary,
        "ai_summary": campaign.ai_summary,
        "comments": comments_payload,
    }


def refresh_poll_analysis(db: Session, campaign: Campaign) -> None:
    comments = [r.comment for r in campaign.poll_responses if r.comment]
    summary = analyze_comments(comments)
    campaign.theme_summary = summary.get("themes")
    campaign.ai_summary = summary.get("summary")
    if campaign.target_user_id and campaign.poll_responses:
        scores = [r.score for r in campaign.poll_responses]
        avg = sum(scores) / len(scores)
        existing = (
            db.query(CampaignTrendSnapshot)
            .filter(
                CampaignTrendSnapshot.campaign_id == campaign.id,
                CampaignTrendSnapshot.target_user_id == campaign.target_user_id,
            )
            .first()
        )
        if existing:
            existing.average_score = avg
            existing.response_count = len(scores)
            existing.captured_at = datetime.utcnow()
        else:
            db.add(
                CampaignTrendSnapshot(
                    target_user_id=campaign.target_user_id,
                    campaign_id=campaign.id,
                    average_score=avg,
                    response_count=len(scores),
                )
            )


def validate_poll_submit(campaign: Campaign, comment: Optional[str]) -> None:
    if campaign.comment_rule == CommentRule.REQUIRED and not (comment and comment.strip()):
        raise ValueError("Comment is required for this campaign")
    if campaign.comment_rule == CommentRule.DISABLED and comment:
        raise ValueError("Comments are disabled for this campaign")


def get_or_create_grade_submission(db: Session, campaign: Campaign) -> GradeSubmission:
    if campaign.grade_submission:
        return campaign.grade_submission
    sub = GradeSubmission(
        campaign_id=campaign.id,
        group_head_id=campaign.group_head_id,
        is_draft=True,
        is_final=False,
    )
    db.add(sub)
    db.flush()
    return sub


def apply_grade_ranks(
    db: Session,
    submission: GradeSubmission,
    ranks: list[dict],
    required_employee_ids: set[int],
    finalize: bool,
) -> GradeSubmission:
    if submission.is_final:
        raise ValueError("Ranking is locked. Ask management to reopen.")

    # Clear and re-apply for draft saves (validates uniqueness)
    seen_employees = set()
    seen_ranks = set()
    n = len(required_employee_ids)
    for item in ranks:
        eid = item["employee_id"]
        rank = item["rank"]
        if eid not in required_employee_ids:
            raise ValueError(f"Employee {eid} is not in this grading group")
        if eid in seen_employees:
            raise ValueError("Duplicate employee in ranking")
        if rank in seen_ranks:
            raise ValueError(f"Rank {rank} is already used")
        if rank < 1 or rank > n:
            raise ValueError(f"Rank must be between 1 and {n}")
        seen_employees.add(eid)
        seen_ranks.add(rank)

    for existing in list(submission.ranks):
        db.delete(existing)
    db.flush()

    for item in ranks:
        db.add(
            GradeRank(
                submission_id=submission.id,
                employee_id=item["employee_id"],
                rank=item["rank"],
            )
        )
    db.flush()

    if finalize:
        if seen_employees != required_employee_ids:
            missing = required_employee_ids - seen_employees
            raise ValueError(f"All employees must be ranked before final submit. Missing: {len(missing)}")
        if len(seen_ranks) != n:
            raise ValueError("Every rank from 1 to N must be used exactly once")
        submission.is_draft = False
        submission.is_final = True
        submission.submitted_at = datetime.utcnow()
    else:
        submission.is_draft = True
        submission.is_final = False

    submission.updated_at = datetime.utcnow()
    return submission


def build_grade_results(db: Session, campaign: Campaign) -> dict[str, Any]:
    targets = campaign.grade_targets
    submission = campaign.grade_submission
    ranking = []
    if submission:
        rank_map = {r.employee_id: r.rank for r in submission.ranks}
        users = {t.employee_id: t.employee for t in targets}
        for eid, emp in users.items():
            ranking.append(
                {
                    "employee_id": eid,
                    "employee_name": emp.full_name if emp else None,
                    "rank": rank_map.get(eid),
                }
            )
        ranking.sort(key=lambda x: (x["rank"] is None, x["rank"] or 9999))
    return {
        "campaign_id": campaign.id,
        "is_final": bool(submission and submission.is_final),
        "ranked_count": len(submission.ranks) if submission else 0,
        "total_required": len(targets),
        "rank_direction": campaign.rank_direction,
        "ranking": ranking,
        "reopened_note": None,
    }


def available_ranks(campaign: Campaign) -> list[int]:
    n = len(campaign.grade_targets)
    used = set()
    if campaign.grade_submission:
        used = {r.rank for r in campaign.grade_submission.ranks}
    return [i for i in range(1, n + 1) if i not in used]
