from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ClaimMethod, ClaimStatus, EntityStatus
from app.core.errors import ConflictError, UnauthorizedError
from app.modules.companies.claims_service import CompanyClaimService
from app.modules.companies.models import Company
from app.modules.users.models import User


async def _make_company(session: AsyncSession, domain: str) -> Company:
    company = Company(name="Claimable Co", slug="claimable-co", domain=domain)
    session.add(company)
    await session.flush()
    return company


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="x", full_name="Claimant")
    session.add(user)
    await session.flush()
    return user


async def test_email_domain_claim_auto_approves_on_matching_domain(
    db_session: AsyncSession,
) -> None:
    company = await _make_company(db_session, "acme.example")
    user = await _make_user(db_session, "priya@acme.example")

    service = CompanyClaimService(db_session)
    claim = await service.start_claim(company.id, user, ClaimMethod.EMAIL_DOMAIN)

    assert claim.status == ClaimStatus.APPROVED
    await db_session.refresh(company)
    assert company.status == EntityStatus.CLAIMED


async def test_email_domain_claim_rejects_mismatched_domain(db_session: AsyncSession) -> None:
    company = await _make_company(db_session, "acme.example")
    user = await _make_user(db_session, "priya@gmail.com")

    service = CompanyClaimService(db_session)
    with pytest.raises(UnauthorizedError):
        await service.start_claim(company.id, user, ClaimMethod.EMAIL_DOMAIN)


async def test_dns_claim_stays_pending_until_verified(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    company = await _make_company(db_session, "acme.example")
    user = await _make_user(db_session, "priya@gmail.com")

    service = CompanyClaimService(db_session)
    claim = await service.start_claim(company.id, user, ClaimMethod.DNS_TXT)
    assert claim.status == ClaimStatus.PENDING

    async def fake_check_txt_record(domain: str, token: str) -> bool:
        return False

    monkeypatch.setattr(service, "_check_txt_record", fake_check_txt_record)

    with pytest.raises(ConflictError):
        await service.verify_dns_claim(claim.id, user)


async def test_dns_claim_approves_when_txt_record_matches(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    company = await _make_company(db_session, "acme.example")
    user = await _make_user(db_session, "priya@gmail.com")

    service = CompanyClaimService(db_session)
    claim = await service.start_claim(company.id, user, ClaimMethod.DNS_TXT)

    async def fake_check_txt_record(domain: str, token: str) -> bool:
        return True

    monkeypatch.setattr(service, "_check_txt_record", fake_check_txt_record)

    verified = await service.verify_dns_claim(claim.id, user)
    assert verified.status == ClaimStatus.APPROVED

    await db_session.refresh(company)
    assert company.status == EntityStatus.CLAIMED


async def test_claim_requires_company_domain(db_session: AsyncSession) -> None:
    company = Company(name="No Domain Co", slug="no-domain-co")
    db_session.add(company)
    await db_session.flush()
    user = await _make_user(db_session, "priya@example.com")

    service = CompanyClaimService(db_session)
    with pytest.raises(ConflictError):
        await service.start_claim(company.id, user, ClaimMethod.DNS_TXT)
