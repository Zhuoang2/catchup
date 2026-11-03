import json
import logging
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import httpx2
import pytest
import respx

from catchup.llm.client import (
    AuthFailed, ConnectionFailed, InsufficientBalance, ModelClient, ModelInfo, ProviderError, RateLimited,
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
    assert client.list_models() == [ModelInfo("latest"), ModelInfo("other")]
    assert route.calls[0].request.extensions["timeout"] == {
        "connect": 15.0, "read": 15.0, "write": 15.0, "pool": 15.0,
    }
    client.close()


@pytest.mark.parametrize("field,value,expected", [
    ("context_window", 1_000_000, 1_000_000),
    ("context_length", 4096, 4096),
    ("context_window", "12", None),
    ("context_window", True, None),
    ("context_window", 0, None),
])
def test_model_context_window_uses_only_positive_integers(mock_provider, field, value, expected):
    router, http_client = mock_provider
    router.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json={
        "object": "list", "data": [{"id": "test", "object": "model", field: value}],
    }))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    assert client.list_models() == [ModelInfo("test", expected)]
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


def test_usage_sums_concurrent_chat_calls_and_ignores_missing_usage(mock_provider, monkeypatch):
    _, http_client = mock_provider
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.usage_totals() is None
    response = lambda usage: SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"summary":"ok"}'))],
        usage=usage,
    )
    monkeypatch.setattr(client._client.chat.completions, "create",
                        lambda **_kwargs: response(SimpleNamespace(prompt_tokens=7, completion_tokens=3)))
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(lambda _: client.chat_json([], 50), range(20))) == [{"summary": "ok"}] * 20
    assert client.usage_totals() == (140, 60)
    monkeypatch.setattr(client._client.chat.completions, "create",
                        lambda **_kwargs: response(None))
    assert client.chat_json([], 50) == {"summary": "ok"}
    assert client.usage_totals() == (140, 60)
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


@pytest.mark.parametrize("status", [500, 502, 503, 504])
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


CUT_OFF = '{"topics": [{"title": "Tech'
PLAIN_TEXT = "upstream overloaded"
HTML_PAGE = "<html><body>Bad gateway</body></html>"


@pytest.mark.parametrize("status", [502, 504])
def test_gateway_error_retries_then_succeeds(mock_provider, status) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [httpx.Response(status, json={"error": {"message": "bad gateway"}}), completion('{"ok": 1}')]
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"ok": 1}
    assert route.call_count == 2
    client.close()


@pytest.mark.parametrize("status", [400, 404, 422])
def test_other_status_fails_at_once(mock_provider, status) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(
        return_value=httpx.Response(status, json={"error": {"message": "not temporary"}}),
    )
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(ProviderError):
        client.chat_json([], 20)
    assert route.call_count == 1
    client.close()


@pytest.mark.parametrize("content", [CUT_OFF, "not json", "[1, 2]"], ids=["cut-off", "not-json", "json-list"])
def test_invalid_json_retries_then_succeeds(mock_provider, content) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [completion(content), completion('{"ok": true}')]
    sleeps = []
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=sleeps.append)
    assert client.chat_json([], 20) == {"ok": True}
    assert route.call_count == 2
    assert sleeps == [0.25]
    client.close()


def test_invalid_json_exhausts_retries(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(return_value=completion(CUT_OFF))
    sleeps = []
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=sleeps.append)
    with pytest.raises(ProviderError):
        client.chat_json([], 20)
    assert route.call_count == 3
    assert sleeps == [0.25, 0.5]
    client.close()


@pytest.mark.parametrize("answer", [
    httpx.Response(200, text=PLAIN_TEXT),
    httpx.Response(200, html=HTML_PAGE),
    httpx.Response(200, json=[]),
    httpx.Response(200, json="busy"),
    httpx.Response(200, json={"choices": "busy"}),
    httpx.Response(200, json={"choices": [{}]}),
    httpx.Response(200, json={"choices": [{"message": "busy"}]}),
], ids=["plain-text", "html", "json-list", "json-string", "choices-string", "choice-without-message",
        "message-string"])
def test_answer_that_is_not_a_chat_completion_retries(mock_provider, answer) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions")
    route.side_effect = [answer, completion('{"ok": true}')]
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"ok": True}
    assert route.call_count == 2
    client.close()


def test_answer_that_is_not_a_chat_completion_exhausts_retries(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, text=PLAIN_TEXT))
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(ProviderError):
        client.chat_json([], 20)
    assert route.call_count == 3
    client.close()


def completion_with_usage(content: str, usage) -> httpx.Response:
    body = json.loads(completion(content).content)
    body["usage"] = usage
    return httpx.Response(200, json=body)


@pytest.mark.parametrize("usage,expected", [
    ("n/a", None),
    ({"prompt_tokens": "7", "completion_tokens": 3}, (0, 3)),
], ids=["usage-string", "token-count-string"])
def test_usage_of_the_wrong_shape_is_not_counted(mock_provider, usage, expected) -> None:
    router, http_client = mock_provider
    route = router.post(f"{BASE}/chat/completions").mock(
        return_value=completion_with_usage('{"summary": "ok"}', usage),
    )
    client = ModelClient(BASE, "test-only-key", "test-model", http_client=http_client, sleep=lambda _: None)
    assert client.chat_json([], 20) == {"summary": "ok"}
    assert route.call_count == 1
    assert client.usage_totals() == expected
    client.close()


def test_model_list_that_is_not_a_model_list_exhausts_retries(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.get(f"{BASE}/models").mock(return_value=httpx.Response(200, text=PLAIN_TEXT))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    with pytest.raises(ProviderError):
        client.list_models()
    assert route.call_count == 3
    client.close()


def test_model_list_that_is_not_a_model_list_retries_then_succeeds(mock_provider) -> None:
    router, http_client = mock_provider
    route = router.get(f"{BASE}/models")
    route.side_effect = [
        httpx.Response(200, text=PLAIN_TEXT),
        httpx.Response(200, json={"object": "list", "data": [{"id": "latest", "object": "model"}]}),
    ]
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    assert client.list_models() == [ModelInfo("latest")]
    assert route.call_count == 2
    client.close()


def test_model_list_skips_entries_that_are_not_models(mock_provider) -> None:
    router, http_client = mock_provider
    router.get(f"{BASE}/models").mock(return_value=httpx.Response(200, json={
        "object": "list", "data": [1, {"id": "m"}],
    }))
    client = ModelClient(BASE, "test-only-key", http_client=http_client, sleep=lambda _: None)
    assert client.list_models() == [ModelInfo("m")]
    client.close()
