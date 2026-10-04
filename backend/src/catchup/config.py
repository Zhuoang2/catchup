"""Instance configuration read from the process environment."""

import os
from dataclasses import dataclass
from pathlib import Path


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
    max_item_chars: int
    grouping_batch_chars: int
    allowed_hosts: tuple[str, ...]
    user_agent_contact: str | None = None
    frontend_dist: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("CATCHUP_DATA_DIR", "./data")),
            secret_key=os.getenv("CATCHUP_SECRET_KEY") or None,
            first_add_days=int(os.getenv("CATCHUP_FIRST_ADD_DAYS", "7")),
            first_add_max=int(os.getenv("CATCHUP_FIRST_ADD_MAX", "5")),
            short_text_chars=int(os.getenv("CATCHUP_SHORT_TEXT_CHARS", "500")),
            max_item_chars=int(os.getenv("CATCHUP_MAX_ITEM_CHARS", "20000")),
            grouping_batch_chars=int(os.getenv("CATCHUP_GROUPING_BATCH_CHARS", "200000")),
            allowed_hosts=tuple(
                host.strip().lower()
                for host in os.getenv("CATCHUP_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
                if host.strip()
            ),
            user_agent_contact=validate_user_agent_contact(os.getenv("CATCHUP_USER_AGENT_CONTACT")),
            frontend_dist=Path(value) if (value := os.getenv("CATCHUP_FRONTEND_DIST")) else None,
        )
