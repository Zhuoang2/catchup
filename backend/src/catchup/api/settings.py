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
from catchup.models import AppSettings, ModelConfig, utc_now

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
    return {"ok": True, "models": models}


@router.get("/preferences")
def read_preferences(session: Session = Depends(get_session)) -> dict:
    row = session.get(AppSettings, 1)
    return {
        "digest_language": row.digest_language if row else "en",
        "youtube_captions": row.youtube_captions if row else False,
        "youtube_skip_shorts": row.youtube_skip_shorts if row else True,
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
    row.updated_at = utc_now()
    session.commit()
    return read_preferences(session)
