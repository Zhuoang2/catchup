"""Source preview, confirmation, listing and deletion."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from catchup.collection import article_text
from catchup.db import get_session
from catchup.errors import AppError
from catchup.models import Item, Source, SourceCheck, utc_now
from catchup.net.safe_fetch import FetchError, safe_fetch
from catchup.sources.discovery import discover
from catchup.sources.feeds import FeedParseError, parse_feed

router = APIRouter(prefix="/api/sources")


class PreviewInput(BaseModel):
    url: str


class ConfirmInput(BaseModel):
    feed_url: str


def _fetch_error(exc: FetchError) -> AppError:
    return AppError(exc.code, str(exc), 422)


def _existing(feed_url: str, session: Session) -> Source | None:
    return session.scalar(select(Source).where(Source.feed_url == feed_url))


def _duplicate(source: Source, status_code: int) -> AppError:
    return AppError(
        "duplicate", f"Already following {source.title}.", status_code,
        existing_source={"id": source.id, "title": source.title, "feed_url": source.feed_url},
    )


def _unique_entries(feed):
    seen_keys: set[str] = set()
    seen_links: set[str] = set()
    for entry in feed.entries:
        if entry.identity_key in seen_keys or (entry.link != feed.feed_url and entry.link in seen_links):
            continue
        seen_keys.add(entry.identity_key)
        if entry.link != feed.feed_url:
            seen_links.add(entry.link)
        yield entry


@router.post("/preview")
def preview(data: PreviewInput, session: Session = Depends(get_session)) -> dict:
    try:
        found = discover(data.url.strip())
    except FetchError as exc:
        raise _fetch_error(exc) from exc
    duplicate = _existing(found.feed.feed_url, session)
    if duplicate:
        raise _duplicate(duplicate, 422)
    recent = sorted(
        found.feed.entries,
        key=lambda entry: entry.published_at.timestamp() if entry.published_at else float("-inf"),
        reverse=True,
    )
    return {
        "feed_url": found.feed.feed_url,
        "site_url": found.feed.site_url,
        "title": found.feed.title,
        "follows_site_feed_notice": found.follows_site_feed_notice,
        "entries": [
            {"title": entry.title, "link": entry.link, "published_at": entry.published_at}
            for entry in recent[:5]
        ],
    }


@router.post("", status_code=201)
def confirm(data: ConfirmInput, request: Request, session: Session = Depends(get_session)) -> dict:
    try:
        feed = parse_feed(safe_fetch(data.feed_url.strip()))
    except FetchError as exc:
        raise _fetch_error(exc) from exc
    except FeedParseError as exc:
        raise AppError("not_a_feed", str(exc), 422) from exc
    duplicate = _existing(feed.feed_url, session)
    if duplicate:
        raise _duplicate(duplicate, 409)

    now = utc_now()
    settings = request.app.state.settings
    lookback = now - timedelta(days=settings.first_add_days)
    entries = list(_unique_entries(feed))
    recent = [entry for entry in entries if entry.published_at and lookback <= entry.published_at <= now]
    selected = {entry.identity_key for entry in sorted(
        recent, key=lambda entry: entry.published_at, reverse=True,
    )[:settings.first_add_max]}
    source = Source(
        title=feed.title, site_url=feed.site_url, feed_url=feed.feed_url, input_url=data.feed_url,
        created_at=now, last_check_at=now, last_check_status="no_new_items",
    )
    session.add(source)
    session.flush()
    pending_count = 0
    for entry in entries:
        state = "pending" if entry.identity_key in selected else "baseline"
        pending_count += state == "pending"
        text, origin = (
            article_text(entry, {feed.feed_url}, settings.short_text_chars)
            if state == "pending" else (entry.content_text, "feed")
        )
        session.add(Item(
            source_id=source.id, identity_key=entry.identity_key, link=entry.link,
            title=entry.title, published_at=entry.published_at, discovered_at=now,
            content_text=text, content_origin=origin, state=state,
        ))
    source.last_check_status = "new_items" if pending_count else "no_new_items"
    session.add(SourceCheck(
        source_id=source.id, run_id=None, status=source.last_check_status,
        possible_gap=False, error=None, http_status=200, entries_seen=len(feed.entries),
        new_count=pending_count, checked_at=now,
    ))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        duplicate = _existing(feed.feed_url, session)
        if duplicate:
            raise _duplicate(duplicate, 409) from exc
        raise
    return {
        "id": source.id, "title": source.title, "site_url": source.site_url,
        "feed_url": source.feed_url, "last_check_at": source.last_check_at,
        "last_check_status": source.last_check_status, "possible_gap": False,
    }


@router.get("")
def list_sources(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(Source).order_by(Source.id)).all()
    result = []
    for source in rows:
        last = session.scalar(
            select(SourceCheck).where(SourceCheck.source_id == source.id)
            .order_by(SourceCheck.checked_at.desc(), SourceCheck.id.desc()).limit(1),
        )
        result.append({
            "id": source.id, "title": source.title, "feed_url": source.feed_url,
            "site_url": source.site_url, "last_check_at": last.checked_at if last else source.last_check_at,
            "last_check_status": last.status if last else source.last_check_status,
            "possible_gap": last.possible_gap if last else False,
        })
    return result


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, session: Session = Depends(get_session)) -> None:
    source = session.get(Source, source_id)
    if source is None:
        raise AppError("not_found", "Source not found.", 404)
    session.delete(source)
    session.commit()
