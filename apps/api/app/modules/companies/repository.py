import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.companies.models import Company


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        company = await self.session.get(Company, company_id)
        if company is None or company.deleted_at is not None:
            return None
        return company

    async def get_by_slug(self, slug: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.slug == slug, Company.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Company | None:
        result = await self.session.execute(
            select(Company).where(Company.domain == domain, Company.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.session.execute(select(Company.id).where(Company.slug == slug))
        return result.scalar_one_or_none() is not None

    async def list_page(self, *, cursor_id: uuid.UUID | None, limit: int) -> list[Company]:
        query = select(Company).where(Company.deleted_at.is_(None)).order_by(Company.id)
        if cursor_id is not None:
            query = query.where(Company.id > cursor_id)
        result = await self.session.execute(query.limit(limit + 1))
        return list(result.scalars().all())

    async def create(self, company: Company) -> Company:
        self.session.add(company)
        await self.session.flush()
        return company
