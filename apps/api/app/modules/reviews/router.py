import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession
from app.core.enums import SubjectType
from app.core.pagination import Page
from app.modules.reviews.schemas import ReviewCreate, ReviewRead, ReviewVoteCreate
from app.modules.reviews.service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_service(session: DbSession) -> ReviewService:
    return ReviewService(session)


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


@router.get("", response_model=Page[ReviewRead])
async def list_reviews(
    service: ReviewServiceDep,
    subject_type: SubjectType,
    subject_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = 20,
) -> Page[ReviewRead]:
    return await service.list_for_subject(subject_type, subject_id, cursor=cursor, limit=limit)


@router.post("", response_model=ReviewRead, status_code=201)
async def create_review(
    body: ReviewCreate, service: ReviewServiceDep, user: CurrentUser
) -> ReviewRead:
    review = await service.create(body, reviewer_user_id=user.id)
    return ReviewRead.model_validate(review)


@router.post("/{review_id}/vote", response_model=ReviewRead)
async def vote_review(
    review_id: uuid.UUID,
    body: ReviewVoteCreate,
    service: ReviewServiceDep,
    user: CurrentUser,
) -> ReviewRead:
    review = await service.vote(review_id, user_id=user.id, is_helpful=body.is_helpful)
    return ReviewRead.model_validate(review)
