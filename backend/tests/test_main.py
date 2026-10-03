from fastapi.testclient import TestClient

from catchup.main import AppError, create_app


def test_health() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_app_error_shape() -> None:
    app = create_app()

    @app.get("/api/example-error")
    def example_error() -> None:
        raise AppError("example", "Try again", 422)

    with TestClient(app) as client:
        response = client.get("/api/example-error")
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "example", "message": "Try again"}}
