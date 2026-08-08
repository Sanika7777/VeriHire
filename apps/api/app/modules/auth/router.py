from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Response
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.deps import AuthServiceDep, CurrentUser
from app.core.errors import UnauthorizedError
from app.core.rate_limit import RateLimiter
from app.modules.auth.schemas import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    GoogleAuthorizationResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserRead,
    VerifyEmailRequest,
)
from app.modules.auth.service import TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "verihire_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)]

_auth_rate_limit = RateLimiter(times=5, seconds=60, scope="auth")


def _set_refresh_cookie(response: Response, tokens: TokenPair) -> None:
    settings = get_settings()
    max_age = max(
        int((tokens.refresh_expires_at - datetime.now(tokens.refresh_expires_at.tzinfo)).total_seconds()),
        0,
    )
    # In development, web and api share a site (different localhost ports),
    # so Lax works and avoids needing Secure over plain http. In every
    # deployed environment the web app (Vercel) and api (Fly/Render) are on
    # different registrable domains — a genuinely cross-site request — so
    # the cookie needs SameSite=None, which browsers only honor if Secure
    # is also set.
    is_development = settings.environment == "development"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        max_age=max_age,
        httponly=True,
        secure=not is_development,
        samesite="lax" if is_development else "none",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    # Browsers only clear a cookie when secure/samesite match how it was
    # set — mismatched attributes silently no-op instead of deleting it.
    is_development = get_settings().environment == "development"
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=not is_development,
        samesite="lax" if is_development else "none",
    )


@router.post(
    "/register",
    response_model=AccessTokenResponse,
    status_code=201,
    dependencies=[Depends(_auth_rate_limit)],
)
async def register(
    body: RegisterRequest, response: Response, auth_service: AuthServiceDep
) -> AccessTokenResponse:
    user = await auth_service.register(
        email=body.email, password=body.password, full_name=body.full_name
    )
    tokens = await auth_service.issue_token_pair(user)
    _set_refresh_cookie(response, tokens)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    dependencies=[Depends(_auth_rate_limit)],
)
async def login(
    body: LoginRequest, response: Response, auth_service: AuthServiceDep
) -> AccessTokenResponse:
    user = await auth_service.authenticate(email=body.email, password=body.password)
    tokens = await auth_service.issue_token_pair(user)
    _set_refresh_cookie(response, tokens)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserRead.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> AccessTokenResponse:
    if refresh_token is None:
        raise UnauthorizedError("No refresh token was provided.")

    user, tokens = await auth_service.rotate_refresh_token(refresh_token)
    _set_refresh_cookie(response, tokens)
    return AccessTokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=UserRead.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token: RefreshCookie = None,
) -> MessageResponse:
    if refresh_token is not None:
        await auth_service.logout(refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.delete("/me", status_code=204)
async def delete_me(
    response: Response,
    user: CurrentUser,
    auth_service: AuthServiceDep,
) -> None:
    await auth_service.delete_account(user.id)
    _clear_refresh_cookie(response)


@router.get("/me/export")
async def export_me(user: CurrentUser, auth_service: AuthServiceDep) -> dict[str, object]:
    return await auth_service.export_account_data(user.id)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(_auth_rate_limit)],
)
async def forgot_password(
    body: ForgotPasswordRequest, auth_service: AuthServiceDep
) -> MessageResponse:
    await auth_service.request_password_reset(body.email)
    return MessageResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest, auth_service: AuthServiceDep
) -> MessageResponse:
    await auth_service.reset_password(token=body.token, new_password=body.new_password)
    return MessageResponse(message="Your password has been reset.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest, auth_service: AuthServiceDep
) -> MessageResponse:
    await auth_service.verify_email(body.token)
    return MessageResponse(message="Your email has been verified.")


@router.get("/oauth/google/start", response_model=GoogleAuthorizationResponse)
async def google_oauth_start(
    auth_service: AuthServiceDep,
    redirect_uri: Annotated[str, Query()],
) -> GoogleAuthorizationResponse:
    url = await auth_service.start_google_oauth(redirect_uri=redirect_uri)
    return GoogleAuthorizationResponse(authorization_url=url)


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    auth_service: AuthServiceDep,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
) -> RedirectResponse:
    _, tokens = await auth_service.complete_google_oauth(code=code, state=state)
    settings = get_settings()
    response = RedirectResponse(url=settings.frontend_url, status_code=302)
    _set_refresh_cookie(response, tokens)
    return response
