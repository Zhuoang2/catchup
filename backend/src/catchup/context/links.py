"""Keep related body links without navigation and login destinations."""

from urllib.parse import urlsplit

from catchup.sources.feeds import EntryLink
from catchup.net.urls import split_url
from catchup.net.x_hosts import is_x_host


TAXONOMY = {"tag", "tags", "category", "categories", "author", "page", "search", "archive"}
MEDIA = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".pdf")


def _site_host(host: str) -> str:
    return host.removeprefix("www.")


def related_links(item_link: str, site_url: str, links: list[EntryLink] | tuple[EntryLink, ...],
                  limit: int) -> list[EntryLink]:
    # An address that cannot be parsed matches nothing.
    item = split_url(item_link)
    own = (item.scheme.lower(), item.netloc.lower(), item.path.rstrip("/")) if item is not None else None
    site = split_url(site_url)
    site_host = _site_host(site.hostname or "") if site is not None else ""
    chosen = []
    for link in links:
        try:
            parts = urlsplit(link.url)
            host = (parts.hostname or "").lower()
            path = parts.path.lower()
            if parts.scheme.lower() not in ("http", "https") or not host:
                continue
            if (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/")) == own:
                continue
            if _site_host(host) == site_host and path.lstrip("/").split("/", 1)[0] in TAXONOMY:
                continue
            video_host = _site_host(host).removeprefix("m.")
            if (is_x_host(host)
                    or video_host == "youtube.com" and path == "/watch"
                    or video_host == "youtu.be"
                    or video_host == "vimeo.com" and path.strip("/").split("/", 1)[0].isdigit()
                    or host == "claude.ai" and path.startswith("/code/")
                    or host == "chatgpt.com" and path.startswith("/share/")
                    or path.startswith("/login") or path == "/share" and bool(parts.query)
                    or path.endswith(MEDIA)):
                continue
            chosen.append(link)
            if len(chosen) >= limit:
                break
        except ValueError:
            continue
    return chosen
