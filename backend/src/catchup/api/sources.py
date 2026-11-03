"""Source preview, confirmation, listing and deletion."""

import re
from datetime import timedelta
from dataclasses import asdict
from contextlib import closing

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from catchup.collection import article_text
from catchup.db import get_session
from catchup.errors import AppError
from catchup.models import AppSettings, Item, Source, SourceCheck, XAccount, utc_now
from catchup.api.settings import _x_token
from catchup.net.host_spacing import HostSpacer
from catchup.net.rate_limit import is_rate_limited
from catchup.net.safe_fetch import FetchError, safe_fetch
from catchup.sources.discovery import FEED_UNAVAILABLE_MESSAGE, discover, http_error_status
from catchup.sources.feeds import FeedParseError, is_short, parse_feed
from catchup.sources.x_accounts import post_item, x_username
from catchup.sources.x_api import XApiError, XClient

router = APIRouter(prefix="/api/sources")


class PreviewInput(BaseModel):
    url: str


class ConfirmInput(BaseModel):
    feed_url: str


def _fetch_error(exc: FetchError) -> AppError:
    details = {}
    if exc.code == "rate_limited":
        details["retry_after"] = exc.retry_after
    if exc.code in ("fetch_failed", "feed_unavailable") and (status := http_error_status(exc)) is not None:
        details["http_status"] = status
    return AppError(exc.code, str(exc), 422, **details)


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
    excluded_links = {feed.feed_url} | feed.shared_links
    for entry in feed.entries:
        if entry.identity_key in seen_keys or (entry.link not in excluded_links and entry.link in seen_links):
            continue
        seen_keys.add(entry.identity_key)
        if entry.link not in excluded_links:
            seen_links.add(entry.link)
        yield entry


def _x_error(exc: XApiError) -> AppError:
    return AppError(exc.code, str(exc), 422, **{
        key: value for key, value in {"http_status": exc.http_status, "retry_after": exc.retry_after}.items()
        if value is not None
    })


def _x_preview(request: Request, session: Session, *, username: str | None = None,
               user_id: str | None = None) -> dict:
    token = _x_token(request, session)
    try:
        with closing(XClient(token)) as client:
            user = client.lookup_user(username) if username is not None else client.lookup_user_by_id(user_id)
            if user.protected:
                raise AppError("x_account_protected", "Protected X accounts cannot be followed.", 422)
            feed_url = f"x:user:{user.id}"
            duplicate = _existing(feed_url, session)
            if duplicate:
                raise _duplicate(duplicate, 422)
            page = client.user_posts(user.id, max_results=5, exclude=["retweets", "replies"])
    except XApiError as exc:
        raise _x_error(exc) from exc
    request.app.state.x_preview_cache.put(feed_url, user, page)
    posts = [post for post in page.posts if not post.is_reply and not post.is_retweet][:5]
    return {
        "feed_url": feed_url, "site_url": f"https://x.com/{user.username}", "title": user.name,
        "follows_site_feed_notice": False, "kind": "x", "captions_enabled": False,
        "username": user.username,
        "entries": [{"title": post_item(post, source_id=0, user=user).title,
                     "link": f"https://x.com/{user.username}/status/{post.id}",
                     "published_at": post.created_at} for post in posts],
    }


def _x_confirm(feed_url: str, request: Request, session: Session) -> dict:
    from catchup.digest.runner import _start_lock

    if not re.fullmatch(r"x:user:[0-9]+", feed_url):
        raise AppError("not_an_x_account", "This is not an X account address.", 422)
    _x_token(request, session)
    duplicate = _existing(feed_url, session)
    if duplicate:
        raise _duplicate(duplicate, 409)
    cached = request.app.state.x_preview_cache.pop(feed_url)
    if cached is None:
        _x_preview(request, session, user_id=feed_url.removeprefix("x:user:"))
        cached = request.app.state.x_preview_cache.pop(feed_url)
    user, page = cached
    now = utc_now()
    settings = request.app.state.settings
    lookback = now - timedelta(days=settings.first_add_days)
    recent = [post for post in page.posts if not post.is_reply and not post.is_retweet
              and lookback <= post.created_at <= now]
    selected = sorted(recent, key=lambda post: post.created_at, reverse=True)[:settings.first_add_max]
    with _start_lock, request.app.state.session_factory() as fresh:
        _x_token(request, fresh)
        duplicate = _existing(feed_url, fresh)
        if duplicate:
            raise _duplicate(duplicate, 409)
        source = Source(
            title=user.name, site_url=f"https://x.com/{user.username}", feed_url=feed_url,
            input_url=f"https://x.com/{user.username}", kind="x", created_at=now,
            last_check_at=None, last_check_status="new_items" if selected else "no_new_items",
        )
        fresh.add(source)
        fresh.flush()
        fresh.add(XAccount(
            source_id=source.id, user_id=user.id, username=user.username,
            newest_id=user.most_recent_post_id or max(
                (post.id for post in page.posts), key=int, default=None,
            ), followed_at=now,
        ))
        for post in selected:
            fresh.add(post_item(post, source_id=source.id, user=user))
        fresh.add(SourceCheck(
            source_id=source.id, run_id=None, status=source.last_check_status,
            possible_gap=False, error=None, http_status=200, entries_seen=len(page.posts),
            new_count=len(selected), checked_at=now,
        ))
        try:
            fresh.commit()
        except IntegrityError as exc:
            fresh.rollback()
            duplicate = _existing(feed_url, fresh)
            if duplicate:
                raise _duplicate(duplicate, 409) from exc
            raise
        return {
            "id": source.id, "title": source.title, "site_url": source.site_url,
            "feed_url": source.feed_url, "kind": source.kind, "last_check_at": source.last_check_at,
            "last_check_status": source.last_check_status, "possible_gap": False,
        }


@router.post("/preview")
def preview(data: PreviewInput, request: Request, session: Session = Depends(get_session)) -> dict:
    username = x_username(data.url.strip())
    if username is not None:
        return _x_preview(request, session, username=username)
    try:
        found = discover(data.url.strip(), cache=request.app.state.feed_cache,
                         max_feed_bytes=request.app.state.settings.max_feed_bytes)
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
        "kind": found.feed.kind,
        "captions_enabled": bool((preferences := session.get(AppSettings, 1)) and preferences.youtube_captions),
        "entries": [
            {"title": entry.title, "link": entry.link, "published_at": entry.published_at}
            for entry in recent[:5]
        ],
    }


@router.post("", status_code=201)
def confirm(data: ConfirmInput, request: Request, session: Session = Depends(get_session)) -> dict:
    if data.feed_url.strip().startswith("x:user:"):
        return _x_confirm(data.feed_url.strip(), request, session)
    try:
        feed_url = data.feed_url.strip()
        response = request.app.state.feed_cache.pop(feed_url)
        feed = parse_feed(response if response is not None else safe_fetch(
            feed_url, max_bytes=request.app.state.settings.max_feed_bytes,
        ))
    except FetchError as exc:
        if exc.code == "fetch_failed" and (status := http_error_status(exc)) is not None:
            raise _fetch_error(FetchError(
                "feed_unavailable", FEED_UNAVAILABLE_MESSAGE, status,
            )) from exc
        raise _fetch_error(exc) from exc
    except FeedParseError as exc:
        raise AppError("not_a_feed", str(exc), 422) from exc
    duplicate = _existing(feed.feed_url, session)
    if duplicate:
        raise _duplicate(duplicate, 409)

    now = utc_now()
    settings = request.app.state.settings
    preferences = session.get(AppSettings, 1)
    skip_shorts = preferences.youtube_skip_shorts if preferences else True
    lookback = now - timedelta(days=settings.first_add_days)
    entries = list(_unique_entries(feed))
    recent = [entry for entry in entries if entry.published_at and lookback <= entry.published_at <= now]
    selected = {entry.identity_key for entry in sorted(
        recent, key=lambda entry: entry.published_at, reverse=True,
    )[:settings.first_add_max]}
    source = Source(
        title=feed.title, site_url=feed.site_url, feed_url=feed.feed_url, input_url=data.feed_url,
        created_at=now, last_check_at=now, last_check_status="no_new_items", kind=feed.kind,
    )
    session.add(source)
    session.flush()
    pending_count = 0
    spacer = HostSpacer()
    fallback_links = {feed.feed_url} | feed.shared_links
    for entry in entries:
        state = "pending" if entry.identity_key in selected else "baseline"
        if feed.kind == "youtube" and skip_shorts and is_short(entry.link):
            state = "baseline"
        pending_count += state == "pending"
        transcript_status = ("to_fetch" if feed.kind == "youtube" or
                             (feed.kind == "podcast" and entry.has_audio) else
                             "text" if feed.kind == "podcast" else None)
        text, origin = (
            article_text(entry, fallback_links, settings.short_text_chars, spacer=spacer)
            if state == "pending" and transcript_status in (None, "text")
            else (entry.content_text, "feed")
        )
        session.add(Item(
            source_id=source.id, identity_key=entry.identity_key, link=entry.link,
            title=entry.title, published_at=entry.published_at, discovered_at=now,
            content_text=text, content_origin=origin, state=state,
            transcript_status=transcript_status,
            entry_links=[{"url": link.url, "text": link.text} for link in entry.links],
            comments_url=entry.comments_url, comment_feed_url=entry.comment_feed_url,
            comment_count=entry.comment_count, entry_author=entry.author,
            image_candidates=[asdict(image) for image in entry.images],
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
        "feed_url": source.feed_url, "kind": source.kind, "last_check_at": source.last_check_at,
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
            "id": source.id, "title": source.title, "feed_url": source.feed_url, "kind": source.kind,
            "site_url": source.site_url, "last_check_at": last.checked_at if last else source.last_check_at,
            "last_check_status": last.status if last else source.last_check_status,
            "possible_gap": last.possible_gap if last else False,
            "http_status": last.http_status if last else None,
            "rate_limited": is_rate_limited(last),
            **({"waiting_count": session.scalar(
                select(func.count()).select_from(Item).where(
                    Item.source_id == source.id, Item.state == "pending",
                )
            )} if source.kind == "capture" else {}),
        })
    return result


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, session: Session = Depends(get_session)) -> None:
    source = session.get(Source, source_id)
    if source is None:
        raise AppError("not_found", "Source not found.", 404)
    session.delete(source)
    session.commit()
