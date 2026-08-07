import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recruiters.models import Recruiter


class RecruiterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, recruiter_id: uuid.UUID) -> Recruiter | None:
        recruiter = await self.session.get(Recruiter, recruiter_id)
        if recruiter is None or recruiter.deleted_at is not None:
            return None
        return recruiter

    async def get_by_linkedin_url(self, linkedin_url: str) -> Recruiter | None:
        result = await self.session.execute(
            select(Recruiter).where(
                Recruiter.linkedin_url == linkedin_url, Recruiter.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_page(self, *, cursor_id: uuid.UUID | None, limit: int) -> list[Recruiter]:
        query = select(Recruiter).where(Recruiter.deleted_at.is_(None)).order_by(Recruiter.id)
        if cursor_id is not None:
            query = query.where(Recruiter.id > cursor_id)
        result = await self.session.execute(query.limit(limit + 1))
        return list(result.scalars().all())

    async def create(self, recruiter: Recruiter) -> Recruiter:
        self.session.add(recruiter)
        await self.session.flush()
        return recruiter
