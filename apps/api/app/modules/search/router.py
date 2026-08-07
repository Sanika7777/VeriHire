from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import DbSession
from app.core.enums import SubjectType, TrustBand
from app.modules.search.schemas import SearchResponse
from app.modules.search.service import SearchService

router = APIRouter(tags=["search"])


def get_search_service(session: DbSession) -> SearchService:
    return SearchService(session)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


@router.get("/search", response_model=SearchResponse)
async def search(
    service: SearchServiceDep,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    type: SubjectType | None = None,  # noqa: A002
    band: TrustBand | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    return await service.search(
        q=q, subject_type=type, band=band, cursor=cursor, limit=limit
    )
