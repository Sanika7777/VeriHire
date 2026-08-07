import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import EntityStatus
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.companies.models import Company
    from app.modules.postings.models import JobPosting


class Recruiter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recruiters"
    __table_args__ = (
        Index(
            "ix_recruiters_full_name_trgm",
            "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    headline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), unique=True, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_created_on: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[EntityStatus] = mapped_column(
        Enum(EntityStatus, name="entity_status", native_enum=True, create_type=False),
        default=EntityStatus.UNVERIFIED,
        server_default=EntityStatus.UNVERIFIED.value,
    )
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company | None"] = relationship(back_populates="recruiters")
    job_postings: Mapped[list["JobPosting"]] = relationship(back_populates="recruiter")
