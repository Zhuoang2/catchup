"""Collect unseen feed entries for one source and record the check outcome."""

from sqlalchemy import select
from sqlalchemy.orm import Session
from trafilatura import extract

from catchup.config import Settings
from catchup.models import Item, Source, SourceCheck, utc_now
from catchup.net.safe_fetch import FetchError, safe_fetch
from catchup.sources.feeds import FeedEntry, FeedParseError, parse_feed


def article_text(entry: FeedEntry, fallback_links: set[str], threshold: int) -> tuple[str, str]:
    if len(entry.content_text) >= threshold or entry.link in fallback_links:
        return entry.content_text, "feed"
    try:
        response = safe_fetch(entry.link)
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


def check_source(session: Session, source: Source, run_id: int, settings: Settings) -> SourceCheck:
    """Check one saved source; persist its items and outcome in one transaction."""
    try:
        response = safe_fetch(source.feed_url)
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

    existing = session.execute(
        select(Item.identity_key, Item.link).where(Item.source_id == source.id),
    ).all()
    keys = {key for key, _ in existing}
    fallback_links = {source.feed_url, feed.feed_url}
    links = {link for _, link in existing if link not in fallback_links}
    matched_previous = any(
        entry.identity_key in keys or (entry.link not in fallback_links and entry.link in links)
        for entry in feed.entries
    )
    seen_keys = keys.copy()
    seen_links = links.copy()
    new_count = 0
    now = utc_now()
    for entry in feed.entries:
        if entry.identity_key in seen_keys or (entry.link not in fallback_links and entry.link in seen_links):
            continue
        text, origin = article_text(entry, fallback_links, settings.short_text_chars)
        session.add(Item(
            source_id=source.id, identity_key=entry.identity_key, link=entry.link,
            title=entry.title, published_at=entry.published_at, discovered_at=now,
            content_text=text, content_origin=origin, state="pending",
        ))
        seen_keys.add(entry.identity_key)
        if entry.link not in fallback_links:
            seen_links.add(entry.link)
        new_count += 1

    check = SourceCheck(
        run_id=run_id, source_id=source.id, status="new_items" if new_count else "no_new_items",
        possible_gap=bool(existing) and not matched_previous, error=None,
        http_status=response.status_code, entries_seen=len(feed.entries),
        new_count=new_count, checked_at=now,
    )
    source.last_check_at = now
    source.last_check_status = check.status
    session.add(check)
    session.commit()
    return check
