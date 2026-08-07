from fastapi import Request

from app.core.errors import RateLimitedError
from app.core.redis import get_redis


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Redis fixed-window limiter, keyed by route + client IP (CLAUDE.md §6)."""

    def __init__(self, *, times: int, seconds: int, scope: str) -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        redis = get_redis()
        key = f"ratelimit:{self.scope}:{_client_ip(request)}"

        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.seconds)

        if count > self.times:
            ttl = await redis.ttl(key)
            raise RateLimitedError(
                f"Rate limit exceeded. Try again in {max(ttl, 1)} seconds.",
                retry_after=max(ttl, 1),
            )
