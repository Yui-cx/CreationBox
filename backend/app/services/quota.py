from datetime import date
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import DailyQuota, User


class QuotaExceeded(Exception):
    pass


UNLIMITED_QUOTA = -1


def is_unlimited_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    # Admin accounts are operational users, so they bypass daily usage limits.
    return bool(user and user.is_admin)


def unlimited_quota_snapshot() -> dict:
    return {
        "quota_total": UNLIMITED_QUOTA,
        "quota_used": 0,
        "quota_remaining": UNLIMITED_QUOTA,
    }


def get_or_create_today_quota(db: Session, user_id: int) -> DailyQuota:
    settings = get_settings()
    today = date.today()
    quota = (
        db.query(DailyQuota)
        .filter(DailyQuota.user_id == user_id, DailyQuota.quota_date == today)
        .one_or_none()
    )
    if quota:
        return quota
    quota = DailyQuota(user_id=user_id, quota_date=today, total_quota=settings.daily_free_quota, used_quota=0)
    db.add(quota)
    db.flush()
    return quota


def quota_snapshot(db: Session, user_id: int) -> dict:
    if is_unlimited_user(db, user_id):
        return unlimited_quota_snapshot()
    quota = get_or_create_today_quota(db, user_id)
    db.commit()
    return {
        "quota_total": quota.total_quota,
        "quota_used": quota.used_quota,
        "quota_remaining": max(quota.total_quota - quota.used_quota, 0),
    }


def deduct_quota(db: Session, user_id: int) -> dict:
    if is_unlimited_user(db, user_id):
        return unlimited_quota_snapshot()
    quota = (
        db.query(DailyQuota)
        .filter(DailyQuota.user_id == user_id, DailyQuota.quota_date == date.today())
        .with_for_update()
        .one_or_none()
    )
    if quota is None:
        quota = get_or_create_today_quota(db, user_id)
    if quota.used_quota >= quota.total_quota:
        raise QuotaExceeded("今日免费次数已用完。")
    quota.used_quota += 1
    db.flush()
    return {
        "quota_total": quota.total_quota,
        "quota_used": quota.used_quota,
        "quota_remaining": max(quota.total_quota - quota.used_quota, 0),
    }


def refund_quota(db: Session, user_id: int) -> None:
    if is_unlimited_user(db, user_id):
        return
    quota = get_or_create_today_quota(db, user_id)
    if quota.used_quota > 0:
        quota.used_quota -= 1
    db.flush()
