"""Native Anthropic adapter with bounded retries and streamed JSON answers."""

import json
import logging
import re
import threading
import time
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2

from catchup.llm.client import (
    AuthFailed, ConnectionFailed, InsufficientBalance, InvalidAnswer, ModelInfo,
    ProviderError, RateLimited,
)

logging.getLogger("anthropic").setLevel(logging.WARNING)

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_MODELS = frozenset({
    "claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5",
    "claude-opus-5", "claude-sonnet-5-5",
})


class AnthropicModelClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "",
        *,
        http_client: httpx2.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url
        self.model = model
        self._sleep = sleep
        self._usage_lock = threading.Lock()
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._usage_reported = False
        self._client = anthropic.Anthropic(
            base_url=base_url, api_key=api_key, max_retries=0, http_client=http_client,
        )

    def close(self) -> None:
        self._client.close()

    def _call(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(3):
            try:
                return operation()
            except anthropic.AuthenticationError as exc:
                raise AuthFailed("The provider rejected the API key.") from exc
            except anthropic.APIStatusError as exc:
                body = exc.body if isinstance(exc.body, dict) else {}
                error = body.get("error", {})
                details = error.get("details", {}) if isinstance(error, dict) else {}
                spend_limit = isinstance(details, dict) and (
                    details.get("error_code") == "enforced_spend_limit_reached"
                )
                if exc.status_code == 402 or exc.status_code == 429 and spend_limit:
                    raise InsufficientBalance("The provider account has insufficient balance.") from exc
                temporary = exc.status_code in (429, 500, 502, 503, 504, 529) or (
                    exc.status_code == 200 and exc.type in ("overloaded_error", "api_error")
                )
                if not temporary or attempt == 2:
                    if exc.status_code == 429:
                        raise RateLimited("The provider is rate limiting requests.") from exc
                    raise ProviderError("The model provider returned an error.") from exc
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                raise ConnectionFailed(f"Could not connect to the model provider at {self.base_url}.") from exc
            except ValueError as exc:
                if attempt == 2:
                    raise InvalidAnswer("The model provider returned an empty or invalid answer.") from exc
            self._sleep(0.25 * (2 ** attempt))
        raise AssertionError("unreachable")

    def list_models(self) -> list[ModelInfo]:
        def fetch() -> list[ModelInfo]:
            models = []
            options = {}
            while True:
                response = self._client.models.with_raw_response.list(timeout=15.0, **options)
                page = response.json()
                if not isinstance(page, dict) or not isinstance(page.get("data"), list):
                    raise ValueError("model list answer has no list of models")
                for entry in page["data"]:
                    if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                        continue
                    if entry.get("lifecycle") == "retired":
                        continue
                    window = entry.get("max_input_tokens")
                    models.append(ModelInfo(
                        entry["id"], window if type(window) is int and window > 0 else None,
                    ))
                if not page.get("has_more"):
                    break
                last_id = page.get("last_id")
                if not isinstance(last_id, str) or not last_id or last_id == options.get("after_id"):
                    raise ValueError("model list answer has no next page")
                options = {"after_id": last_id}
            return sorted(models, key=lambda model: model.id != DEFAULT_MODEL)

        return self._call(fetch)

    def usage_totals(self) -> tuple[int, int] | None:
        with self._usage_lock:
            if not self._usage_reported:
                return None
            return self._prompt_tokens, self._completion_tokens

    def chat_json(self, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        system = []
        remaining = list(messages)
        while remaining and remaining[0]["role"] == "system":
            system.append(remaining.pop(0)["content"])
        options = {
            "model": self.model,
            "messages": remaining,
            "max_tokens": max(max_tokens, 16_000),
            "timeout": httpx2.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
        }
        if system:
            options["system"] = "\n\n".join(system)
        endpoint = self._client.messages
        if self.model in FALLBACK_MODELS:
            endpoint = self._client.beta.messages
            options.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")

        def chat() -> dict[str, Any]:
            with endpoint.stream(**options) as stream:
                try:
                    result = stream.get_final_message()
                except AssertionError as exc:
                    # The SDK asserts when a 200 body contained no message events.
                    raise ValueError("answer is not a message stream") from exc
            usage = getattr(result, "usage", None)
            if hasattr(usage, "input_tokens") or hasattr(usage, "output_tokens"):
                counts = [getattr(usage, field, None) for field in (
                    "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens",
                )]
                output = getattr(usage, "output_tokens", None)
                with self._usage_lock:
                    self._usage_reported = True
                    self._prompt_tokens += sum(value for value in counts if type(value) is int)
                    self._completion_tokens += output if type(output) is int else 0
            if result.stop_reason == "refusal":
                raise InvalidAnswer("The model provider returned an empty or invalid answer.")
            content = "".join(block.text for block in result.content if block.type == "text").strip()
            fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
            if fenced:
                content = fenced.group(1)
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("model answer is not a JSON object")
            return data

        return self._call(chat)
