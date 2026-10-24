"""Parse already-fetched feed bytes into stable, normalized entries."""

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

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


@dataclass(frozen=True)
class EntryLink:
    url: str
    text: str


@dataclass(frozen=True)
class EntryImage:
    url: str
    alt: str = ""
    caption: str = ""
    width: int | None = None
    height: int | None = None
    origin: str = "html"


def _dimension(value: object) -> int | None:
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return None


class _Images(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images: list[EntryImage] = []
        self.figures: list[tuple[list[int], list[str]]] = []
        self.in_caption = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "figure":
            self.figures.append(([], []))
        elif tag == "figcaption" and self.figures:
            self.in_caption = True
        elif tag == "img" and attrs_dict.get("src"):
            if self.figures:
                self.figures[-1][0].append(len(self.images))
            self.images.append(EntryImage(
                url=attrs_dict["src"] or "", alt=attrs_dict.get("alt") or "",
                width=_dimension(attrs_dict.get("width")), height=_dimension(attrs_dict.get("height")),
            ))

    def handle_data(self, data: str) -> None:
        if self.in_caption and self.figures:
            self.figures[-1][1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "figcaption":
            self.in_caption = False
        elif tag == "figure" and self.figures:
            indices, fragments = self.figures.pop()
            caption = " ".join(" ".join(fragments).split())
            for index in indices:
                image = self.images[index]
                self.images[index] = EntryImage(image.url, image.alt, caption, image.width, image.height)


def _entry_images(entry, description: str, base: str, channel_images: set[str]) -> tuple[EntryImage, ...]:
    parser = _Images()
    parser.feed(description)
    candidates = list(parser.images)
    for media in entry.get("media_content", []):
        if media.get("medium") == "image" or str(media.get("type", "")).lower().startswith("image/"):
            candidates.append(EntryImage(
                media.get("url", ""), width=_dimension(media.get("width")),
                height=_dimension(media.get("height")), origin="media",
            ))
    for media in entry.get("media_thumbnail", []):
        candidates.append(EntryImage(
            media.get("url", ""), width=_dimension(media.get("width")),
            height=_dimension(media.get("height")), origin="thumbnail",
        ))
    for media in entry.get("enclosures", []):
        if str(media.get("type", "")).lower().startswith("image/"):
            candidates.append(EntryImage(media.get("href") or media.get("url", ""), origin="enclosure"))
    return filter_image_urls(candidates, base, channel_images)


def filter_image_urls(
    candidates: list[EntryImage], base: str = "", excluded: set[str] | None = None,
) -> tuple[EntryImage, ...]:
    """Keep at most eight safe image addresses, preserving feed candidate order."""
    result: list[EntryImage] = []
    seen: set[str] = set()
    for image in candidates:
        url = urljoin(base, image.url.strip())
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if (parts.scheme.lower() not in ("http", "https") or not parts.hostname
                or "/avatar/" in parts.path.lower() or "/blavatar/" in parts.path.lower()
                or (image.width is not None and image.height is not None
                    and image.width <= 1 and image.height <= 1)
                or url in (excluded or ())):
            continue
        key = parts._replace(fragment="").geturl()
        if key in seen:
            continue
        seen.add(key)
        result.append(EntryImage(url, image.alt, image.caption, image.width, image.height, image.origin))
        if len(result) == 8:
            break
    return tuple(result)


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


class _Links(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.links: list[EntryLink] = []
        self.seen: set[str] = set()
        self.href: str | None = None
        self.fragments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.fragments = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href is not None:
            url = urljoin(self.base, self.href)
            if url not in self.seen:
                self.links.append(EntryLink(url, " ".join(" ".join(self.fragments).split())))
                self.seen.add(url)
            self.href = None


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
    trimmed = prefix.rstrip(" .…。．⋯")
    if not trimmed:
        trimmed = content_text[:80].rstrip(" .…。．⋯")
    return trimmed + "…"


@dataclass(frozen=True)
class FeedEntry:
    identity_key: str
    link: str
    title: str
    published_at: datetime | None
    content_text: str
    has_audio: bool = False
    transcripts: tuple[TranscriptCandidate, ...] = ()
    links: tuple[EntryLink, ...] = ()
    comments_url: str | None = None
    comment_feed_url: str | None = None
    comment_count: int | None = None
    author: str | None = None
    images: tuple[EntryImage, ...] = ()


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
    channel_images = {
        url for field in ("image", "icon", "logo")
        if (value := parsed.feed.get(field))
        for url in ([value] if isinstance(value, str) else
                    [value.get("href") or value.get("url", "")] if isinstance(value, dict) else [])
    }
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
        links_parser = _Links(link)
        links_parser.feed(description)
        try:
            comment_count = int(entry["slash_comments"]) if entry.get("slash_comments") is not None else None
        except (ValueError, TypeError):
            comment_count = None
        entries.append(FeedEntry(
            identity_key=identity, link=link, title=title,
            published_at=published_at, content_text=content_text, has_audio=has_audio,
            transcripts=ordered_candidates(candidates, language),
            links=tuple(links_parser.links),
            comments_url=entry.get("comments") or None,
            comment_feed_url=entry.get("wfw_commentrss") or None,
            comment_count=comment_count,
            author=entry.get("author") or None,
            images=() if has_audio else _entry_images(entry, description, link, channel_images),
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
