from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import compute_verification


async def startup(ctx: dict[str, object]) -> None:  # noqa: ARG001
    pass


async def shutdown(ctx: dict[str, object]) -> None:  # noqa: ARG001
    pass


def _redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings.from_dsn(str(settings.redis_url))


class WorkerSettings:
    functions = [compute_verification]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
