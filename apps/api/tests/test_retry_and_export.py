from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReportCategory, SubjectType
from app.core.retry import retry_with_jitter
from app.modules.auth.service import AuthService
from app.modules.companies.schemas import CompanyCreate
from app.modules.companies.service import CompanyService
from app.modules.reports.schemas import ReportCreate
from app.modules.reports.service import ReportService


async def test_retry_with_jitter_retries_transient_then_succeeds() -> None:
    calls = {"count": 0}

    async def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("transient")
        return "ok"

    result = await retry_with_jitter(flaky, should_retry=lambda exc: isinstance(exc, TimeoutError))
    assert result == "ok"
    assert calls["count"] == 3


async def test_retry_with_jitter_does_not_retry_non_transient() -> None:
    calls = {"count": 0}

    async def always_fails() -> str:
        calls["count"] += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await retry_with_jitter(always_fails, should_retry=lambda exc: isinstance(exc, TimeoutError))
    assert calls["count"] == 1


async def test_export_account_data_includes_reports_and_reviews(
    db_session: AsyncSession, redis_client
) -> None:
    auth = AuthService(db_session, redis_client)
    user = await auth.register(
        email="exportme@example.com", password="CorrectHorseBattery9", full_name="Export Me"
    )

    company = await CompanyService(db_session).create(CompanyCreate(name="Export Target"))
    await ReportService(db_session).create(
        ReportCreate(
            subject_type=SubjectType.COMPANY,
            subject_id=company.id,
            category=ReportCategory.OTHER,
            description="Testing export functionality end to end.",
        ),
        reporter_user_id=user.id,
        idempotency_key=None,
    )

    export = await auth.export_account_data(user.id)
    assert export["profile"]["email"] == "exportme@example.com"
    assert len(export["reports_filed"]) == 1
