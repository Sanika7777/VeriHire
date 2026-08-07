import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    SignalSeverity,
    SubjectType,
    SubScoreCode,
    TrustBand,
    VerificationStatus,
    pg_enum,
)
from app.db.base import Base, UUIDPrimaryKeyMixin


class Verification(UUIDPrimaryKeyMixin, Base):
    """An immutable Trust Score snapshot for one subject.

    Scores are never mutated — recomputation always inserts a new row so
    score history and diffs (CLAUDE.md §5) stay intact.
    """

    __tablename__ = "verifications"
    __table_args__ = (
        Index(
            "ix_verifications_subject_computed_at",
            "subject_type",
            "subject_id",
            "computed_at",
        ),
        Index(
            "ix_verifications_signals_gin",
            "signals",
            postgresql_using="gin",
            postgresql_ops={"signals": "jsonb_path_ops"},
        ),
    )

    subject_type: Mapped[SubjectType] = mapped_column(pg_enum(SubjectType, "subject_type"))
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)

    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band: Mapped[TrustBand] = mapped_column(
        pg_enum(TrustBand, "trust_band"),
        default=TrustBand.UNRATED,
    )
    sub_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config_version: Mapped[int | None] = mapped_column(
        ForeignKey("scoring_configs.version", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[VerificationStatus] = mapped_column(
        pg_enum(VerificationStatus, "verification_status"),
        default=VerificationStatus.PENDING,
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    hard_override_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    signal_rows: Mapped[list["VerificationSignal"]] = relationship(
        back_populates="verification", cascade="all, delete-orphan"
    )


class VerificationSignal(UUIDPrimaryKeyMixin, Base):
    """Denormalized, queryable copy of one entry in `verifications.signals`.

    The JSONB column on `Verification` is the immutable, authoritative
    snapshot returned to clients; these rows exist purely so admin analytics
    can filter/aggregate by signal code or severity without scanning JSONB.
    """

    __tablename__ = "verification_signals"
    __table_args__ = (Index("ix_verification_signals_code", "code"),)

    verification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"), index=True
    )
    sub_score_code: Mapped[SubScoreCode] = mapped_column(pg_enum(SubScoreCode, "sub_score_code"))
    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[SignalSeverity] = mapped_column(
        pg_enum(SignalSeverity, "signal_severity")
    )
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    verification: Mapped["Verification"] = relationship(back_populates="signal_rows")


class ScoringConfig(UUIDPrimaryKeyMixin, Base):
    """Versioned Trust Score weights/thresholds — never hardcoded (CLAUDE.md §5)."""

    __tablename__ = "scoring_configs"

    version: Mapped[int] = mapped_column(Integer, unique=True, index=True, autoincrement=True)
    weights: Mapped[dict[str, float]] = mapped_column(JSONB)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
