"""Fixed-host X API transport for the user's own Bearer token."""

from datetime import datetime, timezone
import json
from math import ceil

import httpx

from catchup.net.safe_fetch import MAX_BYTES, RATE_LIMIT_PREFIX, user_agent


class XApiError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None,
                 retry_after: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.retry_after = retry_after


class XClient:
    def __init__(self, token: str):
        self._client = httpx.Client(
            base_url="https://api.x.com", follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(15, connect=5),
            headers={"Authorization": f"Bearer {token}", "User-Agent": user_agent()},
        )

    def __enter__(self) -> "XClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, path: str, params: dict | None = None) -> dict:
        try:
            with self._client.stream("GET", path, params=params) as response:
                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise XApiError("fetch_failed", "X returned too much data.", response.status_code)
                    chunks.append(chunk)
                if response.status_code in (401, 403):
                    raise XApiError("x_token_rejected", "X rejected the token.", response.status_code)
                if response.status_code == 429:
                    try:
                        delay = max(1, ceil(int(response.headers["x-rate-limit-reset"]) -
                                            datetime.now(timezone.utc).timestamp()))
                    except (KeyError, ValueError):
                        delay = 1
                    raise XApiError("rate_limited", f"{RATE_LIMIT_PREFIX} Try again later.",
                                    response.status_code, delay)
                if response.status_code >= 400:
                    raise XApiError("fetch_failed", "X could not complete the request.", response.status_code)
                try:
                    return json.loads(b"".join(chunks))
                except ValueError as exc:
                    raise XApiError("fetch_failed", "X returned an invalid answer.", response.status_code) from exc
        except httpx.HTTPError as exc:
            raise XApiError("fetch_failed", "Could not reach X.") from exc

    def usage(self) -> None:
        self._request("/2/usage/tweets", {"days": 1})
