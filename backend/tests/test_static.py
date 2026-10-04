from fastapi.testclient import TestClient

from catchup.config import Settings
from catchup.main import create_app


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
