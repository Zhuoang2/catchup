"""Parse already-fetched feed bytes into stable, normalized entries."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

import feedparser

from catchup.net.safe_fetch import FetchResponse


class FeedParseError(Exception):
    pass


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []

    def handle_data(self, data: str) -> None:
        self.fragments.append(data)


def plain_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return " ".join(" ".join(parser.fragments).split())


def _entry_title(title: str, content_text: str) -> str:
    if title:
        return title
    if not content_text:
        return "Untitled"
    if len(content_text) <= 80:
        return content_text
    prefix = content_text[:80]
    if not prefix[-1].isspace() and not content_text[80].isspace():
        prefix = prefix.rsplit(" ", 1)[0] if " " in prefix else prefix
    return prefix.rstrip() + "…"


@dataclass(frozen=True)
class FeedEntry:
    identity_key: str
    link: str
    title: str
    published_at: datetime | None
    content_text: str


@dataclass(frozen=True)
class Feed:
    feed_url: str
    site_url: str
    title: str
    entries: list[FeedEntry]


def parse_feed(response: FetchResponse) -> Feed:
    parsed = feedparser.parse(response.content)
    if not parsed.version:
        raise FeedParseError("The content is not a parsable RSS or Atom feed.")
    entries = []
    for entry in parsed.entries:
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = datetime(*stamp[:6], tzinfo=timezone.utc) if stamp else None
        content = entry.get("content") or []
        description = content[0].get("value", "") if content else entry.get("summary", "")
        content_text = plain_text(description)
        title = _entry_title(plain_text(entry.get("title", "")), content_text)
        original_link = entry.get("link", "")
        try:
            parts = urlsplit(original_link)
            link = original_link if parts.scheme.lower() in ("http", "https") and parts.hostname else response.url
        except ValueError:
            link = response.url
        identity = entry.get("id") or (link if link != response.url else "")
        if not identity:
            identity = hashlib.sha256(f"{title}{published_at.isoformat() if published_at else ''}".encode()).hexdigest()
        entries.append(FeedEntry(
            identity_key=identity, link=link, title=title,
            published_at=published_at, content_text=content_text,
        ))
    site_url = parsed.feed.get("link") or f"{urlsplit(response.url).scheme}://{urlsplit(response.url).netloc}/"
    return Feed(
        feed_url=response.url, site_url=site_url,
        title=plain_text(parsed.feed.get("title", "")) or urlsplit(response.url).hostname or "Untitled feed",
        entries=entries,
    )
