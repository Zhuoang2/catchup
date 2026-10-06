from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, select

from catchup.models import AppSettings, Digest, DigestItem, DigestTopic, Item, Source, SourceCheck
from test_digest_runner import FakeModel, environment, execute, seed, stub_collection

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def add_item(client, kind, status, *, days_ago=0, title="Item", source_title="Show", published=None):
    with client.app.state.session_factory() as session:
        url = f"https://site.example/{source_title}-{kind}"
        source = session.scalar(select(Source).where(Source.feed_url == url))
        if source is None:
            source = Source(
                title=source_title, kind=kind, site_url="https://site.example/",
                feed_url=url, input_url=url,
            )
            session.add(source)
            session.flush()
        item = Item(
            source_id=source.id,
            identity_key=f"yt:video:{title}" if kind == "youtube" else title,
            link=f"https://www.youtube.com/watch?v={title}" if kind == "youtube"
                 else f"https://site.example/{title}",
            title=title, published_at=published, discovered_at=NOW - timedelta(days=days_ago),
            content_text="Descriptions must not reach the model", content_origin="feed",
            state="pending", transcript_status=status,
        )
        session.add(item)
        session.commit()
        return item.id


@pytest.fixture
def ready(environment, monkeypatch):
    seed(environment, count=0, sources=0)
    stub_collection(monkeypatch)
    monkeypatch.setattr("catchup.digest.runner.utc_now", lambda: NOW)
    fake = FakeModel()
    environment.app.state.model_client_factory = lambda *_args: fake
    return environment, fake


def test_episode_waits_then_is_delivered_once(ready):
    client, fake = ready
    item_id = add_item(client, "podcast", "waiting", days_ago=1)
    first = execute(client)
    assert first["status"] == "no_new_content"
    assert first["waiting_count"] == 1
    with client.app.state.session_factory() as session:
        assert session.get(Item, item_id).state == "pending"
        session.get(Item, item_id).discovered_at = NOW - timedelta(days=8)
        session.commit()
    second = execute(client)
    assert second["status"] == "succeeded"
    assert not fake.calls
    digest = client.get(f"/api/digests/{second['digest_id']}").json()
    assert digest["topics"] == []
    assert digest["creator_updates"] == [{"source_name": "Show", "items": [{
        "title": "Item", "link": "https://site.example/Item", "published_at": None,
        "reason": "no_transcript",
    }]}]
    assert digest["transcript_wait_days"] == 7
    with client.app.state.session_factory() as session:
        assert session.get(Item, item_id).transcript_status == "no_transcript"
        assert session.get(Item, item_id).state == "delivered"
        assert session.scalar(select(Digest.item_count)) == 1
    assert execute(client)["status"] == "no_new_content"
    assert len(fake.calls) == 0


def test_only_held_items_and_failed_feed_still_expire(ready):
    client, _ = ready
    add_item(client, "podcast", "to_fetch", days_ago=8)
    add_item(client, "youtube", "caption_wait", days_ago=2, source_title="Channel")
    add_item(client, "youtube", "unplayable_wait", days_ago=2, source_title="Premiere")
    add_item(client, "youtube", "to_fetch", days_ago=1, source_title="Deferred")
    result = execute(client)
    assert result["status"] == "succeeded" and result["deferred_count"] == 0
    reasons = {
        group["source_name"]: group["items"][0]["reason"]
        for group in client.get(f"/api/digests/{result['digest_id']}").json()["creator_updates"]
    }
    assert reasons == {"Show": "no_transcript", "Channel": "no_captions",
                       "Premiere": "captions_failed", "Deferred": "captions_off"}
    assert execute(client)["status"] == "no_new_content"


@pytest.mark.parametrize("status", [None, "to_fetch", "waiting"])
def test_expired_podcast_item_is_selected_even_when_feed_fails(ready, monkeypatch, status):
    client, _ = ready
    item_id = add_item(client, "podcast", status, days_ago=8)

    def failed_check(session, source, run_id, _settings, *, spacer=None, transcripts=None):
        check = SourceCheck(run_id=run_id, source_id=source.id, status="failed",
                            error="feed unavailable", entries_seen=0, new_count=0)
        session.add(check)
        session.commit()
        return check

    monkeypatch.setattr("catchup.digest.runner.check_source", failed_check)
    result = execute(client)
    assert result["status"] == "succeeded"
    assert result["source_checks"][0]["status"] == "failed"
    with client.app.state.session_factory() as session:
        assert session.get(Item, item_id).transcript_status == "no_transcript"


def test_no_new_content_includes_wait_and_deferred_counts(ready, monkeypatch):
    client, fake = ready
    client.app.state.settings = replace(client.app.state.settings, captions_per_run=1)
    with client.app.state.session_factory() as session:
        session.get(AppSettings, 1).youtube_captions = True
        session.commit()
    monkeypatch.setattr("catchup.digest.runner.fetch_captions",
                        lambda *_args: ("caption_wait", None))
    add_item(client, "podcast", None, days_ago=1)
    add_item(client, "youtube", "caption_wait", days_ago=0)
    add_item(client, "youtube", "to_fetch", days_ago=0, source_title="Other")
    result = execute(client)
    assert (result["status"], result["waiting_count"], result["deferred_count"]) == (
        "no_new_content", 2, 1,
    )
    assert fake.calls == []
    assert (result["prompt_tokens"], result["completion_tokens"]) == (0, 0)


def test_creator_updates_only_digest_reports_zero_tokens(ready):
    client, fake = ready
    add_item(client, "youtube", "captions_off")
    result = execute(client)
    assert result["status"] == "succeeded" and fake.calls == []
    digest = client.get(f"/api/digests/{result['digest_id']}").json()
    assert digest["topics"] == [] and len(digest["creator_updates"]) == 1
    assert (digest["prompt_tokens"], digest["completion_tokens"]) == (0, 0)


def test_failed_save_keeps_expiry_status_pending(ready):
    client, _ = ready
    item_id = add_item(client, "podcast", "waiting", days_ago=8)

    def reject(*_args):
        raise RuntimeError("save refused")

    event.listen(DigestItem, "before_insert", reject)
    try:
        assert execute(client)["status"] == "failed"
    finally:
        event.remove(DigestItem, "before_insert", reject)
    with client.app.state.session_factory() as session:
        assert session.get(Item, item_id).transcript_status == "waiting"
        assert session.get(Item, item_id).state == "pending"
        assert session.scalars(select(Digest)).all() == []
    assert execute(client)["status"] == "succeeded"


def test_creator_updates_grouped_and_ordered_and_saved_wait(ready):
    client, _ = ready
    add_item(client, "youtube", "captions_off", source_title="Zed", title="First",
             published=NOW - timedelta(days=1))
    add_item(client, "youtube", "blocked", source_title="Zed", title="Latest",
             published=NOW)
    add_item(client, "podcast", "no_transcript", source_title="Alpha", title="Podcast")
    result = execute(client)
    digest_id = result["digest_id"]
    with client.app.state.session_factory() as session:
        assert session.scalar(select(DigestTopic.kind)) == "creator_updates"
        assert session.scalar(select(Digest.item_count)) == 3
    data = client.get(f"/api/digests/{digest_id}").json()
    assert [group["source_name"] for group in data["creator_updates"]] == ["Alpha", "Zed"]
    assert [item["title"] for item in data["creator_updates"][1]["items"]] == ["Latest", "First"]
    assert [item["reason"] for item in data["creator_updates"][1]["items"]] == ["blocked", "captions_off"]
    client.app.state.settings = replace(client.app.state.settings, transcript_wait_days=10)
    assert client.get(f"/api/digests/{digest_id}").json()["transcript_wait_days"] == 7


def test_exact_case_creator_names_form_two_groups_even_for_interleaved_snapshot(ready):
    client, _ = ready
    add_item(client, "podcast", "no_transcript", source_title="Show", title="First",
             published=NOW - timedelta(days=2))
    add_item(client, "podcast", "no_transcript", source_title="show", title="Middle",
             published=NOW - timedelta(days=1))
    add_item(client, "podcast", "no_transcript", source_title="Show", title="Last",
             published=NOW)
    result = execute(client)
    digest_id = result["digest_id"]
    groups = client.get(f"/api/digests/{digest_id}").json()["creator_updates"]
    assert [group["source_name"] for group in groups] == ["Show", "show"]
    assert [item["title"] for item in groups[0]["items"]] == ["Last", "First"]
    with client.app.state.session_factory() as session:
        rows = session.scalars(select(DigestItem).where(DigestItem.digest_id == digest_id)).all()
        positions = {"First": 0, "Middle": 1, "Last": 2}
        for row in rows:
            row.position = positions[row.title]
        session.commit()
    groups = client.get(f"/api/digests/{digest_id}").json()["creator_updates"]
    assert [group["source_name"] for group in groups] == ["Show", "show"]
    assert [item["title"] for item in groups[0]["items"]] == ["First", "Last"]


def test_old_digest_returns_empty_creator_updates(ready):
    client, _ = ready
    add_item(client, "feed", None, title="Article")
    result = execute(client)
    assert result["status"] == "succeeded"
    assert client.get(f"/api/digests/{result['digest_id']}").json()["creator_updates"] == []
