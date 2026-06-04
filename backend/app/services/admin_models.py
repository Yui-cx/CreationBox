from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.models.entities import AIModelConfig, User
from app.schemas.admin import ModelConfigResponse, ModelValidateResponse, ProviderOption
from app.services.model_config import resolve_provider_config
from app.services.provider_validation import validate_provider_config
from app.services.provider_types import ProviderError


ALLOWED_MODELS = {
    "deepseek": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "openrouter": ["google/gemini-3.1-flash-lite", "openai/gpt-5.4-mini"],
}


def assert_model_allowed(provider: str, model: str) -> tuple[str, str]:
    normalized_provider = provider.strip().lower()
    normalized_model = model.strip()
    if normalized_provider not in ALLOWED_MODELS or normalized_model not in ALLOWED_MODELS[normalized_provider]:
        raise HTTPException(status_code=422, detail="INVALID_MODEL_CONFIG")
    return normalized_provider, normalized_model


def provider_key_configured(settings: Settings, provider: str) -> bool:
    if provider == "deepseek":
        return bool(settings.deepseek_api_key or settings.ai_api_key)
    if provider == "openrouter":
        return bool(settings.openrouter_api_key or settings.ai_api_key)
    return False


def default_model_selection(settings: Settings) -> tuple[str, str]:
    provider = settings.ai_provider.strip().lower()
    if provider not in ALLOWED_MODELS:
        provider = "deepseek"
    configured_model = settings.deepseek_model_text if provider == "deepseek" else settings.openrouter_model_text
    model = configured_model if configured_model in ALLOWED_MODELS[provider] else ALLOWED_MODELS[provider][0]
    return provider, model


def model_options(settings: Settings) -> list[ProviderOption]:
    return [
        ProviderOption(provider="deepseek", label="DeepSeek", models=ALLOWED_MODELS["deepseek"], key_configured=provider_key_configured(settings, "deepseek")),
        ProviderOption(provider="openrouter", label="OpenRouter", models=ALLOWED_MODELS["openrouter"], key_configured=provider_key_configured(settings, "openrouter")),
    ]


def current_model_config(db: Session, settings: Settings) -> ModelConfigResponse:
    config = db.get(AIModelConfig, 1)
    if config:
        provider, model = config.provider, config.model
        updated_at = config.updated_at
        updated_by = config.updated_by
    else:
        provider, model = default_model_selection(settings)
        updated_at = None
        updated_by = None
    return ModelConfigResponse(provider=provider, model=model, options=model_options(settings), updated_at=updated_at, updated_by=updated_by)


def save_model_config(db: Session, settings: Settings, current_admin: User, provider: str, model: str) -> ModelConfigResponse:
    provider, model = assert_model_allowed(provider, model)
    config = db.get(AIModelConfig, 1)
    if not config:
        config = AIModelConfig(id=1, provider=provider, model=model, updated_by=current_admin.id)
        db.add(config)
    else:
        config.provider = provider
        config.model = model
        config.updated_by = current_admin.id
    db.commit()
    return current_model_config(db, settings)


async def validate_selected_model(settings: Settings, provider: str, model: str) -> ModelValidateResponse:
    provider, model = assert_model_allowed(provider, model)
    config = resolve_provider_config(settings, provider, model)
    if config is None:
        raise ProviderError("AI_PROVIDER_NOT_CONFIGURED", "AI provider key is not configured.")
    await validate_provider_config(config, settings.ai_timeout_seconds)
    return ModelValidateResponse(ok=True, provider=provider, model=model)
