from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType, TrustBand, VerificationStatus
from app.modules.companies.models import Company
from app.modules.users.models import User
from app.modules.verification.models import Verification


async def test_insert_company_and_verification_round_trip(db_session: AsyncSession) -> None:
    company = Company(name="Acme Recruiting Pvt Ltd", slug="acme-recruiting-pvt-ltd")
    db_session.add(company)
    await db_session.flush()

    verification = Verification(
        subject_type=SubjectType.COMPANY,
        subject_id=company.id,
        score=82,
        band=TrustBand.TRUSTED,
        sub_scores={"identity": 90, "company_legitimacy": 85},
        signals=[{"code": "domain_age_ok", "severity": "info"}],
        status=VerificationStatus.DONE,
    )
    db_session.add(verification)
    await db_session.flush()

    fetched = await db_session.scalar(
        select(Verification).where(Verification.subject_id == company.id)
    )
    assert fetched is not None
    assert fetched.band == TrustBand.TRUSTED
    assert fetched.score == 82
    assert fetched.sub_scores["identity"] == 90


async def test_user_role_defaults_to_seeker(db_session: AsyncSession) -> None:
    user = User(email="priya.sharma@example.com", full_name="Priya Sharma")
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    assert user.role.value == "seeker"
