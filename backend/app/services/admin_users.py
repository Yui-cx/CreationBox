from datetime import date
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import hash_password
from app.models.entities import DailyQuota, Generation, User
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminQuotaRequest,
    AdminResetPasswordRequest,
    AdminUpdateUserRequest,
    AdminUserItem,
)
from app.services.quota import UNLIMITED_QUOTA


def normalize_email(email: str | None) -> str | None:
    value = (email or "").strip()
    return value or None


def get_or_create_today_quota_for_admin(db: Session, user_id: int, total_quota: int) -> DailyQuota:
    quota = (
        db.query(DailyQuota)
        .filter(DailyQuota.user_id == user_id, DailyQuota.quota_date == date.today())
        .one_or_none()
    )
    if quota:
        return quota
    quota = DailyQuota(user_id=user_id, quota_date=date.today(), total_quota=total_quota, used_quota=0)
    db.add(quota)
    db.flush()
    return quota


def active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.is_admin.is_(True), User.status == "active").count()


def assert_not_removing_last_admin(db: Session, user: User, next_status: str | None, next_is_admin: bool | None) -> None:
    will_be_admin = user.is_admin if next_is_admin is None else next_is_admin
    will_be_active = user.status == "active" if next_status is None else next_status == "active"
    # Prevent locking the whole system out of the admin console.
    if user.is_admin and user.status == "active" and (not will_be_admin or not will_be_active) and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="LAST_ADMIN_REQUIRED")


def serialize_admin_user(db: Session, user: User, settings: Settings) -> AdminUserItem:
    generation_count = db.query(Generation).filter(Generation.user_id == user.id).count()
    if user.is_admin:
        quota_total = quota_used = quota_remaining = UNLIMITED_QUOTA
    else:
        quota = get_or_create_today_quota_for_admin(db, user.id, settings.daily_free_quota)
        quota_total = quota.total_quota
        quota_used = quota.used_quota
        quota_remaining = max(quota.total_quota - quota.used_quota, 0)
    return AdminUserItem(
        id=user.id,
        username=user.username,
        email=user.email,
        status=user.status,
        is_admin=user.is_admin,
        quota_total=quota_total,
        quota_used=quota_used,
        quota_remaining=quota_remaining,
        generation_count=generation_count,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def list_admin_users(db: Session, settings: Settings) -> list[AdminUserItem]:
    users = db.query(User).order_by(User.created_at.desc(), User.id.desc()).all()
    items = [serialize_admin_user(db, user, settings) for user in users]
    db.commit()
    return items


def create_admin_user(db: Session, settings: Settings, payload: AdminCreateUserRequest) -> AdminUserItem:
    user = User(
        username=payload.username.strip(),
        email=normalize_email(payload.email),
        password_hash=hash_password(payload.password),
        status="active",
        is_admin=payload.is_admin,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="USER_ALREADY_EXISTS") from exc
    if not user.is_admin:
        get_or_create_today_quota_for_admin(db, user.id, payload.daily_quota_total if payload.daily_quota_total is not None else settings.daily_free_quota)
    db.commit()
    db.refresh(user)
    return serialize_admin_user(db, user, settings)


def update_admin_user(db: Session, settings: Settings, user_id: int, payload: AdminUpdateUserRequest) -> AdminUserItem:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    assert_not_removing_last_admin(db, user, payload.status, payload.is_admin)
    if payload.email is not None:
        user.email = normalize_email(payload.email)
    if payload.status is not None:
        user.status = payload.status
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="USER_ALREADY_EXISTS") from exc
    db.refresh(user)
    return serialize_admin_user(db, user, settings)


def update_admin_user_quota(db: Session, settings: Settings, user_id: int, payload: AdminQuotaRequest) -> AdminUserItem:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="ADMIN_QUOTA_UNLIMITED")
    if payload.used_quota > payload.total_quota:
        raise HTTPException(status_code=422, detail="USED_QUOTA_EXCEEDS_TOTAL")
    quota = get_or_create_today_quota_for_admin(db, user.id, settings.daily_free_quota)
    quota.total_quota = payload.total_quota
    quota.used_quota = payload.used_quota
    db.commit()
    db.refresh(user)
    return serialize_admin_user(db, user, settings)


def reset_admin_user_password(db: Session, settings: Settings, user_id: int, payload: AdminResetPasswordRequest) -> AdminUserItem:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    user.password_hash = hash_password(payload.password)
    user.refresh_token_hash = None
    db.commit()
    db.refresh(user)
    return serialize_admin_user(db, user, settings)
