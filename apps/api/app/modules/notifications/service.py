import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.pagination import Page, decode_cursor, encode_cursor
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import NotificationRead
from app.modules.users.models import Notification


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list_for_user(
        self, user_id: uuid.UUID, *, cursor: str | None, limit: int
    ) -> Page[NotificationRead]:
        limit = min(max(limit, 1), 100)
        cursor_id = decode_cursor(cursor) if cursor else None
        rows = await self.repo.list_for_user(user_id, cursor_id=cursor_id, limit=limit)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(page_rows[-1].id) if has_more and page_rows else None
        return Page[NotificationRead](
            data=[NotificationRead.model_validate(n) for n in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = await self.repo.get_by_id(notification_id, user_id)
        if notification is None:
            raise NotFoundError("Notification not found.")
        await self.repo.mark_read(notification)
        return notification
