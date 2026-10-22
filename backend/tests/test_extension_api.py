"""Public connection and capture HTTP interfaces."""

import hashlib
import socket

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from catchup.main import create_app
from catchup.models import Digest, DigestItem, DigestRun, DigestTopic, ExtensionToken, Item, ItemContext, Source

FEED = "https://site.example/feed"
ORIGIN = {"Origin": "chrome-extension://abcdefghijklmnop"}
FEED_XML = (b"<rss><channel><title>Example</title><link>https://site.example/</link>"
            b"</channel></rss>")


@pytest.fixture
def client(test_settings):
    with TestClient(create_app(test_settings), base_url="http://localhost:8000") as api:
        yield api


def test_connect_lists_only_metadata_and_stores_only_hash(client):
    response = client.post("/api/settings/extension-tokens", json={"name": "Chrome"})
    assert response.status_code == 201
    created = response.json()
    assert set(created) == {"id", "name", "created_at", "token"}
    assert created["name"] == "Chrome"
    assert created["token"].startswith("cu_")
    with client.app.state.session_factory() as session:
        row = session.scalar(select(ExtensionToken))
        assert row.token_hash == hashlib.sha256(created["token"].encode()).hexdigest()
        assert created["token"] not in row.token_hash
    listed = client.get("/api/settings/extension-tokens")
    assert listed.status_code == 200
    assert listed.json() == [{
        "id": created["id"], "name": "Chrome", "created_at": created["created_at"], "last_used_at": None,
    }]
    assert created["token"] not in listed.text


def test_disconnect_removes_connection(client):
    created = client.post("/api/settings/extension-tokens", json={"name": "Edge"}).json()
    assert client.delete(f"/api/settings/extension-tokens/{created['id']}").status_code == 204
    assert client.get("/api/settings/extension-tokens").json() == []
    with client.app.state.session_factory() as session:
        assert session.get(ExtensionToken, created["id"]) is None


@pytest.mark.parametrize("name", ["", "x" * 61])
def test_connection_name_must_be_one_to_sixty_characters(client, name):
    response = client.post("/api/settings/extension-tokens", json={"name": name})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.fixture
def connected(client):
    token = client.post("/api/settings/extension-tokens", json={"name": "Chrome"}).json()["token"]
    return {**ORIGIN, "Authorization": f"Bearer {token}"}


@pytest.fixture
def public_feed(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, *_a, **_kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get(FEED).mock(return_value=httpx.Response(
            200, content=FEED_XML, headers={"content-type": "application/rss+xml"},
        ))
        yield route


def test_token_previews_and_updates_last_used(client, connected, public_feed):
    assert client.post("/api/sources/preview", json={"url": FEED}, headers=connected).status_code == 200
    assert public_feed.call_count == 1
    with client.app.state.session_factory() as session:
        assert session.scalar(select(ExtensionToken)).last_used_at is not None


def test_token_saves_source(client, connected, public_feed):
    assert client.post("/api/sources", json={"feed_url": FEED}, headers=connected).status_code == 201
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Source)).feed_url == FEED


def test_token_ignores_cross_site_fetch_metadata(client, connected, public_feed):
    response = client.post("/api/sources/preview", json={"url": FEED},
                           headers={**connected, "Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 200


@pytest.mark.parametrize("disconnected", [False, True])
def test_unknown_or_disconnected_token_cannot_fetch(client, connected, public_feed, disconnected):
    if disconnected:
        row = client.get("/api/settings/extension-tokens").json()[0]
        assert client.delete(f"/api/settings/extension-tokens/{row['id']}").status_code == 204
        headers = connected
    else:
        headers = {**ORIGIN, "Authorization": "Bearer cu_not-a-real-token"}
    response = client.post("/api/sources/preview", json={"url": FEED}, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert public_feed.call_count == 0


def test_token_cannot_change_preferences(client, connected):
    response = client.put("/api/settings/preferences", json={"digest_language": "fr"}, headers=connected)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_site_request"
    assert client.get("/api/settings/preferences").json()["digest_language"] == "en"


def test_token_cannot_start_run(client, connected):
    assert client.post("/api/digest-runs", headers=connected).status_code == 403
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DigestRun)) == 0


def test_status_requires_token_even_for_get(client, connected):
    assert client.get("/api/extension/status", headers=connected).json() == {"name": "Chrome", "waiting": 0}
    response = client.get("/api/extension/status", headers=ORIGIN)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


def test_other_auth_scheme_follows_existing_origin_policy(client):
    foreign = {**ORIGIN, "Authorization": "Basic fake-auth"}
    assert client.put("/api/settings/preferences", json={"digest_language": "fr"},
                      headers=foreign).status_code == 403
    own = {**foreign, "Origin": "http://localhost:8000"}
    response = client.put("/api/settings/preferences", json={"digest_language": "fr"}, headers=own)
    assert response.status_code == 200
    assert response.json()["digest_language"] == "fr"


def test_proxy_bearer_without_extension_prefix_follows_origin_policy(client):
    proxy = {"Authorization": "Bearer some-proxy-token"}
    own = client.put("/api/settings/preferences", json={"digest_language": "fr"},
                     headers={**proxy, "Origin": "http://localhost:8000"})
    assert own.status_code == 200
    assert own.json()["digest_language"] == "fr"
    foreign = client.put("/api/settings/preferences", json={"digest_language": "de"},
                         headers={**proxy, "Origin": "http://other.example"})
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "cross_site_request"
    assert client.get("/api/settings/preferences").json()["digest_language"] == "fr"


def test_token_cannot_create_or_list_connections(client, connected):
    assert client.post("/api/settings/extension-tokens", json={"name": "Another"},
                       headers=connected).status_code == 403
    assert client.get("/api/settings/extension-tokens", headers=connected).status_code == 403
    assert len(client.get("/api/settings/extension-tokens").json()) == 1


def test_last_used_failure_does_not_fail_valid_request(client, connected, monkeypatch):
    def locked(*_args):
        raise OperationalError("UPDATE extension_tokens", {}, Exception("database is locked"))
    monkeypatch.setattr("catchup.main._touch_extension_token", locked)
    assert client.get("/api/extension/status", headers=connected).json() == {"name": "Chrome", "waiting": 0}


def save_page(client, connected, **changes):
    body = {"url": "https://example.com/post", "title": "A post", "text": "The post text", **changes}
    return client.post("/api/captures", json=body, headers=connected)


def test_first_capture_creates_source_and_item(client, connected):
    response = save_page(
        client, connected, site_name="Example", author="Writer", published_at="2026-10-01T12:00:00Z",
        replies=["Author's reply"], links=[{"url": "https://other.example/article", "text": "Read"}],
        images=[{"url": "https://example.com/photo.png", "alt": "Photo"}],
    )
    assert response.status_code == 201
    assert response.json()["waiting"] == 1
    with client.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        item = session.scalar(select(Item))
        assert (source.kind, source.title, source.feed_url, source.input_url, source.site_url) == (
            "capture", "Saved from browser", "catchup:captures", "catchup:captures", "",
        )
        assert (item.source_id, item.identity_key, item.link, item.title, item.content_text) == (
            source.id, "https://example.com/post", "https://example.com/post", "A post", "The post text",
        )
        assert (item.content_origin, item.state, item.entry_author, item.site_name) == (
            "capture", "pending", "Writer", "Example",
        )
        assert item.published_at.isoformat() == "2026-10-01T12:00:00+00:00"
        assert item.captured_replies == ["Author's reply"]
        assert item.entry_links == [{"url": "https://other.example/article", "text": "Read"}]
        assert item.image_candidates[0]["url"] == "https://example.com/photo.png"
        assert item.image_candidates[0]["alt"] == "Photo"


def test_capture_caps_and_filters(client, connected):
    response = save_page(
        client, connected, title="T" * 310, text="t" * 17000, site_name="S" * 210,
        author="A" * 210, replies=["r" * 500] * 12,
        images=[{"url": f"https://example.com/{i}.png", "alt": "Image"} for i in range(10)]
        + [{"url": "data:image/png;base64,not-an-image", "alt": ""}, {"url": "https://example.com/avatar/u", "alt": ""}],
        links=[{"url": f"https://other.example/{i}", "text": "Link"} for i in range(55)]
        + [{"url": "javascript:alert(1)", "text": "Bad"}],
    )
    assert response.status_code == 201
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert (len(item.title), len(item.content_text), len(item.site_name), len(item.entry_author)) == (
            300, 16000, 200, 200,
        )
        assert len(item.captured_replies) == 8
        assert len("\n\n".join(item.captured_replies)) == 4000
        assert len(item.image_candidates) == 8
        assert len(item.entry_links) == 50
        assert all(link["url"].startswith("https://") for link in item.entry_links)


def test_capture_without_title_uses_first_eighty_text_characters(client, connected):
    text = "x" * 81 + " a later word"
    response = save_page(client, connected, title="", text=text)
    assert response.status_code == 201
    assert response.json()["title"] == "x" * 80
    with client.app.state.session_factory() as session:
        assert session.get(Item, response.json()["id"]).title == "x" * 80


def test_capture_cuts_long_link_text_and_image_alt(client, connected):
    response = save_page(
        client, connected,
        links=[{"url": "https://other.example/a", "text": "L" * 501}],
        images=[{"url": "https://example.com/photo.png", "alt": "I" * 501}],
    )
    assert response.status_code == 201
    with client.app.state.session_factory() as session:
        item = session.get(Item, response.json()["id"])
        assert item.entry_links == [{"url": "https://other.example/a", "text": "L" * 500}]
        assert item.image_candidates == [{"url": "https://example.com/photo.png", "alt": "I" * 500}]


def test_capture_limits_replies_by_count(client, connected):
    assert save_page(client, connected, replies=["Short"] * 12).status_code == 201
    with client.app.state.session_factory() as session:
        assert session.scalar(select(Item)).captured_replies == ["Short"] * 10


def test_capture_drops_unsafe_links_and_images_before_caps(client, connected):
    assert save_page(
        client, connected,
        links=[{"url": "javascript:alert(1)", "text": "Bad"},
               {"url": "https://other.example/post", "text": "Good"}],
        images=[{"url": "data:image/png;base64,abc", "alt": "Inline"},
                {"url": "https://example.com/avatar/u.png", "alt": "Avatar"},
                {"url": "https://example.com/photo.png", "alt": "Photo"},
                {"url": "https://example.com/photo.png#duplicate", "alt": "Duplicate"}],
    ).status_code == 201
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.entry_links == [{"url": "https://other.example/post", "text": "Good"}]
        assert [image["url"] for image in item.image_candidates] == ["https://example.com/photo.png"]


def test_capture_normalizes_url_and_uses_host_for_missing_site_name(client, connected):
    response = save_page(client, connected, url="HTTPS://Example.COM/a#x", site_name="  ")
    assert response.status_code == 201
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.identity_key == "https://example.com/a"
        assert item.site_name == "example.com"


def test_recapture_replaces_waiting_item_and_clears_cached_context(client, connected):
    created = save_page(client, connected).json()
    with client.app.state.session_factory() as session:
        item = session.get(Item, created["id"])
        item.summary, item.summary_language, item.summary_images, item.context_status = (
            "Old", "en", [{"url": "https://example.com/old.png"}], "gathered",
        )
        item.contexts.append(ItemContext(ref="L1", kind="link", url="https://other.example/",
                                         title="Old", text="Old", position=1))
        session.commit()
    response = save_page(client, connected, title="New", text="Updated")
    assert response.status_code == 201
    assert response.json()["id"] == created["id"]
    assert response.json()["waiting"] == 1
    with client.app.state.session_factory() as session:
        item = session.get(Item, created["id"])
        assert (item.title, item.content_text) == ("New", "Updated")
        assert (item.summary, item.summary_language, item.summary_images, item.context_status) == (
            None, None, None, None,
        )
        assert item.contexts == []


def test_recapture_after_delivery_adds_one_waiting_item(client, connected):
    url = "https://example.com/a"
    first = save_page(client, connected, url=url).json()
    with client.app.state.session_factory() as session:
        session.get(Item, first["id"]).state = "delivered"
        session.commit()
    second = save_page(client, connected, url=url, title="Second").json()
    assert second["id"] != first["id"]
    with client.app.state.session_factory() as session:
        item = session.get(Item, second["id"])
        assert item.identity_key.startswith(url + "#")
    third = save_page(client, connected, url=url, title="Third").json()
    assert third["id"] == second["id"]
    with client.app.state.session_factory() as session:
        waiting = session.scalars(select(Item).where(Item.state == "pending")).all()
        assert len([item for item in waiting if item.link == url]) == 1
        assert session.get(Item, second["id"]).title == "Third"
        assert session.get(Item, first["id"]).state == "delivered"


def test_recapture_preserves_case_sensitive_addresses_after_delivery(client, connected):
    lower = "https://example.com/a"
    delivered = save_page(client, connected, url=lower).json()
    with client.app.state.session_factory() as session:
        session.get(Item, delivered["id"]).state = "delivered"
        session.commit()
    waiting_lower = save_page(client, connected, url=lower, title="Lower").json()
    upper = save_page(client, connected, url="https://example.com/A", title="Upper").json()
    assert upper["id"] != waiting_lower["id"]
    with client.app.state.session_factory() as session:
        lower_item = session.get(Item, waiting_lower["id"])
        assert (lower_item.identity_key.startswith(lower + "#"), lower_item.title, lower_item.link) == (
            True, "Lower", lower,
        )
        pending = session.scalars(select(Item).where(Item.state == "pending")).all()
        assert {(item.link, item.title) for item in pending} == {
            (lower, "Lower"), ("https://example.com/A", "Upper"),
        }


def test_recapture_treats_underscore_as_literal_in_waiting_address(client, connected):
    other_url = "https://example.com/axb"
    delivered = save_page(client, connected, url=other_url).json()
    with client.app.state.session_factory() as session:
        session.get(Item, delivered["id"]).state = "delivered"
        session.commit()
    waiting_other = save_page(client, connected, url=other_url, title="Other").json()
    new = save_page(client, connected, url="https://example.com/a_b", title="Underscore").json()
    assert new["id"] != waiting_other["id"]
    with client.app.state.session_factory() as session:
        assert session.get(Item, waiting_other["id"]).title == "Other"
        assert {(item.link, item.title) for item in session.scalars(
            select(Item).where(Item.state == "pending")
        ).all()} == {
            (other_url, "Other"), ("https://example.com/a_b", "Underscore"),
        }


def test_active_run_refuses_replacing_waiting_but_accepts_new_page(client, connected):
    first = save_page(client, connected).json()
    with client.app.state.session_factory() as session:
        session.add(DigestRun(status="collecting"))
        session.commit()
    response = save_page(client, connected, text="changed")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "run_active"
    with client.app.state.session_factory() as session:
        assert session.get(Item, first["id"]).content_text == "The post text"
    assert save_page(client, connected, url="https://example.com/new").status_code == 201


def test_first_capture_recovers_after_source_creation_race(client, connected, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session

    real_flush = Session.flush
    raced = False

    def flush(self, *args, **kwargs):
        nonlocal raced
        if not raced and any(isinstance(obj, Source) and obj.kind == "capture" for obj in self.new):
            raced = True
            with client.app.state.session_factory() as other:
                other.add(Source(kind="capture", title="Saved from browser", site_url="",
                                 feed_url="catchup:captures", input_url="catchup:captures"))
                other.commit()
            raise IntegrityError("INSERT sources", {}, Exception("unique feed_url"))
        return real_flush(self, *args, **kwargs)

    monkeypatch.setattr(Session, "flush", flush)
    response = save_page(client, connected)
    assert response.status_code == 201
    assert raced
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 1
        assert session.scalar(select(Item)).source_id == session.scalar(select(Source.id))


@pytest.mark.parametrize("body", [
    {"url": "file:///tmp/post", "title": "Title", "text": "Text"},
    {"url": "https://example.com/post", "title": "", "text": ""},
])
def test_capture_rejects_invalid_body(client, connected, body):
    response = client.post("/api/captures", json=body, headers=connected)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_list_captures_is_pending_only_newest_first(client, connected):
    first = save_page(client, connected, url="https://example.com/one").json()
    delivered = save_page(client, connected, url="https://example.com/done").json()
    second = save_page(client, connected, url="https://example.com/two").json()
    with client.app.state.session_factory() as session:
        session.get(Item, delivered["id"]).state = "delivered"
        session.commit()
    response = client.get("/api/captures", headers=connected)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [second["id"], first["id"]]
    assert set(response.json()[0]) == {"id", "url", "title", "site_name", "saved_at"}


def test_remove_only_pending_captures(client, connected):
    pending = save_page(client, connected).json()
    delivered = save_page(client, connected, url="https://example.com/done").json()
    with client.app.state.session_factory() as session:
        session.get(Item, delivered["id"]).state = "delivered"
        other = Source(title="Other", site_url="https://feed.example", input_url="https://feed.example/rss",
                       feed_url="https://feed.example/rss")
        session.add(other)
        session.flush()
        item = Item(source_id=other.id, identity_key="feed", link="https://feed.example/one",
                    title="Feed item", content_text="text", content_origin="feed", state="pending")
        session.add(item)
        session.commit()
        other_id = item.id
    assert client.delete(f"/api/captures/{delivered['id']}", headers=connected).status_code == 404
    assert client.delete(f"/api/captures/{other_id}", headers=connected).status_code == 404
    assert client.delete(f"/api/captures/{pending['id']}", headers=connected).status_code == 204
    assert client.get("/api/extension/status", headers=connected).json()["waiting"] == 0


def test_token_cannot_delete_source(client, connected):
    save_page(client, connected)
    source_id = client.get("/api/sources").json()[0]["id"]
    response = client.delete(f"/api/sources/{source_id}", headers=connected)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_site_request"
    assert [row["id"] for row in client.get("/api/sources").json()] == [source_id]


@pytest.mark.parametrize("method,path", [
    ("post", "/api/captures"),
    ("get", "/api/captures"),
    ("delete", "/api/captures/{id}"),
])
def test_capture_routes_require_token_without_browser_origin(client, connected, method, path):
    saved = save_page(client, connected).json()
    request = getattr(client, method)
    response = request(path.format(id=saved["id"]), **({
        "json": {"url": "https://example.com/another", "title": "Another", "text": "Text"},
    } if method == "post" else {}))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    with client.app.state.session_factory() as session:
        assert [(item.id, item.state) for item in session.scalars(select(Item)).all()] == [
            (saved["id"], "pending"),
        ]


def test_capture_source_waiting_count_and_delete_keeps_digest_snapshot(client, connected):
    first = save_page(client, connected).json()
    save_page(client, connected, url="https://example.com/two")
    sources = client.get("/api/sources").json()
    assert len(sources) == 1
    assert sources[0]["title"] == "Saved from browser"
    assert sources[0]["waiting_count"] == 2
    with client.app.state.session_factory() as session:
        run = DigestRun(status="succeeded")
        session.add(run)
        session.flush()
        digest = Digest(run_id=run.id, model_id="test", item_count=1, source_count=0)
        session.add(digest)
        session.flush()
        topic = DigestTopic(digest_id=digest.id, position=0, title="Saved", overview="Summary")
        session.add(topic)
        session.flush()
        item = DigestItem(digest_id=digest.id, topic_id=topic.id, position=0, item_id=first["id"],
                          title="A post", link="https://example.com/post", source_name="Example",
                          source_kind="capture", summary_unavailable=False)
        session.add(item)
        session.commit()
    assert client.delete(f"/api/sources/{sources[0]['id']}").status_code == 204
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Item)) == 0
        snapshot = session.scalar(select(DigestItem))
        assert (snapshot.title, snapshot.link, snapshot.source_name, snapshot.item_id) == (
            "A post", "https://example.com/post", "Example", None,
        )
