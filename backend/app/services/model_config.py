from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.entities import AIModelConfig
from app.services.provider_types import ProviderConfig, ProviderError


def resolve_provider_config(settings: Settings, provider_override: str | None = None, model_override: str | None = None) -> ProviderConfig | None:
    provider = (provider_override or settings.ai_provider).strip().lower()
    if provider == "mock":
        return None

    if provider == "deepseek":
        extra_body: dict[str, object] = {
            "thinking": {"type": "enabled" if settings.deepseek_thinking_enabled else "disabled"}
        }
        if settings.deepseek_thinking_enabled:
            extra_body["reasoning_effort"] = settings.deepseek_reasoning_effort
        return ProviderConfig(
            name="deepseek",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key or settings.ai_api_key,
            model=model_override or settings.deepseek_model_text or settings.ai_model_text,
            extra_body=extra_body,
        )

    if provider == "openrouter":
        headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_app_title:
            headers["X-Title"] = settings.openrouter_app_title
        extra_body: dict[str, object] = {}
        if settings.openrouter_reasoning_enabled:
            extra_body["reasoning"] = {"enabled": True}
        return ProviderConfig(
            name="openrouter",
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key or settings.ai_api_key,
            model=model_override or settings.openrouter_model_text or settings.ai_model_text,
            extra_headers=headers,
            extra_body=extra_body,
        )

    if provider == "openai-compatible":
        return ProviderConfig(
            name="openai-compatible",
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            model=model_override or settings.ai_model_text,
        )

    raise ProviderError(
        "AI_PROVIDER_UNSUPPORTED",
        "不支持的 AI_PROVIDER，请使用 mock、deepseek、openrouter 或 openai-compatible。",
    )


def get_database_model_selection() -> tuple[str, str] | None:
    # Runtime model selection prefers the admin-managed database row, then falls back to env settings.
    db = SessionLocal()
    try:
        config = db.get(AIModelConfig, 1)
        if not config:
            return None
        return config.provider, config.model
    finally:
        db.close()
