"""Recognize X-owned hosts, including subdomains and fully qualified names."""


def is_x_host(host: str | None) -> bool:
    host = host.lower().removesuffix(".") if host else ""
    return any(host == domain or host.endswith("." + domain)
               for domain in ("x.com", "twitter.com"))
