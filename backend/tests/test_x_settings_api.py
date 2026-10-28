"""X credentials are private, and the test endpoint reads no accounts or posts."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from catchup.main import create_app
from catchup.models import XCredential


@pytest.fixture
def client(test_settings, monkeypatch):
    monkeypatch.setenv("CATCHUP_SECRET_KEY", "test-instance-secret")
    # Settings is frozen; build it with the configured secret, as a real startup does.
    from catchup.config import Settings
    with TestClient(create_app(Settings.from_env()), base_url="http://localhost:8000") as api:
        yield api


def test_empty_x_settings_and_encrypted_save_without_leaking_token(client, caplog):
    assert client.get("/api/settings/x").json() == {"token_set": False, "token_last4": None}
    token = "test-" + "x" * 40
    with caplog.at_level("DEBUG"):
        response = client.put("/api/settings/x", json={"token": f" {token} "})
    assert response.status_code == 200
    assert response.json() == {"token_set": True, "token_last4": token[-4:]}
    assert client.get("/api/settings/x").json() == response.json()
    with client.app.state.session_factory() as session:
        row = session.get(XCredential, 1)
        assert row.token_encrypted != token
        assert token not in row.token_encrypted
    assert token not in response.text + client.get("/api/settings/x").text + caplog.text
    assert client.delete("/api/settings/x").status_code == 204
    assert client.get("/api/settings/x").json() == {"token_set": False, "token_last4": None}


@pytest.mark.parametrize("token", ["", "   ", "bad token", "a\nb", "x" * 1001])
def test_invalid_x_token_is_refused(client, token):
    response = client.put("/api/settings/x", json={"token": token})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_x_token"
    assert client.get("/api/settings/x").json()["token_set"] is False


def test_missing_instance_secret_refuses_x_token(test_settings):
    with TestClient(create_app(test_settings)) as client:
        response = client.put("/api/settings/x", json={"token": "test-" + "x" * 40})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "secret_not_configured"
        assert client.get("/api/settings/x").json()["token_set"] is False


def test_token_test_calls_usage_only_with_bearer_header(client):
    token = "test-" + "x" * 40
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        usage = router.get("https://api.x.com/2/usage/tweets").mock(
            return_value=httpx.Response(200, json={"data": {"project_usage": 0}})
        )
        lookup = router.get("https://api.x.com/2/users/by/username/example").mock(
            return_value=httpx.Response(200, json={})
        )
        posts = router.get("https://api.x.com/2/users/1/tweets").mock(
            return_value=httpx.Response(200, json={})
        )
        response = client.post("/api/settings/x/test", json={"token": token})
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert usage.call_count == 1
        assert usage.calls[0].request.url.params["days"] == "1"
        assert usage.calls[0].request.headers["authorization"] == f"Bearer {token}"
        assert lookup.call_count == posts.call_count == 0
        assert client.put("/api/settings/x", json={"token": token}).status_code == 200
        assert client.post("/api/settings/x/test", json={}).json() == {"ok": True}
        assert usage.call_count == 2


@pytest.mark.parametrize(("status", "code"), [(401, "x_token_rejected"), (403, "x_token_rejected"),
                                                (500, "fetch_failed")])
def test_token_test_reports_api_errors(client, status, code):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/usage/tweets").mock(return_value=httpx.Response(status))
        response = client.post("/api/settings/x/test", json={"token": "test-" + "x" * 40})
    assert response.json()["error"]["code"] == code
    if status == 500:
        assert response.json()["error"]["http_status"] == 500


def test_token_test_reports_reset_delay(client):
    reset = int((datetime.now(timezone.utc) + timedelta(seconds=60)).timestamp())
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://api.x.com/2/usage/tweets").mock(
            return_value=httpx.Response(429, headers={"x-rate-limit-reset": str(reset)})
        )
        response = client.post("/api/settings/x/test", json={"token": "test-" + "x" * 40})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert 1 <= response.json()["error"]["retry_after"] <= 60


def test_token_test_needs_token(client):
    response = client.post("/api/settings/x/test", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "x_token_required"
