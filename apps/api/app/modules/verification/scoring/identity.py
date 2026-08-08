from datetime import UTC, datetime

from app.core.enums import SignalSeverity, SubScoreCode
from app.modules.companies.models import Company
from app.modules.recruiters.models import Recruiter
from app.modules.verification.scoring.signals import Signal, SubScoreResult

NEW_ACCOUNT_DAYS = 14
ESTABLISHED_ACCOUNT_DAYS = 180


def score_recruiter_identity(recruiter: Recruiter, company: Company | None) -> SubScoreResult:
    signals: list[Signal] = []
    points = 0
    max_points = 100

    completeness_fields = [recruiter.headline, recruiter.bio, recruiter.photo_url]
    filled = sum(1 for f in completeness_fields if f)
    completeness_points = round((filled / len(completeness_fields)) * 30)
    points += completeness_points
    if filled == 0:
        signals.append(
            Signal(
                code="profile_incomplete",
                severity=SignalSeverity.MEDIUM,
                title="Profile is nearly empty",
                detail="No headline, bio or photo on this recruiter's profile.",
            )
        )

    if recruiter.email and company and company.domain:
        domain_match = recruiter.email.lower().endswith(f"@{company.domain.lower()}")
        if domain_match:
            points += 25
            signals.append(
                Signal(
                    code="email_domain_matches_company",
                    severity=SignalSeverity.INFO,
                    title="Email matches company domain",
                    detail=f"Recruiter's email uses the {company.domain} domain.",
                )
            )
        else:
            signals.append(
                Signal(
                    code="email_domain_mismatch",
                    severity=SignalSeverity.HIGH,
                    title="Email does not match claimed company",
                    detail="The recruiter's email domain does not match their company's domain.",
                )
            )
    elif not recruiter.email:
        signals.append(
            Signal(
                code="no_verified_contact",
                severity=SignalSeverity.MEDIUM,
                title="No verified contact email",
                detail="This recruiter has not provided a contact email.",
            )
        )

    if recruiter.linkedin_url:
        points += 20
        signals.append(
            Signal(
                code="corroborating_profile_linked",
                severity=SignalSeverity.INFO,
                title="LinkedIn profile linked",
                detail="A corroborating LinkedIn profile is on file.",
            )
        )

    account_age_days = (datetime.now(UTC) - recruiter.created_at).days
    if account_age_days < NEW_ACCOUNT_DAYS:
        signals.append(
            Signal(
                code="new_account",
                severity=SignalSeverity.MEDIUM,
                title="Recently created profile",
                detail=f"This profile was added to VeriHire {account_age_days} day(s) ago.",
            )
        )
    elif account_age_days >= ESTABLISHED_ACCOUNT_DAYS:
        points += 25
        signals.append(
            Signal(
                code="established_account",
                severity=SignalSeverity.INFO,
                title="Established profile",
                detail=f"This profile has been on VeriHire for over {ESTABLISHED_ACCOUNT_DAYS} days.",
            )
        )
    else:
        points += 10

    return SubScoreResult(
        code=SubScoreCode.IDENTITY, score=min(points, max_points), signals=signals
    )


def score_company_identity(company: Company) -> SubScoreResult:
    signals: list[Signal] = []
    points = 0

    completeness_fields = [
        company.description,
        company.logo_url,
        company.industry,
        company.hq_city,
    ]
    filled = sum(1 for f in completeness_fields if f)
    points += round((filled / len(completeness_fields)) * 40)
    if filled == 0:
        signals.append(
            Signal(
                code="profile_incomplete",
                severity=SignalSeverity.MEDIUM,
                title="Company profile is nearly empty",
                detail="No description, logo, industry or location on file.",
            )
        )

    if company.domain:
        points += 30
        signals.append(
            Signal(
                code="domain_on_file",
                severity=SignalSeverity.INFO,
                title="Company domain on file",
                detail=f"Website domain {company.domain} is associated with this company.",
            )
        )
    else:
        signals.append(
            Signal(
                code="no_domain",
                severity=SignalSeverity.MEDIUM,
                title="No company website on file",
                detail="This company has no associated website domain.",
            )
        )

    if company.status.value in ("claimed", "verified"):
        points += 30
        signals.append(
            Signal(
                code="entity_claimed",
                severity=SignalSeverity.INFO,
                title="Company claimed",
                detail="Someone at this company has claimed and verified this listing.",
            )
        )

    return SubScoreResult(code=SubScoreCode.IDENTITY, score=min(points, 100), signals=signals)


def identity_cold_start() -> SubScoreResult:
    return SubScoreResult(
        code=SubScoreCode.IDENTITY,
        score=None,
        signals=[
            Signal(
                code="insufficient_identity_data",
                severity=SignalSeverity.INFO,
                title="Not enough data to assess identity",
                detail="No profile information is available for this subject yet.",
            )
        ],
    )
