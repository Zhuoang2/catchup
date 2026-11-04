"""Run-level recovery from model answers that stay unusable (issue #67)."""

import json
import threading
from collections import Counter

import httpx2
import pytest
from sqlalchemy import select

from catchup.llm.client import ModelClient, RateLimited
from catchup.models import Digest, DigestItem, DigestTopic, Item, ModelConfig
from test_digest_runner import FakeModel, all_rows, environment, execute, seed, stub_collection
from test_llm_client import CUT_OFF, HTML_PAGE, PLAIN_TEXT


def saved_digest(client):
    with client.app.state.session_factory() as session:
        topics = session.scalars(select(DigestTopic).order_by(DigestTopic.position)).all()
        return [
            ((topic.title, topic.overview), [
                (row.title, row.summary, row.summary_unavailable)
                for row in session.scalars(
                    select(DigestItem).where(DigestItem.topic_id == topic.id).order_by(DigestItem.position)
                )
            ])
            for topic in topics
        ]


class NoTopicsModel(FakeModel):
    def chat_json(self, messages, max_tokens):
        self.calls.append((messages, max_tokens))
        if '"summary"' in messages[0]["content"]:
            return {"summary": "English summary"}
        return {}


def test_run_whose_grouping_has_no_topics_saves_one_other_topic(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    environment.app.state.model_client_factory = lambda *_: NoTopicsModel()
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert saved_digest(environment) == [(("Other", ""), [
        ("Item 0", "English summary", False), ("Item 1", "English summary", False),
    ])]
    assert [row.state for row in all_rows(environment, Item)] == ["delivered", "delivered"]

    second = FakeModel()
    environment.app.state.model_client_factory = lambda *_: second
    assert execute(environment)["status"] == "no_new_content"
    assert second.calls == []


def completion(content: str) -> httpx2.Response:
    return httpx2.Response(200, json={
        "id": "test", "object": "chat.completion", "created": 0, "model": "test-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    })


def test_live_failure_recovers_end_to_end(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    lock = threading.Lock()
    attempts = Counter()
    sleeps = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET" and request.url.path.endswith("/models"):
            return httpx2.Response(200, json={"object": "list", "data": []})
        messages = json.loads(request.content)["messages"]
        if "item_refs" in messages[0]["content"]:
            call = "grouping"
        elif "Title: Item 0" in messages[1]["content"]:
            call = "Item 0"
        elif "Title: Item 1" in messages[1]["content"]:
            call = "Item 1"
        else:
            raise AssertionError("unplanned model call")
        with lock:  # Summary calls run in 4 threads.
            attempts[call] += 1
            attempt = attempts[call]
        if call == "Item 0":
            return httpx2.Response(200, text=PLAIN_TEXT) if attempt == 1 else completion('{"summary": "Zero"}')
        if call == "Item 1":
            return httpx2.Response(200, html=HTML_PAGE)
        return completion(CUT_OFF)

    environment.app.state.model_client_factory = lambda base, key, model: ModelClient(
        base, key, model, http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append,
    )
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert attempts == {"Item 0": 2, "Item 1": 3, "grouping": 3}
    assert sorted(sleeps) == [0.25, 0.25, 0.25, 0.5, 0.5]
    assert saved_digest(environment) == [(("Other", ""), [
        ("Item 0", "Zero", False), ("Item 1", None, True),
    ])]


class LongSummaryModel(FakeModel):
    def chat_json(self, messages, max_tokens):
        if '"summary"' in messages[0]["content"]:
            self.calls.append((messages, max_tokens))
            return {"summary": "word " * 120}
        return super().chat_json(messages, max_tokens)


def grouping_calls(model):
    return [
        (messages, max_tokens) for messages, max_tokens in model.calls
        if "item_refs" in messages[0]["content"] or "topic_refs" in messages[0]["content"]
    ]


def test_run_with_a_small_context_window_groups_in_batches_that_fit(environment, monkeypatch):
    seed(environment, count=60)
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        session.get(ModelConfig, 1).context_window = 8192
        session.commit()
    model = LongSummaryModel()
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    calls = grouping_calls(model)
    assert len(calls) > 1
    for messages, max_tokens in calls:
        system, user = messages[0]["content"], messages[1]["content"]
        assert len(system) + len(user) + max_tokens <= 8192
        assert max_tokens <= 4096
        if "item_refs" in system:
            assert len(user) <= 2096
    rows = all_rows(environment, DigestItem)
    assert len(rows) == 60 and len({row.item_id for row in rows}) == 60


def test_run_with_no_known_context_window_groups_in_one_call(environment, monkeypatch):
    seed(environment, count=60)
    stub_collection(monkeypatch)
    model = LongSummaryModel()
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    assert [max_tokens for _, max_tokens in grouping_calls(model)] == [9632]


@pytest.mark.parametrize("status", [500, 404])
def test_run_where_every_model_call_fails_with_a_status_error_keeps_items_pending(
        environment, monkeypatch, status):
    seed(environment, count=2)
    stub_collection(monkeypatch)

    def handle(request: httpx2.Request) -> httpx2.Response:
        if request.method == "GET" and request.url.path.endswith("/models"):
            return httpx2.Response(200, json={"object": "list", "data": []})
        return httpx2.Response(status, json={"error": {"message": "unavailable"}})

    environment.app.state.model_client_factory = lambda base, key, model: ModelClient(
        base, key, model, http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=lambda _: None,
    )
    result = execute(environment)
    assert (result["status"], result["error_kind"]) == ("failed", "provider_error")
    assert all_rows(environment, Digest) == [] and all_rows(environment, DigestItem) == []
    assert [(row.state, row.summary) for row in all_rows(environment, Item)] == [("pending", None)] * 2


class RateLimitedGroupingModel(FakeModel):
    def chat_json(self, messages, max_tokens):
        self.calls.append((messages, max_tokens))
        if '"summary"' in messages[0]["content"]:
            return {"summary": "English summary"}
        raise RateLimited("The provider is rate limiting requests.")


def test_rate_limiting_during_grouping_keeps_items_pending(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    environment.app.state.model_client_factory = lambda *_: RateLimitedGroupingModel()
    result = execute(environment)
    assert (result["status"], result["error_kind"]) == ("failed", "rate_limited")
    assert all_rows(environment, Digest) == []
    assert [row.state for row in all_rows(environment, Item)] == ["pending", "pending"]
