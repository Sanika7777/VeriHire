from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.health import router as health_router
from app.core.logging import configure_logging, correlation_id_middleware
from app.core.metrics import router as metrics_router
from app.core.security_headers import security_headers_middleware
from app.db import all_models as _all_models  # noqa: F401  (registers every model)
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.companies.router import router as companies_router
from app.modules.notifications.router import router as notifications_router
from app.modules.postings.router import router as postings_router
from app.modules.recruiters.router import router as recruiters_router
from app.modules.reports.router import router as reports_router
from app.modules.resolve.router import router as resolve_router
from app.modules.reviews.router import router as reviews_router
from app.modules.search.router import router as search_router
from app.modules.stats.router import router as stats_router
from app.modules.verification.router import router as verification_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(json_logs=settings.environment != "development")

    if settings.sentry_dsn and settings.environment not in ("development", "test"):
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

    app = FastAPI(
        title="VeriHire API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(correlation_id_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    app.include_router(companies_router, prefix=settings.api_prefix)
    app.include_router(recruiters_router, prefix=settings.api_prefix)
    app.include_router(postings_router, prefix=settings.api_prefix)
    app.include_router(search_router, prefix=settings.api_prefix)
    app.include_router(resolve_router, prefix=settings.api_prefix)
    app.include_router(verification_router, prefix=settings.api_prefix)
    app.include_router(reports_router, prefix=settings.api_prefix)
    app.include_router(reviews_router, prefix=settings.api_prefix)
    app.include_router(notifications_router, prefix=settings.api_prefix)
    app.include_router(stats_router, prefix=settings.api_prefix)

    return app


app = create_app()
