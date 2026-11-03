"""Parse addresses from feeds and pages that may be malformed, without raising."""

from urllib.parse import SplitResult, urljoin, urlsplit


def join_url(base: str, href: str) -> str | None:
    """Join like ``urljoin``, or give ``None`` when the address cannot be parsed."""
    try:
        return urljoin(base, href)
    except ValueError:
        return None


def split_url(url: str) -> SplitResult | None:
    """Split like ``urlsplit``, or give ``None`` when the address cannot be parsed."""
    try:
        return urlsplit(url)
    except ValueError:
        return None
