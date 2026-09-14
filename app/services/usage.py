import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db_models import UsageRecord, User
from app.config import settings


def _today():
    return datetime.date.today()


def videos_used_today(db: Session, user: User) -> int:
    return db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.usage_date == _today(),
    ).count()


def user_can_process_video(db: Session, user: User) -> bool:
    if user.is_subscribed and (not user.subscription_expires_at or user.subscription_expires_at > datetime.datetime.utcnow()):
        return True
    return videos_used_today(db, user) < settings.free_daily_videos


def reserve_usage(db: Session, user: User, job_id: str) -> None:
    """Reserve one free-tier slot before expensive AI work starts.

    A unique constraint on (user, date, job_id) prevents duplicate records.
    The caller should roll back if the transaction fails.
    """
    if user.is_subscribed and (not user.subscription_expires_at or user.subscription_expires_at > datetime.datetime.utcnow()):
        return
    if videos_used_today(db, user) >= settings.free_daily_videos:
        raise ValueError("daily_limit")
    db.add(UsageRecord(user_id=user.id, usage_date=_today(), job_id=job_id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("usage_conflict")


def record_usage(db: Session, user: User, job_id: str) -> None:
    # Backward-compatible wrapper; new code should reserve before processing.
    reserve_usage(db, user, job_id)
