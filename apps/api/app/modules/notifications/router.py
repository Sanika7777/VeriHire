import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession
from app.core.pagination import Page
from app.modules.notifications.schemas import NotificationRead
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(session: DbSession) -> NotificationService:
    return NotificationService(session)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("", response_model=Page[NotificationRead])
async def list_notifications(
    service: NotificationServiceDep,
    user: CurrentUser,
    cursor: str | None = None,
    limit: int = 20,
) -> Page[NotificationRead]:
    return await service.list_for_user(user.id, cursor=cursor, limit=limit)


@router.get("/unread-count")
async def unread_count(service: NotificationServiceDep, user: CurrentUser) -> dict[str, int]:
    count = await service.unread_count(user.id)
    return {"count": count}


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: uuid.UUID, service: NotificationServiceDep, user: CurrentUser
) -> NotificationRead:
    notification = await service.mark_read(notification_id, user.id)
    return NotificationRead.model_validate(notification)
