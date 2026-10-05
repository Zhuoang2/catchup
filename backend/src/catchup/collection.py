"""Collect unseen feed entries for one source and record the check outcome."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session
from trafilatura import extract

from catchup.config import Settings
from catchup.models import Item, Source, SourceCheck, utc_now
from catchup.net.host_spacing import HostSpacer
from catchup.net.safe_fetch import FetchError, safe_fetch
from catchup.sources.feeds import FeedEntry, FeedParseError, is_short, parse_feed
from catchup.transcripts.context import TranscriptContext
from catchup.transcripts.convert import convert_transcript

logger = logging.getLogger(__name__)


def _resolve_episode(item: Item, entry: FeedEntry, spacer: HostSpacer | None) -> None:
    if not entry.has_audio:
        return
    item.transcript_status = "waiting"
    for candidate in entry.transcripts[:2]:
        try:
            body = safe_fetch(candidate.url, spacer=spacer).content
            text = convert_transcript(body, candidate.type)
            if text:
                item.content_text = text
                item.content_origin = "transcript"
                item.summary = None
                item.summary_language = None
                item.transcript_status = "found"
                return
        except Exception as exc:
            logger.warning("Transcript unavailable for item %s (%s)", item.id, type(exc).__name__)


def article_text(entry: FeedEntry, fallback_links: set[str], threshold: int,
                 *, spacer: HostSpacer | None = None) -> tuple[str, str]:
    if len(entry.content_text) >= threshold or entry.link in fallback_links:
        return entry.content_text, "feed"
    try:
        response = safe_fetch(entry.link, spacer=spacer)
    except FetchError:
        return entry.content_text, "feed"
    try:
        text = extract(response.content, url=response.url)
        if text and text.strip():
            return text.strip(), "article"
    except Exception:
        # Extraction failures must not turn a successful feed check into a failure.
        pass
    return entry.content_text, "feed"


def check_source(session: Session, source: Source, run_id: int, settings: Settings,
                 *, spacer: HostSpacer | None = None,
                 transcripts: TranscriptContext | None = None) -> SourceCheck:
    """Check one saved source; persist its items and outcome in one transaction."""
    try:
        response = safe_fetch(source.feed_url, spacer=spacer, max_bytes=settings.max_feed_bytes)
        feed = parse_feed(response)
    except (FetchError, FeedParseError) as exc:
        now = utc_now()
        check = SourceCheck(
            run_id=run_id, source_id=source.id, status="failed", possible_gap=False,
            error=str(exc), http_status=exc.status_code if isinstance(exc, FetchError) else response.status_code,
            entries_seen=0, new_count=0, checked_at=now,
        )
        source.last_check_at = now
        source.last_check_status = check.status
        session.add(check)
        session.commit()
        return check

    if source.kind == "feed" and feed.kind != "feed":
        source.kind = feed.kind

    existing_items = session.scalars(select(Item).where(Item.source_id == source.id)).all()
    keys = {item.identity_key for item in existing_items}
    by_key = {item.identity_key: item for item in existing_items}
    fallback_links = {source.feed_url, feed.feed_url} | feed.shared_links
    links = {item.link for item in existing_items if item.link not in fallback_links}
    matched_previous = any(
        entry.identity_key in keys or (entry.link not in fallback_links and entry.link in links)
        for entry in feed.entries
    )
    seen_keys = keys.copy()
    seen_links = links.copy()
    new_count = 0
    now = utc_now()
    for entry in feed.entries:
        if source.kind == "podcast" and (prior := by_key.get(entry.identity_key)) is not None:
            if prior.state == "pending" and prior.transcript_status in ("to_fetch", "waiting", None):
                if entry.has_audio:
                    _resolve_episode(prior, entry, spacer)
                else:
                    prior.content_text, prior.content_origin = article_text(
                        entry, fallback_links, settings.short_text_chars, spacer=spacer,
                    )
                    prior.transcript_status = "text"
                    prior.summary = None
                    prior.summary_language = None
        if entry.identity_key in seen_keys or (entry.link not in fallback_links and entry.link in seen_links):
            continue
        transcript_status = ("to_fetch" if source.kind == "youtube" or
                             (source.kind == "podcast" and entry.has_audio) else
                             "text" if source.kind == "podcast" else None)
        text, origin = (
            article_text(entry, fallback_links, settings.short_text_chars, spacer=spacer)
            if transcript_status in (None, "text") else (entry.content_text, "feed")
        )
        skip_shorts = transcripts.youtube_skip_shorts if transcripts else True
        state = ("baseline" if source.kind == "youtube" and skip_shorts and is_short(entry.link)
                 else "pending")
        item = Item(
            source_id=source.id, identity_key=entry.identity_key, link=entry.link,
            title=entry.title, published_at=entry.published_at, discovered_at=now,
            content_text=text, content_origin=origin, state=state,
            transcript_status=transcript_status,
        )
        session.add(item)
        if source.kind == "podcast" and entry.has_audio:
            session.flush()
            _resolve_episode(item, entry, spacer)
        seen_keys.add(entry.identity_key)
        if entry.link not in fallback_links:
            seen_links.add(entry.link)
        new_count += 1

    check = SourceCheck(
        run_id=run_id, source_id=source.id, status="new_items" if new_count else "no_new_items",
        possible_gap=bool(existing_items) and not matched_previous, error=None,
        http_status=response.status_code, entries_seen=len(feed.entries),
        new_count=new_count, checked_at=now,
    )
    source.last_check_at = now
    source.last_check_status = check.status
    session.add(check)
    session.commit()
    return check
