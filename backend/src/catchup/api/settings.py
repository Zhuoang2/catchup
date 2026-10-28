"""Single-instance model configuration and digest language preferences."""

from collections.abc import Callable
from contextlib import closing
from urllib.parse import urlsplit

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from catchup.crypto import decrypt_key, encrypt_key
from catchup.db import get_session
from catchup.errors import AppError
from catchup.llm.client import (
    AuthFailed, ConnectionFailed, InsufficientBalance, ModelClient, ProviderError, RateLimited,
)
from catchup.models import AppSettings, ModelConfig, XCredential, utc_now
from catchup.sources.x_api import XApiError, XClient

router = APIRouter(prefix="/api/settings")
DEFAULT_BASE_URL = "https://api.deepseek.com"


class ModelInput(BaseModel):
    base_url: str
    model_id: str
    api_key: str | None = None


class TestInput(BaseModel):
    base_url: str | None = None
    api_key: str | None = None


class PreferenceInput(BaseModel):
    digest_language: str | None = None
    youtube_captions: bool | None = None
    youtube_skip_shorts: bool | None = None
    show_images: bool | None = None


class XTokenInput(BaseModel):
    token: str


class XTestInput(BaseModel):
    token: str | None = None


def _public_x(row: XCredential | None) -> dict:
    return {"token_set": row is not None, "token_last4": row.token_last4 if row else None}


def _valid_x_token(value: str) -> str:
    token = value.strip()
    if not token or len(token) > 1000 or any(char.isspace() for char in token):
        raise AppError("invalid_x_token", "Enter an X API token without whitespace (at most 1,000 characters).", 422)
    return token


@router.get("/x")
def read_x(session: Session = Depends(get_session)) -> dict:
    return _public_x(session.get(XCredential, 1))


@router.put("/x")
def save_x(data: XTokenInput, request: Request, session: Session = Depends(get_session)) -> dict:
    token = _valid_x_token(data.token)
    row = session.get(XCredential, 1)
    if getattr(request.state, "extension_token_id", None) is not None and row is not None:
        raise AppError("x_token_exists", "Replace the X token in CatchUp Settings.", 409)
    encrypted = encrypt_key(token, request.app.state.settings.secret_key)
    if row is None:
        row = XCredential(id=1, token_encrypted=encrypted, token_last4=token[-4:])
        session.add(row)
    else:
        row.token_encrypted = encrypted
        row.token_last4 = token[-4:]
        row.updated_at = utc_now()
    session.commit()
    return _public_x(row)


@router.delete("/x", status_code=204)
def delete_x(session: Session = Depends(get_session)) -> None:
    row = session.get(XCredential, 1)
    if row:
        session.delete(row)
        session.commit()


@router.post("/x/test")
def test_x(data: XTestInput, request: Request, session: Session = Depends(get_session)) -> dict:
    row = session.get(XCredential, 1)
    token = _valid_x_token(data.token) if data.token is not None else (
        decrypt_key(row.token_encrypted, request.app.state.settings.secret_key) if row else ""
    )
    if not token:
        raise AppError("x_token_required", "X token needed.", 422)
    try:
        with XClient(token) as client:
            client.usage()
    except XApiError as exc:
        status = 401 if exc.code == "x_token_rejected" else 429 if exc.code == "rate_limited" else 502
        raise AppError(exc.code, str(exc), status, **{
            key: value for key, value in {"retry_after": exc.retry_after, "http_status": exc.http_status}.items()
            if value is not None
        }) from exc
    return {"ok": True}


def get_model_client_factory() -> Callable[..., ModelClient]:
    return ModelClient


def _read_key(row: ModelConfig, secret: str | None) -> str:
    try:
        return decrypt_key(row.api_key_encrypted, secret)
    except InvalidToken as exc:
        raise AppError(
            "secret_invalid",
            "CATCHUP_SECRET_KEY does not match the key used to save the model settings.",
            400,
        ) from exc


def _public_model(row: ModelConfig | None) -> dict:
    return {
        "base_url": row.base_url if row else DEFAULT_BASE_URL,
        "model_id": row.model_id if row else "",
        "key_set": row is not None,
        "api_key_last4": row.api_key_last4 if row else None,
    }


def _valid_provider_url(value: str) -> bool:
    try:
        parts = urlsplit(value)
        return (
            parts.scheme in ("http", "https") and bool(parts.hostname)
            and parts.username is None and parts.password is None
            and (parts.port is None or parts.port > 0)
        )
    except ValueError:
        return False


@router.get("/model")
def read_model(session: Session = Depends(get_session)) -> dict:
    return _public_model(session.get(ModelConfig, 1))


@router.put("/model")
def save_model(data: ModelInput, request: Request, session: Session = Depends(get_session)) -> dict:
    base_url, model_id = data.base_url.strip(), data.model_id.strip()
    if not _valid_provider_url(base_url) or not model_id:
        raise AppError("invalid_model_config", "Enter a valid provider URL and model ID.", 422)
    row = session.get(ModelConfig, 1)
    if data.api_key and data.api_key.strip():
        encrypted = encrypt_key(data.api_key.strip(), request.app.state.settings.secret_key)
        last4 = data.api_key.strip()[-4:]
    elif row and base_url == row.base_url:
        encrypted, last4 = row.api_key_encrypted, row.api_key_last4
    elif row:
        raise AppError("api_key_required", "Enter an API key when changing the provider base URL.", 422)
    else:
        raise AppError("missing_api_key", "Enter an API key before saving model settings.", 422)
    if row is None:
        row = ModelConfig(id=1, base_url=base_url, model_id=model_id,
                          api_key_encrypted=encrypted, api_key_last4=last4)
        session.add(row)
    else:
        if row.base_url != base_url or row.model_id != model_id:
            row.context_window = None
        row.base_url, row.model_id = base_url, model_id
        row.api_key_encrypted, row.api_key_last4 = encrypted, last4
        row.updated_at = utc_now()
    session.commit()
    return _public_model(row)


@router.post("/model/test")
def test_model(
    data: TestInput,
    request: Request,
    session: Session = Depends(get_session),
    factory: Callable[..., ModelClient] = Depends(get_model_client_factory),
) -> dict:
    row = session.get(ModelConfig, 1)
    base_url = (data.base_url or (row.base_url if row else DEFAULT_BASE_URL)).strip()
    if not data.api_key and row and base_url != row.base_url:
        raise AppError("api_key_required", "Enter an API key when changing the provider base URL.", 422)
    api_key = data.api_key or (_read_key(row, request.app.state.settings.secret_key) if row else "")
    if not api_key or not _valid_provider_url(base_url):
        raise AppError("invalid_model_config", "Enter a provider URL and API key to test.", 422)
    try:
        with closing(factory(base_url, api_key, row.model_id if row else "")) as client:
            models = client.list_models()
    except AuthFailed as exc:
        raise AppError(exc.code, str(exc), 401) from exc
    except InsufficientBalance as exc:
        raise AppError(exc.code, str(exc), 402) from exc
    except RateLimited as exc:
        raise AppError(exc.code, str(exc), 429) from exc
    except (ConnectionFailed, ProviderError) as exc:
        raise AppError(exc.code, str(exc), 502) from exc
    return {"ok": True, "models": [model.id for model in models]}


@router.get("/preferences")
def read_preferences(session: Session = Depends(get_session)) -> dict:
    row = session.get(AppSettings, 1)
    return {
        "digest_language": row.digest_language if row else "en",
        "youtube_captions": row.youtube_captions if row else False,
        "youtube_skip_shorts": row.youtube_skip_shorts if row else True,
        "show_images": row.show_images if row else True,
    }


@router.put("/preferences")
def save_preferences(data: PreferenceInput, session: Session = Depends(get_session)) -> dict:
    language = data.digest_language.strip() if data.digest_language is not None else None
    if language is not None and (not language or len(language) > 40):
        raise AppError("invalid_language", "Choose a digest language of at most 40 characters.", 422)
    row = session.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1)
        session.add(row)
    if language is not None:
        row.digest_language = language
    if data.youtube_captions is not None:
        row.youtube_captions = data.youtube_captions
    if data.youtube_skip_shorts is not None:
        row.youtube_skip_shorts = data.youtube_skip_shorts
    if data.show_images is not None:
        row.show_images = data.show_images
    row.updated_at = utc_now()
    session.commit()
    return read_preferences(session)
