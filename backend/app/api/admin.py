from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_admin
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.entities import User
from app.schemas.admin import (
    AdminCreateUserRequest,
    AdminQuotaRequest,
    AdminResetPasswordRequest,
    AdminUpdateUserRequest,
    AdminUserItem,
    ModelConfigResponse,
    ModelConfigUpdateRequest,
    ModelValidateRequest,
    ModelValidateResponse,
)
from app.services.admin_models import current_model_config, save_model_config, validate_selected_model
from app.services.admin_users import (
    create_admin_user,
    list_admin_users,
    reset_admin_user_password,
    update_admin_user,
    update_admin_user_quota,
)
from app.services.ai_provider import ProviderError


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserItem])
def list_users(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return list_admin_users(db, settings)


@router.post("/users", response_model=AdminUserItem, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminCreateUserRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return create_admin_user(db, settings, payload)


@router.patch("/users/{user_id}", response_model=AdminUserItem)
def update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return update_admin_user(db, settings, user_id, payload)


@router.patch("/users/{user_id}/quota", response_model=AdminUserItem)
def update_user_quota(
    user_id: int,
    payload: AdminQuotaRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return update_admin_user_quota(db, settings, user_id, payload)


@router.post("/users/{user_id}/reset-password", response_model=AdminUserItem)
def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return reset_admin_user_password(db, settings, user_id, payload)


@router.get("/model-config", response_model=ModelConfigResponse)
def get_model_config(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return current_model_config(db, settings)


@router.put("/model-config", response_model=ModelConfigResponse)
def update_model_config(
    payload: ModelConfigUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return save_model_config(db, settings, current_admin, payload.provider, payload.model)


@router.post("/model-config/validate", response_model=ModelValidateResponse)
async def validate_model_config(
    payload: ModelValidateRequest,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    current = current_model_config(db, settings)
    try:
        return await validate_selected_model(settings, payload.provider or current.provider, payload.model or current.model)
    except ProviderError as exc:
        status_code = 400 if exc.code in {"AI_PROVIDER_NOT_CONFIGURED", "AI_PROVIDER_UNSUPPORTED"} else 502
        raise HTTPException(status_code=status_code, detail=exc.code) from exc
