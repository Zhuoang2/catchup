"""Fetch public HTTP URLs with DNS, redirect, timeout and body-size checks."""

import ipaddress
import socket
from dataclasses import dataclass
from time import monotonic
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
FETCH_DEADLINE_SECONDS = 30
NAT64_PREFIX = ipaddress.IPv6Network("64:ff9b::/96")


class FetchError(Exception):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


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
        if isinstance(address, ipaddress.IPv6Address) and address in NAT64_PREFIX:
            address = ipaddress.IPv4Address(address.packed[-4:])
        if (not address.is_global or address.is_private or address.is_loopback
                or address.is_link_local or address.is_reserved or address.is_multicast
                or address.is_unspecified):
            raise FetchError("blocked_address", "The source address is not allowed.")


def safe_fetch(url: str, *, same_origin: str | None = None, budget: list[int] | None = None) -> FetchResponse:
    current = url
    deadline = monotonic() + FETCH_DEADLINE_SECONDS

    def remaining(status_code: int | None = None) -> float:
        seconds = deadline - monotonic()
        if seconds <= 0:
            raise FetchError("fetch_failed", "The source fetch timed out.", status_code)
        return seconds

    with httpx.Client(follow_redirects=False, trust_env=False) as client:
        for hop in range(MAX_REDIRECTS + 1):
            remaining()
            parts = urlsplit(current)
            if same_origin is not None and f"{parts.scheme}://{parts.netloc}" != same_origin:
                raise FetchError("fetch_failed", "Feed probing must stay on the same origin.")
            _check_address(current)
            left = remaining()
            if budget is not None:
                if budget[0] <= 0:
                    raise FetchError("fetch_failed", "Feed probing request limit reached.")
                budget[0] -= 1
            status_code = None
            try:
                timeout = httpx.Timeout(
                    connect=min(5.0, left), read=min(15.0, left),
                    write=min(5.0, left), pool=min(5.0, left),
                )
                with client.stream("GET", current, timeout=timeout) as response:
                    status_code = response.status_code
                    remaining(status_code)
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError(
                                "fetch_failed", "The source returned a redirect without a destination.",
                                response.status_code,
                            )
                        if hop == MAX_REDIRECTS:
                            raise FetchError(
                                "fetch_failed", "The source redirected too many times.", response.status_code,
                            )
                        current = urljoin(current, location)
                        continue
                    response.raise_for_status()
                    length = response.headers.get("content-length")
                    if length:
                        try:
                            if int(length) > MAX_BYTES:
                                raise FetchError(
                                    "fetch_failed", "The source response exceeds the 5 MB limit.", status_code,
                                )
                        except ValueError:
                            raise FetchError(
                                "fetch_failed", "The source returned an invalid response size.", status_code,
                            ) from None
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        remaining(status_code)
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise FetchError(
                                "fetch_failed", "The source response exceeds the 5 MB limit.", status_code,
                            )
                    remaining(status_code)
                    return FetchResponse(
                        url=str(response.url), content=bytes(body),
                        content_type=response.headers.get("content-type", ""), status_code=response.status_code,
                    )
            except httpx.TimeoutException as exc:
                raise FetchError("fetch_failed", "The source fetch timed out.", status_code) from exc
            except httpx.HTTPStatusError as exc:
                raise FetchError(
                    "fetch_failed", "The source could not be fetched.", exc.response.status_code,
                ) from exc
            except httpx.HTTPError as exc:
                raise FetchError("fetch_failed", "The source could not be fetched.") from exc
    raise AssertionError("unreachable")
