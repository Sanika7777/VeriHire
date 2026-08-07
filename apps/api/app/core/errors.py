from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_BASE_URL = "https://verihire.app/errors"


class DomainError(Exception):
    """Base class for business-logic errors raised by services.

    Routers never construct HTTP error responses directly (CLAUDE.md §9) —
    they let a domain error propagate and the global handler below maps it
    to an RFC 9457 Problem Details response.
    """

    type_slug = "internal"
    title = "Internal error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class NotFoundError(DomainError):
    type_slug = "not-found"
    title = "Resource not found"
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(DomainError):
    type_slug = "conflict"
    title = "Conflict"
    status_code = status.HTTP_409_CONFLICT


class UnauthorizedError(DomainError):
    type_slug = "unauthorized"
    title = "Authentication required"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(DomainError):
    type_slug = "forbidden"
    title = "Not permitted"
    status_code = status.HTTP_403_FORBIDDEN


class RateLimitedError(DomainError):
    type_slug = "rate-limited"
    title = "Too many requests"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


def _problem(
    *,
    type_slug: str,
    title: str,
    status_code: int,
    detail: str,
    instance: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"{PROBLEM_BASE_URL}/{type_slug}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            type_slug=exc.type_slug,
            title=exc.title,
            status_code=exc.status_code,
            detail=exc.detail,
            instance=str(request.url.path),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return _problem(
            type_slug="validation",
            title="Validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more fields failed validation.",
            instance=str(request.url.path),
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _problem(
            type_slug="http-error",
            title=str(exc.detail),
            status_code=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return _problem(
            type_slug="internal",
            title="Internal error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. It has been logged.",
            instance=str(request.url.path),
        )
