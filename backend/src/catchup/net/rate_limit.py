"""Interpret stored source-check rate limits without changing check outcomes."""

from catchup.models import SourceCheck
from catchup.net.safe_fetch import RATE_LIMIT_PREFIX


def is_rate_limited(check: SourceCheck | None) -> bool:
    return bool(check and (check.http_status == 429 or (
        check.http_status == 503 and (check.error or "").startswith(RATE_LIMIT_PREFIX)
    )))
