"""Bilibili hosts that CatchUp must never request."""


def is_bilibili_host(host: str | None) -> bool:
    host = (host or "").lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain)
               for domain in ("bilibili.com", "b23.tv", "hdslb.com", "bilivideo.com"))
