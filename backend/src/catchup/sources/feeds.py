"""Parse already-fetched feed bytes into stable, normalized entries."""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

import feedparser
from lxml import etree

from catchup.net.safe_fetch import FetchResponse


class FeedParseError(Exception):
    pass


PODCAST_NAMESPACE = "https://podcastindex.org/namespace/1.0"
TRANSCRIPT_TYPES = {
    "text/plain": 0, "text/vtt": 1, "application/x-subrip": 2,
    "application/srt": 2, "application/json": 3, "text/html": 4,
}


@dataclass(frozen=True)
class TranscriptCandidate:
    url: str
    type: str = ""
    language: str = ""
    rel: str = ""


def ordered_candidates(candidates: tuple[TranscriptCandidate, ...],
                       language: str = "") -> tuple[TranscriptCandidate, ...]:
    primary = language.split("-", 1)[0].lower()
    return tuple(sorted(candidates, key=lambda candidate: (
        TRANSCRIPT_TYPES.get(candidate.type.lower().split(";")[0].strip(), 5),
        (candidate.language or language).split("-", 1)[0].lower() != primary if primary else False,
    )))


def _transcript_candidates(body: bytes) -> dict[str, tuple[TranscriptCandidate, ...]]:
    """Read podcast transcripts without network access or internal DTD entities."""
    try:
        parser = etree.XMLParser(recover=True, resolve_entities=False, no_network=True, load_dtd=False)
        root = etree.fromstring(body.lstrip(b"\xef\xbb\xbf \t\r\n"), parser=parser)
        if root is None:
            return {}
        # libxml can expand internal entities in attributes even with
        # resolve_entities=False, so discard candidates after parsing such a DTD.
        internal_dtd = root.getroottree().docinfo.internalDTD
        if internal_dtd is not None and any(internal_dtd.iterentities()):
            return {}
        found: dict[str, tuple[TranscriptCandidate, ...]] = {}
        for item in root.iter():
            if not isinstance(item.tag, str) or etree.QName(item).localname != "item":
                continue
            guid = link = ""
            candidates = []
            for child in item:
                if not isinstance(child.tag, str):
                    continue
                name = etree.QName(child)
                if name.localname == "guid":
                    guid = (child.text or "").strip()
                elif name.localname == "link":
                    link = (child.text or "").strip()
                elif name.localname == "transcript" and name.namespace and (
                    name.namespace == PODCAST_NAMESPACE or child.prefix == "podcast"
                ):
                    if child.get("url"):
                        candidates.append(TranscriptCandidate(
                            url=child.get("url", ""), type=child.get("type", ""),
                            language=child.get("language", ""), rel=child.get("rel", ""),
                        ))
            if candidates and (guid or link):
                found[guid or link] = tuple(candidates)
                if guid and link:
                    found[link] = tuple(candidates)
        return found
    except (etree.LxmlError, ValueError, TypeError):
        return {}


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


def is_short(link: str) -> bool:
    return urlsplit(link).path.startswith("/shorts/")


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
    has_audio: bool = False
    transcripts: tuple[TranscriptCandidate, ...] = ()


@dataclass(frozen=True)
class Feed:
    feed_url: str
    site_url: str
    title: str
    entries: list[FeedEntry]
    youtube_host: bool = False
    audio_share: float = 0.0

    @property
    def shared_links(self) -> set[str]:
        counts = Counter(entry.link for entry in self.entries if entry.link != self.feed_url)
        return {link for link, count in counts.items() if count > 1}

    @property
    def kind(self) -> str:
        if self.youtube_host:
            return "youtube"
        if self.audio_share > 0.5:
            return "podcast"
        return "feed"


def parse_feed(response: FetchResponse) -> Feed:
    parsed = feedparser.parse(response.content)
    if not parsed.version:
        raise FeedParseError("The content is not a parsable RSS or Atom feed.")
    transcript_candidates = _transcript_candidates(response.content)
    language = parsed.feed.get("language", "")
    raw_links = [entry.get("link", "") for entry in parsed.entries]
    shared_links = {link for link, count in Counter(raw_links).items() if link and count > 1}
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
        identity = entry.get("id") or (link if link != response.url and original_link not in shared_links else "")
        if not identity:
            identity = hashlib.sha256(f"{title}{published_at.isoformat() if published_at else ''}".encode()).hexdigest()
        guid = entry.get("id")
        candidates = (transcript_candidates.get(guid, ()) if guid else
                      transcript_candidates.get(original_link, ()) if original_link not in shared_links else ())
        if not candidates and (fallback := entry.get("podcast_transcript")):
            if isinstance(fallback, dict) and fallback.get("url"):
                candidates = (TranscriptCandidate(
                    url=fallback["url"], type=fallback.get("type", ""),
                    language=fallback.get("language", ""), rel=fallback.get("rel", ""),
                ),)
        has_audio = any(str(enclosure.get("type", "")).lower().startswith("audio/")
                        for enclosure in entry.get("enclosures", []))
        entries.append(FeedEntry(
            identity_key=identity, link=link, title=title,
            published_at=published_at, content_text=content_text, has_audio=has_audio,
            transcripts=ordered_candidates(candidates, language),
        ))
    site_url = parsed.feed.get("link") or f"{urlsplit(response.url).scheme}://{urlsplit(response.url).netloc}/"
    parts = urlsplit(response.url)
    return Feed(
        feed_url=response.url, site_url=site_url,
        title=plain_text(parsed.feed.get("title", "")) or urlsplit(response.url).hostname or "Untitled feed",
        entries=entries,
        youtube_host=parts.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}
        and parts.path == "/feeds/videos.xml",
        audio_share=sum(entry.has_audio for entry in entries) / len(entries) if entries else 0.0,
    )
