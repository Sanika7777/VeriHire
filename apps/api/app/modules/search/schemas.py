import uuid

from pydantic import BaseModel

from app.core.enums import SubjectType, TrustBand


class SearchResultItem(BaseModel):
    id: uuid.UUID
    subject_type: SubjectType
    name: str
    subtitle: str | None
    band: TrustBand
    score: int | None
    relevance: float


class SearchFacet(BaseModel):
    value: str
    count: int


class SearchFacets(BaseModel):
    subject_type: list[SearchFacet]
    band: list[SearchFacet]


class SearchResponse(BaseModel):
    data: list[SearchResultItem]
    next_cursor: str | None
    has_more: bool
    facets: SearchFacets
