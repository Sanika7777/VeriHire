import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType
from app.modules.reviews.models import Review, ReviewVote


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        result = await self.session.execute(
            select(Review).where(Review.id == review_id, Review.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_for_subject(
        self, subject_type: SubjectType, subject_id: uuid.UUID, *, cursor_id: uuid.UUID | None, limit: int
    ) -> list[Review]:
        query = (
            select(Review)
            .where(
                Review.subject_type == subject_type,
                Review.subject_id == subject_id,
                Review.deleted_at.is_(None),
            )
            .order_by(Review.id)
        )
        if cursor_id is not None:
            query = query.where(Review.id > cursor_id)
        result = await self.session.execute(query.limit(limit + 1))
        return list(result.scalars().all())

    async def create(self, review: Review) -> Review:
        self.session.add(review)
        await self.session.flush()
        return review

    async def get_vote(self, review_id: uuid.UUID, user_id: uuid.UUID) -> ReviewVote | None:
        result = await self.session.execute(
            select(ReviewVote).where(
                ReviewVote.review_id == review_id, ReviewVote.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def create_vote(self, vote: ReviewVote) -> ReviewVote:
        self.session.add(vote)
        await self.session.flush()
        return vote
