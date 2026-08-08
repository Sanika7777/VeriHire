import uuid
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EntityStatus
from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, decode_cursor, paginate_rows
from app.modules.postings.models import JobPosting
from app.modules.recruiters.models import Recruiter
from app.modules.recruiters.repository import RecruiterRepository
from app.modules.recruiters.schemas import RecruiterCreate, RecruiterRead, RecruiterUpdate

MAX_PAGE_SIZE = 100


class RecruiterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecruiterRepository(session)

    async def get(self, recruiter_id: uuid.UUID) -> Recruiter:
        recruiter = await self.repo.get_by_id(recruiter_id)
        if recruiter is None:
            raise NotFoundError("Recruiter not found.")
        return recruiter

    async def list(self, *, cursor: str | None, limit: int) -> Page[RecruiterRead]:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_page(cursor_id=cursor_id, limit=limit)
        page = paginate_rows(rows, limit, lambda r: r.id)
        return Page[RecruiterRead](
            data=[RecruiterRead.model_validate(r) for r in page.data],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def create(self, payload: RecruiterCreate) -> Recruiter:
        if payload.linkedin_url and await self.repo.get_by_linkedin_url(payload.linkedin_url):
            raise ConflictError("A recruiter with this LinkedIn profile already exists.")

        recruiter = Recruiter(
            full_name=payload.full_name,
            company_id=payload.company_id,
            headline=payload.headline,
            email=payload.email,
            linkedin_url=payload.linkedin_url,
            bio=payload.bio,
            profile_created_on=payload.profile_created_on,
        )
        return await self.repo.create(recruiter)

    async def update(self, recruiter_id: uuid.UUID, payload: RecruiterUpdate) -> Recruiter:
        recruiter = await self.get(recruiter_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(recruiter, field, value)
        await self.session.flush()
        return recruiter

    async def soft_delete(self, recruiter_id: uuid.UUID) -> None:
        recruiter = await self.get(recruiter_id)
        recruiter.deleted_at = datetime.now(UTC)
        await self.session.flush()

    async def merge(self, source_id: uuid.UUID, target_id: uuid.UUID) -> Recruiter:
        if source_id == target_id:
            raise ConflictError("Cannot merge a recruiter into itself.")

        source = await self.get(source_id)
        target = await self.get(target_id)

        await self.session.execute(
            update(JobPosting)
            .where(JobPosting.recruiter_id == source_id)
            .values(recruiter_id=target_id)
        )

        source.merged_into_id = target.id
        source.status = EntityStatus.MERGED
        source.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return target
