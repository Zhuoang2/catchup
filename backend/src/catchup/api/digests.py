"""Read saved digests from their snapshots, independent of current sources."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from catchup.db import get_session
from catchup.errors import AppError
from catchup.models import Digest, DigestItem, DigestRun, DigestTopic

router = APIRouter(prefix="/api/digests")


@router.get("")
def list_digests(session: Session = Depends(get_session)) -> list[dict]:
    digests = session.scalars(
        select(Digest).order_by(Digest.created_at.desc(), Digest.id.desc())
    ).all()
    titles: dict[int, list[str]] = {digest.id: [] for digest in digests}
    creator_ids: set[int] = set()
    if digests:
        for digest_id, title, kind in session.execute(
            select(DigestTopic.digest_id, DigestTopic.title, DigestTopic.kind)
            .order_by(DigestTopic.digest_id, DigestTopic.position, DigestTopic.id)
        ):
            if digest_id not in titles:
                continue  # saved after the digest query; it appears on the next load
            if kind == "creator_updates":
                creator_ids.add(digest_id)
            else:
                titles[digest_id].append(title)
    return [
        {"id": digest.id, "created_at": digest.created_at,
         "item_count": digest.item_count, "source_count": digest.source_count,
         "language": digest.language, "topics": titles[digest.id],
         "creator_updates_only": not titles[digest.id] and digest.id in creator_ids}
        for digest in digests
    ]


@router.get("/latest")
def latest_digest(session: Session = Depends(get_session)) -> dict | None:
    digest = session.scalars(
        select(Digest).order_by(Digest.created_at.desc(), Digest.id.desc()).limit(1)
    ).first()
    return _serialize_digest(digest, session) if digest else None


@router.get("/{digest_id}")
def get_digest(digest_id: int, session: Session = Depends(get_session)) -> dict:
    digest = session.get(Digest, digest_id)
    if digest is None:
        raise AppError("not_found", "Digest not found.", 404)
    return _serialize_digest(digest, session)


def _serialize_digest(digest: Digest, session: Session) -> dict:
    digest_id = digest.id
    topics = session.scalars(
        select(DigestTopic).where(DigestTopic.digest_id == digest_id)
        .order_by(DigestTopic.position, DigestTopic.id)
    ).all()
    items = session.scalars(
        select(DigestItem).where(DigestItem.digest_id == digest_id)
        .order_by(DigestItem.topic_id, DigestItem.position, DigestItem.id)
    ).all()
    by_topic: dict[int, list[dict]] = {topic.id: [] for topic in topics}
    for item in items:
        by_topic[item.topic_id].append({
            "title": item.title, "link": item.link, "source_name": item.source_name,
            "source_kind": item.source_kind,
            "published_at": item.published_at, "summary": item.summary,
            "summary_unavailable": item.summary_unavailable,
            "also_read": item.context_links or [],
        })
    creator_groups: dict[tuple[str, str | None], list[dict]] = {}
    for topic in topics:
        if topic.kind != "creator_updates":
            continue
        for item in items:
            if item.topic_id != topic.id:
                continue
            creator_groups.setdefault((item.source_name, item.source_kind), []).append({
                "title": item.title, "link": item.link, "published_at": item.published_at,
                "reason": item.update_reason, "source_kind": item.source_kind,
            })
    creator_updates = [
        {"source_name": name, "source_kind": kind, "items": group}
        for (name, kind), group in creator_groups.items()
    ]
    run = session.get(DigestRun, digest.run_id)
    return {
        "id": digest.id, "created_at": digest.created_at, "model_id": digest.model_id,
        "item_count": digest.item_count, "source_count": digest.source_count,
        "language": digest.language,
        "creator_updates": creator_updates, "transcript_wait_days": digest.transcript_wait_days,
        "prompt_tokens": run.prompt_tokens if run else None,
        "completion_tokens": run.completion_tokens if run else None,
        "topics": [
            {"title": topic.title, "overview": topic.overview, "items": by_topic[topic.id]}
            for topic in topics if topic.kind == "topic"
        ],
    }
