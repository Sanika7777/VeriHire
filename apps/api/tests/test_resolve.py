from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType
from app.integrations.web_fetch import FetchResult, UnsafeUrlError
from app.modules.resolve import service as resolve_service_module
from app.modules.resolve.service import ResolveService, classify_url


def test_classify_url_linkedin_profile_is_recruiter() -> None:
    assert classify_url("https://www.linkedin.com/in/jane-doe") == SubjectType.RECRUITER


def test_classify_url_bare_domain_is_company() -> None:
    assert classify_url("https://acme.com/") == SubjectType.COMPANY
    assert classify_url("https://acme.com") == SubjectType.COMPANY


def test_classify_url_job_board_is_job_posting() -> None:
    assert (
        classify_url("https://www.naukri.com/job-listings-backend-engineer-12345")
        == SubjectType.JOB_POSTING
    )


async def test_resolve_company_degrades_gracefully_on_unsafe_url(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch_url(url: str) -> FetchResult:
        raise UnsafeUrlError("blocked for test")

    monkeypatch.setattr(resolve_service_module, "fetch_url", fake_fetch_url)

    service = ResolveService(db_session)
    result = await service.resolve("https://some-new-company.example/")

    assert result.outcome == "created"
    assert result.degraded is True
    assert result.subject_type == SubjectType.COMPANY


async def test_resolve_same_domain_twice_returns_existing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch_url(url: str) -> FetchResult:
        raise UnsafeUrlError("blocked for test")

    monkeypatch.setattr(resolve_service_module, "fetch_url", fake_fetch_url)

    service = ResolveService(db_session)
    first = await service.resolve("https://repeat-company.example/")
    second = await service.resolve("https://repeat-company.example/")

    assert first.outcome == "created"
    assert second.outcome == "existing"
    assert first.subject_id == second.subject_id


async def test_resolve_job_posting_dedupes_by_source_url(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch_url(url: str) -> FetchResult:
        return FetchResult(
            final_url=url,
            status_code=200,
            html="<title>Backend Engineer at Acme</title>",
            content_hash="deadbeef",
            from_cache=False,
        )

    monkeypatch.setattr(resolve_service_module, "fetch_url", fake_fetch_url)

    service = ResolveService(db_session)
    url = "https://boards.example/job/12345"
    first = await service.resolve(url)
    second = await service.resolve(url)

    assert first.subject_type == SubjectType.JOB_POSTING
    assert first.name == "Backend Engineer at Acme"
    assert second.outcome == "existing"
    assert first.subject_id == second.subject_id
