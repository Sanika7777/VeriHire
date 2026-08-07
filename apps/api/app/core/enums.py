import enum
from typing import Any

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str, **kwargs: Any) -> SAEnum:
    """Native Postgres enum storing member `.value` strings, not member names.

    SQLAlchemy's `Enum` type stores Python enum *names* in the database by
    default. Every enum in this module is a `str` enum whose `.value` is the
    lowercase wire format used in server defaults, seeds and the API — so
    every native enum column must be built through this helper to keep the
    stored values consistent with those strings.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda obj: [e.value for e in obj],
        **kwargs,
    )


class UserRole(enum.StrEnum):
    SEEKER = "seeker"
    EMPLOYER = "employer"
    MODERATOR = "moderator"
    ADMIN = "admin"


class TrustBand(enum.StrEnum):
    UNRATED = "unrated"
    HIGH_RISK = "high_risk"
    CAUTION = "caution"
    TRUSTED = "trusted"


class SubjectType(enum.StrEnum):
    COMPANY = "company"
    RECRUITER = "recruiter"
    JOB_POSTING = "job_posting"


class EntityStatus(enum.StrEnum):
    UNVERIFIED = "unverified"
    CLAIMED = "claimed"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    MERGED = "merged"
    REMOVED = "removed"


class ReportCategory(enum.StrEnum):
    ADVANCE_FEE = "advance_fee"
    FAKE_JOB_POSTING = "fake_job_posting"
    IMPERSONATION = "impersonation"
    DATA_HARVESTING = "data_harvesting"
    PYRAMID_SCHEME = "pyramid_scheme"
    INTERVIEW_SCAM = "interview_scam"
    PAYMENT_SCAM = "payment_scam"
    OTHER = "other"


class ReportStatus(enum.StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    APPEALED = "appealed"


class ClaimMethod(enum.StrEnum):
    DNS_TXT = "dns_txt"
    EMAIL_DOMAIN = "email_domain"


class ClaimStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SignalSeverity(enum.StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubScoreCode(enum.StrEnum):
    IDENTITY = "identity"
    COMPANY_LEGITIMACY = "company_legitimacy"
    CONTENT_RISK = "content_risk"
    LINK_SAFETY = "link_safety"
    COMMUNITY_SIGNAL = "community_signal"


class VerificationStatus(enum.StrEnum):
    PENDING = "pending"
    RESOLVING = "resolving"
    FETCHING = "fetching"
    ANALYSING = "analysing"
    SCORING = "scoring"
    DONE = "done"
    FAILED = "failed"
