import hashlib
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.redis import get_redis

USER_AGENT = "VeriHireBot/1.0 (+https://verihire.app/bot; job-posting-verification)"
FETCH_TIMEOUT_SECONDS = 8.0
MAX_REDIRECTS = 3
HTML_CACHE_TTL_SECONDS = 6 * 60 * 60
ROBOTS_CACHE_TTL_SECONDS = 24 * 60 * 60
MAX_BODY_BYTES = 3 * 1024 * 1024


class UnsafeUrlError(Exception):
    """Raised for anything that looks like an SSRF attempt or unsupported URL."""


class FetchBlockedByRobotsError(Exception):
    pass


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    status_code: int
    html: str
    content_hash: str
    from_cache: bool


def _reject_private_hosts(hostname: str) -> None:
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve host: {hostname}") from exc

    for _family, _, _, _, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeUrlError(f"Host {hostname} resolves to a disallowed address ({ip}).")


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Only http(s) URLs are supported.")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no host.")
    if parsed.hostname.lower() in ("localhost",):
        raise UnsafeUrlError("Localhost is not a permitted target.")
    _reject_private_hosts(parsed.hostname)
    return url


async def _is_allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    redis = get_redis()
    cache_key = f"robots:{parsed.netloc}"

    cached = await redis.get(cache_key)
    if cached is not None:
        robots_text = cached
    else:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
            robots_text = response.text if response.status_code == 200 else ""
        except httpx.HTTPError:
            robots_text = ""
        await redis.set(cache_key, robots_text, ex=ROBOTS_CACHE_TTL_SECONDS)

    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


async def fetch_url(url: str) -> FetchResult:
    """Robots-respecting, SSRF-guarded fetch with Redis caching (CLAUDE.md §9,
    Phase 3 task 4). Every redirect hop is re-validated against the same
    SSRF guard, since an attacker-controlled server could otherwise redirect
    a validated public URL to an internal address.
    """
    current_url = _validate_url(url)

    redis = get_redis()
    url_hash = hashlib.sha256(current_url.encode("utf-8")).hexdigest()
    cache_key = f"fetch:{url_hash}"
    cached_html = await redis.get(cache_key)
    if cached_html is not None:
        return FetchResult(
            final_url=current_url,
            status_code=200,
            html=cached_html,
            content_hash=hashlib.sha256(cached_html.encode("utf-8")).hexdigest(),
            from_cache=True,
        )

    if not await _is_allowed_by_robots(current_url):
        raise FetchBlockedByRobotsError(f"robots.txt disallows fetching {current_url}")

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=False
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            response = await client.get(current_url, headers={"User-Agent": USER_AGENT})

            if response.is_redirect:
                next_url = str(response.next_request.url) if response.next_request else None
                if not next_url:
                    break
                current_url = _validate_url(next_url)
                if not await _is_allowed_by_robots(current_url):
                    raise FetchBlockedByRobotsError(
                        f"robots.txt disallows fetching {current_url}"
                    )
                continue

            html = response.text[:MAX_BODY_BYTES]
            content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
            await redis.set(cache_key, html, ex=HTML_CACHE_TTL_SECONDS)
            return FetchResult(
                final_url=current_url,
                status_code=response.status_code,
                html=html,
                content_hash=content_hash,
                from_cache=False,
            )

    raise UnsafeUrlError("Too many redirects.")
