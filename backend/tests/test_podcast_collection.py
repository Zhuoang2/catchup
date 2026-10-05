import socket
from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.collection import check_source
from catchup.main import create_app
from catchup.models import DigestRun, Item, Source

FEED_URL = "https://site.example/podcast.xml"
TRANSCRIPT_URL = "https://site.example/transcript.vtt"
NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
VTT = b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<v Alice>Spoken content.</v>\n"


def episode_feed(*transcripts: tuple[str, str]) -> bytes:
    tags = "".join(
        f'<podcast:transcript url="{url}" type="{kind}"/>' for url, kind in transcripts
    )
    return f"""<rss xmlns:podcast="https://podcastindex.org/namespace/1.0"><channel>
    <title>Show</title><item><guid>ep1</guid><title>Episode one</title>
    <link>https://site.example/episode</link>
    <pubDate>Fri, 02 Oct 2026 10:00:00 GMT</pubDate>
    <description>Short show notes</description>
    <enclosure url="https://site.example/a.mp3" type="audio/mpeg"/>
    {tags}</item></channel></rss>""".encode()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    monkeypatch.setattr("catchup.api.sources.utc_now", lambda: NOW)
    with TestClient(create_app()) as client:
        yield client


def run_check(client, spacer=None):
    with client.app.state.session_factory() as session:
        run = DigestRun(status="collecting")
        session.add(run)
        session.flush()
        check = check_source(
            session, session.scalar(select(Source)), run.id, client.app.state.settings, spacer=spacer,
        )
        return check.status


def seed_source(client):
    with client.app.state.session_factory() as session:
        session.add(Source(
            title="Show", kind="podcast", site_url="https://site.example/",
            feed_url=FEED_URL, input_url=FEED_URL,
        ))
        session.commit()


def test_new_episode_fetches_vtt_with_spacer(client):
    seed_source(client)
    seen = []

    class Spacer:
        def wait(self, url):
            seen.append(url)

    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(
            200, content=episode_feed((TRANSCRIPT_URL, "text/vtt"))))
        router.get(TRANSCRIPT_URL).mock(return_value=httpx.Response(200, content=VTT))
        assert run_check(client, Spacer()) == "new_items"
    assert seen == [FEED_URL, TRANSCRIPT_URL]
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.transcript_status == "found"
        assert item.content_text == "Alice: Spoken content."
        assert item.content_origin == "transcript"


def test_best_candidate_404_tries_next(client):
    seed_source(client)
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(200, content=episode_feed(
            ("https://site.example/first.txt", "text/plain"), (TRANSCRIPT_URL, "text/vtt"),
        )))
        bad = router.get("https://site.example/first.txt").mock(return_value=httpx.Response(404))
        good = router.get(TRANSCRIPT_URL).mock(return_value=httpx.Response(200, content=VTT))
        assert run_check(client) == "new_items"
    assert bad.call_count == good.call_count == 1
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.transcript_status)) == "found"


def test_missing_transcript_waits_and_later_replaces_summary(client):
    seed_source(client)
    with respx.mock(assert_all_mocked=True) as router:
        feed = router.get(FEED_URL).mock(return_value=httpx.Response(200, content=episode_feed()))
        assert run_check(client) == "new_items"
        with client.app.state.session_factory() as session:
            item = session.scalar(select(Item))
            assert item.transcript_status == "waiting"
            item.summary = "Old description-based summary"
            item.summary_language = "en"
            session.commit()
        feed.mock(return_value=httpx.Response(
            200, content=episode_feed((TRANSCRIPT_URL, "text/vtt"))))
        router.get(TRANSCRIPT_URL).mock(return_value=httpx.Response(200, content=VTT))
        assert run_check(client) == "no_new_items"
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.transcript_status == "found"
        assert item.summary is None and item.summary_language is None


def test_unexpected_converter_exception_does_not_fail_check(client, monkeypatch, caplog):
    seed_source(client)
    monkeypatch.setattr("catchup.collection.convert_transcript", lambda *_args: 1 / 0)
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(
            200, content=episode_feed((TRANSCRIPT_URL, "text/vtt"))))
        router.get(TRANSCRIPT_URL).mock(return_value=httpx.Response(200, content=VTT))
        assert run_check(client) == "new_items"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.transcript_status)) == "waiting"
    assert "ZeroDivisionError" in caplog.text
    assert "Spoken content" not in caplog.text


def test_confirm_skips_episode_page_and_transcript(client):
    with respx.mock(assert_all_mocked=True) as router:
        feed = router.get(FEED_URL).mock(return_value=httpx.Response(
            200, content=episode_feed((TRANSCRIPT_URL, "text/vtt"))))
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
    assert feed.call_count == 1
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.state == "pending" and item.transcript_status == "to_fetch"
