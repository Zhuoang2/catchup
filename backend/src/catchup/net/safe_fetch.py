"""Fetch public HTTP URLs with DNS, redirect, timeout and body-size checks."""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5


class FetchError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FetchResponse:
    url: str
    content: bytes
    content_type: str
    status_code: int


def _check_address(url: str) -> None:
    try:
        parts = urlsplit(url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ValueError("invalid URL")
    except ValueError as exc:
        raise FetchError("invalid_url", "Enter a valid public HTTP or HTTPS URL.") from exc

    try:
        answers = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise FetchError("fetch_failed", "The source host could not be resolved.") from exc
    if not answers:
        raise FetchError("fetch_failed", "The source host could not be resolved.")
    for answer in answers:
        try:
            address = ipaddress.ip_address(answer[4][0])
        except ValueError as exc:
            raise FetchError("blocked_address", "The source address is not allowed.") from exc
        if (not address.is_global or address.is_private or address.is_loopback
                or address.is_link_local or address.is_reserved or address.is_multicast
                or address.is_unspecified):
            raise FetchError("blocked_address", "The source address is not allowed.")


def safe_fetch(url: str, *, same_origin: str | None = None, budget: list[int] | None = None) -> FetchResponse:
    current = url
    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        for hop in range(MAX_REDIRECTS + 1):
            parts = urlsplit(current)
            if same_origin is not None and f"{parts.scheme}://{parts.netloc}" != same_origin:
                raise FetchError("fetch_failed", "Feed probing must stay on the same origin.")
            _check_address(current)
            if budget is not None:
                if budget[0] <= 0:
                    raise FetchError("fetch_failed", "Feed probing request limit reached.")
                budget[0] -= 1
            try:
                with client.stream("GET", current) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("fetch_failed", "The source returned a redirect without a destination.")
                        if hop == MAX_REDIRECTS:
                            raise FetchError("fetch_failed", "The source redirected too many times.")
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    length = response.headers.get("content-length")
                    if length:
                        try:
                            if int(length) > MAX_BYTES:
                                raise FetchError("fetch_failed", "The source response exceeds the 5 MB limit.")
                        except ValueError:
                            raise FetchError("fetch_failed", "The source returned an invalid response size.") from None
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise FetchError("fetch_failed", "The source response exceeds the 5 MB limit.")
                    return FetchResponse(
                        url=str(response.url), content=bytes(body),
                        content_type=response.headers.get("content-type", ""), status_code=response.status_code,
                    )
            except httpx.TimeoutException as exc:
                raise FetchError("fetch_failed", "The source fetch timed out.") from exc
            except httpx.HTTPError as exc:
                raise FetchError("fetch_failed", "The source could not be fetched.") from exc
    raise AssertionError("unreachable")
