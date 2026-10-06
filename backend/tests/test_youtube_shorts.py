import socket
from dataclasses import replace
from datetime import datetime, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.collection import check_source
from catchup.digest.runner import run_digest, start_run
from catchup.main import create_app
from catchup.models import AppSettings, Item, Source
from catchup.transcripts.context import TranscriptContext
from catchup.net.host_spacing import HostSpacer
from test_digest_runner import seed, stub_collection, FakeModel

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id=abc"
SHORT_URL = "https://www.youtube.com/shorts/short123"
NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
FEED = b"""<feed xmlns="http://www.w3.org/2005/Atom"><title>Channel</title>
<entry><id>yt:video:short123</id><title>Short</title><link href="https://www.youtube.com/shorts/short123"/>
<updated>2026-10-02T10:00:00Z</updated></entry></feed>"""


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    monkeypatch.setattr("catchup.api.sources.utc_now", lambda: NOW)
    with TestClient(create_app()) as client:
        yield client


@pytest.mark.parametrize("skip,expected", [(True, "baseline"), (False, "pending")])
def test_confirm_short_default_and_opted_in(client, skip, expected):
    if not skip:
        with client.app.state.session_factory() as session:
            session.add(AppSettings(id=1, youtube_skip_shorts=False))
            session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(200, content=FEED))
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.state == expected
        assert item.transcript_status == "to_fetch"


def test_check_short_uses_skip_preference(client):
    with client.app.state.session_factory() as session:
        source = Source(title="Channel", kind="youtube", site_url="https://www.youtube.com/",
                        feed_url=FEED_URL, input_url=FEED_URL)
        session.add(source)
        session.commit()
        source_id = source.id
    for skip, expected in ((True, "baseline"), (False, "pending")):
        with client.app.state.session_factory() as session:
            session.query(Item).delete()
            session.commit()
        with respx.mock(assert_all_mocked=True) as router:
            router.get(FEED_URL).mock(return_value=httpx.Response(200, content=FEED))
            with client.app.state.session_factory() as session:
                ctx = TranscriptContext(
                    spacer=HostSpacer(sleep=lambda _seconds: None), settings=client.app.state.settings,
                    youtube_skip_shorts=skip,
                )
                check_source(session, session.get(Source, source_id), None, client.app.state.settings,
                             transcripts=ctx)
                assert session.scalar(select(Item.state)) == expected


def test_preexisting_pending_short_never_delivered(client, monkeypatch):
    client.app.state.settings = replace(
        client.app.state.settings, secret_key="test-only-secret")
    seed(client, count=0, sources=0)
    with client.app.state.session_factory() as session:
        source = Source(title="Channel", kind="youtube", site_url="https://www.youtube.com/",
                        feed_url=FEED_URL, input_url=FEED_URL)
        session.add(source)
        session.flush()
        session.add(Item(source_id=source.id, identity_key="yt:video:short123",
                         title="Short", link=SHORT_URL, content_text="Not spoken",
                         content_origin="feed", state="pending", transcript_status=None))
        session.commit()
    stub_collection(monkeypatch)
    model = FakeModel()
    client.app.state.model_client_factory = lambda *_args: model
    run = start_run(client.app, background=False)
    run_digest(client.app, run.id)
    assert client.get(f"/api/digest-runs/{run.id}").json()["status"] == "no_new_content"
    assert model.calls == []
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item.state)) == "baseline"
