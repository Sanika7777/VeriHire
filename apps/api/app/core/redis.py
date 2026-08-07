from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis[str] | None = None


def get_redis() -> Redis[str]:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(str(settings.redis_url), decode_responses=True)
    return _redis


async def ping_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False
