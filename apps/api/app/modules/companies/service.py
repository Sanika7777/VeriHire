import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page, decode_cursor, paginate_rows
from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanyCreate, CompanyRead, CompanyUpdate, slugify

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class CompanyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CompanyRepository(session)

    async def get(self, company_id: uuid.UUID) -> Company:
        company = await self.repo.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found.")
        return company

    async def get_by_slug(self, slug: str) -> Company:
        company = await self.repo.get_by_slug(slug)
        if company is None:
            raise NotFoundError("Company not found.")
        return company

    async def list(self, *, cursor: str | None, limit: int) -> Page[CompanyRead]:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_page(cursor_id=cursor_id, limit=limit)
        page = paginate_rows(rows, limit, lambda c: c.id)
        return Page[CompanyRead](
            data=[CompanyRead.model_validate(c) for c in page.data],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def create(self, payload: CompanyCreate) -> Company:
        base_slug = slugify(payload.name)
        slug = base_slug
        suffix = 1
        while await self.repo.slug_exists(slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        company = Company(
            name=payload.name,
            slug=slug,
            domain=payload.domain,
            website_url=payload.website_url,
            description=payload.description,
            industry=payload.industry,
            employee_count_range=payload.employee_count_range,
            hq_city=payload.hq_city,
            hq_country=payload.hq_country,
            founded_year=payload.founded_year,
        )
        return await self.repo.create(company)

    async def update(self, company_id: uuid.UUID, payload: CompanyUpdate) -> Company:
        company = await self.get(company_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        await self.session.flush()
        return company

    async def soft_delete(self, company_id: uuid.UUID) -> None:
        company = await self.get(company_id)
        company.deleted_at = datetime.now(UTC)
        await self.session.flush()
