"""Every response tells the browser not to show CatchUp inside another page's frame (#69)."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from catchup.config import Settings
from catchup.main import create_app

INDEX = "<html>CatchUp index</html>"
OFFLINE = "<html>CatchUp offline</html>"
WORKER = "self.addEventListener('fetch', () => {});"
MANIFEST = "{}"
SCRIPT = "console.log('CatchUp app');"
JAVASCRIPT = {"text/javascript", "application/javascript"}
LOCAL = {"Host": "localhost:8000"}
PREFERENCES = "/api/settings/preferences"


def assert_refuses_framing(response) -> None:
    assert response.headers.get_list("x-frame-options") == ["DENY"]
    assert response.headers.get_list("content-security-policy") == ["frame-ancestors 'none'"]


def media_type(response) -> str:
    return response.headers["content-type"].split(";")[0]


def make_dist(path: Path) -> Path:
    (path / "assets").mkdir(parents=True)
    (path / "index.html").write_text(INDEX, encoding="utf-8")
    (path / "offline.html").write_text(OFFLINE, encoding="utf-8")
    (path / "sw.js").write_text(WORKER, encoding="utf-8")
    (path / "manifest.webmanifest").write_text(MANIFEST, encoding="utf-8")
    (path / "assets" / "app.js").write_text(SCRIPT, encoding="utf-8")
    return path


def crash() -> None:
    raise RuntimeError("test-only crash")


@pytest.fixture
def app(tmp_path, test_settings: Settings):
    application = create_app(test_settings, dist_dir=make_dist(tmp_path / "dist"))
    application.add_api_route("/api/test-crash", crash, methods=["GET"])
    return application


@pytest.fixture
def client(app):
    with TestClient(app, base_url="http://localhost:8000", raise_server_exceptions=False) as api:
        yield api


@pytest.mark.parametrize(("path", "media_types", "body"), [
    ("/", {"text/html"}, INDEX),  # 1
    ("/digests/3", {"text/html"}, INDEX),  # 2: SPA fallback for a client route
    ("/offline.html", {"text/html"}, OFFLINE),  # 3: file at the dist root
    ("/sw.js", JAVASCRIPT, WORKER),  # 4
    ("/manifest.webmanifest", {"application/manifest+json"}, MANIFEST),  # 5
    ("/assets/app.js", JAVASCRIPT, SCRIPT),  # 6: static mount
])
def test_pages_and_files_refuse_framing(client, path, media_types, body):
    response = client.get(path, headers=LOCAL)
    assert response.status_code == 200
    assert media_type(response) in media_types
    assert response.text == body
    assert_refuses_framing(response)


def test_api_response_refuses_framing(client):  # 7
    response = client.get("/api/health", headers=LOCAL)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert_refuses_framing(response)


def test_unknown_api_address_refuses_framing(client):  # 8
    response = client.get("/api/missing", headers=LOCAL)
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}
    assert_refuses_framing(response)


def test_refused_host_refuses_framing(client):  # 9
    response = client.get("/api/health", headers={"Host": "evil.example"})
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "invalid_host", "message": "Host is not allowed."}}
    assert_refuses_framing(response)


def test_refused_cross_site_write_refuses_framing(client):  # 10
    response = client.put(
        PREFERENCES, json={"digest_language": "fr"},
        headers={**LOCAL, "Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json() == {"error": {
        "code": "cross_site_request",
        "message": "This request came from another site and was refused.",
    }}
    assert_refuses_framing(response)


def test_invalid_browser_token_refuses_framing(client):  # 11
    response = client.get(
        "/api/extension/status", headers={**LOCAL, "Authorization": "Bearer cu_unknown"},
    )
    assert response.status_code == 401
    assert response.json() == {"error": {
        "code": "invalid_token",
        "message": "This browser is not connected to CatchUp. Connect it in Settings.",
    }}
    assert_refuses_framing(response)


def test_invalid_request_refuses_framing(client):  # 12
    response = client.put(
        PREFERENCES, content=b"{", headers={**LOCAL, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "invalid_request", "message": "Invalid request."}}
    assert_refuses_framing(response)


def test_internal_error_keeps_plain_body_and_refuses_framing(client):  # 13
    response = client.get("/api/test-crash", headers=LOCAL)
    assert response.status_code == 500
    assert media_type(response) == "text/plain"
    assert response.text == "Internal Server Error"
    assert_refuses_framing(response)


def test_refuses_framing_without_built_frontend(tmp_path, test_settings: Settings):  # 14
    app = create_app(replace(test_settings, frontend_dist=tmp_path / "missing"))
    with TestClient(app, base_url="http://localhost:8000") as client:
        page = client.get("/", headers=LOCAL)
        health = client.get("/api/health", headers=LOCAL)
    assert page.status_code == 404
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert_refuses_framing(page)
    assert_refuses_framing(health)


def test_internal_error_still_reaches_the_server(app):  # 15: guard
    with TestClient(app, base_url="http://localhost:8000") as client:
        with pytest.raises(RuntimeError, match="test-only crash"):
            client.get("/api/test-crash", headers=LOCAL)
