import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubjectType
from app.core.errors import ConflictError, NotFoundError
from app.core.pagination import Page, decode_cursor, paginate_rows
from app.modules.reviews.models import Review, ReviewVote
from app.modules.reviews.repository import ReviewRepository
from app.modules.reviews.schemas import ReviewCreate, ReviewRead

MAX_PAGE_SIZE = 100


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReviewRepository(session)

    async def list_for_subject(
        self, subject_type: SubjectType, subject_id: uuid.UUID, *, cursor: str | None, limit: int
    ) -> Page[ReviewRead]:
        limit = min(max(limit, 1), MAX_PAGE_SIZE)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_for_subject(
            subject_type, subject_id, cursor_id=cursor_id, limit=limit
        )
        page = paginate_rows(rows, limit, lambda r: r.id)
        return Page[ReviewRead](
            data=[ReviewRead.model_validate(r) for r in page.data],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )

    async def create(self, payload: ReviewCreate, *, reviewer_user_id: uuid.UUID) -> Review:
        review = Review(
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            reviewer_user_id=reviewer_user_id,
            rating_communication=payload.rating_communication,
            rating_process_transparency=payload.rating_process_transparency,
            rating_offer_accuracy=payload.rating_offer_accuracy,
            rating_professionalism=payload.rating_professionalism,
            body=payload.body,
            verified_interaction=payload.verified_interaction,
        )
        return await self.repo.create(review)

    async def vote(self, review_id: uuid.UUID, *, user_id: uuid.UUID, is_helpful: bool) -> Review:
        review = await self.repo.get_by_id(review_id)
        if review is None:
            raise NotFoundError("Review not found.")

        existing_vote = await self.repo.get_vote(review_id, user_id)
        if existing_vote is not None:
            raise ConflictError("You've already voted on this review.")

        await self.repo.create_vote(
            ReviewVote(review_id=review_id, user_id=user_id, is_helpful=is_helpful)
        )
        if is_helpful:
            review.helpful_count += 1
        else:
            review.unhelpful_count += 1
        await self.session.flush()
        return review
