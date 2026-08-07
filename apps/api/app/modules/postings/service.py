import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, decode_cursor, paginate_rows
from app.modules.postings.models import JobPosting
from app.modules.postings.repository import JobPostingRepository
from app.modules.postings.schemas import JobPostingCreate, JobPostingRead

MAX_PAGE_SIZE = 100


def compute_content_hash(title: str, description: str, company_id: uuid.UUID | None) -> str:
    """Dedupe key: the same posting re-scraped from a different URL should
    resolve to one record, not a duplicate."""
    raw = f"{title.strip().lower()}|{description.strip().lower()}|{company_id or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobPostingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = JobPostingRepository(session)

    async def get(self, posting_id: uuid.UUID) -> JobPosting:
        posting = await self.repo.get_by_id(posting_id)
        if posting is None:
            raise NotFoundError("Job posting not found.")
        return posting

    async def list(self, *, cursor: str | None, limit: int) -> Page[JobPostingRead]:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_page(cursor_id=cursor_id, limit=limit)
        page = paginate_rows(rows, limit, lambda p: p.id)
        return Page[JobPostingRead](
            data=[JobPostingRead.model_validate(p) for p in page.data],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def create(self, payload: JobPostingCreate) -> JobPosting:
        content_hash = compute_content_hash(payload.title, payload.description, payload.company_id)
        if await self.repo.get_by_content_hash(content_hash):
            raise ConflictError("An identical job posting already exists.")

        posting = JobPosting(
            **payload.model_dump(),
            content_hash=content_hash,
            posted_at=datetime.now(UTC),
        )
        return await self.repo.create(posting)

    async def soft_delete(self, posting_id: uuid.UUID) -> None:
        posting = await self.get(posting_id)
        posting.deleted_at = datetime.now(UTC)
        await self.session.flush()
