"""Concurrent model-only summarization; persistence stays on the runner thread."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from collections.abc import Callable, Iterable
import re

from catchup.llm.client import AuthFailed, InsufficientBalance, ModelClient, ModelError, ProviderError
from catchup.llm.prompts import (
    SUMMARY_MAX_TOKENS, combine_messages, long_transcript_messages,
    part_messages, summary_messages,
)


@dataclass(frozen=True)
class SummaryInput:
    id: int
    title: str
    content_text: str
    summary: str | None
    summary_language: str | None
    content_origin: str = "feed"


@dataclass(frozen=True)
class SummaryResult:
    id: int
    summary: str | None
    unavailable: bool = False


def split_parts(text: str, max_chars: int) -> list[str]:
    """Pack consecutive blank-line, line and word segments without discarding text."""
    parts: list[str] = []
    current = ""

    def pack(segment: str) -> None:
        nonlocal current
        if len(current) + len(segment) > max_chars and current.strip():
            parts.append(current)
            current = ""
        current += segment

    def add(segment: str, level: int) -> None:
        if len(segment) <= max_chars:
            pack(segment)
            return
        separators = (r"(\n[ \t]*\n+)", r"(\n)", r"(\s+)")
        if level == len(separators):
            raise ValueError("A word exceeds the single-call budget.")
        for piece in re.split(separators[level], segment):
            if piece:
                add(piece, level + 1)

    add(text, 0)
    if current.strip():
        parts.append(current)
    return parts


def _summarize(client: ModelClient, item: SummaryInput, language: str,
               max_chars: int, long_item_chars: int) -> SummaryResult:
    try:
        long_transcript = item.content_origin == "transcript" and len(item.content_text) > long_item_chars
        if len(item.content_text) <= max_chars:
            messages = (long_transcript_messages(item.title, item.content_text, language)
                        if long_transcript else summary_messages(item.title, item.content_text, language))
        else:
            parts = split_parts(item.content_text, max_chars)
            notes = []
            for index, part in enumerate(parts, 1):
                response = client.chat_json(
                    part_messages(item.title, part, language, index, len(parts)),
                    max_tokens=SUMMARY_MAX_TOKENS,
                )
                note = response.get("summary")
                if not isinstance(note, str) or not note.strip():
                    raise ProviderError("The model provider returned no part summary.")
                notes.append(note.strip())
            messages = combine_messages(item.title, "\n\n".join(notes), language,
                                        long_transcript=long_transcript)
        response = client.chat_json(messages, max_tokens=SUMMARY_MAX_TOKENS)
        summary = response.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ProviderError("The model provider returned no summary.")
        return SummaryResult(item.id, summary.strip())
    except (AuthFailed, InsufficientBalance):
        raise
    except (ModelError, ValueError):
        return SummaryResult(item.id, None, unavailable=True)


def summarize_items(
    client: ModelClient,
    items: Iterable[SummaryInput],
    language: str,
    max_chars: int,
    on_result: Callable[[SummaryResult], None],
    *,
    long_item_chars: int = 20_000,
) -> None:
    """Call on_result in the caller thread, never in the four model workers."""
    uncached = []
    for item in items:
        if item.summary and item.summary_language == language:
            on_result(SummaryResult(item.id, item.summary))
        else:
            uncached.append(item)
    pool = ThreadPoolExecutor(max_workers=4)
    try:
        futures = [pool.submit(_summarize, client, item, language, max_chars, long_item_chars)
                   for item in uncached]
        for future in as_completed(futures):
            on_result(future.result())
    except (AuthFailed, InsufficientBalance):
        # Do not wait for unrelated, possibly slow provider calls before failing.
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    except Exception:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)
