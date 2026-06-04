from redis.asyncio import Redis
from app.core.config import get_settings


_redis: Redis | None = None


async def get_redis() -> Redis | None:
    global _redis
    if _redis is not None:
        return _redis
    settings = get_settings()
    try:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception:
        _redis = None
        return None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
