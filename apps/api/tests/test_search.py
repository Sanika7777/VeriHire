from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType, TrustBand
from app.modules.companies.schemas import CompanyCreate
from app.modules.companies.service import CompanyService
from app.modules.recruiters.schemas import RecruiterCreate
from app.modules.recruiters.service import RecruiterService
from app.modules.search.service import SearchService

COMPANY_NAMES = [
    "Infosys Limited",
    "Wipro Technologies",
    "Tata Consultancy Services",
    "Zomato Limited",
]


async def _seed_companies(session: AsyncSession) -> None:
    service = CompanyService(session)
    for name in COMPANY_NAMES:
        await service.create(CompanyCreate(name=name))


async def test_misspelled_query_surfaces_correct_company_first(db_session: AsyncSession) -> None:
    await _seed_companies(db_session)
    search = SearchService(db_session)

    result = await search.search(
        q="Infosis", subject_type=None, band=None, cursor=None, limit=5
    )

    assert len(result.data) >= 1
    assert result.data[0].name == "Infosys Limited"


async def test_search_filters_by_subject_type(db_session: AsyncSession) -> None:
    await _seed_companies(db_session)
    recruiters = RecruiterService(db_session)
    await recruiters.create(RecruiterCreate(full_name="Infosys Recruiter"))
    search = SearchService(db_session)

    result = await search.search(
        q="Infosys", subject_type=SubjectType.COMPANY, band=None, cursor=None, limit=5
    )

    assert all(item.subject_type == SubjectType.COMPANY for item in result.data)
    assert any(item.name == "Infosys Limited" for item in result.data)


async def test_search_defaults_unrated_band_when_no_verification_exists(
    db_session: AsyncSession,
) -> None:
    await _seed_companies(db_session)
    search = SearchService(db_session)

    result = await search.search(q="Infosys", subject_type=None, band=None, cursor=None, limit=5)

    assert result.data[0].band == TrustBand.UNRATED


async def test_search_band_filter_excludes_unrated_when_filtering_trusted(
    db_session: AsyncSession,
) -> None:
    await _seed_companies(db_session)
    search = SearchService(db_session)

    result = await search.search(
        q="Infosys", subject_type=None, band=TrustBand.TRUSTED, cursor=None, limit=5
    )

    assert result.data == []


async def test_search_pagination_seeks_forward_without_duplicates(
    db_session: AsyncSession,
) -> None:
    service = CompanyService(db_session)
    for i in range(6):
        await service.create(CompanyCreate(name=f"Searchable Corp {i}"))
    search = SearchService(db_session)

    first_page = await search.search(
        q="Searchable", subject_type=None, band=None, cursor=None, limit=3
    )
    assert len(first_page.data) == 3
    assert first_page.has_more is True

    second_page = await search.search(
        q="Searchable",
        subject_type=None,
        band=None,
        cursor=first_page.next_cursor,
        limit=3,
    )
    first_ids = {item.id for item in first_page.data}
    second_ids = {item.id for item in second_page.data}
    assert first_ids.isdisjoint(second_ids)


async def test_search_facets_count_by_subject_type(db_session: AsyncSession) -> None:
    await _seed_companies(db_session)
    recruiters = RecruiterService(db_session)
    await recruiters.create(RecruiterCreate(full_name="Infosys Talent Scout"))
    search = SearchService(db_session)

    result = await search.search(q="Infosys", subject_type=None, band=None, cursor=None, limit=5)

    facet_values = {f.value for f in result.facets.subject_type}
    assert "company" in facet_values
    assert "recruiter" in facet_values
