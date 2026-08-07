import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ClaimMethod, ClaimStatus, EntityStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.postings.models import JobPosting
    from app.modules.recruiters.models import Recruiter


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index(
            "ix_companies_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(String(300), index=True)
    slug: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employee_count_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hq_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hq_country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    registry_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status", native_enum=True),
        default=EntityStatus.UNVERIFIED,
        server_default=EntityStatus.UNVERIFIED.value,
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recruiters: Mapped[list["Recruiter"]] = relationship(back_populates="company")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="company")
    claims: Mapped[list["EntityClaim"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )


class EntityClaim(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Domain-verified company claim flow (DNS TXT record or email at the
    company domain) — powers the company portal.
    """

    __tablename__ = "entity_claims"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[ClaimMethod] = mapped_column(
        Enum(ClaimMethod, name="claim_method", native_enum=True)
    )
    verification_token: Mapped[str] = mapped_column(String(128))
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status", native_enum=True),
        default=ClaimStatus.PENDING,
        server_default=ClaimStatus.PENDING.value,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="claims")
