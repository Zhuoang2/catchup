"""Small OpenAI-compatible adapter with bounded, explicit retries."""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx2
import openai

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


class ConnectionFailed(ModelError):
    code = "connection_failed"


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
                if exc.status_code not in (429, 500, 503) or attempt == 2:
                    if exc.status_code == 429:
                        raise RateLimited("The provider is rate limiting requests.") from exc
                    raise ProviderError("The model provider returned an error.") from exc
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                raise ConnectionFailed(f"Could not connect to the model provider at {self.base_url}.") from exc
            except ValueError as exc:
                if attempt == 2:
                    raise ProviderError("The model provider returned empty content.") from exc
            self._sleep(0.25 * (2 ** attempt))
        raise AssertionError("unreachable")

    def list_models(self) -> list[str]:
        result = self._call(lambda: self._client.models.list(timeout=15.0))
        return [entry.id for entry in result.data]

    def chat_json(self, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        def chat() -> str | None:
            result = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=httpx2.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
            )
            return result.choices[0].message.content if result.choices else None

        content = self._call(chat)
        try:
            data = json.loads(content)
        except (ValueError, TypeError) as exc:
            raise ProviderError("The model provider returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise ProviderError("The model provider returned invalid JSON.")
        return data
