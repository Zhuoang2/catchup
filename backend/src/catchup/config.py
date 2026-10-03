"""Instance configuration read from the process environment."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    secret_key: str | None
    first_add_days: int
    first_add_max: int
    short_text_chars: int
    max_item_chars: int
    grouping_batch_chars: int

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
        )
