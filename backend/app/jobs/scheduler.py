from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Campaign, CampaignMode, CampaignStatus
from app.services.campaigns import refresh_poll_analysis, sync_campaign_status
from app.services.notifications import log_notification, reminder_message

scheduler = BackgroundScheduler()


def tick_campaigns():
    db: Session = SessionLocal()
    try:
        campaigns = db.query(Campaign).filter(Campaign.status.notin_([CampaignStatus.ARCHIVED, CampaignStatus.DRAFT])).all()
        now = datetime.utcnow()
        for c in campaigns:
            prev = c.status
            sync_campaign_status(c)
            if prev == CampaignStatus.OPEN and c.status in (CampaignStatus.CLOSED, CampaignStatus.ANALYSIS_READY):
                if c.mode == CampaignMode.POLL:
                    refresh_poll_analysis(db, c)
            # Final reminder within 24h of close
            if c.status == CampaignStatus.OPEN and c.reminder_enabled and c.end_at:
                hours_left = (c.end_at - now).total_seconds() / 3600
                if 0 < hours_left <= 24:
                    for p in c.participants:
                        if not p.has_submitted and not p.notified_final:
                            subj, body = reminder_message(c.name, c.end_at)
                            log_notification(db, subject=f"[Final] {subj}", body=body, user_id=p.user_id, campaign_id=c.id)
                            p.notified_final = True
        db.commit()
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(tick_campaigns, "interval", minutes=1, id="campaign_tick", replace_existing=True)
        scheduler.start()
