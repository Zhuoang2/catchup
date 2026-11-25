"""Read Bilibili uploaders and inline subtitles only through the operator's RSSHub."""

import base64
import binascii
import json
import re
from datetime import datetime, timezone
from urllib.parse import unquote_to_bytes, urlsplit

from catchup.config import Settings
from catchup.errors import AppError
from catchup.net.bilibili_hosts import is_bilibili_host
from catchup.net.safe_fetch import FetchError, FetchResponse, safe_fetch
from catchup.sources.feeds import Feed, FeedEntry, FeedParseError, _entry_title, plain_text
from catchup.transcripts.convert import convert_transcript

NOT_UPLOADER_MESSAGE = "Paste the uploader's space address, such as https://space.bilibili.com/2267573."
NOT_CONFIGURED_MESSAGE = (
    "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README."
)
FAILED_MESSAGE = "RSSHub could not read this uploader."


def _origin(parts) -> tuple[str, str, int]:
    return (parts.scheme.lower(), (parts.hostname or "").lower().rstrip("."),
            parts.port or (443 if parts.scheme.lower() == "https" else 80))


def uploader_mid(url: str, rsshub_url: str | None) -> str | None:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        if is_bilibili_host(host):
            match = None
            if parts.scheme in ("http", "https") and parts.username is None and parts.password is None:
                if host == "space.bilibili.com":
                    match = re.fullmatch(r"/([0-9]{1,20})(?:/.*)?", parts.path)
                elif host == "m.bilibili.com":
                    match = re.fullmatch(r"/space/([0-9]{1,20})(?:/.*)?", parts.path)
            if match:
                return match[1]
            raise AppError("not_a_bilibili_uploader", NOT_UPLOADER_MESSAGE, 422)
        if rsshub_url:
            base = urlsplit(rsshub_url)
            if _origin(parts) == _origin(base):
                match = re.fullmatch(
                    re.escape(base.path.rstrip("/")) + r"/bilibili/user/video/([0-9]{1,20})(?:/[^/]+)?/?",
                    parts.path,
                )
                if match:
                    return match[1]
    except ValueError:
        return None
    return None


def fetch_uploader(mid: str, settings: Settings, *, spacer=None) -> FetchResponse:
    if not settings.rsshub_url:
        raise FetchError("rsshub_not_configured", NOT_CONFIGURED_MESSAGE)
    parts = urlsplit(settings.rsshub_url)
    try:
        return safe_fetch(
            f"{settings.rsshub_url}/bilibili/user/video/{mid}?format=json",
            private_origin=f"{parts.scheme}://{parts.netloc}",
            max_bytes=settings.max_feed_bytes, spacer=spacer,
        )
    except FetchError as exc:
        if exc.code != "fetch_failed":
            raise
        message = (f"RSSHub could not read this uploader (HTTP {exc.status_code})."
                   if exc.status_code is not None else FAILED_MESSAGE)
        raise FetchError("rsshub_failed", message, exc.status_code) from exc


def _subtitles(attachments: list) -> str | None:
    for attachment in attachments:
        if not isinstance(attachment, dict) or attachment.get("mime_type") != "text/srt":
            continue
        url = attachment.get("url", "")
        if not isinstance(url, str) or not url.startswith("data:"):
            continue
        media, separator, data = url.partition(",")
        if not separator:
            return None
        try:
            body = unquote_to_bytes(data)
            if media.endswith(";base64"):
                body = base64.b64decode(body, validate=True)
            return convert_transcript(body, "text/srt")
        except (ValueError, binascii.Error):
            return None
    return None


def parse_uploader_feed(response: FetchResponse, mid: str) -> Feed:
    try:
        data = json.loads(response.content)
    except (ValueError, UnicodeError) as exc:
        raise FeedParseError(FAILED_MESSAGE) from exc
    if (not isinstance(data, dict) or not isinstance(data.get("version"), str)
            or not data["version"].startswith("https://jsonfeed.org/version/")
            or not isinstance(data.get("items"), list)):
        raise FeedParseError(FAILED_MESSAGE)
    items = data["items"]
    title = plain_text(data.get("title") or "").removesuffix(" 的 bilibili 空间")
    if not title and items and isinstance(items[0], dict):
        authors = items[0].get("authors") or []
        if authors and isinstance(authors[0], dict):
            title = authors[0].get("name") or ""
    entries = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        try:
            match = re.fullmatch(r"/video/(BV[A-Za-z0-9]+|av[0-9]+)/?", urlsplit(item["url"]).path)
        except ValueError:
            continue
        if not match:
            continue
        try:
            published_at = datetime.fromisoformat(item.get("date_published", ""))
            published_at = published_at.replace(tzinfo=timezone.utc) if published_at.tzinfo is None else published_at
        except (ValueError, TypeError):
            published_at = None
        text = plain_text(item.get("content_html") or "")
        entries.append(FeedEntry(
            identity_key=f"bilibili:video:{match[1]}", link=item["url"],
            title=_entry_title(plain_text(item.get("title") or ""), text),
            published_at=published_at, content_text=text,
            transcript_text=_subtitles(item.get("attachments") or []),
        ))
    return Feed(
        feed_url=f"bilibili:uploader:{mid}", site_url=f"https://space.bilibili.com/{mid}",
        title=title or f"Bilibili uploader {mid}", entries=entries, source_kind="bilibili",
    )
