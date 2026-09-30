from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.database import get_db
from app.models import AuditLog, NotificationLog, User, UserRole

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def list_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.MANAGEMENT)),
):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "actor_id": r.actor_id,
            "actor_name": r.actor.full_name if r.actor else None,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "detail": r.detail,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/notifications")
def list_notifications(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.MANAGEMENT)),
):
    rows = db.query(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "campaign_id": r.campaign_id,
            "user_id": r.user_id,
            "subject": r.subject,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/health")
def health():
    return {"status": "ok"}
