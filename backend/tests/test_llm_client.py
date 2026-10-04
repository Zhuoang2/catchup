import json
import logging

import httpx
import httpx2
import pytest
import respx

from catchup.llm.client import (
    AuthFailed, ConnectionFailed, InsufficientBalance, ModelClient, ProviderError, RateLimited,
)

BASE = "https://provider.example/v1"


@pytest.fixture
def mock_provider():
    """Bridge OpenAI 3's httpx2 transport to respx's httpx router, without sockets."""
    router = respx.Router(assert_all_mocked=True)

    def handle(request: httpx2.Request) -> httpx2.Response:
        old_request = httpx.Request(
            request.method, str(request.url), headers=dict(request.headers), content=request.content,
            extensions=dict(request.extensions),
        )
        try:
            response = router.handler(old_request)
        except httpx.TimeoutException as exc:
            raise httpx2.ConnectTimeout("test transport timed out") from exc
        return httpx2.Response(
            response.status_code, headers=dict(response.headers), content=response.content, request=request,
        )

    return router, httpx2.Client(transport=httpx2.MockTransport(handle))


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={
        "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    })


def test_lists_provider_models(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json={
        "object": "list", "data": [{"id": "latest", "object": "model"}, {"id": "other", "object": "model"}],
    }))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    assert client.list_models() == ["latest", "other"]
    assert route.calls[0].request.extensions["timeout"] == {
        "connect": 15.0, "read": 15.0, "write": 15.0, "pool": 15.0,
    }
    client.close()


def test_json_mode_success_and_no_key_in_logs(mock_provider, caplog) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(return_value=completion('{"summary":"ok"}'))
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    with caplog.at_level(logging.DEBUG):
        assert client.chat_json([{"role": "user", "content": "Give JSON"}], 200) == {"summary": "ok"}
    body = json.loads(route.calls[0].request.content)
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 200
    assert route.calls[0].request.extensions["timeout"] == {
        "connect": 10.0, "read": 300.0, "write": 10.0, "pool": 10.0,
    }
    assert "test-only-key" not in caplog.text
    client.close()


def test_empty_response_retries(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [completion(""), completion('{"ok":true}')]
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"ok": True}
    assert route.call_count == 2
    client.close()


def test_empty_choices_retries(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [
        httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0,
            "model": "test-model", "choices": [],
        }),
        completion('{"ok":true}'),
    ]
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"ok": True}
    assert route.call_count == 2
    client.close()


@pytest.mark.parametrize("status,error_type", [
    (401, AuthFailed), (402, InsufficientBalance),
])
def test_auth_and_balance_fail_immediately(mock_provider, status, error_type) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(status, json={"error": {"message": "sensitive provider response"}}),
    )
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(error_type) as error:
        client.chat_json([], 20)
    assert "sensitive provider response" not in str(error.value)
    assert route.call_count == 1
    client.close()


def test_rate_limit_retries_then_succeeds(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [httpx.Response(429, json={"error": {"message": "slow down"}}), completion('{"ok":1}')]
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"ok": 1}
    assert route.call_count == 2
    client.close()


@pytest.mark.parametrize("status", [500, 503])
def test_server_error_exhausts_retries(mock_provider, status) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(status, json={"error": {"message": "temporary"}}),
    )
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(ProviderError):
        client.chat_json([], 20)
    assert route.call_count == 3
    client.close()


def test_connection_timeout(mock_provider) -> None:
    router, http_client = mock_provider
    router.get(f"{BASE}/models").mock(side_effect=httpx.ConnectTimeout("mock timeout"))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(ConnectionFailed, match=BASE):
        client.list_models()
    client.close()


def test_rate_limit_exhaustion(mock_provider) -> None:
    router, http_client = mock_provider
    router.get(f"{BASE}/models").mock(return_value=httpx.Response(429, json={"error": {"message": "slow"}}))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(RateLimited):
        client.list_models()
    client.close()
