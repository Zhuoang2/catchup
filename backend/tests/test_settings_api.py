import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.api.settings import get_model_client_factory
from catchup.crypto import decrypt_key
from catchup.llm.client import AuthFailed, ConnectionFailed, InsufficientBalance, ProviderError
from catchup.main import create_app
from catchup.models import ModelConfig

KEY = "test-only-secret-value-4821"


class FakeProvider:
    def __init__(self):
        self.error = None
        self.calls = []

    def __call__(self, base_url, api_key, model):
        self.calls.append((base_url, api_key, model))
        return self

    def list_models(self):
        if self.error:
            raise self.error
        return ["provider-current", "provider-next"]

    def close(self):
        pass


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("CATCHUP_SECRET_KEY", "unit-test-encryption-secret")
    app = create_app()
    fake = FakeProvider()
    app.dependency_overrides[get_model_client_factory] = lambda: fake
    with TestClient(app) as client:
        yield client, fake


def save(client, key=KEY):
    return client.put("/api/settings/model", json={
        "base_url": "https://provider.example/v1", "model_id": "provider-current", "api_key": key,
    })


def test_save_and_read_encrypted_configuration(api):
    client, _ = api
    response = save(client)
    assert response.status_code == 200
    assert response.json() == {
        "base_url": "https://provider.example/v1", "model_id": "provider-current",
        "key_set": True, "api_key_last4": "4821",
    }
    assert client.get("/api/settings/model").json() == response.json()
    assert KEY.encode() not in response.content
    with client.app.state.session_factory() as session:
        row = session.scalar(select(ModelConfig))
        assert KEY not in row.api_key_encrypted
        assert decrypt_key(row.api_key_encrypted, client.app.state.settings.secret_key) == KEY


def test_update_without_reentering_key(api):
    client, _ = api
    save(client)
    response = client.put("/api/settings/model", json={
        "base_url": "https://provider.example/v1", "model_id": "provider-next", "api_key": "",
    })
    assert response.json()["model_id"] == "provider-next"
    assert response.json()["api_key_last4"] == "4821"
    with client.app.state.session_factory() as session:
        row = session.get(ModelConfig, 1)
        assert decrypt_key(row.api_key_encrypted, client.app.state.settings.secret_key) == KEY


def test_can_test_unsaved_key_and_list_provider_models(api):
    client, fake = api
    response = client.post("/api/settings/model/test", json={
        "base_url": "https://provider.example/v1", "api_key": KEY,
    })
    assert response.json() == {"ok": True, "models": ["provider-current", "provider-next"]}
    assert fake.calls[0][:2] == ("https://provider.example/v1", KEY)
    assert KEY.encode() not in response.content
    assert client.get("/api/settings/model").json()["key_set"] is False


def test_can_test_stored_key_without_resending_it(api):
    client, fake = api
    save(client)
    response = client.post("/api/settings/model/test", json={})
    assert response.json()["models"] == ["provider-current", "provider-next"]
    assert fake.calls[-1] == ("https://provider.example/v1", KEY, "provider-current")


@pytest.mark.parametrize("error,code,status", [
    (AuthFailed("The provider rejected the API key."), "auth_failed", 401),
    (ConnectionFailed("Could not connect to the model provider at https://provider.example/v1."),
     "connection_failed", 502),
    (InsufficientBalance("The provider account has insufficient balance."), "insufficient_balance", 402),
    (ProviderError("The provider returned an error."), "provider_error", 502),
])
def test_provider_errors_are_safe(api, error, code, status):
    client, fake = api
    fake.error = error
    response = client.post("/api/settings/model/test", json={
        "base_url": "https://provider.example/v1", "api_key": KEY,
    })
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert KEY.encode() not in response.content
    if code == "connection_failed":
        assert "https://provider.example/v1" in response.json()["error"]["message"]


def test_missing_instance_secret_refuses_save():
    with TestClient(create_app()) as client:
        response = save(client)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "secret_not_configured"
        assert "CATCHUP_SECRET_KEY" in response.json()["error"]["message"]
        assert client.get("/api/settings/model").json()["key_set"] is False


def test_invalid_request_never_echoes_submitted_key(api):
    client, _ = api
    response = client.put("/api/settings/model", json={
        "base_url": "https://provider.example/v1", "model_id": "test", "api_key": {"raw": KEY},
    })
    assert response.status_code == 422
    assert response.json() == {"error": {"code": "invalid_request", "message": "Invalid request."}}
    assert KEY.encode() not in response.content


def test_preference_save_and_read(api):
    client, _ = api
    assert client.get("/api/settings/preferences").json() == {"digest_language": "en"}
    for language in ("zh-Hans", "original", "Français"):
        assert client.put("/api/settings/preferences", json={"digest_language": language}).json() == {
            "digest_language": language,
        }
        assert client.get("/api/settings/preferences").json() == {"digest_language": language}


@pytest.mark.parametrize("language", ["", "   ", "x" * 41])
def test_invalid_language(api, language):
    client, _ = api
    response = client.put("/api/settings/preferences", json={"digest_language": language})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_language"
