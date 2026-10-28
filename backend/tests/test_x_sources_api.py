"""Preview and follow X accounts without visiting x.com pages."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from catchup.config import Settings
from catchup.main import create_app
from catchup.models import Item, Source, SourceCheck, XAccount

UID = "1234567890123456789"
TOKEN = "test-" + "x" * 40
PROFILE = "https://x.com/writer"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CATCHUP_SECRET_KEY", "test-instance-secret")
    with TestClient(create_app(Settings.from_env()), base_url="http://localhost:8000") as api:
        yield api


def post(post_id: str, *, days: int = 1, reply: bool = False):
    result = {
        "id": post_id, "text": f"Post {post_id} https://t.co/link",
        "created_at": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
        "conversation_id": post_id, "entities": {"urls": [
            {"url": "https://t.co/link", "expanded_url": "https://blog.example/article"}]},
        "attachments": {"media_keys": ["3_photo"]},
    }
    if reply:
        result["in_reply_to_user_id"] = UID
        result["referenced_tweets"] = [{"type": "replied_to", "id": "900"}]
    return result


def mock_x(router, *, username="writer", newest="900", posts=None, protected=False):
    user = {"data": {"id": UID, "name": "Sample Writer", "username": username,
                     "protected": protected, "most_recent_tweet_id": newest}}
    lookup = router.get(f"https://api.x.com/2/users/by/username/{username}").mock(
        return_value=httpx.Response(200, json=user))
    by_id = router.get(f"https://api.x.com/2/users/{UID}").mock(
        return_value=httpx.Response(200, json=user))
    timeline = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
        return_value=httpx.Response(200, json={
            "data": posts or [], "meta": {"result_count": len(posts or [])},
            "includes": {"media": [{"media_key": "3_photo", "type": "photo",
                                    "url": "https://pbs.twimg.com/media/photo.jpg", "alt_text": "Chart"}]},
        }))
    return lookup, by_id, timeline


def save_token(client):
    assert client.put("/api/settings/x", json={"token": TOKEN}).status_code == 200


def test_x_preview_without_token_does_not_request_x_or_discover(client, monkeypatch):
    monkeypatch.setattr("catchup.api.sources.discover", lambda *_args, **_kw: pytest.fail("feed discovery called"))
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        x_page = router.get(PROFILE).mock(return_value=httpx.Response(200))
        lookup, _, posts = mock_x(router)
        response = client.post("/api/sources/preview", json={"url": PROFILE})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "x_token_required"
        assert x_page.call_count == lookup.call_count == posts.call_count == 0


def test_preview_shape_self_reply_filter_and_no_writes(client, monkeypatch):
    save_token(client)
    monkeypatch.setattr("catchup.api.sources.discover", lambda *_args, **_kw: pytest.fail("feed discovery called"))
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        x_page = router.get(PROFILE).mock(return_value=httpx.Response(200))
        lookup, _, timeline = mock_x(router, posts=[post("900"), post("899", reply=True)])
        response = client.post("/api/sources/preview", json={"url": PROFILE})
        assert x_page.call_count == 0 and lookup.call_count == timeline.call_count == 1
        params = timeline.calls[0].request.url.params
        assert params["max_results"] == "5" and params["exclude"] == "retweets,replies"
    assert response.status_code == 200
    data = response.json()
    assert {key: data[key] for key in ("feed_url", "site_url", "title", "kind",
                                        "follows_site_feed_notice", "captions_enabled", "username")} == {
        "feed_url": f"x:user:{UID}", "site_url": PROFILE, "title": "Sample Writer", "kind": "x",
        "follows_site_feed_notice": False, "captions_enabled": False, "username": "writer",
    }
    assert len(data["entries"]) == 1
    assert data["entries"][0]["title"].startswith("Post 900")
    assert data["entries"][0]["link"] == "https://x.com/writer/status/900"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 0
        assert session.scalar(select(func.count()).select_from(Item)) == 0


def test_preview_rejects_protected_unknown_and_invalid_pages(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, _, posts = mock_x(router, protected=True)
        protected = client.post("/api/sources/preview", json={"url": PROFILE})
        assert protected.json()["error"]["code"] == "x_account_protected"
        assert posts.call_count == 0
        lookup.mock(return_value=httpx.Response(200, json={"errors": [
            {"type": "https://api.x.com/2/problems/resource-not-found", "resource_type": "user"}]}))
        missing = client.post("/api/sources/preview", json={"url": PROFILE})
        assert missing.json()["error"]["code"] == "x_account_not_found"
        bad = client.post("/api/sources/preview", json={"url": "https://x.com/home"})
        assert bad.json()["error"]["code"] == "not_an_x_account"


def test_preview_detects_duplicate_by_id_after_username_change(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, _, timeline = mock_x(router, posts=[post("900")])
        first = client.post("/api/sources/preview", json={"url": PROFILE})
        assert client.post("/api/sources", json={"feed_url": first.json()["feed_url"]}).status_code == 201
        again = client.post("/api/sources/preview", json={"url": PROFILE})
        assert again.status_code == 422 and again.json()["error"]["code"] == "duplicate"
        assert again.json()["error"]["existing_source"]["id"] > 0
        renamed = router.get("https://api.x.com/2/users/by/username/newwriter").mock(
            return_value=httpx.Response(200, json={"data": {
                "id": UID, "name": "Sample Writer", "username": "newwriter", "protected": False}}))
        second = client.post("/api/sources/preview", json={"url": "https://x.com/newwriter"})
        assert second.json()["error"]["code"] == "duplicate"
        assert renamed.call_count == 1 and timeline.call_count == 1
        assert lookup.call_count == 2


def test_confirm_uses_cache_and_stores_only_recent_posts(client):
    save_token(client)
    posts = [post("900"), post("899", days=2), post("898", days=8), post("897", days=9), post("896", days=10)]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, _, timeline = mock_x(router, posts=posts)
        preview = client.post("/api/sources/preview", json={"url": PROFILE})
        assert preview.status_code == 200
        confirm = client.post("/api/sources", json={"feed_url": preview.json()["feed_url"]})
        assert confirm.status_code == 201
        assert lookup.call_count == timeline.call_count == 1
    with client.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        account = session.get(XAccount, source.id)
        items = session.scalars(select(Item).order_by(Item.id)).all()
        check = session.scalar(select(SourceCheck))
        assert (source.kind, source.site_url, source.title, source.last_check_at) == (
            "x", PROFILE, "Sample Writer", None,
        )
        assert (account.user_id, account.username, account.newest_id) == (UID, "writer", "900")
        assert account.gap_since_id is account.gap_until_id is None
        assert [item.identity_key for item in items] == ["900", "899"]
        assert all(item.state == "pending" and item.content_origin == "x" for item in items)
        assert items[0].site_name == "X · Sample Writer"
        assert items[0].entry_author == "Sample Writer @writer"
        assert items[0].content_text.endswith("https://blog.example/article")
        assert items[0].entry_links == [{"url": "https://blog.example/article", "text": ""}]
        assert items[0].image_candidates[0]["alt"] == "Chart"
        assert check.run_id is None and check.new_count == 2


def test_confirm_cache_miss_looks_up_by_id_and_handles_never_posted(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        by_name, by_id, timeline = mock_x(router, newest=None)
        result = client.post("/api/sources", json={"feed_url": f"x:user:{UID}"})
        assert result.status_code == 201
        assert by_name.call_count == 0
        assert by_id.call_count == timeline.call_count == 1
    with client.app.state.session_factory() as session:
        assert session.scalar(select(XAccount)).newest_id is None
        assert session.scalar(select(func.count()).select_from(Item)) == 0


def test_preview_other_x_host_refuses_without_discovery(client, monkeypatch):
    monkeypatch.setattr("catchup.api.sources.discover", lambda *_a, **_kw: pytest.fail("discovery on X host"))
    response = client.post("/api/sources/preview", json={"url": "https://help.x.com/en"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "not_an_x_account"


def test_confirm_feed_url_on_x_host_refuses_without_fetch(client, monkeypatch):
    response = client.post("/api/sources", json={"feed_url": "https://help.x.com/rss"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "blocked_address"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)) is None


def test_removed_token_invalidates_cached_preview_and_refuses_confirm(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, by_id, timeline = mock_x(router, posts=[post("900")])
        preview = client.post("/api/sources/preview", json={"url": PROFILE})
        assert preview.status_code == 200
        assert client.delete("/api/settings/x").status_code == 204
        confirm = client.post("/api/sources", json={"feed_url": preview.json()["feed_url"]})
        assert lookup.call_count == timeline.call_count == 1 and by_id.call_count == 0
    assert confirm.status_code == 422 and confirm.json()["error"]["code"] == "x_token_required"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)) is None and session.scalar(select(Item)) is None


def test_delete_all_clears_cached_preview_before_confirm_with_a_new_token(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, by_id, timeline = mock_x(router, posts=[post("900")])
        assert client.post("/api/sources/preview", json={"url": PROFILE}).status_code == 200
        assert client.post("/api/settings/x/delete-all").status_code == 200
        save_token(client)
        confirm = client.post("/api/sources", json={"feed_url": f"x:user:{UID}"})
        assert confirm.status_code == 201
        assert lookup.call_count == 1 and by_id.call_count == 1 and timeline.call_count == 2


def test_confirm_rejects_cached_preview_when_instance_secret_has_changed(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, by_id, timeline = mock_x(router, posts=[post("900")])
        assert client.post("/api/sources/preview", json={"url": PROFILE}).status_code == 200
        client.app.state.settings = replace(client.app.state.settings, secret_key="different-instance-secret")
        response = client.post("/api/sources", json={"feed_url": f"x:user:{UID}"})
        assert lookup.call_count == timeline.call_count == 1 and by_id.call_count == 0
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "secret_invalid"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)) is None and session.scalar(select(Item)) is None


def test_confirm_refuses_late_preview_cached_after_token_removal(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        lookup, by_id, timeline = mock_x(router, posts=[post("900")])
        assert client.post("/api/sources/preview", json={"url": PROFILE}).status_code == 200
        cached = client.app.state.x_preview_cache.pop(f"x:user:{UID}")
        assert client.delete("/api/settings/x").status_code == 204
        client.app.state.x_preview_cache.put(f"x:user:{UID}", *cached)
        response = client.post("/api/sources", json={"feed_url": f"x:user:{UID}"})
        assert lookup.call_count == timeline.call_count == 1 and by_id.call_count == 0
    assert response.status_code == 422 and response.json()["error"]["code"] == "x_token_required"
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)) is None


def test_confirm_starts_after_lookup_most_recent_id_even_if_preview_is_older(client):
    save_token(client)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        mock_x(router, newest="999", posts=[post("900"), post("899")])
        preview = client.post("/api/sources/preview", json={"url": PROFILE})
        assert preview.status_code == 200
        assert client.post("/api/sources", json={"feed_url": preview.json()["feed_url"]}).status_code == 201
    with client.app.state.session_factory() as session:
        assert session.scalar(select(XAccount)).newest_id == "999"
