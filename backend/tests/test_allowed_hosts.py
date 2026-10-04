import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from catchup.main import create_app
from catchup.models import ModelConfig


@pytest.mark.parametrize("host", [
    "evil.example", "evil.example:8000", "localhost.evil.example", "127.0.0.1.evil.example",
    "localhost:bad", "localhost/evil", "localhost:80@evil.example",
])
def test_disallowed_host_rejected_before_action(host, monkeypatch):
    monkeypatch.delenv("CATCHUP_ALLOWED_HOSTS")
    with TestClient(create_app(), base_url="http://localhost") as client:
        response = client.put(
            "/api/settings/model",
            json={"base_url": "https://provider.example/v1", "model_id": "test", "api_key": "test-only-key"},
            headers={"Host": host},
        )
        assert response.status_code == 400
        assert response.json() == {"error": {"code": "invalid_host", "message": "Host is not allowed."}}
        with client.app.state.session_factory() as session:
            assert session.scalar(select(func.count()).select_from(ModelConfig)) == 0


@pytest.mark.parametrize("host", [
    "localhost", "localhost:8000", "127.0.0.1", "127.0.0.1:8000", "[::1]", "[::1]:8000",
])
def test_local_hosts_allowed_by_default(host, monkeypatch):
    monkeypatch.delenv("CATCHUP_ALLOWED_HOSTS")
    with TestClient(create_app(), base_url="http://localhost") as client:
        response = client.get("/api/health", headers={"Host": host})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_configured_deployment_host(monkeypatch):
    monkeypatch.setenv("CATCHUP_ALLOWED_HOSTS", "localhost,catchup.example.org")
    with TestClient(create_app(), base_url="http://localhost") as client:
        assert client.get("/api/health", headers={"Host": "catchup.example.org:443"}).status_code == 200
        assert client.get("/api/health", headers={"Host": "elsewhere.example.org"}).status_code == 400
