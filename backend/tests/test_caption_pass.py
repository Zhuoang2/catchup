from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from catchup.models import AppSettings, Item, Source
from test_digest_runner import FakeModel, environment, execute, seed, stub_collection

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


@pytest.fixture
def ready(environment, monkeypatch):
    seed(environment, count=0, sources=0)
    stub_collection(monkeypatch)
    monkeypatch.setattr("catchup.digest.runner.utc_now", lambda: NOW)
    model = FakeModel()
    environment.app.state.model_client_factory = lambda *_args: model
    return environment, model


def videos(client, count, *, status="to_fetch", captions=True, shorts=False, discovered=None):
    with client.app.state.session_factory() as session:
        session.get(AppSettings, 1).youtube_captions = captions
        source = Source(title="Channel", kind="youtube", site_url="https://www.youtube.com/",
                        feed_url="https://www.youtube.com/feeds/videos.xml?channel_id=abc",
                        input_url="https://www.youtube.com/channel/abc")
        session.add(source)
        session.flush()
        for index in range(count):
            session.add(Item(
                source_id=source.id, identity_key=f"yt:video:video{index}",
                link=f"https://www.youtube.com/{'shorts/' if shorts else 'watch?v='}video{index}",
                title=f"Video {index}", content_text="Description not spoken",
                content_origin="feed", state="pending", transcript_status=status,
                discovered_at=discovered or NOW,
            ))
        session.commit()


def test_captions_off_creates_creator_updates_without_fetch_or_model(ready, monkeypatch):
    client, model = ready
    videos(client, 2, captions=False)
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: pytest.fail("captions off must not contact YouTube"))
    result = execute(client)
    assert result["status"] == "succeeded"
    assert model.calls == []
    data = client.get(f"/api/digests/{result['digest_id']}").json()
    assert data["topics"] == []
    assert [item["reason"] for item in data["creator_updates"][0]["items"]] == ["captions_off"] * 2


def test_twenty_of_twenty_five_fetched_oldest_then_deferred(ready, monkeypatch):
    client, _ = ready
    videos(client, 25)
    called = []

    def fetch(video_id, spacer):
        called.append(video_id)
        return "found", f"Spoken {video_id}"

    monkeypatch.setattr("catchup.digest.runner.fetch_captions", fetch)
    result = execute(client)
    assert result["status"] == "succeeded"
    assert result["deferred_count"] == 5
    assert called == [f"video{i}" for i in range(20)]
    with client.app.state.session_factory() as session:
        rows = session.scalars(select(Item).order_by(Item.id)).all()
        assert [row.transcript_status for row in rows] == ["found"] * 20 + ["to_fetch"] * 5
        assert [row.state for row in rows] == ["delivered"] * 20 + ["pending"] * 5
    result = execute(client)
    assert result["status"] == "succeeded"
    assert called[-5:] == [f"video{i}" for i in range(20, 25)]


def test_block_stops_subsequent_caption_requests(ready, monkeypatch):
    client, _ = ready
    videos(client, 10)
    called = []

    def fetch(video_id, spacer):
        called.append(video_id)
        return ("blocked", None) if video_id == "video2" else ("found", f"Spoken {video_id}")

    monkeypatch.setattr("catchup.digest.runner.fetch_captions", fetch)
    result = execute(client)
    assert called == ["video0", "video1", "video2"]
    assert result["deferred_count"] == 7
    with client.app.state.session_factory() as session:
        statuses = session.scalars(select(Item.transcript_status).order_by(Item.id)).all()
        assert statuses == ["found", "found", "blocked"] + ["to_fetch"] * 7
    assert client.get(f"/api/digests/{result['digest_id']}").json()["creator_updates"][0]["items"][0]["reason"] == "blocked"


def test_wait_retried_before_new_video_and_remaining_new_deferred(ready, monkeypatch):
    client, _ = ready
    client.app.state.settings = replace(client.app.state.settings, captions_per_run=1)
    videos(client, 2, status="caption_wait", discovered=NOW - timedelta(hours=1))
    with client.app.state.session_factory() as session:
        second = session.scalar(select(Item).where(Item.identity_key == "yt:video:video1"))
        second.transcript_status = None
        second.discovered_at = NOW
        session.commit()
    called = []
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda video_id, _spacer: (called.append(video_id) or ("caption_wait", None)))
    result = execute(client)
    assert called == ["video0"]
    assert result["waiting_count"] == 1
    assert result["deferred_count"] == 1
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.transcript_status).where(Item.identity_key == "yt:video:video1")) == "to_fetch"


def test_caption_wait_retries_then_finds_caption(ready, monkeypatch):
    client, _ = ready
    videos(client, 1, status="caption_wait", discovered=NOW - timedelta(hours=6))
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: ("found", "Transcript now available"))
    result = execute(client)
    assert result["status"] == "succeeded"
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.content_text == "Transcript now available"
        assert item.content_origin == "transcript"
        assert item.state == "delivered"


def test_turning_captions_off_ends_wait(ready, monkeypatch):
    client, model = ready
    videos(client, 1, status="caption_wait", captions=False, discovered=NOW - timedelta(hours=1))
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: pytest.fail("captions off must not fetch"))
    result = execute(client)
    assert result["status"] == "succeeded"
    assert model.calls == []
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.transcript_status)) == "captions_off"


def test_caption_off_item_from_failed_run_refetched_when_on(ready, monkeypatch):
    client, _ = ready
    videos(client, 1, status="captions_off")
    called = []
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda video_id, _spacer: (called.append(video_id) or ("found", "Transcript")))
    assert execute(client)["status"] == "succeeded"
    assert called == ["video0"]


def test_preexisting_short_does_not_call_caption_library(ready, monkeypatch):
    client, _ = ready
    videos(client, 1, status="to_fetch", shorts=True)
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: pytest.fail("Short must be skipped"))
    assert execute(client)["status"] == "no_new_content"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.state)) == "baseline"


def test_wait_item_skipped_after_block_keeps_wait_status(ready, monkeypatch):
    client, _ = ready
    videos(client, 2, status="caption_wait", discovered=NOW - timedelta(hours=1))
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda video_id, _spacer: ("blocked", None))
    result = execute(client)
    assert result["waiting_count"] == 1
    assert result["deferred_count"] == 0
    with client.app.state.session_factory() as session:
        assert session.scalars(select(Item.transcript_status).order_by(Item.id)).all() == [
            "blocked", "caption_wait",
        ]


def test_unexpected_caption_exception_becomes_failed_reason(ready, monkeypatch, caplog):
    client, model = ready
    videos(client, 1)

    def fail(*_args):
        raise KeyError("confidential payload")

    monkeypatch.setattr("catchup.digest.runner.fetch_captions", fail)
    result = execute(client)
    assert result["status"] == "succeeded"
    assert model.calls == []
    assert client.get(f"/api/digests/{result['digest_id']}").json()["creator_updates"][0]["items"][0]["reason"] == "captions_failed"
    assert "confidential payload" not in caplog.text


def test_upgraded_youtube_feed_uses_caption_rules_for_old_items(ready, monkeypatch):
    client, model = ready
    videos(client, 1, status=None, captions=False)
    with client.app.state.session_factory() as session:
        session.scalar(select(Source)).kind = "feed"
        session.commit()

    def upgraded_check(session, source, run_id, _settings, *, spacer=None, transcripts=None):
        source.kind = "youtube"
        session.commit()

    monkeypatch.setattr("catchup.digest.runner.check_source", upgraded_check)
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: pytest.fail("off by default"))
    result = execute(client)
    assert result["status"] == "succeeded"
    assert model.calls == []
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.transcript_status)) == "captions_off"
