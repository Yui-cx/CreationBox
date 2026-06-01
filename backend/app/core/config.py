from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "CreationBox"
    environment: str = "local"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    database_url: str = "sqlite:///./creationbox.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    daily_free_quota: int = 5
    login_rate_limit_per_minute: int = 8
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"

    ai_provider: str = "deepseek"
    ai_base_url: str = "https://api.deepseek.com"
    ai_api_key: str = ""
    ai_model_text: str = "deepseek-v4-flash"
    ai_timeout_seconds: int = 60

    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model_text: str = "deepseek-v4-flash"
    deepseek_thinking_enabled: bool = False
    deepseek_reasoning_effort: str = "high"

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model_text: str = "google/gemini-3.1-flash-lite"
    openrouter_http_referer: str = ""
    openrouter_app_title: str = "CreationBox"
    openrouter_reasoning_enabled: bool = False

    generation_lock_seconds: int = 90

    inpaint_lama_enabled: bool = True
    inpaint_lama_device: str = "cpu"
    inpaint_lama_max_image_bytes: int = 5 * 1024 * 1024
    inpaint_lama_max_pixels: int = 4_194_304
    inpaint_lama_concurrency: int = 1
    inpaint_lama_fallback_opencv: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
