from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ReportCategory, SubjectType
from app.core.errors import ConflictError
from app.modules.companies.schemas import CompanyCreate
from app.modules.companies.service import CompanyService
from app.modules.reports.schemas import ReportCreate
from app.modules.reports.service import ReportService
from app.modules.reviews.schemas import ReviewCreate
from app.modules.reviews.service import ReviewService
from app.modules.users.models import User
from app.modules.verification.scoring.community_signal import score_community_signal


async def _make_company(session: AsyncSession) -> str:
    company = await CompanyService(session).create(CompanyCreate(name="Report Target Inc"))
    return str(company.id)


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="x", full_name="Reporter")
    session.add(user)
    await session.flush()
    return user


async def test_duplicate_report_within_window_is_rejected(db_session: AsyncSession) -> None:
    company_id = await _make_company(db_session)
    reporter = await _make_user(db_session, "reporter1@example.com")
    service = ReportService(db_session)

    payload = ReportCreate(
        subject_type=SubjectType.COMPANY,
        subject_id=company_id,
        category=ReportCategory.ADVANCE_FEE,
        description="Asked me to pay a deposit before the interview.",
    )
    await service.create(payload, reporter_user_id=reporter.id, idempotency_key=None)

    with pytest.raises(ConflictError):
        await service.create(payload, reporter_user_id=reporter.id, idempotency_key=None)


async def test_idempotency_key_returns_same_report(db_session: AsyncSession) -> None:
    company_id = await _make_company(db_session)
    reporter = await _make_user(db_session, "reporter2@example.com")
    service = ReportService(db_session)

    payload = ReportCreate(
        subject_type=SubjectType.COMPANY,
        subject_id=company_id,
        category=ReportCategory.FAKE_JOB_POSTING,
        description="This posting disappeared after I paid a fee.",
    )
    first = await service.create(payload, reporter_user_id=reporter.id, idempotency_key="key-1")
    second = await service.create(payload, reporter_user_id=reporter.id, idempotency_key="key-1")

    assert first.id == second.id


async def test_confirmed_report_feeds_community_signal(db_session: AsyncSession) -> None:
    company_id = await _make_company(db_session)
    reporter = await _make_user(db_session, "reporter3@example.com")
    moderator = await _make_user(db_session, "moderator1@example.com")

    service = ReportService(db_session)
    report = await service.create(
        ReportCreate(
            subject_type=SubjectType.COMPANY,
            subject_id=company_id,
            category=ReportCategory.ADVANCE_FEE,
            description="Classic advance-fee scam pattern here.",
        ),
        reporter_user_id=reporter.id,
        idempotency_key=None,
    )
    await service.confirm(report.id, moderator_id=moderator.id)

    result = await score_community_signal(db_session, SubjectType.COMPANY, company_id)
    assert result.score is not None
    assert result.score < 70
    assert any(s.code == "confirmed_fraud_reports" for s in result.signals)


async def test_review_vote_cannot_be_cast_twice(db_session: AsyncSession) -> None:
    company_id = await _make_company(db_session)
    reviewer = await _make_user(db_session, "reviewer1@example.com")
    voter = await _make_user(db_session, "voter1@example.com")

    reviews = ReviewService(db_session)
    review = await reviews.create(
        ReviewCreate(
            subject_type=SubjectType.COMPANY,
            subject_id=company_id,
            rating_communication=5,
            rating_process_transparency=5,
            rating_offer_accuracy=5,
            rating_professionalism=5,
            verified_interaction=True,
        ),
        reviewer_user_id=reviewer.id,
    )

    await reviews.vote(review.id, user_id=voter.id, is_helpful=True)
    with pytest.raises(ConflictError):
        await reviews.vote(review.id, user_id=voter.id, is_helpful=True)
