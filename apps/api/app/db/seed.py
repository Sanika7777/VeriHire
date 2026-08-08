"""Seeds realistic development data (CLAUDE.md §8).

Run with: uv run python -m app.db.seed
Volumes here are scaled down from the production targets in CLAUDE.md §8 to
keep local seeding fast; the generation logic itself produces the same
shape of data (real Indian names/cities, INR salaries, a believable mix of
trust bands) and can simply be re-run with larger constants.
"""

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import (
    EntityStatus,
    ReportCategory,
    ReportStatus,
    SignalSeverity,
    SubjectType,
    SubScoreCode,
    TrustBand,
    UserRole,
    VerificationStatus,
)
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.modules.companies.models import Company
from app.modules.companies.schemas import slugify
from app.modules.postings.models import JobPosting
from app.modules.postings.service import compute_content_hash
from app.modules.recruiters.models import Recruiter
from app.modules.reports.models import Report
from app.modules.reviews.models import Review
from app.modules.users.models import User
from app.modules.verification.models import Verification, VerificationSignal

SEED = 1312
N_COMPANIES = 60
N_RECRUITERS = 150
N_POSTINGS = 300
N_REPORTS = 60
N_REVIEWS = 200

INDIAN_CITIES = [
    ("Bengaluru", "India"),
    ("Mumbai", "India"),
    ("Pune", "India"),
    ("Hyderabad", "India"),
    ("Chennai", "India"),
    ("Gurugram", "India"),
    ("Noida", "India"),
    ("Kolkata", "India"),
    ("Ahmedabad", "India"),
    ("Jaipur", "India"),
]

INDUSTRIES = [
    "Information Technology",
    "Financial Services",
    "E-commerce",
    "EdTech",
    "Healthcare",
    "Manufacturing",
    "Logistics",
    "Telecommunications",
]

EMPLOYEE_RANGES = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]

fake = Faker("en_IN")
Faker.seed(SEED)
random.seed(SEED)


def _load_emscad_sample(n: int) -> pd.DataFrame:
    # apps/api/app/db/seed.py -> app -> api -> apps -> repo root
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "services" / "ml" / "data" / "raw" / "fake_job_postings.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df.sample(n=min(n, len(df)), random_state=SEED)


def _signal(
    sub_score_code: str,
    code: str,
    severity: str,
    title: str,
    detail: str,
    evidence_url: str | None = None,
) -> dict[str, object]:
    return {
        "sub_score_code": sub_score_code,
        "code": code,
        "severity": severity,
        "title": title,
        "detail": detail,
        "evidence_url": evidence_url,
    }


async def _record_verification(
    session: AsyncSession,
    *,
    subject_type: SubjectType,
    subject_id: uuid.UUID,
    score: int | None,
    band: TrustBand,
    sub_scores: dict[str, int | None],
    signals: list[dict[str, object]],
    hard_override_reason: str | None = None,
    computed_at: datetime | None = None,
) -> Verification:
    """Inserts a fixed-outcome Verification row for a demo story entity.

    Story entities need a deterministic, reproducible narrative (an amber
    band, a confirmed-scam cap at 25, a score that visibly dropped) that a
    live re-run of the scoring engine can't guarantee, since three of its
    five sub-scores depend on real outbound network calls (RDAP/DNS/TLS,
    Safe Browsing). The shape below matches exactly what
    `verification/service.py` writes so these rows are indistinguishable
    from real ones to every reader (API, UI, admin dashboard).
    """
    verification = Verification(
        subject_type=subject_type,
        subject_id=subject_id,
        score=score,
        band=band,
        sub_scores=sub_scores,
        signals=signals,
        model_version="v1" if sub_scores.get(SubScoreCode.CONTENT_RISK.value) is not None else None,
        status=VerificationStatus.DONE,
        hard_override_reason=hard_override_reason,
        computed_at=computed_at or datetime.now(UTC),
    )
    session.add(verification)
    await session.flush()
    for sig in signals:
        session.add(
            VerificationSignal(
                verification_id=verification.id,
                sub_score_code=SubScoreCode(str(sig["sub_score_code"])),
                code=str(sig["code"]),
                severity=SignalSeverity(str(sig["severity"])),
                title=str(sig["title"]),
                detail=str(sig["detail"]),
                evidence_url=sig["evidence_url"] if isinstance(sig["evidence_url"], str) else None,
            )
        )
    return verification


async def seed_story_entities(session: AsyncSession, moderator: User) -> dict[str, Company]:
    """Eight hand-crafted entities that give the demo a fixed, repeatable narrative.

    See docs/demo-script.md, which walks through each of these by name.
    """
    print("Seeding 8 story entities for the demo script...")
    story: dict[str, Company] = {}

    # 1. Clearly legitimate MNC — long track record, every sub-score strong.
    mnc = Company(
        name="Meridian Software Solutions Pvt Ltd",
        slug=slugify("Meridian Software Solutions Pvt Ltd"),
        domain="meridiansoftware.com",
        description="A 20-year-old enterprise software and IT services company "
        "with delivery centers in Bengaluru, Pune and Hyderabad.",
        website_url="https://www.meridiansoftware.com",
        industry="Information Technology",
        employee_count_range="1000+",
        hq_city="Bengaluru",
        hq_country="India",
        founded_year=2004,
        status=EntityStatus.VERIFIED,
    )
    session.add(mnc)
    await session.flush()
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=mnc.id,
        score=94,
        band=TrustBand.TRUSTED,
        sub_scores={
            SubScoreCode.IDENTITY.value: 96,
            SubScoreCode.COMPANY_LEGITIMACY.value: 97,
            SubScoreCode.CONTENT_RISK.value: 92,
            SubScoreCode.LINK_SAFETY.value: 95,
            SubScoreCode.COMMUNITY_SIGNAL.value: 90,
        },
        signals=[
            _signal(
                "company_legitimacy", "domain_age_mature", "info",
                "Domain registered 20 years ago",
                "meridiansoftware.com has been continuously registered since 2004, well "
                "past the threshold associated with shell/shell-like operations.",
            ),
            _signal(
                "company_legitimacy", "mx_records_valid", "info",
                "Valid corporate mail infrastructure",
                "MX, SPF and DMARC records are all present and consistent with an "
                "established company mail system.",
            ),
            _signal(
                "community_signal", "no_confirmed_reports", "info",
                "No confirmed fraud reports",
                "Zero confirmed fraud reports across this company's full history on VeriHire.",
            ),
        ],
    )
    story["legitimate_mnc"] = mnc

    # 2. Verified startup — smaller, younger, but claimed and clean.
    startup = Company(
        name="NimbusStack Labs",
        slug=slugify("NimbusStack Labs"),
        domain="nimbusstack.io",
        description="A 3-year-old cloud infrastructure startup, Series A funded, "
        "building developer tooling for Kubernetes fleets.",
        website_url="https://nimbusstack.io",
        industry="Information Technology",
        employee_count_range="51-200",
        hq_city="Pune",
        hq_country="India",
        founded_year=2023,
        status=EntityStatus.CLAIMED,
    )
    session.add(startup)
    await session.flush()
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=startup.id,
        score=81,
        band=TrustBand.TRUSTED,
        sub_scores={
            SubScoreCode.IDENTITY.value: 85,
            SubScoreCode.COMPANY_LEGITIMACY.value: 78,
            SubScoreCode.CONTENT_RISK.value: 88,
            SubScoreCode.LINK_SAFETY.value: 90,
            SubScoreCode.COMMUNITY_SIGNAL.value: 70,
        },
        signals=[
            _signal(
                "identity", "domain_email_match", "info",
                "Company email domain claimed and verified",
                "An account holder verified control of nimbusstack.io via the email-domain "
                "claim flow.",
            ),
            _signal(
                "company_legitimacy", "domain_age_moderate", "low",
                "Domain registered 3 years ago",
                "A younger domain than an established enterprise, consistent with a "
                "recently founded but legitimate startup.",
            ),
        ],
    )
    story["verified_startup"] = startup

    # 3. Amber-band ambiguous case — mixed signals, nothing decisive either way.
    ambiguous = Company(
        name="Bluepeak Consulting Services",
        slug=slugify("Bluepeak Consulting Services"),
        domain="bluepeakconsulting.net",
        description="An HR/staffing consultancy placing contract IT roles across India.",
        website_url="https://bluepeakconsulting.net",
        industry="Information Technology",
        employee_count_range="11-50",
        hq_city="Noida",
        hq_country="India",
        founded_year=2021,
        status=EntityStatus.UNVERIFIED,
    )
    session.add(ambiguous)
    await session.flush()
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=ambiguous.id,
        score=54,
        band=TrustBand.CAUTION,
        sub_scores={
            SubScoreCode.IDENTITY.value: 60,
            SubScoreCode.COMPANY_LEGITIMACY.value: 52,
            SubScoreCode.CONTENT_RISK.value: 48,
            SubScoreCode.LINK_SAFETY.value: 75,
            SubScoreCode.COMMUNITY_SIGNAL.value: 40,
        },
        signals=[
            _signal(
                "company_legitimacy", "no_registry_match", "medium",
                "No company registry match found",
                "No matching entity was found in available company registry lookups — "
                "this alone is not conclusive, as many small consultancies register "
                "under a parent LLP not searchable here.",
            ),
            _signal(
                "content_risk", "salary_outlier_moderate", "medium",
                "Posted salary somewhat above market band",
                "One active posting quotes a salary in the top decile for its role and "
                "city, without a clear seniority justification.",
            ),
            _signal(
                "community_signal", "mixed_reviews", "low",
                "Mixed reviewer feedback",
                "Reviews are split between describing a legitimate, if disorganized, "
                "hiring process and complaints about slow communication.",
            ),
        ],
    )
    story["amber_ambiguous"] = ambiguous

    # 4. Confirmed advance-fee scam — hard override caps at 25.
    scam = Company(
        name="GlobalCareer Overseas Placements",
        slug=slugify("GlobalCareer Overseas Placements"),
        domain="globalcareer-placements.tk",
        description="Claims to place candidates in high-paying overseas logistics jobs.",
        website_url="https://globalcareer-placements.tk",
        industry="Logistics",
        employee_count_range="1-10",
        hq_city="Gurugram",
        hq_country="India",
        founded_year=2025,
        status=EntityStatus.FLAGGED,
    )
    session.add(scam)
    await session.flush()
    scam_report = Report(
        subject_type=SubjectType.COMPANY,
        subject_id=scam.id,
        reporter_user_id=None,
        category=ReportCategory.ADVANCE_FEE,
        status=ReportStatus.CONFIRMED,
        description="Asked for a refundable 'visa processing fee' of INR 15,000 via UPI "
        "before any offer letter was issued. No such overseas role existed.",
        confirmed_at=datetime.now(UTC),
        confirmed_by_user_id=moderator.id,
    )
    session.add(scam_report)
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=scam.id,
        score=25,
        band=TrustBand.HIGH_RISK,
        sub_scores={
            SubScoreCode.IDENTITY.value: 30,
            SubScoreCode.COMPANY_LEGITIMACY.value: 15,
            SubScoreCode.CONTENT_RISK.value: 8,
            SubScoreCode.LINK_SAFETY.value: 20,
            SubScoreCode.COMMUNITY_SIGNAL.value: 5,
        },
        signals=[
            _signal(
                "content_risk", "advance_fee_language", "critical",
                "Advance-fee language detected",
                "Posting text requests upfront payment for visa/processing fees before "
                "any employment relationship is established — a defining pattern of "
                "advance-fee fraud.",
            ),
            _signal(
                "community_signal", "confirmed_fraud_report", "critical",
                "Confirmed fraud report on file",
                "A Trust & Safety moderator confirmed a report describing an upfront "
                "payment demand with no legitimate role behind it.",
            ),
        ],
        hard_override_reason="Capped at 25 due to a confirmed fraud report.",
    )
    story["confirmed_scam"] = scam

    # 5. Impersonation of a real brand — typosquat domain, high risk.
    impersonation = Company(
        name="Tata Consultancy Servicess Careers",
        slug=slugify("Tata Consultancy Servicess Careers"),
        domain="tcs-careers-hiring.com",
        description="A recruiting page claiming affiliation with a large, well-known "
        "Indian IT services company.",
        website_url="https://tcs-careers-hiring.com",
        industry="Information Technology",
        employee_count_range="1-10",
        hq_city="Mumbai",
        hq_country="India",
        founded_year=2026,
        status=EntityStatus.FLAGGED,
    )
    session.add(impersonation)
    await session.flush()
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=impersonation.id,
        score=18,
        band=TrustBand.HIGH_RISK,
        sub_scores={
            SubScoreCode.IDENTITY.value: 20,
            SubScoreCode.COMPANY_LEGITIMACY.value: 10,
            SubScoreCode.CONTENT_RISK.value: 22,
            SubScoreCode.LINK_SAFETY.value: 15,
            SubScoreCode.COMMUNITY_SIGNAL.value: 25,
        },
        signals=[
            _signal(
                "link_safety", "lookalike_domain", "critical",
                "Domain mimics a well-known company",
                "tcs-careers-hiring.com is not a domain controlled by the company it "
                "names, and closely mimics official naming — a common impersonation "
                "pattern used to borrow an established brand's trust.",
            ),
            _signal(
                "company_legitimacy", "domain_age_new", "high",
                "Domain registered days ago",
                "The domain was registered recently, inconsistent with the decades-long "
                "history of the company it claims to represent.",
            ),
        ],
    )
    story["brand_impersonation"] = impersonation

    # 6. Newly created shell company — too new to have any track record.
    shell = Company(
        name="Rapid Corp Solutions",
        slug=slugify("Rapid Corp Solutions"),
        domain="rapidcorpsolutions.in",
        description="A recently registered staffing entity with no public track record.",
        website_url="https://rapidcorpsolutions.in",
        industry="Manufacturing",
        employee_count_range="1-10",
        hq_city="Ahmedabad",
        hq_country="India",
        founded_year=2026,
        status=EntityStatus.UNVERIFIED,
    )
    session.add(shell)
    await session.flush()
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=shell.id,
        score=42,
        band=TrustBand.CAUTION,
        sub_scores={
            SubScoreCode.IDENTITY.value: 45,
            SubScoreCode.COMPANY_LEGITIMACY.value: 30,
            SubScoreCode.CONTENT_RISK.value: 55,
            SubScoreCode.LINK_SAFETY.value: 60,
            SubScoreCode.COMMUNITY_SIGNAL.value: None,
        },
        signals=[
            _signal(
                "company_legitimacy", "domain_age_new", "medium",
                "Domain registered a few weeks ago",
                "rapidcorpsolutions.in was registered very recently, which is not "
                "disqualifying on its own but removes a major source of corroborating "
                "history.",
            ),
            _signal(
                "community_signal", "no_data_yet", "info",
                "No reports or reviews yet",
                "This entity has no community activity to weigh — the community_signal "
                "sub-score is excluded and the other weights are renormalized.",
            ),
        ],
    )
    story["new_shell"] = shell

    # 7. Score dropped after reports — two immutable verifications, same subject.
    dropped = Company(
        name="Bright Horizon Careers",
        slug=slugify("Bright Horizon Careers"),
        domain="brighthorizoncareers.com",
        description="A recruitment agency placing entry-level sales and BPO roles.",
        website_url="https://brighthorizoncareers.com",
        industry="Telecommunications",
        employee_count_range="51-200",
        hq_city="Chennai",
        hq_country="India",
        founded_year=2019,
        status=EntityStatus.FLAGGED,
    )
    session.add(dropped)
    await session.flush()
    earlier = datetime.now(UTC) - timedelta(days=21)
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=dropped.id,
        score=79,
        band=TrustBand.TRUSTED,
        sub_scores={
            SubScoreCode.IDENTITY.value: 80,
            SubScoreCode.COMPANY_LEGITIMACY.value: 82,
            SubScoreCode.CONTENT_RISK.value: 75,
            SubScoreCode.LINK_SAFETY.value: 85,
            SubScoreCode.COMMUNITY_SIGNAL.value: 70,
        },
        signals=[
            _signal(
                "community_signal", "no_confirmed_reports", "info",
                "No confirmed fraud reports at time of scoring",
                "At this point in its history, this company had no confirmed reports.",
            ),
        ],
        computed_at=earlier,
    )
    drop_report = Report(
        subject_type=SubjectType.COMPANY,
        subject_id=dropped.id,
        reporter_user_id=None,
        category=ReportCategory.INTERVIEW_SCAM,
        status=ReportStatus.CONFIRMED,
        description="Multiple candidates report being charged a 'training kit' fee "
        "after a scripted phone interview, with no real job offered afterward.",
        confirmed_at=datetime.now(UTC) - timedelta(days=2),
        confirmed_by_user_id=moderator.id,
    )
    session.add(drop_report)
    await _record_verification(
        session,
        subject_type=SubjectType.COMPANY,
        subject_id=dropped.id,
        score=25,
        band=TrustBand.HIGH_RISK,
        sub_scores={
            SubScoreCode.IDENTITY.value: 80,
            SubScoreCode.COMPANY_LEGITIMACY.value: 82,
            SubScoreCode.CONTENT_RISK.value: 60,
            SubScoreCode.LINK_SAFETY.value: 85,
            SubScoreCode.COMMUNITY_SIGNAL.value: 12,
        },
        signals=[
            _signal(
                "community_signal", "confirmed_fraud_report", "critical",
                "Confirmed fraud report on file",
                "A Trust & Safety moderator confirmed a report describing a paid "
                "'training kit' scheme with no real job behind it — this caps the "
                "overall score regardless of the other four sub-scores.",
            ),
        ],
        hard_override_reason="Capped at 25 due to a confirmed fraud report.",
        computed_at=datetime.now(UTC) - timedelta(days=1),
    )
    story["score_dropped"] = dropped

    # 8. Unrated cold start — exists, but nothing has ever scored it.
    cold_start = Company(
        name="Sundari Textiles Exports",
        slug=slugify("Sundari Textiles Exports"),
        domain=None,
        description="A textile exporter that recently began hiring on VeriHire-linked boards.",
        website_url=None,
        industry="Manufacturing",
        employee_count_range="11-50",
        hq_city="Jaipur",
        hq_country="India",
        founded_year=2018,
        status=EntityStatus.UNVERIFIED,
    )
    session.add(cold_start)
    await session.flush()
    story["cold_start_unrated"] = cold_start

    return story


async def seed() -> None:
    async with async_session_factory() as session:
        print("Seeding users...")
        admin = User(
            email="admin@verihire.app",
            password_hash=hash_password("AdminPassword123!"),
            full_name="VeriHire Admin",
            role=UserRole.ADMIN,
            email_verified_at=datetime.now(UTC),
        )
        moderator = User(
            email="moderator@verihire.app",
            password_hash=hash_password("ModeratorPassword123!"),
            full_name="Trust & Safety Moderator",
            role=UserRole.MODERATOR,
            email_verified_at=datetime.now(UTC),
        )
        session.add_all([admin, moderator])
        await session.flush()

        seeker_users = []
        for _ in range(30):
            user = User(
                email=fake.unique.email(),
                password_hash=hash_password("SeekerPassword123!"),
                full_name=fake.name(),
                role=UserRole.SEEKER,
                email_verified_at=datetime.now(UTC) if random.random() > 0.2 else None,
            )
            session.add(user)
            seeker_users.append(user)
        await session.flush()

        print(f"Seeding {N_COMPANIES} companies...")
        companies: list[Company] = []
        for _ in range(N_COMPANIES):
            name = fake.company()
            city, country = random.choice(INDIAN_CITIES)
            slug_base = slugify(name)
            slug = slug_base
            suffix = 1
            existing_slugs = {c.slug for c in companies}
            while slug in existing_slugs:
                suffix += 1
                slug = f"{slug_base}-{suffix}"

            company = Company(
                name=name,
                slug=slug,
                domain=fake.domain_name() if random.random() > 0.15 else None,
                description=fake.catch_phrase() + ". " + fake.bs(),
                website_url=fake.url(),
                industry=random.choice(INDUSTRIES),
                employee_count_range=random.choice(EMPLOYEE_RANGES),
                hq_city=city,
                hq_country=country,
                founded_year=random.randint(1990, 2023),
                status=random.choice(
                    [EntityStatus.UNVERIFIED, EntityStatus.UNVERIFIED, EntityStatus.CLAIMED]
                ),
            )
            session.add(company)
            companies.append(company)
        await session.flush()

        print(f"Seeding {N_RECRUITERS} recruiters...")
        recruiters = []
        for _ in range(N_RECRUITERS):
            recruiter_company = random.choice(companies) if random.random() > 0.1 else None
            recruiter = Recruiter(
                company_id=recruiter_company.id if recruiter_company else None,
                full_name=fake.name(),
                headline=fake.job(),
                email=fake.unique.email() if random.random() > 0.3 else None,
                linkedin_url=f"https://www.linkedin.com/in/{fake.unique.user_name()}",
                bio=fake.text(max_nb_chars=200) if random.random() > 0.4 else None,
                status=EntityStatus.UNVERIFIED,
            )
            session.add(recruiter)
            recruiters.append(recruiter)
        await session.flush()

        print(f"Seeding {N_POSTINGS} job postings from EMSCAD sample...")
        emscad = _load_emscad_sample(N_POSTINGS)
        postings = []
        if not emscad.empty:
            for _, row in emscad.iterrows():
                posting_company = random.choice(companies) if random.random() > 0.3 else None
                posting_recruiter = random.choice(recruiters) if random.random() > 0.3 else None
                title = str(row["title"])[:300] or "Untitled posting"
                description = str(row.get("description") or "No description provided.")
                content_hash = compute_content_hash(
                    title, description, posting_company.id if posting_company else None
                )
                posting = JobPosting(
                    company_id=posting_company.id if posting_company else None,
                    recruiter_id=posting_recruiter.id if posting_recruiter else None,
                    title=title,
                    description=description,
                    requirements=str(row.get("requirements") or "") or None,
                    location_city=random.choice(INDIAN_CITIES)[0],
                    location_country="India",
                    employment_type=str(row.get("employment_type") or "") or None,
                    telecommuting=bool(row.get("telecommuting", False)),
                    has_company_logo=bool(row.get("has_company_logo", False)),
                    has_questions=bool(row.get("has_questions", False)),
                    content_hash=content_hash,
                    status=EntityStatus.UNVERIFIED,
                    posted_at=datetime.now(UTC) - timedelta(days=random.randint(0, 30)),
                )
                session.add(posting)
                postings.append(posting)
            await session.flush()

        print(f"Seeding {N_REPORTS} reports...")
        all_subjects = (
            [(SubjectType.COMPANY, c.id) for c in companies]
            + [(SubjectType.RECRUITER, r.id) for r in recruiters]
            + [(SubjectType.JOB_POSTING, p.id) for p in postings]
        )
        for _ in range(min(N_REPORTS, len(all_subjects))):
            subject_type, subject_id = random.choice(all_subjects)
            status = random.choices(
                [ReportStatus.PENDING, ReportStatus.CONFIRMED, ReportStatus.REJECTED],
                weights=[0.5, 0.3, 0.2],
            )[0]
            report = Report(
                subject_type=subject_type,
                subject_id=subject_id,
                reporter_user_id=random.choice(seeker_users).id,
                category=random.choice(list(ReportCategory)),
                status=status,
                description=fake.paragraph(nb_sentences=3),
                confirmed_at=datetime.now(UTC) if status == ReportStatus.CONFIRMED else None,
                confirmed_by_user_id=moderator.id if status == ReportStatus.CONFIRMED else None,
            )
            session.add(report)
        await session.flush()

        print(f"Seeding {N_REVIEWS} reviews...")
        for _ in range(min(N_REVIEWS, len(all_subjects))):
            subject_type, subject_id = random.choice(all_subjects)
            review = Review(
                subject_type=subject_type,
                subject_id=subject_id,
                reviewer_user_id=random.choice(seeker_users).id,
                rating_communication=random.randint(1, 5),
                rating_process_transparency=random.randint(1, 5),
                rating_offer_accuracy=random.randint(1, 5),
                rating_professionalism=random.randint(1, 5),
                body=fake.paragraph(nb_sentences=2),
                verified_interaction=random.random() > 0.5,
            )
            session.add(review)
        await session.flush()

        story = await seed_story_entities(session, moderator)
        await session.flush()

        await session.commit()
        print("Seed complete.")
        print(f"  companies={len(companies)} recruiters={len(recruiters)} postings={len(postings)}")
        print("  Admin login: admin@verihire.app / AdminPassword123!")
        print("  Moderator login: moderator@verihire.app / ModeratorPassword123!")
        print("  Story entities (see docs/demo-script.md):")
        for key, company in story.items():
            print(f"    {key}: {company.name!r} ({company.id})")


if __name__ == "__main__":
    asyncio.run(seed())
