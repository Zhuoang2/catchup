"""X credentials are private, and the test endpoint reads no accounts or posts."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.main import create_app
from catchup.models import (Digest, DigestItem, DigestRun, DigestTopic, Item, ItemContext,
                             Source, XAccount, XCredential)
from catchup.sources.x_api import XPage, XUser


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


def test_saved_token_with_changed_instance_secret_fails_before_usage_request(client):
    assert client.put("/api/settings/x", json={"token": "test-" + "x" * 40}).status_code == 200
    client.app.state.settings = replace(client.app.state.settings, secret_key="different-instance-secret")
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        usage = router.get("https://api.x.com/2/usage/tweets").mock(
            return_value=httpx.Response(200, json={"data": {"project_usage": 0}}))
        response = client.post("/api/settings/x/test", json={})
        assert usage.call_count == 0
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "secret_invalid", "message": "Check the X token and instance secret.",
    }


def seed_mixed_digest(client, language="en"):
    with client.app.state.session_factory() as session:
        feed = Source(title="News", feed_url="https://feed.example/rss",
                      site_url="https://feed.example", input_url="https://feed.example/rss", kind="feed")
        x_source = Source(title="Writer", feed_url="x:user:123", site_url="https://x.com/writer",
                          input_url="https://x.com/writer", kind="x")
        capture = Source(title="Saved from browser", feed_url="catchup:captures",
                         site_url="", input_url="catchup:captures", kind="capture")
        session.add_all([feed, x_source, capture])
        session.flush()
        session.add(XAccount(source_id=x_source.id, user_id="123", username="writer"))
        feed_item = Item(source_id=feed.id, identity_key="feed", link="https://feed.example/post",
                         title="Feed", content_text="Feed text", content_origin="feed", state="delivered")
        x_item = Item(source_id=x_source.id, identity_key="x", link="https://x.com/writer/status/1",
                      title="X title", content_text="X text", content_origin="x", state="delivered")
        capture_item = Item(source_id=capture.id, identity_key="saved", link="https://x.com/other/status/2",
                            title="Saved", content_text="Saved page", content_origin="capture", state="delivered")
        session.add_all([feed_item, x_item, capture_item])
        session.flush()
        session.add(ItemContext(item_id=x_item.id, ref="L1", kind="link",
                                url="https://blog.example/post", title="Article", text="X context", position=1))
        run = DigestRun(status="succeeded")
        session.add(run)
        session.flush()
        digest = Digest(run_id=run.id, model_id="fake", item_count=3, source_count=3, language=language)
        session.add(digest)
        session.flush()
        run.digest_id = digest.id
        topic = DigestTopic(digest_id=digest.id, position=0, title="About X", overview="Derived from X")
        session.add(topic)
        session.flush()
        session.add_all([
            DigestItem(digest_id=digest.id, topic_id=topic.id, position=0, item_id=feed_item.id,
                       title="Feed", link=feed_item.link, source_name="News", source_kind="feed"),
            DigestItem(digest_id=digest.id, topic_id=topic.id, position=1, item_id=x_item.id,
                       title="X title", link=x_item.link, source_name="X · Writer", source_kind="x",
                       summary="X derived summary", context_links=[{"url": "https://blog.example/post"}]),
            DigestItem(digest_id=digest.id, topic_id=topic.id, position=2, item_id=capture_item.id,
                       title="Saved", link=capture_item.link, source_name="Saved from browser",
                       source_kind="capture"),
        ])
        session.commit()
        return digest.id, run.id, x_source.id


@pytest.mark.parametrize(("language", "title"), [("en", "Other"), ("zh-Hans", "其他")])
def test_delete_all_x_data_preserves_non_x_items_and_scrubs_mixed_topics(client, language, title):
    client.put("/api/settings/x", json={"token": "test-" + "x" * 40})
    digest_id, _, _ = seed_mixed_digest(client, language)
    response = client.post("/api/settings/x/delete-all")
    assert response.status_code == 200
    assert response.json() == {"digest_items": 1, "digests": 0, "accounts": 1}
    detail = client.get(f"/api/digests/{digest_id}").json()
    assert (detail["item_count"], detail["source_count"]) == (2, 2)
    assert detail["topics"][0]["title"] == title
    assert detail["topics"][0]["overview"] == ""
    assert [item["source_kind"] for item in detail["topics"][0]["items"]] == ["feed", "capture"]
    assert client.get("/api/settings/x").json()["token_set"] is False
    with client.app.state.session_factory() as session:
        assert session.scalars(select(Source.kind)).all() == ["feed", "capture"]
        assert session.scalar(select(XAccount)) is None
        assert session.scalars(select(Item.content_text)).all() == ["Feed text", "Saved page"]
        assert session.scalar(select(ItemContext)) is None


def test_delete_all_removes_orphaned_x_digest_items_and_x_only_digests(client):
    _, _, x_source_id = seed_mixed_digest(client)
    with client.app.state.session_factory() as session:
        x_only_run = DigestRun(status="succeeded")
        session.add(x_only_run)
        session.flush()
        x_only = Digest(run_id=x_only_run.id, model_id="fake", item_count=1, source_count=1, language="en")
        session.add(x_only)
        session.flush()
        x_only_run.digest_id = x_only.id
        topic = DigestTopic(digest_id=x_only.id, position=0, title="X", overview="X")
        session.add(topic)
        session.flush()
        session.add(DigestItem(digest_id=x_only.id, topic_id=topic.id, position=0, item_id=None,
                               title="Orphan post", link="https://x.com/writer/status/3",
                               source_name="X · Writer", source_kind="x"))
        session.delete(session.get(Source, x_source_id))
        session.commit()
        assert session.scalar(select(DigestItem).where(DigestItem.title == "X title")).item_id is None
        x_only_id, run_id = x_only.id, x_only_run.id
    response = client.post("/api/settings/x/delete-all")
    assert response.json() == {"digest_items": 2, "digests": 1, "accounts": 0}
    assert client.get(f"/api/digests/{x_only_id}").status_code == 404
    assert all(row["id"] != x_only_id for row in client.get("/api/digests").json())
    with client.app.state.session_factory() as session:
        assert session.get(DigestRun, run_id).digest_id is None
        assert session.scalar(select(DigestItem).where(DigestItem.source_kind == "x")) is None


def test_delete_all_refuses_active_run_without_any_changes(client):
    client.put("/api/settings/x", json={"token": "test-" + "x" * 40})
    digest_id, _, x_source_id = seed_mixed_digest(client)
    with client.app.state.session_factory() as session:
        session.add(DigestRun(status="collecting"))
        session.commit()
    response = client.post("/api/settings/x/delete-all")
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "run_active", "message": "A digest is being made. Try again when it finishes.",
    }
    assert client.get("/api/settings/x").json()["token_set"] is True
    with client.app.state.session_factory() as session:
        assert session.get(Source, x_source_id) is not None
        assert session.get(Digest, digest_id).item_count == 3


def test_extension_cannot_delete_all_x_data(client):
    client.put("/api/settings/x", json={"token": "test-" + "x" * 40})
    token = client.post("/api/settings/extension-tokens", json={"name": "Chrome"}).json()["token"]
    response = client.post("/api/settings/x/delete-all", headers={
        "Origin": "chrome-extension://abcdefghijklmnop", "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 403
    assert client.get("/api/settings/x").json()["token_set"] is True


@pytest.mark.parametrize("operation", ["delete-token", "delete-all"])
def test_removing_x_access_empties_the_preview_cache(client, operation):
    feed_url = "x:user:123"
    cache = client.app.state.x_preview_cache
    cache.put(feed_url, XUser("123", "Writer", "writer", False, None), XPage((), None, 0))
    response = (client.delete("/api/settings/x") if operation == "delete-token"
                else client.post("/api/settings/x/delete-all"))
    assert response.status_code in (200, 204)
    assert cache.pop(feed_url) is None
