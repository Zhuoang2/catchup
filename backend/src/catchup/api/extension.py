"""Browser connections and saved-page endpoints."""

import hashlib
import secrets
from dataclasses import asdict
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from catchup.db import get_session
from catchup.digest.runner import active_run
from catchup.errors import AppError
from catchup.models import ExtensionToken, Item, Source, utc_now
from catchup.sources.feeds import EntryImage, filter_image_urls

router = APIRouter(prefix="/api")


class BrowserInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)


def require_connection(request: Request) -> int:
    token_id = getattr(request.state, "extension_token_id", None)
    if token_id is None:
        raise AppError("invalid_token", "This browser is not connected to CatchUp. Connect it in Settings.", 401)
    return token_id


@router.post("/settings/extension-tokens", status_code=201)
def connect_browser(data: BrowserInput, session: Session = Depends(get_session)) -> dict:
    name = data.name.strip()
    if not name:
        raise AppError("invalid_request", "Invalid request.", 422)
    token = "cu_" + secrets.token_urlsafe(32)
    row = ExtensionToken(name=name, token_hash=hashlib.sha256(token.encode()).hexdigest())
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": row.id, "name": row.name, "created_at": row.created_at, "token": token}


@router.get("/settings/extension-tokens")
def list_browsers(session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(ExtensionToken).order_by(ExtensionToken.created_at.desc())).all()
    return [{
        "id": row.id, "name": row.name, "created_at": row.created_at, "last_used_at": row.last_used_at,
    } for row in rows]


@router.delete("/settings/extension-tokens/{token_id}", status_code=204)
def disconnect_browser(token_id: int, session: Session = Depends(get_session)) -> Response:
    row = session.get(ExtensionToken, token_id)
    if row is None:
        raise AppError("not_found", "Browser connection not found.", 404)
    session.delete(row)
    session.commit()
    return Response(status_code=204)


@router.get("/extension/status")
def connection_status(
    token_id: int = Depends(require_connection), session: Session = Depends(get_session),
) -> dict:
    token = session.get(ExtensionToken, token_id)
    waiting = session.scalar(
        select(func.count()).select_from(Item).join(Source).where(
            Source.kind == "capture", Item.state == "pending",
        )
    )
    return {"name": token.name, "waiting": waiting}


class CaptureLink(BaseModel):
    url: str
    text: str


class CaptureImage(BaseModel):
    url: str
    alt: str


class CaptureInput(BaseModel):
    url: str
    title: str
    text: str
    site_name: str | None = None
    author: str | None = None
    published_at: str | None = None
    replies: list[str] = Field(default_factory=list)
    links: list[CaptureLink] = Field(default_factory=list)
    images: list[CaptureImage] = Field(default_factory=list)


def _web_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return parts.scheme.lower() in ("http", "https") and bool(parts.hostname) and parts.port != 0
    except ValueError:
        return False


def _capture_source(session: Session) -> Source:
    source = session.scalar(select(Source).where(Source.feed_url == "catchup:captures"))
    if source is not None:
        return source
    source = Source(kind="capture", title="Saved from browser", site_url="",
                    feed_url="catchup:captures", input_url="catchup:captures")
    session.add(source)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        source = session.scalar(select(Source).where(Source.feed_url == "catchup:captures"))
        if source is None:
            raise
    return source


def _waiting_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Item).join(Source).where(
        Source.kind == "capture", Item.state == "pending",
    ))


@router.post("/captures", status_code=201)
def save_capture(
    data: CaptureInput, _: int = Depends(require_connection), session: Session = Depends(get_session),
) -> dict:
    url = data.url.strip()
    if not _web_url(url) or not (data.title.strip() or data.text.strip()):
        raise AppError("invalid_request", "Invalid request.", 422)
    parts = urlsplit(url)
    identity = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
    source = _capture_source(session)
    waiting = session.scalar(select(Item).where(
        Item.source_id == source.id, Item.state == "pending",
        (Item.identity_key == identity)
        | (func.substr(Item.identity_key, 1, len(identity) + 1) == identity + "#"),
    ).order_by(Item.id.desc()).limit(1))
    if waiting and active_run(session):
        raise AppError("run_active", "A digest is being made. Save this page again when it finishes.", 409)
    now = utc_now()
    if waiting is None:
        key = identity
        if session.scalar(select(Item.id).where(Item.source_id == source.id, Item.identity_key == key)):
            key = f"{identity}#{now.isoformat()}"
        waiting = Item(source_id=source.id, identity_key=key, state="pending")
        session.add(waiting)
    else:
        waiting.summary = waiting.summary_language = waiting.summary_images = waiting.context_status = None
        waiting.contexts.clear()
    try:
        published = datetime.fromisoformat(data.published_at.replace("Z", "+00:00")) if data.published_at else None
    except ValueError:
        published = None
    replies: list[str] = []
    for reply in data.replies[:10]:
        remaining = 4000 - len("\n\n".join(replies)) - (2 if replies else 0)
        if remaining <= 0:
            break
        replies.append(reply[:remaining])
    waiting.link = url
    waiting.title = data.title.strip()[:300]
    waiting.published_at = published
    waiting.discovered_at = now
    waiting.content_text = data.text.strip()[:16000]
    waiting.content_origin = "capture"
    waiting.entry_author = data.author.strip()[:200] if data.author else None
    waiting.site_name = (data.site_name or "").strip()[:200] or parts.hostname.lower()[:200]
    waiting.captured_replies = replies
    waiting.entry_links = [
        {"url": link.url, "text": link.text}
        for link in data.links if _web_url(link.url)
    ][:50]
    waiting.image_candidates = [
        asdict(image) for image in filter_image_urls(
            [EntryImage(url=image.url, alt=image.alt) for image in data.images], url,
        )
    ]
    session.commit()
    return {
        "id": waiting.id, "url": waiting.link, "title": waiting.title,
        "site_name": waiting.site_name, "waiting": _waiting_count(session),
    }


@router.get("/captures")
def list_captures(
    _: int = Depends(require_connection), session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.scalars(
        select(Item).join(Source).where(Source.kind == "capture", Item.state == "pending")
        .order_by(Item.discovered_at.desc(), Item.id.desc())
    ).all()
    return [{
        "id": item.id, "url": item.link, "title": item.title,
        "site_name": item.site_name, "saved_at": item.discovered_at,
    } for item in rows]


@router.delete("/captures/{item_id}", status_code=204)
def remove_capture(
    item_id: int, _: int = Depends(require_connection), session: Session = Depends(get_session),
) -> Response:
    item = session.scalar(
        select(Item).join(Source).where(
            Item.id == item_id, Item.state == "pending", Source.kind == "capture",
        )
    )
    if item is None:
        raise AppError("not_found", "Saved page not found.", 404)
    session.delete(item)
    session.commit()
    return Response(status_code=204)
