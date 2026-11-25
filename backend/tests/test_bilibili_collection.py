"""Collection and full digest runs through invented RSSHub responses."""

from dataclasses import replace
from datetime import timedelta

import pytest
import respx
from sqlalchemy import select

from catchup.collection import check_source
from catchup.models import DigestRun, Item, Source
from catchup.net.bilibili_hosts import is_bilibili_host
from test_bilibili import RSSHUB, uploader_body
from test_bilibili_sources_api import NOW, SPACE, STABLE, rsshub_dns, serve_uploader
from test_digest_runner import FakeModel, environment, execute, seed


@pytest.fixture
def uploader(environment, monkeypatch):
    seed(environment, count=0, sources=0)
    environment.app.state.settings = replace(environment.app.state.settings, rsshub_url=RSSHUB)
    rsshub_dns(monkeypatch)
    monkeypatch.setattr("catchup.collection.utc_now", lambda: NOW)
    monkeypatch.setattr("catchup.digest.runner.utc_now", lambda: NOW)
    with environment.app.state.session_factory() as session:
        source = Source(title="Sample Uploader", kind="bilibili", feed_url=STABLE,
                        site_url=SPACE, input_url=STABLE)
        session.add(source)
        session.commit()
    return environment


def run_check(client):
    with client.app.state.session_factory() as session:
        run = DigestRun(status="collecting")
        session.add(run)
        session.flush()
        return check_source(session, session.scalar(select(Source)), run.id, client.app.state.settings)


def test_check_records_new_videos(uploader):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        check = run_check(uploader)
        assert (check.status, check.http_status, check.new_count) == ("new_items", 200, 3)
        assert route.call_count == 1 and blocked.call_count == 0
    with uploader.app.state.session_factory() as session:
        assert session.scalar(select(Source.kind)) == "bilibili"
        items = {item.identity_key: item for item in session.scalars(select(Item))}
        found = items["bilibili:video:BV1aa411c7aA"]
        assert (found.transcript_status, found.content_origin, found.content_text) == (
            "found", "transcript", "Hello\n\nworld",
        )
        assert items["bilibili:video:BV1bb411c7bB"].transcript_status == "subtitle_wait"
        assert items["bilibili:video:av170001"].state == "pending"
        assert all(item.state == "pending" and item.image_candidates == [] and item.entry_links == []
                   for item in items.values())


def test_subtitles_that_appear_later_are_used(uploader):
    body = uploader_body()
    body["items"] = [body["items"][1]]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, body)
        assert run_check(uploader).status == "new_items"
        with uploader.app.state.session_factory() as session:
            item = session.scalar(select(Item))
            assert item.transcript_status == "subtitle_wait"
            item.summary = "Old"
            item.summary_language = "en"
            session.commit()
        body["items"][0]["attachments"] = [uploader_body()["items"][0]["attachments"][1]]
        route.respond(200, json=body)
        assert run_check(uploader).status == "no_new_items"
        assert route.call_count == 2 and blocked.call_count == 0
    with uploader.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert (item.transcript_status, item.content_text, item.content_origin, item.summary,
                item.summary_language) == ("found", "Hello\n\nworld", "transcript", None, None)


def test_check_without_rsshub_fails(uploader):
    uploader.app.state.settings = replace(uploader.app.state.settings, rsshub_url=None)
    check = run_check(uploader)
    assert (check.status, check.error) == (
        "failed", "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README.",
    )


@pytest.mark.parametrize("status,body,message", [
    (503, b"Busy", "RSSHub could not read this uploader (HTTP 503)."),
    (200, b"<html>Busy</html>", "RSSHub could not read this uploader."),
])
def test_check_with_rsshub_errors_fails(uploader, status, body, message):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, body, status)
        check = run_check(uploader)
        assert (check.status, check.http_status, check.error) == ("failed", status, message)
        assert route.call_count == 1 and blocked.call_count == 0


def test_whole_run_never_requests_bilibili(uploader, monkeypatch):
    hosts = []
    rsshub_dns(monkeypatch, hosts)
    fake = FakeModel()
    uploader.app.state.model_client_factory = lambda *_args: fake
    with uploader.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        session.add(Item(
            source_id=source.id, identity_key="bilibili:video:BV1bb411c7bB",
            link="https://www.bilibili.com/video/BV1bb411c7bB", title="Video without subtitles",
            discovered_at=NOW - timedelta(hours=25), state="pending", transcript_status="subtitle_wait",
            content_text="Description B", content_origin="feed",
        ))
        session.commit()
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        result = execute(uploader)
        assert result["status"] == "succeeded"
        assert route.call_count == 1 and blocked.call_count == 0
    digest = uploader.get(f"/api/digests/{result['digest_id']}").json()
    assert [item["title"] for topic in digest["topics"] for item in topic["items"]] == ["Video with subtitles"]
    assert digest["creator_updates"] == [{
        "source_name": "Sample Uploader", "source_kind": "bilibili", "items": [{
            "title": "Video without subtitles", "link": "https://www.bilibili.com/video/BV1bb411c7bB",
            "published_at": None, "reason": "no_subtitles", "source_kind": "bilibili",
        }],
    }]
    summary_users = [message["content"] for messages, _tokens in fake.calls
                     if '"summary"' in messages[0]["content"] for message in messages if message["role"] == "user"]
    assert len(summary_users) == 1
    assert "Hello" in summary_users[0] and "Description A" not in summary_users[0]
    assert "Description B" not in summary_users[0]
    assert hosts == []
    assert not any(is_bilibili_host(host) for host in hosts)
