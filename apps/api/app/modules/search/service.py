import base64
import binascii
import uuid
from dataclasses import dataclass

from sqlalchemy import String, cast, func, literal, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import CTE

from app.core.enums import SubjectType, TrustBand
from app.modules.companies.models import Company
from app.modules.postings.models import JobPosting
from app.modules.recruiters.models import Recruiter
from app.modules.search.schemas import SearchFacet, SearchFacets, SearchResponse, SearchResultItem
from app.modules.verification.models import Verification

MAX_PAGE_SIZE = 50
RELEVANCE_FLOOR = 0.1


@dataclass(frozen=True)
class _Cursor:
    relevance: float
    entity_id: uuid.UUID


def _encode_cursor(relevance: float, entity_id: uuid.UUID) -> str:
    raw = f"{relevance}|{entity_id}"
    return base64.urlsafe_b64encode(raw.encode("ascii")).decode("ascii")


def _decode_cursor(cursor: str) -> _Cursor:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii")
        relevance_str, id_str = raw.split("|", 1)
        return _Cursor(relevance=float(relevance_str), entity_id=uuid.UUID(id_str))
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid search cursor.") from exc


def _candidates_cte(q: str) -> CTE:
    company_q = select(
        Company.id.label("id"),
        literal(SubjectType.COMPANY.value).label("subject_type"),
        Company.name.label("name"),
        Company.domain.label("subtitle"),
        func.similarity(Company.name, q).label("relevance"),
    ).where(Company.deleted_at.is_(None))

    recruiter_q = select(
        Recruiter.id.label("id"),
        literal(SubjectType.RECRUITER.value).label("subject_type"),
        Recruiter.full_name.label("name"),
        Recruiter.headline.label("subtitle"),
        func.similarity(Recruiter.full_name, q).label("relevance"),
    ).where(Recruiter.deleted_at.is_(None))

    posting_q = select(
        JobPosting.id.label("id"),
        literal(SubjectType.JOB_POSTING.value).label("subject_type"),
        JobPosting.title.label("name"),
        JobPosting.location_city.label("subtitle"),
        func.similarity(JobPosting.title, q).label("relevance"),
    ).where(JobPosting.deleted_at.is_(None))

    return union_all(company_q, recruiter_q, posting_q).cte("search_candidates")


def _latest_verification_cte() -> CTE:
    # Native enum columns are cast to text so they compare cleanly against
    # the plain varchar `subject_type`/`band` literals produced by
    # _candidates_cte — Postgres won't implicitly compare enum = varchar.
    ranked = select(
        cast(Verification.subject_type, String).label("subject_type"),
        Verification.subject_id,
        cast(Verification.band, String).label("band"),
        Verification.score,
        func.row_number()
        .over(
            partition_by=(Verification.subject_type, Verification.subject_id),
            order_by=Verification.computed_at.desc(),
        )
        .label("rn"),
    ).subquery()
    return select(ranked).where(ranked.c.rn == 1).cte("latest_verifications")


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        *,
        q: str,
        subject_type: SubjectType | None,
        band: TrustBand | None,
        cursor: str | None,
        limit: int,
    ) -> SearchResponse:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        query_term = q.strip()

        candidates = _candidates_cte(query_term)
        latest_verifications = _latest_verification_cte()

        resolved_band = func.coalesce(latest_verifications.c.band, TrustBand.UNRATED.value)
        resolved_score = latest_verifications.c.score

        base = (
            select(
                candidates.c.id,
                candidates.c.subject_type,
                candidates.c.name,
                candidates.c.subtitle,
                candidates.c.relevance,
                resolved_band.label("band"),
                resolved_score.label("score"),
            )
            .select_from(candidates)
            .outerjoin(
                latest_verifications,
                (latest_verifications.c.subject_type == candidates.c.subject_type)
                & (latest_verifications.c.subject_id == candidates.c.id),
            )
            .where(
                or_(
                    candidates.c.relevance > RELEVANCE_FLOOR,
                    candidates.c.name.ilike(f"%{query_term}%"),
                )
            )
        )

        # Facets are computed on the text-matched set before type/band filters
        # narrow it further, so counts reflect "what else could I filter to".
        facet_base = base.subquery()
        subject_type_facets = await self.session.execute(
            select(facet_base.c.subject_type, func.count())
            .group_by(facet_base.c.subject_type)
        )
        band_facets = await self.session.execute(
            select(facet_base.c.band, func.count()).group_by(facet_base.c.band)
        )

        filtered = base
        if subject_type is not None:
            filtered = filtered.where(candidates.c.subject_type == subject_type.value)
        if band is not None:
            filtered = filtered.where(resolved_band == band.value)

        if cursor:
            seek = _decode_cursor(cursor)
            filtered = filtered.where(
                or_(
                    candidates.c.relevance < seek.relevance,
                    (candidates.c.relevance == seek.relevance) & (candidates.c.id < seek.entity_id),
                )
            )

        filtered = filtered.order_by(candidates.c.relevance.desc(), candidates.c.id.desc()).limit(
            limit + 1
        )

        rows = (await self.session.execute(filtered)).all()
        has_more = len(rows) > limit
        page_rows = rows[:limit]

        items = [
            SearchResultItem(
                id=row.id,
                subject_type=SubjectType(row.subject_type),
                name=row.name,
                subtitle=row.subtitle,
                band=TrustBand(row.band),
                score=row.score,
                relevance=float(row.relevance),
            )
            for row in page_rows
        ]

        next_cursor = (
            _encode_cursor(page_rows[-1].relevance, page_rows[-1].id)
            if has_more and page_rows
            else None
        )

        return SearchResponse(
            data=items,
            next_cursor=next_cursor,
            has_more=has_more,
            facets=SearchFacets(
                subject_type=[
                    SearchFacet(value=row[0], count=row[1]) for row in subject_type_facets
                ],
                band=[SearchFacet(value=row[0], count=row[1]) for row in band_facets],
            ),
        )
