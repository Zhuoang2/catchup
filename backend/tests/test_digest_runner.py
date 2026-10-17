import threading
import socket
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from catchup.crypto import encrypt_key
from catchup.digest.runner import run_digest, start_run
from catchup.llm.client import AuthFailed, InsufficientBalance, ProviderError
from catchup.llm.client import ModelInfo
from catchup.main import create_app
from catchup.models import (
    AppSettings, Digest, DigestItem, DigestRun, DigestTopic, Item, ModelConfig, Source, SourceCheck,
)
from catchup.net.host_spacing import HostSpacer
from catchup.net.safe_fetch import RATE_LIMIT_PREFIX
import httpx
import respx


class FakeModel:
    def __init__(self, responses=None):
        self.responses = iter(responses) if responses is not None else None
        self.calls = []

    def chat_json(self, messages, max_tokens):
        self.calls.append((messages, max_tokens))
        if self.responses is not None:
            result = next(self.responses)
            if isinstance(result, Exception):
                raise result
            return result
        if '"summary"' in messages[0]["content"]:
            return {"summary": "English summary"}
        return {"topics": [{"title": "Technology", "overview": "News",
                            "item_refs": [f"i{n}" for n in range(1, 141)]}]}

    def close(self):
        pass

    def list_models(self):
        return []

    def usage_totals(self):
        return None


@pytest.fixture
def environment(test_settings):
    settings = replace(test_settings, secret_key="a test-only instance secret")
    with TestClient(create_app(settings)) as client:
        client.app.state.model_client_factory = lambda *_: FakeModel()
        yield client


def seed(client, count=1, sources=1, language="en"):
    with client.app.state.session_factory() as session:
        session.add(ModelConfig(id=1, base_url="https://model.example", model_id="test",
                                api_key_encrypted=encrypt_key("fake-key", client.app.state.settings.secret_key),
                                api_key_last4="-key"))
        session.add(AppSettings(id=1, digest_language=language))
        for n in range(sources):
            source = Source(title=f"Source {n}", site_url=f"https://s{n}.example/",
                            feed_url=f"https://s{n}.example/feed", input_url=f"https://s{n}.example/feed")
            session.add(source)
            session.flush()
            for index in range(n, count, sources):
                session.add(Item(source_id=source.id, identity_key=str(index),
                                 link=f"https://s{n}.example/{index}", title=f"Item {index}",
                                 content_text="Original content", content_origin="feed", state="pending",
                                 published_at=datetime(2026, 10, 3, tzinfo=timezone.utc)))
        session.commit()


def stub_collection(monkeypatch, on_check=None):
    def check(session, source, run_id, _settings, *, spacer=None, transcripts=None):
        if on_check:
            on_check()
        row = SourceCheck(run_id=run_id, source_id=source.id, status="no_new_items",
                          entries_seen=0, new_count=0)
        session.add(row)
        session.commit()
        return row
    monkeypatch.setattr("catchup.digest.runner.check_source", check)


def stub_outcomes(monkeypatch, statuses):
    def check(session, source, run_id, _settings, *, spacer=None, transcripts=None):
        status = statuses[source.title]
        row = SourceCheck(
            run_id=run_id, source_id=source.id, status=status,
            entries_seen=1 if status == "new_items" else 0,
            new_count=1 if status == "new_items" else 0,
            error="feed unavailable" if status == "failed" else None,
        )
        source.last_check_status = status
        session.add(row)
        session.commit()
        return row
    monkeypatch.setattr("catchup.digest.runner.check_source", check)


def run_checks(client, run_id):
    with client.app.state.session_factory() as session:
        return session.scalars(
            select(SourceCheck).where(SourceCheck.run_id == run_id).order_by(SourceCheck.source_id)
        ).all()


def all_rows(client, model):
    with client.app.state.session_factory() as session:
        return session.scalars(select(model)).all()


def execute(client):
    run = start_run(client.app, background=False)
    run_digest(client.app, run.id)
    return client.get(f"/api/digest-runs/{run.id}").json()


def test_long_gap_snapshots_every_item_once_and_delivers_atomically(environment, monkeypatch):
    seed(environment, count=140, sources=2)
    stub_collection(monkeypatch)
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert result["items_done"] == result["items_total"] == 140
    assert result["sources_total"] == len(result["source_checks"]) == 2
    assert len(all_rows(environment, DigestItem)) == 140
    assert len({row.item_id for row in all_rows(environment, DigestItem)}) == 140
    assert len(all_rows(environment, DigestTopic)) == 1
    assert all(item.state == "delivered" for item in all_rows(environment, Item))
    assert all(row.summary_language == "en" for row in all_rows(environment, Item))
    assert all(row.link.startswith("https://s") and row.source_name.startswith("Source ")
               for row in all_rows(environment, DigestItem))


def test_group_failure_preserves_pending_and_retry_uses_cached_summary(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)
    first = FakeModel([{"summary": "Cached"}, ProviderError("group failed")])
    environment.app.state.model_client_factory = lambda *_: first
    failed = execute(environment)
    assert failed["status"] == "failed" and failed["error_kind"] == "provider_error"
    assert failed["digest_item_count"] is None and failed["digest_update_count"] is None
    assert all_rows(environment, Digest) == []
    assert all_rows(environment, Item)[0].state == "pending"
    retry = FakeModel([{"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]}])
    environment.app.state.model_client_factory = lambda *_: retry
    succeeded = execute(environment)
    assert succeeded["status"] == "succeeded"
    assert succeeded["source_checks"][0]["status"] == "new_items"
    assert run_checks(environment, succeeded["id"])[0].new_count == 1
    assert len(retry.calls) == 1
    assert all_rows(environment, DigestItem)[0].summary == "Cached"


def test_carried_over_item_sets_final_outcome_in_run_and_sources(environment, monkeypatch):
    seed(environment)
    stub_outcomes(monkeypatch, {"Source 0": "no_new_items"})
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert result["source_checks"][0]["status"] == "new_items"
    assert run_checks(environment, result["id"])[0].new_count == 1
    assert environment.get("/api/sources").json()[0]["last_check_status"] == "new_items"


def test_only_source_with_included_item_reports_new_items(environment, monkeypatch):
    seed(environment, count=1, sources=2)
    stub_outcomes(monkeypatch, {"Source 0": "no_new_items", "Source 1": "no_new_items"})
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert [check["status"] for check in result["source_checks"]] == ["new_items", "no_new_items"]
    assert [check.new_count for check in run_checks(environment, result["id"])] == [1, 0]
    assert [source["last_check_status"] for source in environment.get("/api/sources").json()] == [
        "new_items", "no_new_items",
    ]


def test_held_podcast_episode_is_waiting_not_new(environment, monkeypatch):
    seed(environment)
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    monkeypatch.setattr("catchup.digest.runner.utc_now", lambda: now)
    with environment.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        source.kind = "podcast"
        item = session.scalar(select(Item))
        item.transcript_status = "waiting"
        item.discovered_at = now - timedelta(days=1)
        source.last_check_status = "new_items"
        session.commit()
    stub_collection(monkeypatch)
    result = execute(environment)
    assert result["status"] == "no_new_content" and result["waiting_count"] == 1
    assert result["source_checks"][0]["status"] == "no_new_items"
    assert run_checks(environment, result["id"])[0].new_count == 0
    assert environment.get("/api/sources").json()[0]["last_check_status"] == "no_new_items"


def test_skipped_short_recorded_as_new_is_not_included(environment, monkeypatch):
    seed(environment)
    with environment.app.state.session_factory() as session:
        session.scalar(select(Source)).kind = "youtube"
        item = session.scalar(select(Item))
        item.link = "https://www.youtube.com/shorts/short-id"
        item.state = "baseline"
        session.commit()
    stub_outcomes(monkeypatch, {"Source 0": "new_items"})
    result = execute(environment)
    assert result["status"] == "no_new_content"
    assert result["source_checks"][0]["status"] == "no_new_items"
    assert run_checks(environment, result["id"])[0].new_count == 0
    assert environment.get("/api/sources").json()[0]["last_check_status"] == "no_new_items"


def test_failed_check_keeps_error_even_when_item_is_included(environment, monkeypatch):
    seed(environment, count=1, sources=2)
    stub_outcomes(monkeypatch, {"Source 0": "failed", "Source 1": "new_items"})
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert [(check["status"], check["error"]) for check in result["source_checks"]] == [
        ("failed", "feed unavailable"), ("no_new_items", None),
    ]
    assert [check.new_count for check in run_checks(environment, result["id"])] == [0, 0]
    assert [source["last_check_status"] for source in environment.get("/api/sources").json()] == [
        "failed", "no_new_items",
    ]


def test_check_that_saw_item_but_has_nothing_pending_reports_no_new_content(environment, monkeypatch):
    seed(environment, count=0)
    stub_outcomes(monkeypatch, {"Source 0": "new_items"})
    result = execute(environment)
    assert result["status"] == "no_new_content"
    assert result["source_checks"][0]["status"] == "no_new_items"
    assert run_checks(environment, result["id"])[0].new_count == 0
    assert environment.get("/api/sources").json()[0]["last_check_status"] == "no_new_items"


def test_creator_updates_count_toward_their_source_outcome(environment, monkeypatch):
    seed(environment, count=3, sources=2)
    with environment.app.state.session_factory() as session:
        episode = session.scalar(select(Item).where(Item.source_id == 2))
        episode.transcript_status = "no_transcript"
        session.commit()
    stub_collection(monkeypatch)
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert [(check.status, check.new_count) for check in run_checks(environment, result["id"])] == [
        ("new_items", 2), ("new_items", 1),
    ]
    assert [check["status"] for check in result["source_checks"]] == ["new_items", "new_items"]
    assert result["digest_update_count"] == 1


def test_final_outcomes_are_committed_before_first_summary_call(environment, monkeypatch):
    seed(environment, count=2, sources=2)
    stub_collection(monkeypatch)
    observed = []
    first_call = threading.Lock()

    class InspectingModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            with first_call:
                if not observed:
                    with environment.app.state.session_factory() as session:
                        checks = session.scalars(select(SourceCheck).order_by(SourceCheck.source_id)).all()
                        sources = session.scalars(select(Source).order_by(Source.id)).all()
                        observed.append((
                            [(check.status, check.new_count) for check in checks],
                            [source.last_check_status for source in sources],
                        ))
            return super().chat_json(messages, max_tokens)

    environment.app.state.model_client_factory = lambda *_: InspectingModel()
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert observed == [([("new_items", 1), ("new_items", 1)], ["new_items", "new_items"])]


def test_save_failure_rolls_back_snapshot_and_delivery(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)

    def reject_snapshot(*_args):
        raise RuntimeError("snapshot insert rejected")

    event.listen(DigestItem, "before_insert", reject_snapshot)
    try:
        result = execute(environment)
    finally:
        event.remove(DigestItem, "before_insert", reject_snapshot)
    assert result["status"] == "failed"
    assert all_rows(environment, Digest) == []
    assert all_rows(environment, DigestTopic) == []
    assert all_rows(environment, Item)[0].state == "pending"


def test_unexpected_failure_is_logged_without_key_or_collected_content(environment, monkeypatch, caplog):
    seed(environment)
    stub_collection(monkeypatch)
    secret = "fake-key"
    content = "Original content"

    def fail(*_args):
        raise RuntimeError(f"failed with {secret} and {content}")

    monkeypatch.setattr("catchup.digest.runner.group_items", fail)
    with caplog.at_level("ERROR", logger="catchup.digest.runner"):
        result = execute(environment)
    assert result["status"] == "failed" and result["error_kind"] == "run_failed"
    assert "Unexpected digest generation failure" in caplog.text
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text
    assert content not in caplog.text
    assert "https://model.example" not in caplog.text


def test_deleted_source_during_grouping_saves_only_surviving_items(environment, monkeypatch):
    seed(environment, count=2, sources=2)
    stub_collection(monkeypatch)

    class DeletingModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            if '"item_refs"' in messages[0]["content"]:
                with environment.app.state.session_factory() as session:
                    session.delete(session.get(Source, 1))
                    session.commit()
            return super().chat_json(messages, max_tokens)

    environment.app.state.model_client_factory = lambda *_: DeletingModel()
    result = execute(environment)
    assert result["status"] == "succeeded"
    digest = all_rows(environment, Digest)[0]
    assert (digest.item_count, digest.source_count) == (1, 1)
    assert [row.title for row in all_rows(environment, DigestItem)] == ["Item 1"]
    assert all_rows(environment, Item)[0].state == "delivered"


def test_all_items_deleted_during_grouping_does_not_save_empty_digest(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)

    class DeletingModel(FakeModel):
        def usage_totals(self):
            return (12, 4)

        def chat_json(self, messages, max_tokens):
            if '"item_refs"' in messages[0]["content"]:
                with environment.app.state.session_factory() as session:
                    session.delete(session.get(Source, 1))
                    session.commit()
            return super().chat_json(messages, max_tokens)

    environment.app.state.model_client_factory = lambda *_: DeletingModel()
    result = execute(environment)
    assert result["status"] == "no_new_content"
    assert (result["prompt_tokens"], result["completion_tokens"]) == (12, 4)
    assert all_rows(environment, Digest) == []


def test_run_and_saved_digest_show_reported_tokens(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)

    class UsageModel(FakeModel):
        def usage_totals(self):
            return (25, 10)

    environment.app.state.model_client_factory = lambda *_args: UsageModel()
    result = execute(environment)
    assert result["status"] == "succeeded"
    assert (result["prompt_tokens"], result["completion_tokens"]) == (25, 10)
    digest = environment.get(f"/api/digests/{result['digest_id']}").json()
    assert (digest["prompt_tokens"], digest["completion_tokens"]) == (25, 10)


def test_failed_run_preserves_reported_usage(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)

    class UsageModel(FakeModel):
        def usage_totals(self):
            return (7, 2)

    environment.app.state.model_client_factory = lambda *_args: UsageModel([
        {"summary": "Summary"}, ProviderError("group failed"),
    ])
    result = execute(environment)
    assert result["status"] == "failed"
    assert (result["prompt_tokens"], result["completion_tokens"]) == (7, 2)


def test_source_deleted_during_summarization_is_skipped(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)

    class DeletingModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            if '"summary"' in messages[0]["content"]:
                with environment.app.state.session_factory() as session:
                    session.delete(session.get(Source, 1))
                    session.commit()
            return super().chat_json(messages, max_tokens)

    environment.app.state.model_client_factory = lambda *_: DeletingModel()
    result = execute(environment)
    assert result["status"] == "no_new_content"
    assert all_rows(environment, Digest) == []


@pytest.mark.parametrize("failure", [AuthFailed("Rejected key"), InsufficientBalance("No balance")])
def test_auth_or_balance_fails_immediately_with_pending_items(environment, monkeypatch, failure):
    seed(environment, count=5)
    stub_collection(monkeypatch)
    model = FakeModel([failure] * 5)
    environment.app.state.model_client_factory = lambda *_: model
    result = execute(environment)
    assert result["status"] == "failed" and result["error_kind"] == failure.code
    assert "model settings" in result["error_message"]
    assert all(item.state == "pending" for item in all_rows(environment, Item))
    assert all_rows(environment, Digest) == []


def test_item_model_failure_is_unavailable_not_a_failed_run(environment, monkeypatch):
    seed(environment)
    stub_collection(monkeypatch)
    model = FakeModel([ProviderError("temporary"),
                       {"topics": [{"title": "T", "overview": "O", "item_refs": ["i1"]}]}])
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    snapshot = all_rows(environment, DigestItem)[0]
    assert snapshot.summary is None and snapshot.summary_unavailable
    assert snapshot.title == "Item 0" and snapshot.link.endswith("/0")


def test_missing_group_ref_goes_to_other_and_unknown_ref_is_ignored(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    model = FakeModel([
        {"summary": "One"}, {"summary": "Two"},
        {"topics": [{"title": "Chosen", "overview": "O", "item_refs": ["i1", "i999"]}]},
    ])
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    assert {topic.title for topic in all_rows(environment, DigestTopic)} == {"Chosen", "Other"}
    assert len(all_rows(environment, DigestItem)) == 2


def test_no_content_reports_failed_source_without_digest(environment, monkeypatch):
    seed(environment, count=0, sources=2)

    def check(session, source, run_id, _settings, *, spacer=None, transcripts=None):
        row = SourceCheck(run_id=run_id, source_id=source.id, status="failed",
                          error="offline", possible_gap=True)
        session.add(row)
        session.commit()
        return row
    monkeypatch.setattr("catchup.digest.runner.check_source", check)
    result = execute(environment)
    assert result["status"] == "no_new_content" and result["digest_id"] is None
    assert len(result["source_checks"]) == 2
    assert result["source_checks"][0]["error"] == "offline"
    assert all_rows(environment, Digest) == []


def test_runner_caches_matching_context_window(environment, monkeypatch):
    seed(environment, count=0)
    stub_collection(monkeypatch)

    class WindowModel(FakeModel):
        reads = 0

        def list_models(self):
            self.reads += 1
            return [ModelInfo("other", 2048), ModelInfo("test", 1_000_000)]

    model = WindowModel()
    environment.app.state.model_client_factory = lambda *_args: model
    assert execute(environment)["status"] == "no_new_content"
    with environment.app.state.session_factory() as session:
        assert session.get(ModelConfig, 1).context_window == 1_000_000
    assert execute(environment)["status"] == "no_new_content"
    assert model.reads == 1


@pytest.mark.parametrize("bad_client", [
    type("MissingList", (), {"close": lambda self: None}),
    type("FailedList", (), {"close": lambda self: None,
                             "list_models": lambda self: (_ for _ in ()).throw(RuntimeError("failure"))}),
])
def test_model_list_failure_does_not_block_run(environment, monkeypatch, bad_client):
    seed(environment, count=0)
    stub_collection(monkeypatch)
    environment.app.state.model_client_factory = lambda *_args: bad_client()
    assert execute(environment)["status"] == "no_new_content"
    with environment.app.state.session_factory() as session:
        assert session.get(ModelConfig, 1).context_window is None


def test_language_change_resummarizes_and_keeps_old_snapshot(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    first = FakeModel([{"summary": "English"}, {"summary": "English"},
                       {"topics": [{"title": "English", "overview": "English", "item_refs": ["i1", "i2"]}]}])
    environment.app.state.model_client_factory = lambda *_: first
    assert execute(environment)["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        session.get(AppSettings, 1).digest_language = "zh-Hans"
        session.scalars(select(Item)).first().state = "pending"
        session.commit()
    next_model = FakeModel([{"summary": "中文"},
                            {"topics": [{"title": "中文", "overview": "中文", "item_refs": ["i1"]}]}])
    environment.app.state.model_client_factory = lambda *_: next_model
    assert execute(environment)["status"] == "succeeded"
    assert "Simplified Chinese" in str(next_model.calls)
    assert [row.summary for row in all_rows(environment, DigestItem)] == [
        "English", "English", "中文",
    ]


def test_language_is_read_once_before_collection(environment, monkeypatch):
    seed(environment)

    def change_language():
        with environment.app.state.session_factory() as session:
            session.get(AppSettings, 1).digest_language = "zh-Hans"
            session.commit()

    stub_collection(monkeypatch, change_language)
    model = FakeModel()
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    assert "Write the summary in English" in str(model.calls[0])
    assert all_rows(environment, Item)[0].summary_language == "en"


def test_recovery_marks_unfinished_failed_and_allows_retry(test_settings, monkeypatch):
    settings = replace(test_settings, secret_key="a test-only instance secret")
    with TestClient(create_app(settings)) as client:
        seed(client)
        with client.app.state.session_factory() as session:
            session.add(DigestRun(status="summarizing", items_total=1))
            session.commit()
    with TestClient(create_app(settings)) as restarted:
        stub_collection(monkeypatch)
        restarted.app.state.model_client_factory = lambda *_: FakeModel()
        previous = restarted.get("/api/digest-runs/1").json()
        assert previous["status"] == "failed" and previous["error_kind"] == "interrupted"
        assert all_rows(restarted, Item)[0].state == "pending"
        assert execute(restarted)["status"] == "succeeded"


def test_api_rejects_unconfigured_and_reports_active_progress(environment, monkeypatch):
    assert environment.post("/api/digest-runs").json()["error"]["code"] == "model_not_configured"
    assert environment.get("/api/digest-runs/active").json() is None
    seed(environment, count=1, sources=2)
    entered, release = threading.Event(), threading.Event()

    checks = 0

    def blocked():
        nonlocal checks
        checks += 1
        if checks == 2:
            entered.set()
            assert release.wait(timeout=5)

    stub_collection(monkeypatch, blocked)
    finished = threading.Event()
    from catchup.digest import runner
    original = runner.run_digest

    def signaled(app, run_id):
        try:
            original(app, run_id)
        finally:
            finished.set()

    monkeypatch.setattr(runner, "run_digest", signaled)
    response = environment.post("/api/digest-runs")
    assert response.status_code == 202
    run_id = response.json()["id"]
    assert entered.wait(timeout=5)
    active = environment.get("/api/digest-runs/active").json()
    assert active["id"] == run_id and active["status"] == "collecting"
    assert active["sources_total"] == 2 and len(active["source_checks"]) == 1
    conflict = environment.post("/api/digest-runs")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["active_run_id"] == run_id
    release.set()
    assert finished.wait(timeout=5)
    detail = environment.get(f"/api/digest-runs/{run_id}").json()
    assert detail["status"] == "succeeded"
    assert detail["items_total"] == detail["items_done"] == 1
    assert len(detail["source_checks"]) == 2
    assert environment.get("/api/digest-runs/active").json() is None
    assert environment.get("/api/digest-runs/9999").status_code == 404


@pytest.mark.parametrize("same_host", [True, False])
def test_runner_spaces_same_host_checks_without_delaying_other_hosts(environment, monkeypatch, same_host):
    seed(environment, count=0, sources=2)
    with environment.app.state.session_factory() as session:
        sources = session.scalars(select(Source).order_by(Source.id)).all()
        sources[0].feed_url = "https://site.example/one"
        sources[1].feed_url = f"https://{'site' if same_host else 'other'}.example/two"
        session.commit()

    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    now = [10.0]
    starts = []
    sleeps = []

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(
        "catchup.digest.runner.HostSpacer",
        lambda: HostSpacer(clock=lambda: now[0], sleep=advance),
    )

    def answer(_request):
        starts.append(now[0])
        return httpx.Response(200, content=b"<rss><channel><title>Empty</title></channel></rss>")

    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/one").mock(side_effect=answer)
        router.get(sources[1].feed_url).mock(side_effect=answer)
        result = execute(environment)
    assert result["status"] == "no_new_content"
    assert len(starts) == 2
    assert starts[1] - starts[0] == (1.0 if same_host else 0.0)
    assert sleeps == ([1.0] if same_host else [])


@pytest.mark.parametrize("status,error,expected", [
    (429, f"{RATE_LIMIT_PREFIX} Try again in about 120 seconds.", True),
    (503, f"{RATE_LIMIT_PREFIX} Try again in about 120 seconds.", True),
    (503, "The source could not be fetched.", False),
])
def test_run_detail_identifies_only_rate_limited_checks(environment, status, error, expected):
    seed(environment, count=0)
    with environment.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        run = DigestRun(status="no_new_content")
        session.add(run)
        session.flush()
        session.add(SourceCheck(source_id=source.id, run_id=run.id, status="failed",
                                http_status=status, error=error, entries_seen=0, new_count=0))
        session.commit()
        run_id = run.id
    check = environment.get(f"/api/digest-runs/{run_id}").json()["source_checks"][0]
    assert check["status"] == "failed"
    assert check["http_status"] == status
    assert check["rate_limited"] is expected


def test_rate_limited_run_check_is_visible_in_progress_and_source_list(environment, monkeypatch):
    seed(environment, count=0)
    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://s0.example/feed").mock(return_value=httpx.Response(
            429, headers={"Retry-After": "120"},
        ))
        result = execute(environment)
    assert route.call_count == 1
    assert route.calls[0].request.headers["user-agent"].startswith("CatchUp/")
    assert result["status"] == "no_new_content"
    check = result["source_checks"][0]
    assert (check["status"], check["http_status"], check["rate_limited"]) == ("failed", 429, True)
    assert "about 120 seconds" in check["error"]
    listed = environment.get("/api/sources").json()[0]
    assert (listed["last_check_status"], listed["http_status"], listed["rate_limited"]) == ("failed", 429, True)
