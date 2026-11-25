"""Uploader preview and confirmation without requesting Bilibili."""

import json
import socket
from datetime import datetime, timedelta, timezone

import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.main import create_app
from catchup.models import Item, Source
from catchup.net.bilibili_hosts import is_bilibili_host
from test_bilibili import BILIBILI, ROUTE, RSSHUB, uploader_body

NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)
SPACE = "https://space.bilibili.com/2267573"
STABLE = "bilibili:uploader:2267573"


def rsshub_dns(monkeypatch, hosts=None):
    def lookup(host, port, *args, **kwargs):
        if hosts is not None:
            hosts.append(host)
        if is_bilibili_host(host):
            raise AssertionError("Bilibili DNS must never be requested")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port))] if host == "rsshub.test" else []
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


@pytest.fixture
def client(monkeypatch):
    rsshub_dns(monkeypatch)
    monkeypatch.setenv("CATCHUP_RSSHUB_URL", RSSHUB)
    monkeypatch.setattr("catchup.api.sources.utc_now", lambda: NOW)
    with TestClient(create_app()) as api:
        yield api


def serve_uploader(router, body, status=200):
    route = router.get(ROUTE).respond(
        status, content=json.dumps(body).encode() if isinstance(body, dict) else body,
        headers={"content-type": "application/feed+json"},
    )
    blocked = router.get(BILIBILI).mock(side_effect=AssertionError("Bilibili must never be requested"))
    return route, blocked


def assert_saved_items(client):
    with client.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        assert (source.title, source.input_url) == ("Sample Uploader", STABLE)
        items = {item.identity_key: item for item in session.scalars(select(Item))}
        subtitled = items["bilibili:video:BV1aa411c7aA"]
        assert (subtitled.state, subtitled.transcript_status, subtitled.content_origin, subtitled.content_text) == (
            "pending", "found", "transcript", "Hello\n\nworld",
        )
        waiting = items["bilibili:video:BV1bb411c7bB"]
        assert (waiting.state, waiting.transcript_status, waiting.content_origin, waiting.content_text) == (
            "pending", "subtitle_wait", "feed", "Description B",
        )
        assert items["bilibili:video:av170001"].state == "baseline"
        assert len(items) == 3
        assert all(item.image_candidates == [] and item.entry_links == [] for item in items.values())


def test_duplicate_is_reported_without_asking_rsshub(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 201
        route.respond(503, content=b"Busy")
        again = client.post("/api/sources/preview", json={"url": "https://m.bilibili.com/space/2267573"})
        assert again.status_code == 422 and again.json()["error"]["code"] == "duplicate"
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 409
        assert route.call_count == 1 and blocked.call_count == 0


def test_preview_uploader(client):
    body = uploader_body()
    body["items"] = [{
        "url": f"https://www.bilibili.com/video/BV1sample{i}", "title": f"Video {i}",
        "date_published": (NOW - timedelta(days=7 - i)).isoformat(),
    } for i in range(7)]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, body)
        result = client.post("/api/sources/preview", json={"url": SPACE})
        assert result.status_code == 200
        assert result.json() == {
            "feed_url": STABLE, "site_url": SPACE, "title": "Sample Uploader",
            "follows_site_feed_notice": False, "kind": "bilibili", "captions_enabled": False,
            "entries": [{
                "title": f"Video {i}", "link": f"https://www.bilibili.com/video/BV1sample{i}",
                "published_at": (NOW - timedelta(days=7 - i)).isoformat().replace("+00:00", "Z"),
            } for i in (6, 5, 4, 3, 2)],
        }
        assert route.call_count == 1 and blocked.call_count == 0
    assert client.get("/api/sources").json() == []


def test_preview_through_the_rsshub_route_address(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        result = client.post("/api/sources/preview", json={"url": ROUTE})
        assert result.status_code == 200
        assert (result.json()["feed_url"], result.json()["title"]) == (STABLE, "Sample Uploader")
        assert route.call_count == 1 and blocked.call_count == 0


def test_preview_refuses_other_bilibili_addresses(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        result = client.post("/api/sources/preview", json={"url": "https://www.bilibili.com/video/BV1xx411c7mD"})
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "not_a_bilibili_uploader"
        assert route.call_count == blocked.call_count == 0


def test_preview_without_rsshub(client, monkeypatch):
    monkeypatch.delenv("CATCHUP_RSSHUB_URL")
    with TestClient(create_app()) as unconfigured, respx.mock(
        assert_all_mocked=True, assert_all_called=False,
    ) as router:
        route, blocked = serve_uploader(router, uploader_body())
        result = unconfigured.post("/api/sources/preview", json={"url": SPACE})
        assert result.status_code == 422
        assert result.json()["error"] == {
            "code": "rsshub_not_configured",
            "message": "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README.",
        }
        assert route.call_count == blocked.call_count == 0


@pytest.mark.parametrize("status,body,message", [
    (503, b"Busy", "RSSHub could not read this uploader (HTTP 503)."),
    (200, b"<html>Busy</html>", "RSSHub could not read this uploader."),
])
def test_preview_rsshub_failures(client, status, body, message):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, body, status)
        result = client.post("/api/sources/preview", json={"url": SPACE})
        assert result.status_code == 422
        assert result.json()["error"] == {"code": "rsshub_failed", "message": message}
        assert route.call_count == 1 and blocked.call_count == 0
    assert client.get("/api/sources").json() == []


def test_confirm_uploader(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        assert client.post("/api/sources/preview", json={"url": SPACE}).status_code == 200
        result = client.post("/api/sources", json={"feed_url": STABLE})
        assert result.status_code == 201
        assert (result.json()["kind"], result.json()["site_url"], result.json()["feed_url"]) == (
            "bilibili", SPACE, STABLE,
        )
        assert route.call_count == 1 and blocked.call_count == 0
    assert_saved_items(client)


def test_confirm_without_a_cached_preview_fetches_again(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, uploader_body())
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 201
        assert route.call_count == 1 and blocked.call_count == 0
    assert_saved_items(client)


def test_duplicate_uploader_in_any_address_form(client):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        _, blocked = serve_uploader(router, uploader_body())
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 201
        again = client.post("/api/sources/preview", json={"url": "https://m.bilibili.com/space/2267573"})
        assert again.status_code == 422 and again.json()["error"]["code"] == "duplicate"
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 409
        assert blocked.call_count == 0


def test_confirm_refuses_a_malformed_bilibili_address(client):
    result = client.post("/api/sources", json={"feed_url": "bilibili:uploader:abc"})
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "not_a_bilibili_uploader"


def test_bilibili_entries_never_request_their_video_page(client, monkeypatch):
    def no_article(*args, **kwargs):
        raise AssertionError("Bilibili entries must never call article_text")
    monkeypatch.setattr("catchup.api.sources.article_text", no_article)
    body = uploader_body()
    body["items"] = body["items"][:2]
    for item in body["items"]:
        item["attachments"] = []
        item["date_published"] = (NOW - timedelta(days=1)).isoformat()
        item["content_html"] = "Short"
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route, blocked = serve_uploader(router, body)
        assert client.post("/api/sources", json={"feed_url": STABLE}).status_code == 201
        assert [str(call.request.url) for call in router.calls] == [ROUTE]
        assert route.call_count == 1 and blocked.call_count == 0
    with client.app.state.session_factory() as session:
        assert all(item.state == "pending" for item in session.scalars(select(Item)))
