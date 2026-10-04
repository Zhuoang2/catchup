import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from catchup.main import create_app
from catchup.models import Digest, DigestItem, DigestRun, DigestTopic, Item, Source, SourceCheck
from catchup.net.safe_fetch import RATE_LIMIT_PREFIX

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
FEED_URL = "https://site.example/feed.xml"
FIXTURES = Path(__file__).parent / "fixtures"


def entries_xml(recent: int, old: int = 0, undated: int = 0) -> bytes:
    entries = []
    for i in range(recent + old + undated):
        date = NOW - timedelta(days=(i % 6) + 1 if i < recent else 20)
        date_tag = (
            f"<pubDate>{date.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>"
            if i < recent + old else ""
        )
        entries.append(
            f"<item><guid>item-{i}</guid><title>Entry {i}</title>"
            f"<link>https://site.example/articles/{i}</link>{date_tag}"
            f"<description>{'Feed text ' * 60}</description></item>",
        )
    return (
        "<rss version='2.0'><channel><title>Example News</title>"
        "<link>https://site.example/</link>" + "".join(entries) + "</channel></rss>"
    ).encode()


@pytest.fixture
def public_dns(monkeypatch):
    def lookup(host, port, *_args, **_kwargs):
        address = "8.8.8.8" if host == "site.example" else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    monkeypatch.setattr("catchup.api.sources.utc_now", lambda: NOW)


@pytest.fixture
def client(public_dns):
    with TestClient(create_app()) as test_client:
        yield test_client


def serve_feed(router, content: bytes):
    return router.get(FEED_URL).mock(return_value=httpx.Response(
        200, content=content, headers={"content-type": "application/rss+xml"},
    ))


def test_preview_does_not_write_and_limits_entries(client):
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(8))
        response = client.post("/api/sources/preview", json={"url": FEED_URL})
    assert response.status_code == 200
    assert response.json()["title"] == "Example News"
    assert response.json()["feed_url"] == FEED_URL
    assert response.json()["site_url"] == "https://site.example/"
    assert len(response.json()["entries"]) == 5
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Source)) == 0
        assert session.scalar(select(func.count()).select_from(Item)) == 0


@pytest.mark.parametrize("path", ["direct", "declared", "probed"])
def test_preview_confirm_uses_final_feed_url_once(client, path):
    target = "https://site.example/final.xml"
    with respx.mock(assert_all_mocked=True) as router:
        if path == "direct":
            start_url = FEED_URL
        else:
            start_url = "https://site.example/"
            page = (b"<html><link rel='alternate' type='application/rss+xml' href='/feed.xml'></html>"
                    if path == "declared" else b"<!doctype html><html></html>")
            router.get(start_url).mock(return_value=httpx.Response(
                200, content=page, headers={"content-type": "text/html"},
            ))
        if path == "probed":
            router.get("https://site.example/.rss").mock(return_value=httpx.Response(404))
            router.get("https://site.example/feed").mock(
                return_value=httpx.Response(302, headers={"location": "/final.xml"}),
            )
        else:
            router.get(FEED_URL).mock(return_value=httpx.Response(302, headers={"location": "/final.xml"}))
        final = router.get(target).mock(return_value=httpx.Response(
            200, content=entries_xml(1), headers={"content-type": "application/rss+xml"},
        ))
        preview = client.post("/api/sources/preview", json={"url": start_url})
        assert preview.status_code == 200
        assert preview.json()["feed_url"] == target
        confirmed = client.post("/api/sources", json={"feed_url": target})
        assert confirmed.status_code == 201
        assert final.call_count == 1


def test_expired_preview_refetches_feed(client):
    now = [0.0]
    client.app.state.feed_cache.clock = lambda: now[0]
    with respx.mock(assert_all_mocked=True) as router:
        route = serve_feed(router, entries_xml(1))
        assert client.post("/api/sources/preview", json={"url": FEED_URL}).status_code == 200
        now[0] = 601
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
        assert route.call_count == 2


def test_confirm_without_preview_fetches_feed(client):
    with respx.mock(assert_all_mocked=True) as router:
        route = serve_feed(router, entries_xml(1))
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
        assert route.call_count == 1
        assert route.calls[0].request.headers["user-agent"].startswith("CatchUp/")


def test_declared_html_article_notice(client):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/story").mock(return_value=httpx.Response(
            200, content=(FIXTURES / "article.html").read_bytes(), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/atom.xml").mock(return_value=httpx.Response(
            200, content=(FIXTURES / "atom.xml").read_bytes(), headers={"content-type": "application/atom+xml"},
        ))
        result = client.post("/api/sources/preview", json={"url": "https://site.example/story"})
    assert result.status_code == 200
    assert result.json()["follows_site_feed_notice"]
    assert result.json()["feed_url"] == "https://site.example/atom.xml"


@pytest.mark.parametrize("recent,old,undated,pending,baseline", [
    (2, 10, 1, 2, 11), (8, 0, 0, 5, 3),
])
def test_confirm_marks_first_add_baseline(client, recent, old, undated, pending, baseline):
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(recent, old, undated))
        result = client.post("/api/sources", json={"feed_url": FEED_URL})
    assert result.status_code == 201
    assert result.json()["last_check_status"] == "new_items"
    with client.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        states = session.scalars(select(Item.state).where(Item.source_id == source.id)).all()
        assert states.count("pending") == pending
        assert states.count("baseline") == baseline
        check = session.scalar(select(SourceCheck))
        assert check.run_id is None
        assert check.new_count == pending
        assert check.entries_seen == recent + old + undated


def test_configurable_first_add_limits(monkeypatch, public_dns):
    monkeypatch.setenv("CATCHUP_FIRST_ADD_DAYS", "2")
    monkeypatch.setenv("CATCHUP_FIRST_ADD_MAX", "1")
    with TestClient(create_app()) as client, respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(8))
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
        assert all(call.request.headers["user-agent"].startswith("CatchUp/") for call in router.calls)
        with client.app.state.session_factory() as session:
            assert session.scalars(select(Item.state)).all().count("pending") == 1


def test_confirm_preserves_entries_without_links(client):
    xml = b"""<rss version="2.0"><channel><title>No links</title>
    <item><title>One</title><pubDate>Fri, 02 Oct 2026 10:00:00 GMT</pubDate></item>
    <item><title>Two</title><pubDate>Thu, 01 Oct 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, xml)
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
    with client.app.state.session_factory() as session:
        assert session.scalars(select(Item.state)).all().count("pending") == 2


def test_confirm_enriches_short_pending_entry_but_not_baseline(client):
    xml = b"""<rss version="2.0"><channel><title>News</title>
    <item><guid>recent</guid><link>https://site.example/recent</link>
    <title>Recent</title><pubDate>Fri, 02 Oct 2026 10:00:00 GMT</pubDate>
    <description>Short</description></item>
    <item><guid>old</guid><link>https://site.example/old</link>
    <title>Old</title><pubDate>Thu, 01 Jan 2026 10:00:00 GMT</pubDate>
    <description>Short</description></item></channel></rss>"""
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, xml)
        article = router.get("https://site.example/recent").mock(return_value=httpx.Response(
            200, content=b"<html><body><article><h1>Recent</h1>"
                         b"<p>Full article text for the newly pending entry.</p>"
                         b"</article></body></html>",
        ))
        assert client.post("/api/sources", json={"feed_url": FEED_URL}).status_code == 201
        assert all(call.request.headers["user-agent"].startswith("CatchUp/") for call in router.calls)
    assert article.call_count == 1
    with client.app.state.session_factory() as session:
        recent = session.scalar(select(Item).where(Item.identity_key == "recent"))
        old = session.scalar(select(Item).where(Item.identity_key == "old"))
        assert recent.state == "pending"
        assert recent.content_origin == "article"
        assert "Full article text" in recent.content_text
        assert old.state == "baseline"
        assert old.content_text == "Short"


def test_duplicate_preview_and_confirm_name_existing_source(client):
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(2))
        created = client.post("/api/sources", json={"feed_url": FEED_URL}).json()
        preview = client.post("/api/sources/preview", json={"url": FEED_URL})
        confirm = client.post("/api/sources", json={"feed_url": FEED_URL})
    for response, status in ((preview, 422), (confirm, 409)):
        assert response.status_code == status
        assert response.json()["error"]["code"] == "duplicate"
        assert response.json()["error"]["existing_source"]["title"] == "Example News"
        assert response.json()["error"]["existing_source"]["id"] == created["id"]


@pytest.mark.parametrize("url,code", [
    ("not-a-url", "invalid_url"), ("http://127.0.0.1/feed", "blocked_address"),
])
def test_invalid_and_blocked_urls(client, url, code):
    response = client.post("/api/sources/preview", json={"url": url})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_no_feed_and_not_a_feed(client):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=(FIXTURES / "no-feed.html").read_bytes(), headers={"content-type": "text/html"},
        ))
        serve_feed(router, b"not rss")
        router.get(url__regex=r"https://site\.example/.*").mock(return_value=httpx.Response(404))
        no_feed = client.post("/api/sources/preview", json={"url": "https://site.example/"})
        not_feed = client.post("/api/sources/preview", json={"url": FEED_URL})
    assert no_feed.json()["error"]["code"] == "no_feed"
    assert not_feed.json()["error"]["code"] == "not_a_feed"


def test_fetch_failure(client):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(side_effect=httpx.ReadTimeout("test timeout"))
        response = client.post("/api/sources/preview", json={"url": FEED_URL})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "fetch_failed"


@pytest.mark.parametrize("endpoint", ["/api/sources/preview", "/api/sources"])
def test_rate_limited_preview_or_confirm_has_retry_after(client, endpoint):
    payload = {"url": FEED_URL} if endpoint.endswith("preview") else {"feed_url": FEED_URL}
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(FEED_URL).mock(return_value=httpx.Response(
            429, headers={"Retry-After": "120"},
        ))
        response = client.post(endpoint, json=payload)
    assert route.call_count == 1
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "rate_limited",
        "message": f"{RATE_LIMIT_PREFIX} Try again in about 120 seconds.",
        "retry_after": 120,
    }


@pytest.mark.parametrize("path", ["declared", "probed"])
def test_preview_surfaces_rate_limit_on_discovered_feed(client, path):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=(b"<html><link rel='alternate' type='application/rss+xml' href='/feed.xml'></html>"
                          if path == "declared" else b"<!doctype html><html></html>"),
            headers={"content-type": "text/html"},
        ))
        if path == "probed":
            router.get("https://site.example/.rss").mock(return_value=httpx.Response(404))
            target = "https://site.example/feed"
        else:
            target = FEED_URL
        route = router.get(target).mock(return_value=httpx.Response(429))
        response = client.post("/api/sources/preview", json={"url": "https://site.example/"})
    assert route.call_count == 1
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "rate_limited"
    assert response.json()["error"]["retry_after"] is None


def test_list_status_and_delete_keeps_digest_snapshot(client):
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(1))
        source_id = client.post("/api/sources", json={"feed_url": FEED_URL}).json()["id"]
    with client.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        run = DigestRun(status="succeeded", items_total=1, items_done=1, started_at=NOW)
        session.add(run)
        session.flush()
        digest = Digest(run_id=run.id, model_id="mock-model", item_count=1, source_count=1, created_at=NOW)
        session.add(digest)
        session.flush()
        topic = DigestTopic(digest_id=digest.id, position=0, title="News", overview="Overview")
        session.add(topic)
        session.flush()
        session.add(DigestItem(
            digest_id=digest.id, topic_id=topic.id, item_id=item.id, position=0,
            title=item.title, link=item.link, source_name="Example News", summary="Saved",
            summary_unavailable=False,
        ))
        session.add(SourceCheck(
            source_id=source_id, status="failed", possible_gap=True, error="bad feed",
            entries_seen=0, new_count=0, checked_at=NOW + timedelta(minutes=1),
        ))
        session.commit()
    listed = client.get("/api/sources").json()
    assert len(listed) == 1
    assert listed[0]["last_check_status"] == "failed"
    assert listed[0]["possible_gap"] is True
    assert client.delete(f"/api/sources/{source_id}").status_code == 204
    assert client.get("/api/sources").json() == []
    with client.app.state.session_factory() as session:
        saved = session.scalar(select(DigestItem))
        assert saved.item_id is None
        assert saved.source_name == "Example News"
        assert saved.summary == "Saved"
        assert saved.link.endswith("/0")
        assert session.scalar(select(func.count()).select_from(Digest)) == 1


@pytest.mark.parametrize("status,error,expected", [
    (429, "The source is rate limiting requests. Try again later.", True),
    (503, f"{RATE_LIMIT_PREFIX} Try again in about 120 seconds.", True),
    (503, "The source could not be fetched.", False),
])
def test_source_list_exposes_check_rate_limit(client, status, error, expected):
    with respx.mock(assert_all_mocked=True) as router:
        serve_feed(router, entries_xml(1))
        source_id = client.post("/api/sources", json={"feed_url": FEED_URL}).json()["id"]
    with client.app.state.session_factory() as session:
        session.add(SourceCheck(source_id=source_id, status="failed", http_status=status,
                                error=error, entries_seen=0, new_count=0,
                                checked_at=NOW + timedelta(minutes=1)))
        session.commit()
    source = client.get("/api/sources").json()[0]
    assert source["last_check_status"] == "failed"
    assert source["http_status"] == status
    assert source["rate_limited"] is expected
