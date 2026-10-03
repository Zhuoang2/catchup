from fastapi.testclient import TestClient

from catchup.config import Settings
from catchup.errors import AppError
from catchup.main import create_app


def test_health(test_settings: Settings) -> None:
    with TestClient(create_app(test_settings)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_app_error_shape(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/api/example-error")
    def example_error() -> None:
        raise AppError("example", "Try again", 422)

    with TestClient(app) as client:
        response = client.get("/api/example-error")
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "example", "message": "Try again"}}


def test_tests_do_not_touch_configured_data_dir(test_settings: Settings, tmp_path, monkeypatch) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    marker = sentinel / "keep.txt"
    marker.write_text("untouched", encoding="utf-8")
    monkeypatch.setenv("CATCHUP_DATA_DIR", str(sentinel))

    with TestClient(create_app(test_settings)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

    assert marker.read_text(encoding="utf-8") == "untouched"
    assert list(sentinel.iterdir()) == [marker]
    assert (test_settings.data_dir / "catchup.sqlite3").exists()
