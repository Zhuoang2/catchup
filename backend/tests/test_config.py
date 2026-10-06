import logging

import pytest

from catchup.config import Settings


def test_transcript_defaults() -> None:
    settings = Settings.from_env()
    assert (settings.max_feed_bytes, settings.transcript_wait_days, settings.caption_wait_hours,
            settings.captions_per_run, settings.long_item_chars, settings.single_call_chars) == (
                33_554_432, 7, 24, 20, 20_000, None,
            )
    assert not hasattr(settings, "max_item_chars")


@pytest.mark.parametrize("name", [
    "CATCHUP_MAX_FEED_BYTES", "CATCHUP_TRANSCRIPT_WAIT_DAYS", "CATCHUP_CAPTION_WAIT_HOURS",
    "CATCHUP_CAPTIONS_PER_RUN", "CATCHUP_LONG_ITEM_CHARS", "CATCHUP_SINGLE_CALL_CHARS",
])
@pytest.mark.parametrize("value", ["0", "-2", "abc", "1.2", ""])
def test_transcript_settings_reject_invalid_values(monkeypatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match=f"{name} must be a positive integer"):
        Settings.from_env()


def test_transcript_settings_accept_positive_values(monkeypatch) -> None:
    monkeypatch.setenv("CATCHUP_SINGLE_CALL_CHARS", "2000")
    monkeypatch.setenv("CATCHUP_MAX_FEED_BYTES", "1024")
    settings = Settings.from_env()
    assert settings.single_call_chars == 2000
    assert settings.max_feed_bytes == 1024


def test_removed_cap_warns_once(monkeypatch, caplog) -> None:
    monkeypatch.setenv("CATCHUP_MAX_ITEM_CHARS", "12")
    with caplog.at_level(logging.WARNING, logger="catchup.config"):
        Settings.from_env()
    assert len(caplog.records) == 1
    assert "CATCHUP_MAX_ITEM_CHARS" in caplog.text
    assert "CATCHUP_SINGLE_CALL_CHARS" in caplog.text
