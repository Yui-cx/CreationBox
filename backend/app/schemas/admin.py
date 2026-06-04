from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None
    status: str
    is_admin: bool
    quota_total: int
    quota_used: int
    quota_remaining: int
    generation_count: int
    created_at: datetime
    last_login_at: datetime | None


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    is_admin: bool = False
    daily_quota_total: int | None = Field(default=None, ge=0, le=100000)


class AdminUpdateUserRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")
    is_admin: bool | None = None


class AdminQuotaRequest(BaseModel):
    total_quota: int = Field(ge=0, le=100000)
    used_quota: int = Field(ge=0, le=100000)


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ProviderOption(BaseModel):
    provider: str
    label: str
    models: list[str]
    key_configured: bool


class ModelConfigResponse(BaseModel):
    provider: str
    model: str
    options: list[ProviderOption]
    updated_at: datetime | None = None
    updated_by: int | None = None


class ModelConfigUpdateRequest(BaseModel):
    provider: str
    model: str


class ModelValidateRequest(BaseModel):
    provider: str | None = None
    model: str | None = None


class ModelValidateResponse(BaseModel):
    ok: bool
    provider: str
    model: str
