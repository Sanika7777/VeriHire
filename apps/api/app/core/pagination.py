import base64
import binascii
import uuid
from collections.abc import Callable

from pydantic import BaseModel


class Page[T](BaseModel):
    data: list[T]
    next_cursor: str | None
    has_more: bool


def encode_cursor(entity_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(str(entity_id).encode("ascii")).decode("ascii")


def decode_cursor(cursor: str) -> uuid.UUID:
    try:
        return uuid.UUID(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii"))
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid cursor.") from exc


def paginate_rows[T](rows: list[T], limit: int, id_getter: Callable[[T], uuid.UUID]) -> Page[T]:
    """Builds a Page from `limit + 1` fetched rows (the caller over-fetches by
    one to cheaply learn `has_more` without a separate COUNT query)."""
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = encode_cursor(id_getter(page_rows[-1])) if has_more and page_rows else None
    return Page(data=page_rows, next_cursor=next_cursor, has_more=has_more)
