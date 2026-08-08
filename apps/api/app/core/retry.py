import asyncio
import random
from collections.abc import Awaitable, Callable

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 0.25
MAX_DELAY_SECONDS = 2.0


async def retry_with_jitter[T](
    fn: Callable[[], Awaitable[T]],
    *,
    should_retry: Callable[[BaseException], bool],
    max_attempts: int = MAX_ATTEMPTS,
) -> T:
    """Retries a transient-failure-prone async call with exponential backoff
    plus jitter (CLAUDE.md §10). `should_retry` decides which exceptions are
    worth retrying (e.g. timeouts, 5xx) versus failing fast (e.g. 404s).
    """
    for attempt in range(max_attempts):
        try:
            return await fn()
        except BaseException as exc:  # noqa: BLE001
            if attempt == max_attempts - 1 or not should_retry(exc):
                raise
            delay = min(BASE_DELAY_SECONDS * (2**attempt), MAX_DELAY_SECONDS)
            delay += random.uniform(0, delay * 0.5)  # noqa: S311
            await asyncio.sleep(delay)

    raise AssertionError("unreachable")  # loop always returns or raises
