import socket
from datetime import datetime, timedelta, timezone
from html import escape

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.collection import check_source
from catchup.main import create_app
from catchup.models import DigestRun, Item, Source, SourceCheck

FEED_URL = "https://site.example/feed.xml"
ARTICLE_URL = "https://site.example/story"
NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
LONG_TEXT = "Feed text " * 60


def feed_bytes(*entries: dict) -> bytes:
    items = []
    for entry in entries:
        fields = "".join(
            f"<{tag}>{escape(str(entry[value]))}</{tag}>"
            for tag, value in (("guid", "id"), ("link", "link"), ("pubDate", "date"))
            if entry.get(value)
        )
        items.append(
            f"<item>{fields}<title>{escape(entry['title'])}</title>"
            f"<description>{escape(entry.get('text', LONG_TEXT))}</description></item>"
        )
    return (
        "<rss version='2.0'><channel><title>News</title><link>https://site.example/</link>"
        + "".join(items) + "</channel></rss>"
    ).encode()


def item(identity: str, *, link: str = ARTICLE_URL, date: datetime | None = None,
         text: str = LONG_TEXT) -> dict:
    return {
        "id": identity, "link": link, "title": identity, "text": text,
        "date": date.strftime("%a, %d %b %Y %H:%M:%S GMT") if date else None,
    }


@pytest.fixture
def app(monkeypatch):
    def lookup(_host, port, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with TestClient(create_app()) as client:
        yield client.app


@pytest.fixture
def session(app):
    with app.state.session_factory() as db:
        source = Source(
            title="News", site_url="https://site.example/", feed_url=FEED_URL, input_url=FEED_URL,
        )
        db.add(source)
        db.commit()
        yield db


def run_check(session, settings, source=None):
    run = DigestRun(status="collecting", started_at=NOW)
    session.add(run)
    session.commit()
    source = source or session.scalar(select(Source))
    result = check_source(session, source, run.id, settings)
    assert result.run_id == run.id
    assert session.scalars(select(SourceCheck).where(SourceCheck.run_id == run.id)).one().id == result.id
    assert source.last_check_status == result.status
    assert source.last_check_at == result.checked_at
    return result


def serve(router, *entries):
    router.get(FEED_URL).mock(return_value=httpx.Response(
        200, content=feed_bytes(*entries), headers={"content-type": "application/rss+xml"},
    ))


def test_repeated_entries_are_not_reinserted_or_changed(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one"), item("two", link="https://site.example/two"))
        first = run_check(session, app.state.settings)
        saved = session.scalars(select(Item).order_by(Item.id)).all()
        saved[0].state = "delivered"
        session.commit()
        second = run_check(session, app.state.settings)
    assert (first.status, first.new_count, first.entries_seen, first.http_status) == (
        "new_items", 2, 2, 200,
    )
    assert (second.status, second.new_count, second.entries_seen, second.http_status) == (
        "no_new_items", 0, 2, 200,
    )
    assert not first.possible_gap and not second.possible_gap
    assert session.scalars(select(Item)).all() == saved
    assert saved[0].state == "delivered"


def test_late_entry_is_new_despite_older_publish_date(session, app):
    old_date = NOW - timedelta(days=90)
    source = session.scalar(select(Source))
    source.last_check_at = NOW
    session.add(Item(
        source_id=source.id, identity_key="known", link="https://site.example/known",
        title="Known", content_text=LONG_TEXT, content_origin="feed", state="delivered",
    ))
    session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("known", link="https://site.example/known"), item("late", date=old_date))
        check = run_check(session, app.state.settings, source)
    assert check.status == "new_items"
    assert check.new_count == 1
    assert not check.possible_gap
    late = session.scalar(select(Item).where(Item.identity_key == "late"))
    assert late.published_at.replace(tzinfo=timezone.utc) == old_date
    assert late.state == "pending"


def test_changed_identifier_same_link_is_not_new(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("original"))
        run_check(session, app.state.settings)
        serve(router, item("changed"))
        check = run_check(session, app.state.settings)
    assert check.status == "no_new_items"
    assert check.new_count == 0
    assert not check.possible_gap
    assert len(session.scalars(select(Item)).all()) == 1


def test_failed_check_then_success_recovers_both_items(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(503))
        failed = run_check(session, app.state.settings)
        serve(router, item("one"), item("two", link="https://site.example/two"))
        recovered = run_check(session, app.state.settings)
    assert failed.status == "failed"
    assert failed.http_status == 503
    assert failed.error == "The source could not be fetched."
    assert failed.entries_seen == failed.new_count == 0
    assert not failed.possible_gap
    assert (recovered.status, recovered.new_count, recovered.http_status) == ("new_items", 2, 200)
    assert not recovered.possible_gap
    assert {entry.identity_key for entry in session.scalars(select(Item))} == {"one", "two"}


def test_rate_limited_check_preserves_suggested_wait(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(FEED_URL).mock(return_value=httpx.Response(
            429, headers={"Retry-After": "120"},
        ))
        check = run_check(session, app.state.settings)
    assert route.call_count == 1
    assert check.status == "failed"
    assert check.http_status == 429
    assert "about 120 seconds" in check.error


def test_failed_source_does_not_prevent_checking_another_source(session, app):
    other_url = "https://site.example/other.xml"
    other = Source(
        title="Other", site_url="https://site.example/", feed_url=other_url, input_url=other_url,
    )
    session.add(other)
    session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(return_value=httpx.Response(503))
        router.get(other_url).mock(return_value=httpx.Response(
            200, content=feed_bytes(item("other")), headers={"content-type": "application/rss+xml"},
        ))
        failed = run_check(session, app.state.settings)
        succeeded = run_check(session, app.state.settings, other)
    assert failed.status == "failed"
    assert succeeded.status == "new_items"
    assert session.scalar(select(Item).where(Item.source_id == other.id)).identity_key == "other"


def test_possible_gap_only_with_prior_items_and_no_match(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one"))
        initial = run_check(session, app.state.settings)
        serve(router, item("two", link="https://site.example/two"))
        gap = run_check(session, app.state.settings)
        serve(router, item("two", link="https://site.example/two"), item("three",
              link="https://site.example/three"))
        overlap = run_check(session, app.state.settings)
    assert not initial.possible_gap
    assert gap.status == "new_items" and gap.possible_gap
    assert overlap.status == "new_items" and not overlap.possible_gap


def test_linkless_entries_use_distinct_keys_not_feed_url_for_dedup(session, app):
    first = {"title": "First", "text": LONG_TEXT}
    second = {"title": "Second", "text": LONG_TEXT}
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, first)
        run_check(session, app.state.settings)
        serve(router, first, second)
        check = run_check(session, app.state.settings)
    assert check.status == "new_items" and check.new_count == 1
    assert not check.possible_gap
    assert len(session.scalars(select(Item)).all()) == 2


def test_linkless_new_entry_can_signal_gap(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, {"title": "First", "text": LONG_TEXT})
        run_check(session, app.state.settings)
        serve(router, {"title": "Second", "text": LONG_TEXT})
        check = run_check(session, app.state.settings)
    assert check.status == "new_items" and check.possible_gap


def test_empty_feed_after_recorded_entries_is_success_with_possible_gap(session, app):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one"))
        run_check(session, app.state.settings)
        serve(router)
        check = run_check(session, app.state.settings)
    assert check.status == "no_new_items"
    assert check.possible_gap
    assert check.error is None
    assert (check.entries_seen, check.new_count, check.http_status) == (0, 0, 200)


@pytest.mark.parametrize("failure,expected_status", [
    (httpx.ReadTimeout("offline"), None),
    (httpx.Response(404), 404),
    (httpx.Response(200, content=b"not a feed"), 200),
])
def test_fetch_or_parse_failure_never_reports_no_new_items(session, app, failure, expected_status):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(FEED_URL).mock(
            side_effect=failure if isinstance(failure, Exception) else None,
            return_value=failure if isinstance(failure, httpx.Response) else None,
        )
        check = run_check(session, app.state.settings)
    assert check.status == "failed"
    assert check.error
    assert check.http_status == expected_status
    assert check.new_count == 0
    assert not check.possible_gap
    assert session.scalars(select(Item)).all() == []


def test_short_feed_excerpt_is_replaced_with_extracted_article(session, app):
    article = b"""<html><head><title>A story</title></head><body><article>
    <h1>A story</h1><p>This is the complete article content with enough context
    to replace the small feed excerpt for the digest.</p></article></body></html>"""
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one", text="Short excerpt"))
        article_route = router.get(ARTICLE_URL).mock(return_value=httpx.Response(
            200, content=article, headers={"content-type": "text/html"},
        ))
        check = run_check(session, app.state.settings)
        assert all(call.request.headers["user-agent"].startswith("CatchUp/") for call in router.calls)
    saved = session.scalar(select(Item))
    assert check.status == "new_items" and article_route.call_count == 1
    assert saved.content_origin == "article"
    assert "complete article content" in saved.content_text


@pytest.mark.parametrize("article_response", [
    httpx.Response(503),
    httpx.Response(200, content=b"<html><body></body></html>"),
])
def test_article_failure_or_empty_extraction_falls_back_to_feed(session, app, article_response):
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one", text="Short excerpt"))
        router.get(ARTICLE_URL).mock(return_value=article_response)
        run_check(session, app.state.settings)
    saved = session.scalar(select(Item))
    assert saved.content_origin == "feed"
    assert saved.content_text == "Short excerpt"


def test_article_blocked_by_safe_fetch_falls_back_to_feed(session, app, monkeypatch):
    def lookup(host, port, *_args, **_kwargs):
        address = "127.0.0.1" if host == "private.example" else "8.8.8.8"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one", link="https://private.example/story", text="Short excerpt"))
        run_check(session, app.state.settings)
    saved = session.scalar(select(Item))
    assert saved.content_text == "Short excerpt" and saved.content_origin == "feed"


def test_extractor_exception_falls_back_to_feed(session, app, monkeypatch):
    def broken_extractor(*_args, **_kwargs):
        raise ValueError("extractor failed")

    monkeypatch.setattr("catchup.collection.extract", broken_extractor)
    with respx.mock(assert_all_mocked=True) as router:
        serve(router, item("one", text="Short excerpt"))
        router.get(ARTICLE_URL).mock(return_value=httpx.Response(200, content=b"<article>text</article>"))
        check = run_check(session, app.state.settings)
    saved = session.scalar(select(Item))
    assert check.status == "new_items"
    assert saved.content_text == "Short excerpt" and saved.content_origin == "feed"
