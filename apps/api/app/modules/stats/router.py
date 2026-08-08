from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.core.enums import ReportStatus
from app.modules.companies.models import Company
from app.modules.recruiters.models import Recruiter
from app.modules.reports.models import Report
from app.modules.reviews.models import Review

router = APIRouter(tags=["stats"])


class PublicStats(BaseModel):
    companies_verified: int
    recruiters_tracked: int
    scams_confirmed: int
    community_reviews: int


@router.get("/stats", response_model=PublicStats)
async def public_stats(session: DbSession) -> PublicStats:
    companies_count = await session.scalar(select(func.count()).select_from(Company))
    recruiters_count = await session.scalar(select(func.count()).select_from(Recruiter))
    confirmed_reports = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == ReportStatus.CONFIRMED)
    )
    reviews_count = await session.scalar(select(func.count()).select_from(Review))

    return PublicStats(
        companies_verified=companies_count or 0,
        recruiters_tracked=recruiters_count or 0,
        scams_confirmed=confirmed_reports or 0,
        community_reviews=reviews_count or 0,
    )
