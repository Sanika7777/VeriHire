from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import DbSession
from app.core.rate_limit import RateLimiter
from app.modules.resolve.schemas import ResolveRequest, ResolveResponse
from app.modules.resolve.service import ResolveService

router = APIRouter(tags=["resolve"])

_resolve_rate_limit = RateLimiter(times=10, seconds=60, scope="resolve")


def get_resolve_service(session: DbSession) -> ResolveService:
    return ResolveService(session)


ResolveServiceDep = Annotated[ResolveService, Depends(get_resolve_service)]


@router.post(
    "/resolve",
    response_model=ResolveResponse,
    dependencies=[Depends(_resolve_rate_limit)],
)
async def resolve(body: ResolveRequest, service: ResolveServiceDep) -> ResolveResponse:
    return await service.resolve(str(body.url))
