"""Instance configuration read from the process environment."""

import os
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def positive_env(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def validate_user_agent_contact(contact: str | None) -> str | None:
    if contact is not None and (len(contact) > 100 or any(not 32 <= ord(ch) <= 126 for ch in contact)):
        raise ValueError("CATCHUP_USER_AGENT_CONTACT must be printable ASCII (no CR/LF), at most 100 characters.")
    return contact


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    secret_key: str | None
    first_add_days: int
    first_add_max: int
    short_text_chars: int
    grouping_batch_chars: int
    allowed_hosts: tuple[str, ...]
    max_feed_bytes: int = 33_554_432
    transcript_wait_days: int = 7
    caption_wait_hours: int = 24
    captions_per_run: int = 20
    long_item_chars: int = 20_000
    single_call_chars: int | None = None
    user_agent_contact: str | None = None
    frontend_dist: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        if "CATCHUP_MAX_ITEM_CHARS" in os.environ:
            logger.warning("CATCHUP_MAX_ITEM_CHARS is ignored; use CATCHUP_SINGLE_CALL_CHARS instead.")
        return cls(
            data_dir=Path(os.getenv("CATCHUP_DATA_DIR", "./data")),
            secret_key=os.getenv("CATCHUP_SECRET_KEY") or None,
            first_add_days=int(os.getenv("CATCHUP_FIRST_ADD_DAYS", "7")),
            first_add_max=int(os.getenv("CATCHUP_FIRST_ADD_MAX", "5")),
            short_text_chars=int(os.getenv("CATCHUP_SHORT_TEXT_CHARS", "500")),
            grouping_batch_chars=int(os.getenv("CATCHUP_GROUPING_BATCH_CHARS", "200000")),
            max_feed_bytes=positive_env("CATCHUP_MAX_FEED_BYTES", 33_554_432),
            transcript_wait_days=positive_env("CATCHUP_TRANSCRIPT_WAIT_DAYS", 7),
            caption_wait_hours=positive_env("CATCHUP_CAPTION_WAIT_HOURS", 24),
            captions_per_run=positive_env("CATCHUP_CAPTIONS_PER_RUN", 20),
            long_item_chars=positive_env("CATCHUP_LONG_ITEM_CHARS", 20_000),
            single_call_chars=positive_env("CATCHUP_SINGLE_CALL_CHARS"),
            allowed_hosts=tuple(
                host.strip().lower()
                for host in os.getenv("CATCHUP_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
                if host.strip()
            ),
            user_agent_contact=validate_user_agent_contact(os.getenv("CATCHUP_USER_AGENT_CONTACT")),
            frontend_dist=Path(value) if (value := os.getenv("CATCHUP_FRONTEND_DIST")) else None,
        )
