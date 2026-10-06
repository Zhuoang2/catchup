"""Shared per-run request limits and preferences."""

from dataclasses import dataclass

from catchup.config import Settings
from catchup.net.host_spacing import HostSpacer


@dataclass
class TranscriptContext:
    spacer: HostSpacer
    settings: Settings
    youtube_captions: bool = False
    youtube_skip_shorts: bool = True
    captions_remaining: int = 20
    captions_blocked: bool = False
