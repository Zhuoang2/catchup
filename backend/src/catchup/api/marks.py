"""Local marks on saved digest items, independent of their snapshots."""

from fastapi import APIRouter, Depends
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from catchup.db import get_session
from catchup.errors import AppError
from catchup.models import DigestItem, DigestItemMark, DigestTopic, utc_now

router = APIRouter(prefix="/api")


def markable_item(session: Session, item_id: int) -> DigestItem:
    item = session.get(DigestItem, item_id)
    if item is None:
        raise AppError("not_found", "Digest item not found.", 404)
    if session.get(DigestTopic, item.topic_id).kind == "creator_updates":
        raise AppError("not_markable", "Items in Creator updates cannot be bookmarked or rated.", 422)
    return item


def marks_answer(mark: DigestItemMark) -> dict:
    return {
        "id": mark.digest_item_id,
        "bookmarked": mark.bookmarked_at is not None,
        "liked": mark.liked_at is not None,
        "rating": mark.rating, "note": mark.note,
    }


def change_toggle(session: Session, item_id: int, column: str, enabled: bool) -> dict:
    markable_item(session, item_id)
    now = utc_now()
    session.execute(insert(DigestItemMark).values(
        digest_item_id=item_id, updated_at=now,
    ).on_conflict_do_nothing(index_elements=["digest_item_id"]))
    mark = session.get(DigestItemMark, item_id)
    if not enabled:
        setattr(mark, column, None)
    elif getattr(mark, column) is None:
        setattr(mark, column, now)
    mark.updated_at = now
    session.commit()
    return marks_answer(mark)


@router.put("/digest-items/{item_id}/bookmark")
def bookmark(item_id: int, session: Session = Depends(get_session)) -> dict:
    return change_toggle(session, item_id, "bookmarked_at", True)


@router.delete("/digest-items/{item_id}/bookmark")
def remove_bookmark(item_id: int, session: Session = Depends(get_session)) -> dict:
    return change_toggle(session, item_id, "bookmarked_at", False)


@router.put("/digest-items/{item_id}/like")
def like(item_id: int, session: Session = Depends(get_session)) -> dict:
    return change_toggle(session, item_id, "liked_at", True)


@router.delete("/digest-items/{item_id}/like")
def remove_like(item_id: int, session: Session = Depends(get_session)) -> dict:
    return change_toggle(session, item_id, "liked_at", False)
