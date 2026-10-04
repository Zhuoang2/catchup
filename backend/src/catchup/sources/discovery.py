"""Find a public feed from a feed URL or an HTML page."""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from catchup.net.safe_fetch import FetchError, FetchResponse, safe_fetch
from catchup.sources.feeds import Feed, FeedParseError, parse_feed

FEED_TYPES = ("application/rss+xml", "application/atom+xml")
COMMON_PATHS = ("/feed", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml")


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.feeds: list[str] = []
        self.is_article = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        if tag == "link" and "alternate" in (attrs_by_name.get("rel") or "").lower().split():
            if (attrs_by_name.get("type") or "").lower().split(";")[0].strip() in FEED_TYPES:
                if attrs_by_name.get("href"):
                    self.feeds.append(attrs_by_name["href"])
        if tag == "meta" and (attrs_by_name.get("property") or "").lower() == "og:type":
            self.is_article |= (attrs_by_name.get("content") or "").lower() == "article"


@dataclass(frozen=True)
class Discovery:
    feed: Feed
    follows_site_feed_notice: bool


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _probes(url: str) -> list[str]:
    parts = urlsplit(url)
    base = parts.path or "/"
    paths = [base.rstrip("/") + ".rss", base.rstrip("/") + "/.rss", *COMMON_PATHS]
    origin = _origin(url)
    return list(dict.fromkeys(origin + path for path in paths))[:8]


def discover(url: str) -> Discovery:
    response = safe_fetch(url)
    is_feed_type = response.content_type.lower().split(";")[0].strip() in FEED_TYPES
    try:
        feed = parse_feed(response)
        if feed.entries or is_feed_type:
            return Discovery(feed, False)
    except FeedParseError:
        if is_feed_type:
            raise FetchError("not_a_feed", "The URL did not return a parsable feed.") from None
    if is_feed_type:
        raise FetchError("not_a_feed", "The URL did not return a parsable feed.")
    if "html" not in response.content_type.lower() and not response.content.lstrip().lower().startswith(b"<!doctype html"):
        raise FetchError("not_a_feed", "The URL did not return a parsable feed.")

    links = _Links()
    links.feed(response.content.decode("utf-8", errors="replace"))
    deeper_page = urlsplit(response.url).path not in ("", "/")
    notice = links.is_article
    if links.feeds:
        for href in links.feeds:
            candidate = urljoin(response.url, href)
            try:
                return Discovery(parse_feed(safe_fetch(candidate)), notice)
            except (FetchError, FeedParseError):
                continue
        raise FetchError("not_a_feed", "The declared feed could not be parsed.")

    budget = [8]
    for candidate in _probes(response.url):
        if _origin(candidate) != _origin(response.url):
            continue
        if not budget[0]:
            break
        try:
            found = parse_feed(safe_fetch(candidate, same_origin=_origin(response.url), budget=budget))
            if found.entries:
                origin_level = urlsplit(candidate).path in COMMON_PATHS
                return Discovery(found, notice or (deeper_page and origin_level))
        except (FetchError, FeedParseError):
            continue
    raise FetchError("no_feed", "No supported feed was found at this URL.")
