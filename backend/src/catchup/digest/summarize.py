"""Concurrent model-only summarization; persistence stays on the runner thread."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from collections.abc import Callable, Iterable

from catchup.llm.client import AuthFailed, InsufficientBalance, ModelClient, ModelError, ProviderError
from catchup.llm.prompts import SUMMARY_MAX_TOKENS, summary_messages


@dataclass(frozen=True)
class SummaryInput:
    id: int
    title: str
    content_text: str
    summary: str | None
    summary_language: str | None


@dataclass(frozen=True)
class SummaryResult:
    id: int
    summary: str | None
    unavailable: bool = False


def _summarize(client: ModelClient, item: SummaryInput, language: str, max_chars: int) -> SummaryResult:
    try:
        response = client.chat_json(
            summary_messages(item.title, item.content_text[:max_chars], language),
            max_tokens=SUMMARY_MAX_TOKENS,
        )
        summary = response.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ProviderError("The model provider returned no summary.")
        return SummaryResult(item.id, summary.strip())
    except (AuthFailed, InsufficientBalance):
        raise
    except ModelError:
        return SummaryResult(item.id, None, unavailable=True)


def summarize_items(
    client: ModelClient,
    items: Iterable[SummaryInput],
    language: str,
    max_chars: int,
    on_result: Callable[[SummaryResult], None],
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
        futures = [pool.submit(_summarize, client, item, language, max_chars) for item in uncached]
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
