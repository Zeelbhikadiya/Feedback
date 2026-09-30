from datetime import datetime
from email.mime.text import MIMEText
import smtplib
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import NotificationLog


def log_notification(
    db: Session,
    *,
    subject: str,
    body: str,
    user_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    channel: str = "email",
) -> NotificationLog:
    settings = get_settings()
    status = "logged"
    if settings.smtp_host and settings.smtp_user:
        try:
            _send_smtp(subject, body, to_user_id=user_id, db=db)
            status = "sent"
        except Exception as exc:
            status = f"failed:{exc}"
            body = body + f"\n\n[send_error] {exc}"

    entry = NotificationLog(
        campaign_id=campaign_id,
        user_id=user_id,
        channel=channel,
        subject=subject,
        body=body,
        status=status,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.flush()
    return entry


def _send_smtp(subject: str, body: str, to_user_id: Optional[int], db: Session) -> None:
    from app.models import User

    settings = get_settings()
    if not to_user_id:
        return
    user = db.query(User).filter(User.id == to_user_id).first()
    if not user:
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = user.email
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def campaign_open_message(campaign_name: str, end_at) -> tuple[str, str]:
    subject = f"Campaign open: {campaign_name}"
    body = (
        f"A feedback campaign '{campaign_name}' is now open for your response.\n"
        f"Please complete it before {end_at}.\n"
        f"Open the Leader Feedback portal to submit."
    )
    return subject, body


def reminder_message(campaign_name: str, end_at) -> tuple[str, str]:
    subject = f"Reminder: complete '{campaign_name}'"
    body = (
        f"You still have a pending response for '{campaign_name}'.\n"
        f"Closes at {end_at}."
    )
    return subject, body
