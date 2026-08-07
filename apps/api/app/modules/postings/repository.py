import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.postings.models import JobPosting


class JobPostingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, posting_id: uuid.UUID) -> JobPosting | None:
        posting = await self.session.get(JobPosting, posting_id)
        if posting is None or posting.deleted_at is not None:
            return None
        return posting

    async def get_by_content_hash(self, content_hash: str) -> JobPosting | None:
        result = await self.session.execute(
            select(JobPosting).where(
                JobPosting.content_hash == content_hash, JobPosting.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_source_url(self, source_url: str) -> JobPosting | None:
        result = await self.session.execute(
            select(JobPosting).where(
                JobPosting.source_url == source_url, JobPosting.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_page(self, *, cursor_id: uuid.UUID | None, limit: int) -> list[JobPosting]:
        query = (
            select(JobPosting).where(JobPosting.deleted_at.is_(None)).order_by(JobPosting.id)
        )
        if cursor_id is not None:
            query = query.where(JobPosting.id > cursor_id)
        result = await self.session.execute(query.limit(limit + 1))
        return list(result.scalars().all())

    async def create(self, posting: JobPosting) -> JobPosting:
        self.session.add(posting)
        await self.session.flush()
        return posting
