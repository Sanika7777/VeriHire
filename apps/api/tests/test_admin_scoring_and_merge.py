from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType, TrustBand, VerificationStatus
from app.core.errors import ConflictError
from app.modules.companies.schemas import CompanyCreate
from app.modules.companies.service import CompanyService
from app.modules.postings.schemas import JobPostingCreate
from app.modules.postings.service import JobPostingService
from app.modules.verification.models import Verification
from app.modules.verification.service import VerificationService


async def test_publish_scoring_config_deactivates_previous(db_session: AsyncSession) -> None:
    service = VerificationService(db_session)
    first = await service.get_active_scoring_config()
    assert first.is_active is True

    second = await service.publish_scoring_config(
        {
            "identity": 0.1,
            "company_legitimacy": 0.2,
            "content_risk": 0.4,
            "link_safety": 0.1,
            "community_signal": 0.2,
        },
        {},
        created_by=None,
    )

    await db_session.refresh(first)
    assert first.is_active is False
    assert second.is_active is True
    assert second.version == first.version + 1


async def test_preview_weight_change_uses_stored_sub_scores(db_session: AsyncSession) -> None:
    company = await CompanyService(db_session).create(CompanyCreate(name="Preview Target"))
    verification = Verification(
        subject_type=SubjectType.COMPANY,
        subject_id=company.id,
        score=80,
        band=TrustBand.TRUSTED,
        sub_scores={"identity": 90, "company_legitimacy": 70},
        signals=[],
        status=VerificationStatus.DONE,
    )
    db_session.add(verification)
    await db_session.flush()

    service = VerificationService(db_session)
    impact = await service.preview_weight_change(
        {
            "identity": 0.5,
            "company_legitimacy": 0.5,
            "content_risk": 0.0,
            "link_safety": 0.0,
            "community_signal": 0.0,
        }
    )

    assert impact["sample_size"] >= 1
    assert impact["average_score_after"] is not None


async def test_merge_company_reassigns_postings_and_soft_deletes_source(
    db_session: AsyncSession,
) -> None:
    companies = CompanyService(db_session)
    source = await companies.create(CompanyCreate(name="Duplicate Co"))
    target = await companies.create(CompanyCreate(name="Canonical Co"))

    postings = JobPostingService(db_session)
    posting = await postings.create(
        JobPostingCreate(title="Engineer", description="Build things.", company_id=source.id)
    )

    merged_target = await companies.merge(source.id, target.id)
    assert merged_target.id == target.id

    await db_session.refresh(posting)
    assert posting.company_id == target.id

    with pytest.raises(Exception, match="not found"):
        await companies.get(source.id)


async def test_merge_company_into_itself_raises(db_session: AsyncSession) -> None:
    companies = CompanyService(db_session)
    company = await companies.create(CompanyCreate(name="Solo Co"))
    with pytest.raises(ConflictError):
        await companies.merge(company.id, company.id)
