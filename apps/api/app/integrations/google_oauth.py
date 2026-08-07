from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuthError(Exception):
    pass


def build_authorization_url(*, state: str, code_challenge: str, redirect_uri: str) -> str:
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise GoogleOAuthError("Google OAuth client ID is not configured.")

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


async def exchange_code_for_userinfo(
    *, code: str, code_verifier: str, redirect_uri: str
) -> dict[str, Any]:
    """Exchanges an authorization code for tokens, then fetches the profile.

    Raises GoogleOAuthError on any failure — network, bad code, or Google
    returning an unverified email — so the caller always deals with one
    exception type regardless of where the flow broke.
    """
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise GoogleOAuthError("Google OAuth is not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_response = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret.get_secret_value(),
                    "code": code,
                    "code_verifier": code_verifier,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json()["access_token"]

            userinfo_response = await client.get(
                USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleOAuthError(f"Google OAuth exchange failed: {exc}") from exc

    userinfo: dict[str, Any] = userinfo_response.json()

    if not userinfo.get("email_verified"):
        raise GoogleOAuthError("Google account email is not verified.")

    return userinfo
