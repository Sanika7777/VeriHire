import enum


class UserRole(str, enum.Enum):
    SEEKER = "seeker"
    EMPLOYER = "employer"
    MODERATOR = "moderator"
    ADMIN = "admin"


class TrustBand(str, enum.Enum):
    UNRATED = "unrated"
    HIGH_RISK = "high_risk"
    CAUTION = "caution"
    TRUSTED = "trusted"


class SubjectType(str, enum.Enum):
    COMPANY = "company"
    RECRUITER = "recruiter"
    JOB_POSTING = "job_posting"


class EntityStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    CLAIMED = "claimed"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    MERGED = "merged"
    REMOVED = "removed"


class ReportCategory(str, enum.Enum):
    ADVANCE_FEE = "advance_fee"
    FAKE_JOB_POSTING = "fake_job_posting"
    IMPERSONATION = "impersonation"
    DATA_HARVESTING = "data_harvesting"
    PYRAMID_SCHEME = "pyramid_scheme"
    INTERVIEW_SCAM = "interview_scam"
    PAYMENT_SCAM = "payment_scam"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    APPEALED = "appealed"


class ClaimMethod(str, enum.Enum):
    DNS_TXT = "dns_txt"
    EMAIL_DOMAIN = "email_domain"


class ClaimStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SignalSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubScoreCode(str, enum.Enum):
    IDENTITY = "identity"
    COMPANY_LEGITIMACY = "company_legitimacy"
    CONTENT_RISK = "content_risk"
    LINK_SAFETY = "link_safety"
    COMMUNITY_SIGNAL = "community_signal"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    FETCHING = "fetching"
    ANALYSING = "analysing"
    SCORING = "scoring"
    DONE = "done"
    FAILED = "failed"
