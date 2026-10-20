"""Cross-site write policy at the HTTP boundary."""

import socket
from dataclasses import replace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from catchup.config import Settings
from catchup.crypto import encrypt_key
from catchup.main import create_app
from catchup.models import DigestRun, ModelConfig, Source

REFUSED = {
    "error": {
        "code": "cross_site_request",
        "message": "This request came from another site and was refused.",
    },
}
HOST = {"Host": "localhost:8000"}
PREFERENCES = "/api/settings/preferences"


@pytest.fixture
def client(test_settings):
    with TestClient(create_app(replace(test_settings, secret_key="test-only-instance-secret")),
                    base_url="http://localhost:8000") as api:
        yield api


def configure_model(client, monkeypatch):
    with client.app.state.session_factory() as session:
        session.add(ModelConfig(
            id=1, base_url="https://model.example/v1", model_id="test",
            api_key_encrypted=encrypt_key("fake-key", client.app.state.settings.secret_key),
            api_key_last4="-key",
        ))
        session.commit()
    monkeypatch.setattr("catchup.digest.runner.run_digest", lambda *_: None)


def assert_refused(response):
    assert response.status_code == 403
    assert response.json() == REFUSED


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"},  # 1: form post from another site
    {"Sec-Fetch-Site": "cross-site"},  # 2: browser omits Origin
])
def test_foreign_form_cannot_start_run(client, monkeypatch, headers):
    configure_model(client, monkeypatch)
    response = client.post(
        "/api/digest-runs", content=b"",
        headers={**HOST, **headers, "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert_refused(response)
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DigestRun)) == 0


@pytest.mark.parametrize("headers", [
    {"Origin": "http://localhost:3000"},  # 3: another local port
    {"Sec-Fetch-Site": "same-site"},  # 6: same site but not same origin
    {"Origin": "chrome-extension://abc"},  # 7: non-web origin
    {"Origin": "file://"},  # 7: non-web origin
    {"Origin": "http://127.0.0.1:8000"},  # 8: different local host
])
def test_foreign_origin_cannot_change_preferences(client, headers):
    before = client.get(PREFERENCES, headers=HOST).json()
    assert_refused(client.put(PREFERENCES, json={"digest_language": "fr"}, headers={**HOST, **headers}))
    assert client.get(PREFERENCES, headers=HOST).json() == before


def test_foreign_origin_cannot_delete_source(client):
    with client.app.state.session_factory() as session:
        source = Source(title="Saved", site_url="https://site.example/",
                        feed_url="https://site.example/feed", input_url="https://site.example/feed")
        session.add(source)
        session.commit()
        source_id = source.id
    assert_refused(client.delete(f"/api/sources/{source_id}",
                                 headers={**HOST, "Origin": "https://evil.example"}))
    assert any(row["id"] == source_id for row in client.get("/api/sources", headers=HOST).json())


def test_null_origin_cannot_preview_feed(client, monkeypatch):
    feed_url = "https://site.example/feed"
    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get(feed_url).mock(return_value=httpx.Response(
            200, content=b"<rss><channel><title>Feed</title></channel></rss>",
            headers={"content-type": "application/rss+xml"},
        ))
        assert_refused(client.post(
            "/api/sources/preview", json={"url": feed_url},
            headers={**HOST, "Origin": "null"},
        ))
        assert route.call_count == 0


def test_patch_on_unknown_path_is_refused(client):
    assert_refused(client.patch("/some-path", headers={**HOST, "Origin": "https://evil.example"}))


@pytest.mark.parametrize("host,origin,extra_headers", [
    ("localhost:8000", "http://localhost:8000", {"Sec-Fetch-Site": "same-origin"}),  # 9
    ("localhost:5173", "http://localhost:5173", {}),  # 10: Vite proxy
    ("[::1]:8000", "http://[::1]:8000", {}),  # 12
    ("localhost", "http://localhost", {}),  # 13: default port
    ("localhost:8000", None, {}),  # 14: tool, neither browser header
    ("localhost:8000", None, {"Sec-Fetch-Site": "none"}),  # 15
])
def test_own_origin_and_tools_can_save_preferences(client, host, origin, extra_headers):
    headers = {"Host": host, **extra_headers}
    if origin is not None:
        headers["Origin"] = origin
    response = client.put(PREFERENCES, json={"digest_language": "fr"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["digest_language"] == "fr"
    assert client.get(PREFERENCES, headers=headers).json()["digest_language"] == "fr"


def test_domain_origin_can_save_preferences(monkeypatch):
    monkeypatch.setenv("CATCHUP_ALLOWED_HOSTS", "localhost,catchup.example.org")
    settings = replace(Settings.from_env(), secret_key="test-only-instance-secret")
    headers = {"Host": "catchup.example.org", "Origin": "https://catchup.example.org"}
    with TestClient(create_app(settings), base_url="http://localhost:8000") as client:
        response = client.put(PREFERENCES, json={"digest_language": "fr"}, headers=headers)
        assert response.status_code == 200
        assert client.get(PREFERENCES, headers=headers).json()["digest_language"] == "fr"


def test_tool_can_start_run(client, monkeypatch):
    configure_model(client, monkeypatch)
    response = client.post("/api/digest-runs", headers=HOST)
    assert response.status_code == 202
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DigestRun)) == 1


def test_cross_site_read_is_unaffected(client):
    response = client.get("/api/digests", headers={
        **HOST, "Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site",
    })
    assert response.status_code == 200
    assert response.json() == []


def test_disallowed_host_wins_over_cross_site_origin(client):
    response = client.put(PREFERENCES, json={"digest_language": "fr"}, headers={
        "Host": "evil.example", "Origin": "https://evil.example",
    })
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "invalid_host", "message": "Host is not allowed."}}
