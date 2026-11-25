import json
import threading
from collections import Counter

import httpx2

from catchup.llm.providers import make_model_client
from catchup.models import Item, ModelConfig
from test_anthropic_client import BASE, error_event, error_response, stream_body
from test_digest_runner import all_rows, environment, execute, seed, stub_collection
from test_model_errors import saved_digest


def configure(client):
    seed(client, count=3)
    with client.app.state.session_factory() as session:
        row = session.get(ModelConfig, 1)
        row.provider, row.base_url, row.model_id = "anthropic", BASE, "claude-opus-5-5"
        session.commit()


def install_factory(client, handle, sleeps):
    client.app.state.model_client_factory = lambda base, key, model, provider, reasoning: make_model_client(
        base, key, model, provider, reasoning,
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append,
    )


def test_anthropic_run_saves_summaries_groups_and_usage(environment, monkeypatch):
    configure(environment)
    stub_collection(monkeypatch)
    attempts, sleeps = Counter(), []
    lock = threading.Lock()

    def handle(request):
        assert request.url.host == "anthropic.example"
        if request.method == "GET" and request.url.path == "/v1/models":
            return httpx2.Response(200, json={"has_more": False, "data": [{
                "id": "claude-opus-5-5", "type": "model", "display_name": "Opus",
                "created_at": "2026-01-01T00:00:00Z", "lifecycle": "active",
                "max_input_tokens": 1_000_000,
            }]})
        assert request.method == "POST" and request.url.path == "/v1/messages"
        body = json.loads(request.content)
        assert body["fallbacks"] == "default"
        if "item_refs" in body["system"]:
            call = "grouping"
        else:
            call = next((f"Item {n}" for n in range(3)
                         if f"Title: Item {n}" in body["messages"][0]["content"]), None)
            assert call is not None, "unplanned model call"
        with lock:
            attempts[call] += 1
            attempt = attempts[call]
        if call == "Item 0":
            return error_response(529, "overloaded_error") if attempt == 1 else stream_body('{"summary": "Zero"}')
        if call == "Item 1":
            return stream_body('```json\n{"summary": "One"}\n```')
        if call == "Item 2":
            return stream_body("", stop_reason="refusal")
        return stream_body('{"topics": [{"title": "Technology", "overview": "News", "item_refs": ["i1", "i2", "i3"]}]}')

    install_factory(environment, handle, sleeps)
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert saved_digest(environment) == [(("Technology", "News"), [
        ("Item 0", "Zero", False), ("Item 1", "One", False), ("Item 2", None, True),
    ])]
    assert attempts == {"Item 0": 2, "Item 1": 1, "Item 2": 1, "grouping": 1}
    assert sleeps == [0.25]
    assert (result["prompt_tokens"], result["completion_tokens"]) == (40, 20)
    with environment.app.state.session_factory() as session:
        assert session.get(ModelConfig, 1).context_window == 1_000_000


def test_anthropic_rejected_key_fails_the_run(environment, monkeypatch):
    configure(environment)
    stub_collection(monkeypatch)
    sleeps = []

    def handle(request):
        assert request.url.host == "anthropic.example"
        assert (request.method, request.url.path) in (("GET", "/v1/models"), ("POST", "/v1/messages"))
        return error_response(401, "authentication_error")

    install_factory(environment, handle, sleeps)
    result = execute(environment)
    assert (result["status"], result["error_kind"]) == ("failed", "auth_failed")
    assert [row.state for row in all_rows(environment, Item)] == ["pending"] * 3
    assert sleeps == []


def test_anthropic_run_sends_low_effort_with_fallback(environment, monkeypatch):
    configure(environment)
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        session.get(ModelConfig, 1).reasoning = "low"
        session.commit()
    bodies, sleeps = [], []

    def handle(request):
        assert request.url.host == "anthropic.example"
        if request.method == "GET" and request.url.path == "/v1/models":
            return httpx2.Response(200, json={"has_more": False, "data": []})
        assert request.method == "POST" and request.url.path == "/v1/messages"
        body = json.loads(request.content)
        bodies.append(body)
        if "item_refs" in body["system"]:
            return stream_body('{"topics": [{"title": "Technology", "overview": "News", "item_refs": ["i1", "i2", "i3"]}]}')
        return stream_body('{"summary": "English summary"}')

    install_factory(environment, handle, sleeps)
    assert execute(environment)["status"] == "succeeded"
    assert len(bodies) == 4
    for body in bodies:
        assert body["output_config"] == {"effort": "low"}
        assert body["fallbacks"] == "default"
        assert "thinking" not in body
