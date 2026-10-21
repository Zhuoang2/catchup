"""Browser connections and saved-page endpoints."""

import hashlib
import secrets

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from catchup.db import get_session
from catchup.errors import AppError
from catchup.models import ExtensionToken, Item, Source

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
