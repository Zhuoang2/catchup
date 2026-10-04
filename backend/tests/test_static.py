from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from catchup.config import Settings
from catchup.main import create_app
import catchup.main as main_module


def make_dist(path: Path, label: str) -> Path:
    path.mkdir()
    (path / "index.html").write_text(f"<html>{label}</html>", encoding="utf-8")
    return path


def test_built_frontend_fallback_keeps_api_json(tmp_path, test_settings: Settings) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>CatchUp</html>", encoding="utf-8")
    with TestClient(create_app(test_settings, dist_dir=dist)) as client:
        page = client.get("/digests/3")
        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert "CatchUp" in page.text
        assert client.get("/api/health").json() == {"status": "ok"}
        missing = client.get("/api/missing")
        assert missing.status_code == 404
        assert missing.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_explicit_dist_overrides_setting(tmp_path, test_settings: Settings) -> None:
    configured = make_dist(tmp_path / "configured", "configured")
    explicit = make_dist(tmp_path / "explicit", "explicit")
    with TestClient(create_app(replace(test_settings, frontend_dist=configured), dist_dir=explicit)) as client:
        assert "explicit" in client.get("/").text
        assert "configured" not in client.get("/").text


def test_configured_dist_from_environment(tmp_path, monkeypatch) -> None:
    dist = make_dist(tmp_path / "configured", "configured")
    monkeypatch.setenv("CATCHUP_FRONTEND_DIST", str(dist))
    with TestClient(create_app()) as client:
        assert "configured" in client.get("/").text
        assert client.get("/api/health").json() == {"status": "ok"}


def test_source_tree_dist_fallback(tmp_path, test_settings: Settings, monkeypatch) -> None:
    source_dist = tmp_path / "frontend" / "dist"
    source_dist.parent.mkdir()
    make_dist(source_dist, "source checkout")
    monkeypatch.setattr(main_module, "__file__", str(tmp_path / "backend" / "src" / "catchup" / "main.py"))
    with TestClient(create_app(replace(test_settings, frontend_dist=None))) as client:
        assert "source checkout" in client.get("/").text


def test_missing_dist_leaves_api_available(tmp_path, test_settings: Settings) -> None:
    with TestClient(create_app(replace(test_settings, frontend_dist=tmp_path / "missing"))) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/health").json() == {"status": "ok"}
