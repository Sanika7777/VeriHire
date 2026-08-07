import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ReportCategory, ReportStatus, SubjectType, pg_enum
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index(
            "ix_reports_pending",
            "status",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    subject_type: Mapped[SubjectType] = mapped_column(
        pg_enum(SubjectType, "subject_type", create_type=False)
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)

    reporter_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[ReportCategory] = mapped_column(pg_enum(ReportCategory, "report_category"))
    status: Mapped[ReportStatus] = mapped_column(
        pg_enum(ReportStatus, "report_status"),
        default=ReportStatus.PENDING,
        server_default=ReportStatus.PENDING.value,
    )
    description: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    appeal_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    evidence: Mapped[list["ReportEvidence"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportEvidence(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "report_evidence"

    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    file_url: Mapped[str] = mapped_column(String(2048))
    file_type: Mapped[str] = mapped_column(String(120))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    report: Mapped["Report"] = relationship(back_populates="evidence")
