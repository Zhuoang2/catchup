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


def test_autouse_sandbox_applies_without_settings(tmp_path) -> None:
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.app.state.settings.data_dir == tmp_path
        assert client.app.state.settings.secret_key is None
    assert (tmp_path / "catchup.sqlite3").exists()
