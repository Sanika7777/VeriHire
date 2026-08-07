import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.redis import ping_redis
from app.db.session import ping_database

router = APIRouter(tags=["health"])


class LivenessResponse(BaseModel):
    status: str = "ok"


class ReadinessResponse(BaseModel):
    status: str
    database: bool
    redis: bool


@router.get("/health", response_model=LivenessResponse)
async def health() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def ready() -> ReadinessResponse:
    database_ok, redis_ok = await asyncio.gather(ping_database(), ping_redis())
    return ReadinessResponse(
        status="ok" if database_ok and redis_ok else "degraded",
        database=database_ok,
        redis=redis_ok,
    )
