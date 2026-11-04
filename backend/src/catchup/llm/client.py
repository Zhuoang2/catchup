"""Small OpenAI-compatible adapter with bounded, explicit retries."""

import json
import logging
import time
import threading
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import httpx2
import openai
from openai.types import Model

# Neither SDK debug logging nor transport logging should contain request headers.
for name in ("openai", "httpx2", "httpcore2"):
    logging.getLogger(name).setLevel(logging.WARNING)


class ModelError(Exception):
    code = "provider_error"


class AuthFailed(ModelError):
    code = "auth_failed"


class InsufficientBalance(ModelError):
    code = "insufficient_balance"


class RateLimited(ModelError):
    code = "rate_limited"


class ProviderError(ModelError):
    code = "provider_error"


class InvalidAnswer(ProviderError):
    """The provider answered, but the answer stayed empty or unusable after retries."""


class ConnectionFailed(ModelError):
    code = "connection_failed"


@dataclass(frozen=True)
class ModelInfo:
    id: str
    context_window: int | None = None


class ModelClient:
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
        self._client = openai.OpenAI(
            base_url=base_url, api_key=api_key, max_retries=0, http_client=http_client,
        )

    def close(self) -> None:
        self._client.close()

    def _call(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(3):
            try:
                result = operation()
                if result is None or isinstance(result, str) and not result.strip():
                    raise ValueError("empty model response")
                return result
            except openai.AuthenticationError as exc:
                raise AuthFailed("The provider rejected the API key.") from exc
            except openai.APIStatusError as exc:
                if exc.status_code == 402:
                    raise InsufficientBalance("The provider account has insufficient balance.") from exc
                if exc.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                    if exc.status_code == 429:
                        raise RateLimited("The provider is rate limiting requests.") from exc
                    raise ProviderError("The model provider returned an error.") from exc
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                raise ConnectionFailed(f"Could not connect to the model provider at {self.base_url}.") from exc
            except ValueError as exc:
                if attempt == 2:
                    raise InvalidAnswer("The model provider returned an empty or invalid answer.") from exc
            self._sleep(0.25 * (2 ** attempt))
        raise AssertionError("unreachable")

    def list_models(self) -> list[ModelInfo]:
        def fetch() -> list[Any]:
            try:
                result = self._client.models.list(timeout=15.0)
            except AttributeError as exc:
                # openai 3.24.0 fails in its post-parser when a 200 answer is not a JSON object.
                raise ValueError("model list answer is not a model list") from exc
            data = getattr(result, "data", None)
            if not isinstance(data, list):
                raise ValueError("model list answer has no list of models")
            return data

        models = []
        for entry in self._call(fetch):
            if not isinstance(entry, Model):
                continue
            extra = entry.model_extra or {}
            value = extra.get("context_window")
            if value is None:
                value = extra.get("context_length")
            models.append(ModelInfo(
                entry.id, value if type(value) is int and value > 0 else None,
            ))
        return models

    def usage_totals(self) -> tuple[int, int] | None:
        with self._usage_lock:
            if not self._usage_reported:
                return None
            return self._prompt_tokens, self._completion_tokens

    def chat_json(self, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        def chat() -> dict[str, Any] | None:
            # The SDK returns a str, list, or partly built object for answers that are not
            # chat completions, so nothing about the result's shape is assumed.
            result = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=httpx2.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
            )
            usage = getattr(result, "usage", None)
            if hasattr(usage, "prompt_tokens") or hasattr(usage, "completion_tokens"):
                prompt = getattr(usage, "prompt_tokens", None)
                completion = getattr(usage, "completion_tokens", None)
                with self._usage_lock:
                    self._usage_reported = True
                    self._prompt_tokens += prompt if type(prompt) is int else 0
                    self._completion_tokens += completion if type(completion) is int else 0
            choices = getattr(result, "choices", None)
            if not isinstance(choices, list) or not choices:
                return None
            content = getattr(getattr(choices[0], "message", None), "content", None)
            if not isinstance(content, str) or not content.strip():
                return None
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("model answer is not a JSON object")
            return data

        return self._call(chat)
