import json
import logging
from concurrent.futures import ThreadPoolExecutor

import httpx2
import pytest

from catchup.llm.anthropic_client import AnthropicModelClient
from catchup.llm.client import (
    AuthFailed, ConnectionFailed, InsufficientBalance, InvalidAnswer, ModelInfo,
    ProviderError, RateLimited,
)

BASE = "https://anthropic.example"


def stream_body(text, *, stop_reason="end_turn", input_tokens=10, output_tokens=5,
                cache_creation=0, cache_read=0):
    events = [
        {"type": "message_start", "message": {
            "id": "test-message", "type": "message", "role": "assistant",
            "model": "claude-opus-5-5", "content": [], "stop_reason": None,
            "stop_sequence": None, "usage": {
                "input_tokens": input_tokens, "output_tokens": 0,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
            },
        }},
    ]
    if text:
        events.extend([
            {"type": "content_block_start", "index": 0,
             "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0,
             "delta": {"type": "text_delta", "text": text}},
            {"type": "content_block_stop", "index": 0},
        ])
    events.extend([
        {"type": "message_delta", "delta": {"stop_reason": stop_reason, "stop_sequence": None},
         "usage": {"output_tokens": output_tokens}},
        {"type": "message_stop"},
    ])
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content="".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    ))


def error_event(type):
    body = {"type": "error", "error": {"type": type, "message": "test provider error"}}
    return httpx2.Response(200, headers={"content-type": "text/event-stream"},
                           content=f"event: error\ndata: {json.dumps(body)}\n\n")


def error_response(status, type, *, spend_limit=False):
    error = {"type": type, "message": "test provider error"}
    if spend_limit:
        error["details"] = {"error_code": "enforced_spend_limit_reached"}
    return httpx2.Response(status, json={"type": "error", "error": error})


@pytest.fixture
def provider():
    clients = []

    def make(answers, *, model="claude-haiku-5-5", path="/v1/messages"):
        requests, sleeps = [], []

        def handle(request):
            assert request.url.host == "anthropic.example"
            assert request.url.path == path
            requests.append(request)
            answer = answers[min(len(requests) - 1, len(answers) - 1)]
            if isinstance(answer, Exception):
                raise answer
            return answer

        client = AnthropicModelClient(
            BASE, "test-only-key", model,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append,
        )
        clients.append(client)
        return client, requests, sleeps

    yield make
    for client in clients:
        client.close()


def test_lists_models_with_positive_context_windows_and_opus_first(provider):
    def model(id, window=None, lifecycle="active"):
        return {"id": id, "type": "model", "display_name": id,
                "created_at": "2026-01-01T00:00:00Z", "lifecycle": lifecycle,
                "max_input_tokens": window}

    client, requests, _ = provider([
        httpx2.Response(200, json={"has_more": True, "last_id": "claude-3-retired", "data": [
            model("claude-sonnet-5-5", 1_000_000), model("claude-opus-5-5", "12"),
            model("claude-3-retired", lifecycle="retired"),
        ]}),
        httpx2.Response(200, json={"has_more": False, "data": [
            model("claude-haiku-5-5", True), model("claude-x-zero", 0),
        ]}),
    ], path="/v1/models")
    assert client.list_models() == [
        ModelInfo("claude-opus-5-5"), ModelInfo("claude-sonnet-5-5", 1_000_000),
        ModelInfo("claude-haiku-5-5"), ModelInfo("claude-x-zero"),
    ]
    assert len(requests) == 2
    assert "after_id" not in requests[0].url.params
    assert requests[1].url.params["after_id"] == "claude-3-retired"
    for request in requests:
        assert request.method == "GET"
        assert request.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 15.0)


def test_json_answer_request_shape_and_no_key_in_logs(provider, caplog):
    client, requests, _ = provider([stream_body('{"summary": "ok"}')])
    with caplog.at_level(logging.DEBUG):
        assert client.chat_json([
            {"role": "system", "content": "Rules"}, {"role": "user", "content": "Item"},
        ], 200) == {"summary": "ok"}
    request = requests[0]
    assert request.method == "POST"
    assert "beta" not in request.url.params
    body = json.loads(request.content)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == 16000
    assert body["system"] == "Rules"
    assert body["messages"] == [{"role": "user", "content": "Item"}]
    assert body["stream"] is True
    assert not {"temperature", "top_p", "top_k", "thinking", "output_config", "fallbacks"} & body.keys()
    assert request.headers["x-api-key"] == "test-only-key"
    assert "anthropic-beta" not in request.headers
    assert request.extensions["timeout"] == {"connect": 10.0, "read": 300.0, "write": 10.0, "pool": 10.0}
    assert "test-only-key" not in caplog.text


def test_two_system_messages_join_into_the_system_field(provider):
    client, requests, _ = provider([stream_body("{}")])
    client.chat_json([{"role": "system", "content": "One"}, {"role": "system", "content": "Two"},
                      {"role": "user", "content": "Item"}], 200)
    body = json.loads(requests[0].content)
    assert body["system"] == "One\n\nTwo"
    assert body["messages"] == [{"role": "user", "content": "Item"}]


def test_large_output_limits_are_kept(provider):
    client, requests, _ = provider([stream_body("{}")])
    client.chat_json([], 32768)
    assert json.loads(requests[0].content)["max_tokens"] == 32768


def test_host_environment_credentials_are_never_used(provider, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "env-token")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://env.example")
    client, requests, _ = provider([stream_body("{}")])
    client.chat_json([], 200)
    assert requests[0].headers["x-api-key"] == "test-only-key"
    assert all("env-key" not in value and "env-token" not in value
               for value in requests[0].headers.values())


@pytest.mark.parametrize("fence", ["```json", "```"])
def test_fenced_json_is_accepted_without_retry(provider, fence):
    client, requests, sleeps = provider([stream_body(f'{fence}\n{{"summary": "ok"}}\n```')])
    assert client.chat_json([], 200) == {"summary": "ok"}
    assert len(requests) == 1
    assert sleeps == []


@pytest.mark.parametrize("answer", [
    httpx2.Response(200, html="<html>wrong address</html>"),
    stream_body(""), stream_body('Here is the JSON: {"summary": "x"}'),
    stream_body('["a"]'), stream_body('{"summary": "o', stop_reason="max_tokens"),
], ids=["html", "empty", "prefixed", "array", "max-tokens"])
def test_invalid_answers_retry_then_succeed(provider, answer):
    client, requests, sleeps = provider([answer, stream_body('{"summary": "ok"}')])
    assert client.chat_json([], 200) == {"summary": "ok"}
    assert len(requests) == 2
    assert sleeps == [0.25]


def test_invalid_answers_exhaust_retries(provider):
    client, requests, sleeps = provider([httpx2.Response(200, html="<html>wrong address</html>")])
    with pytest.raises(InvalidAnswer):
        client.chat_json([], 200)
    assert len(requests) == 3
    assert sleeps == [0.25, 0.5]


def test_refusal_fails_at_once(provider):
    client, requests, sleeps = provider([stream_body("", stop_reason="refusal")])
    with pytest.raises(InvalidAnswer):
        client.chat_json([], 200)
    assert len(requests) == 1
    assert sleeps == []


@pytest.mark.parametrize("answer,error", [
    (error_response(401, "authentication_error"), AuthFailed),
    (error_response(402, "billing_error"), InsufficientBalance),
    (error_response(429, "rate_limit_error", spend_limit=True), InsufficientBalance),
    *[(error_response(status, "invalid_request_error"), ProviderError) for status in (400, 403, 404, 413)],
    (error_event("invalid_request_error"), ProviderError),
], ids=["401", "402", "spend-limit", "400", "403", "404", "413", "stream-invalid"])
def test_failures_that_do_not_retry(provider, answer, error):
    client, requests, sleeps = provider([answer])
    with pytest.raises(error) as caught:
        client.chat_json([], 200)
    assert not isinstance(caught.value, RateLimited)
    if error is ProviderError:
        assert not isinstance(caught.value, InsufficientBalance)
    assert "test provider error" not in str(caught.value)
    assert len(requests) == 1
    assert sleeps == []


@pytest.mark.parametrize("answer", [
    error_response(429, "rate_limit_error"),
    *[error_response(status, "api_error") for status in (500, 502, 503, 504)],
    error_response(529, "overloaded_error"),
    error_event("overloaded_error"), error_event("api_error"),
], ids=["429", "500", "502", "503", "504", "529", "stream-overloaded", "stream-api"])
def test_temporary_errors_retry_then_succeed(provider, answer):
    client, requests, sleeps = provider([answer, stream_body('{"summary": "ok"}')])
    assert client.chat_json([], 200) == {"summary": "ok"}
    assert len(requests) == 2
    assert sleeps == [0.25]


def test_rate_limit_exhaustion(provider):
    client, requests, sleeps = provider([error_response(429, "rate_limit_error")])
    with pytest.raises(RateLimited):
        client.chat_json([], 200)
    assert len(requests) == 3
    assert sleeps == [0.25, 0.5]


def test_overload_exhaustion(provider):
    client, requests, sleeps = provider([error_response(529, "overloaded_error")])
    with pytest.raises(ProviderError) as caught:
        client.chat_json([], 200)
    assert not isinstance(caught.value, RateLimited)
    assert len(requests) == 3
    assert sleeps == [0.25, 0.5]


@pytest.mark.parametrize("operation", ["chat_json", "list_models"])
def test_connection_timeout_names_the_base_url(provider, operation):
    client, requests, sleeps = provider([httpx2.ConnectTimeout("test timeout")],
                                        path="/v1/models" if operation == "list_models" else "/v1/messages")
    with pytest.raises(ConnectionFailed, match=BASE):
        if operation == "list_models":
            client.list_models()
        else:
            client.chat_json([], 200)
    assert len(requests) == 1
    assert sleeps == []


def test_model_list_rejected_key(provider):
    client, requests, _ = provider([error_response(401, "authentication_error")], path="/v1/models")
    with pytest.raises(AuthFailed):
        client.list_models()
    assert len(requests) == 1


@pytest.mark.parametrize("answer", [
    httpx2.Response(200, html="<html>wrong address</html>"),
    httpx2.Response(200, json={"data": "busy", "has_more": False}),
], ids=["html", "data-string"])
def test_model_list_that_is_not_a_model_list_exhausts_retries(provider, answer):
    client, requests, _ = provider([answer], path="/v1/models")
    with pytest.raises(ProviderError):
        client.list_models()
    assert len(requests) == 3


@pytest.mark.parametrize("model,fallback", [
    ("claude-fable-5-2", True), ("claude-fable-5-1", True), ("claude-opus-5-5", True),
    ("claude-opus-5", True), ("claude-sonnet-5-5", True),
    ("claude-haiku-5-5", False), ("claude-sonnet-4-6", False),
])
def test_fallback_models(provider, model, fallback):
    client, requests, _ = provider([stream_body("{}")], model=model)
    client.chat_json([], 200)
    request = requests[0]
    body = json.loads(request.content)
    if fallback:
        assert request.url.params["beta"] == "true"
        assert "server-side-fallback-2026-07-01" in request.headers["anthropic-beta"]
        assert body["fallbacks"] == "default"
    else:
        assert "beta" not in request.url.params
        assert "anthropic-beta" not in request.headers
        assert "fallbacks" not in body


def test_usage_sums_input_cache_and_output_tokens_across_threads(provider):
    client, _, _ = provider([stream_body('{"summary": "ok"}', cache_creation=2, cache_read=3)])
    assert client.usage_totals() is None
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(lambda _: client.chat_json([], 200), range(4))) == [{"summary": "ok"}] * 4
    assert client.usage_totals() == (60, 20)


@pytest.mark.parametrize("input_tokens,output_tokens,expected", [
    ("seven", 3, (0, 3)), (7, "three", (7, 0)), ("seven", "three", (0, 0)),
])
def test_usage_of_the_wrong_shape_is_not_counted(provider, input_tokens, output_tokens, expected):
    client, _, _ = provider([stream_body("{}", input_tokens=input_tokens, output_tokens=output_tokens)])
    assert client.chat_json([], 200) == {}
    assert client.usage_totals() == expected
