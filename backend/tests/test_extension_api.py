"""Public connection and capture HTTP interfaces."""

import hashlib
import socket

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from catchup.main import create_app
from catchup.models import DigestRun, ExtensionToken, Source

FEED = "https://site.example/feed"
ORIGIN = {"Origin": "chrome-extension://abcdefghijklmnop"}
FEED_XML = (b"<rss><channel><title>Example</title><link>https://site.example/</link>"
            b"</channel></rss>")


@pytest.fixture
def client(test_settings):
    with TestClient(create_app(test_settings), base_url="http://localhost:8000") as api:
        yield api


def test_connect_lists_only_metadata_and_stores_only_hash(client):
    response = client.post("/api/settings/extension-tokens", json={"name": "Chrome"})
    assert response.status_code == 201
    created = response.json()
    assert set(created) == {"id", "name", "created_at", "token"}
    assert created["name"] == "Chrome"
    assert created["token"].startswith("cu_")
    with client.app.state.session_factory() as session:
        row = session.scalar(select(ExtensionToken))
        assert row.token_hash == hashlib.sha256(created["token"].encode()).hexdigest()
        assert created["token"] not in row.token_hash
    listed = client.get("/api/settings/extension-tokens")
    assert listed.status_code == 200
    assert listed.json() == [{
        "id": created["id"], "name": "Chrome", "created_at": created["created_at"], "last_used_at": None,
    }]
    assert created["token"] not in listed.text


def test_disconnect_removes_connection(client):
    created = client.post("/api/settings/extension-tokens", json={"name": "Edge"}).json()
    assert client.delete(f"/api/settings/extension-tokens/{created['id']}").status_code == 204
    assert client.get("/api/settings/extension-tokens").json() == []
    with client.app.state.session_factory() as session:
        assert session.get(ExtensionToken, created["id"]) is None


@pytest.mark.parametrize("name", ["", "x" * 61])
def test_connection_name_must_be_one_to_sixty_characters(client, name):
    response = client.post("/api/settings/extension-tokens", json={"name": name})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.fixture
def connected(client):
    token = client.post("/api/settings/extension-tokens", json={"name": "Chrome"}).json()["token"]
    return {**ORIGIN, "Authorization": f"Bearer {token}"}


@pytest.fixture
def public_feed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, *_a, **_kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get(FEED).mock(return_value=httpx.Response(
            200, content=FEED_XML, headers={"content-type": "application/rss+xml"},
        ))
        yield route


def test_token_previews_and_updates_last_used(client, connected, public_feed):
    assert client.post("/api/sources/preview", json={"url": FEED}, headers=connected).status_code == 200
    assert public_feed.call_count == 1
    with client.app.state.session_factory() as session:
        assert session.scalar(select(ExtensionToken)).last_used_at is not None


def test_token_saves_source(client, connected, public_feed):
    assert client.post("/api/sources", json={"feed_url": FEED}, headers=connected).status_code == 201
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)).feed_url == FEED


def test_token_ignores_cross_site_fetch_metadata(client, connected, public_feed):
    response = client.post("/api/sources/preview", json={"url": FEED},
                           headers={**connected, "Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 200


@pytest.mark.parametrize("disconnected", [False, True])
def test_unknown_or_disconnected_token_cannot_fetch(client, connected, public_feed, disconnected):
    if disconnected:
        row = client.get("/api/settings/extension-tokens").json()[0]
        assert client.delete(f"/api/settings/extension-tokens/{row['id']}").status_code == 204
        headers = connected
    else:
        headers = {**ORIGIN, "Authorization": "Bearer cu_not-a-real-token"}
    response = client.post("/api/sources/preview", json={"url": FEED}, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert public_feed.call_count == 0


def test_token_cannot_change_preferences(client, connected):
    response = client.put("/api/settings/preferences", json={"digest_language": "fr"}, headers=connected)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_site_request"
    assert client.get("/api/settings/preferences").json()["digest_language"] == "en"


def test_token_cannot_start_run(client, connected):
    assert client.post("/api/digest-runs", headers=connected).status_code == 403
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DigestRun)) == 0


def test_status_requires_token_even_for_get(client, connected):
    assert client.get("/api/extension/status", headers=connected).json() == {"name": "Chrome", "waiting": 0}
    response = client.get("/api/extension/status", headers=ORIGIN)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_other_auth_scheme_follows_existing_origin_policy(client):
    foreign = {**ORIGIN, "Authorization": "Basic fake-auth"}
    assert client.put("/api/settings/preferences", json={"digest_language": "fr"},
                      headers=foreign).status_code == 403
    own = {**foreign, "Origin": "http://localhost:8000"}
    response = client.put("/api/settings/preferences", json={"digest_language": "fr"}, headers=own)
    assert response.status_code == 200
    assert response.json()["digest_language"] == "fr"


def test_token_cannot_create_or_list_connections(client, connected):
    assert client.post("/api/settings/extension-tokens", json={"name": "Another"},
                       headers=connected).status_code == 403
    assert client.get("/api/settings/extension-tokens", headers=connected).status_code == 403
    assert len(client.get("/api/settings/extension-tokens").json()) == 1


def test_last_used_failure_does_not_fail_valid_request(client, connected, monkeypatch):
    def locked(*_args):
        raise OperationalError("UPDATE extension_tokens", {}, Exception("database is locked"))
    monkeypatch.setattr("catchup.main._touch_extension_token", locked)
    assert client.get("/api/extension/status", headers=connected).json() == {"name": "Chrome", "waiting": 0}
