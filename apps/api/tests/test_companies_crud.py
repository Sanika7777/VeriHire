import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.companies.schemas import CompanyCreate, CompanyUpdate, slugify
from app.modules.companies.service import CompanyService


def test_slugify_handles_punctuation_and_apostrophes() -> None:
    assert slugify("Byju's Learning") == "byju-s-learning"
    assert slugify("  Multiple   Spaces  ") == "multiple-spaces"


async def test_create_and_get_company(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    company = await service.create(CompanyCreate(name="Acme Recruiting"))

    fetched = await service.get(company.id)
    assert fetched.name == "Acme Recruiting"
    assert fetched.slug == "acme-recruiting"
    assert fetched.status.value == "unverified"


async def test_duplicate_name_gets_disambiguated_slug(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    first = await service.create(CompanyCreate(name="Acme Recruiting"))
    second = await service.create(CompanyCreate(name="Acme Recruiting"))

    assert first.slug != second.slug
    assert second.slug.startswith("acme-recruiting")


async def test_update_company_only_touches_provided_fields(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    company = await service.create(CompanyCreate(name="Acme Recruiting", industry="IT"))

    updated = await service.update(company.id, CompanyUpdate(hq_city="Bengaluru"))

    assert updated.hq_city == "Bengaluru"
    assert updated.industry == "IT"  # untouched


async def test_soft_delete_hides_company_from_get(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    company = await service.create(CompanyCreate(name="Acme Recruiting"))

    await service.soft_delete(company.id)

    with pytest.raises(NotFoundError):
        await service.get(company.id)


async def test_get_missing_company_raises_not_found(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    with pytest.raises(NotFoundError):
        await service.get_by_slug("does-not-exist")


async def test_list_pagination_has_more_and_cursor(db_session: AsyncSession) -> None:
    service = CompanyService(db_session)
    for i in range(5):
        await service.create(CompanyCreate(name=f"Company {i}"))

    page = await service.list(cursor=None, limit=2)
    assert len(page.data) == 2
    assert page.has_more is True
    assert page.next_cursor is not None

    next_page = await service.list(cursor=page.next_cursor, limit=2)
    assert len(next_page.data) == 2
    assert {c.id for c in page.data}.isdisjoint({c.id for c in next_page.data})
