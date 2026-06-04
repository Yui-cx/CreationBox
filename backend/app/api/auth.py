from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.redis_client import get_redis


router = APIRouter(prefix="/auth", tags=["auth"])


async def check_login_rate_limit(request: Request, settings: Settings) -> None:
    redis = await get_redis()
    if redis is None:
        return
    key = f"login-rate:{request.client.host if request.client else 'unknown'}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)
    if count > settings.login_rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="LOGIN_RATE_LIMITED")


def issue_tokens(db: Session, user: User) -> TokenResponse:
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    user.refresh_token_hash = hash_token(refresh)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenResponse)
def register(_: RegisterRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="REGISTRATION_DISABLED")


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    await check_login_rate_limit(request, settings)
    username = payload.username.strip()
    user = db.query(User).filter(User.username == username).one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="USER_INACTIVE")
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    user_id = decode_token(payload.refresh_token, "refresh")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_REFRESH_TOKEN")
    user = db.get(User, user_id)
    if not user or user.refresh_token_hash != hash_token(payload.refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_REFRESH_TOKEN")
    return issue_tokens(db, user)
