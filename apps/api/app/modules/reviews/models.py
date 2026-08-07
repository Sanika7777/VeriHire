import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import SubjectType, pg_enum
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"

    subject_type: Mapped[SubjectType] = mapped_column(
        pg_enum(SubjectType, "subject_type", create_type=False)
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)

    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    rating_communication: Mapped[int] = mapped_column(Integer)
    rating_process_transparency: Mapped[int] = mapped_column(Integer)
    rating_offer_accuracy: Mapped[int] = mapped_column(Integer)
    rating_professionalism: Mapped[int] = mapped_column(Integer)

    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_interaction: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    unhelpful_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    votes: Mapped[list["ReviewVote"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewVote(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_votes"
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="uq_review_vote_user"),)

    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    is_helpful: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    review: Mapped["Review"] = relationship(back_populates="votes")
