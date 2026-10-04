import hashlib
import re
import socket
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from catchup.net.safe_fetch import FetchError, FetchResponse
from catchup.sources.discovery import discover
from catchup.sources.feeds import FeedParseError, parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def public_dns(monkeypatch):
    def lookup(host, port, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


@pytest.mark.parametrize("name,expected", [
    ("rss.xml", "rss20"), ("atom.xml", "atom10"), ("malformed.xml", "rss20"),
    ("no-ids.xml", "rss20"), ("no-dates.xml", "rss20"),
])
def test_parses_all_feed_fixtures(name, expected):
    import feedparser
    raw = fixture(name)
    assert feedparser.parse(raw).version == expected
    feed = parse_feed(FetchResponse("https://site.example/feed", raw, "application/rss+xml", 200))
    assert feed.entries


def test_normalizes_identity_date_and_text():
    feed = parse_feed(FetchResponse("https://site.example/feed", fixture("rss.xml"), "application/rss+xml", 200))
    first = feed.entries[0]
    assert feed.title == "Example News"
    assert first.identity_key == "entry-a"
    assert first.title == "First & Best"
    assert first.published_at == datetime(2026, 10, 2, 10, tzinfo=timezone.utc)
    assert first.content_text == "News summary ."

    no_ids = parse_feed(FetchResponse("https://site.example/feed", fixture("no-ids.xml"), "", 200))
    assert no_ids.entries[0].identity_key == "https://site.example/linked"
    date = datetime(2026, 10, 2, 11, tzinfo=timezone.utc)
    assert no_ids.entries[1].identity_key == hashlib.sha256(f"Hash fallback{date.isoformat()}".encode()).hexdigest()
    undated = parse_feed(FetchResponse("https://site.example/feed", fixture("no-dates.xml"), "", 200))
    assert undated.entries[0].published_at is None
    atom = parse_feed(FetchResponse("https://site.example/atom", fixture("atom.xml"), "", 200))
    assert atom.entries[0].content_text == "Atom text"


def test_untitled_social_post_uses_plain_text_at_word_boundary():
    feed = parse_feed(FetchResponse("https://site.example/feed", fixture("bluesky-untitled.xml"),
                                    "application/rss+xml", 200))
    entry = feed.entries[0]
    assert entry.content_text == (
        "Happy opening day, hockey fans! Follow all 1,344 games and enjoy every moment of the season."
    )
    assert entry.title == "Happy opening day, hockey fans! Follow all 1,344 games and enjoy every moment of…"
    assert entry.identity_key == "at://did:plc:example/app.bsky.feed.post/1"
    assert entry.link == "https://bsky.app/profile/example.bsky.social/post/1"


def test_untitled_long_cjk_text_cuts_at_80_characters():
    text = "今天天气真好" * 20
    raw = (f"<rss version='2.0'><channel><title>Posts</title>"
           f"<item><link>https://site.example/post</link><description>{text}</description></item>"
           f"</channel></rss>").encode()
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.title == text[:80] + "…"
    assert entry.identity_key == "https://site.example/post"


def test_no_title_or_text_is_untitled_and_titled_hash_stays_stable():
    raw = (b"<rss version='2.0'><channel><title>Posts</title>"
           b"<item><guid>empty-post</guid></item>"
           b"<item><title>Existing title</title><description>Different text</description></item>"
           b"</channel></rss>")
    entries = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries
    assert entries[0].title == "Untitled"
    assert entries[0].identity_key == "empty-post"
    assert entries[1].title == "Existing title"
    assert entries[1].identity_key == hashlib.sha256(b"Existing title").hexdigest()


def test_rejects_unparseable_bytes():
    with pytest.raises(FeedParseError):
        parse_feed(FetchResponse("https://site.example/feed", b"not a feed", "", 200))


@pytest.mark.parametrize("unsafe_link", ["javascript:alert(1)", "data:text/html,unsafe", "file:///etc/passwd"])
def test_unsafe_entry_links_fall_back_to_feed_url(unsafe_link):
    raw = (f"<rss version='2.0'><channel><title>Links</title>"
           f"<item><title>Unsafe</title><link>{unsafe_link}</link></item>"
           f"<item><title>Safe</title><link>https://site.example/article</link></item>"
           f"</channel></rss>").encode()
    feed = parse_feed(FetchResponse("https://site.example/feed", raw, "application/rss+xml", 200))
    assert feed.entries[0].link == feed.feed_url
    assert feed.entries[0].identity_key != unsafe_link
    assert feed.entries[1].link == "https://site.example/article"


def test_direct_feed_and_declared_html(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=fixture("declared.html"), headers={"content-type": "text/html"},
        ))
        direct = discover("https://site.example/feed.xml")
        declared = discover("https://site.example/")
    assert direct.feed.feed_url == declared.feed.feed_url == "https://site.example/feed.xml"
    assert not direct.follows_site_feed_notice
    assert not declared.follows_site_feed_notice


def test_article_page_follows_whole_site(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/story").mock(return_value=httpx.Response(
            200, content=fixture("article.html"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/atom.xml").mock(return_value=httpx.Response(
            200, content=fixture("atom.xml"), headers={"content-type": "application/atom+xml"},
        ))
        found = discover("https://site.example/story")
    assert found.follows_site_feed_notice
    assert found.feed.feed_url == "https://site.example/atom.xml"


def test_profile_with_declared_feed_does_not_show_site_notice(public_dns):
    html = (b"<!doctype html><html><head><meta property='og:type' content='profile'>"
            b"<link rel='alternate' type='application/rss+xml' href='/@user.rss'>"
            b"</head></html>")
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/@user").mock(return_value=httpx.Response(
            200, content=html, headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/@user.rss").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        found = discover("https://site.example/@user")
    assert found.feed.feed_url == "https://site.example/@user.rss"
    assert not found.follows_site_feed_notice


def test_reddit_path_dot_rss_probe(public_dns):
    url = "https://site.example/r/catchup/"
    with respx.mock(assert_all_mocked=True) as router:
        router.get(url).mock(return_value=httpx.Response(
            200, content=fixture("no-feed.html"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/r/catchup.rss").mock(return_value=httpx.Response(404))
        router.get("https://site.example/r/catchup/.rss").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        found = discover(url)
        assert len(router.calls) == 3
    assert found.feed.feed_url.endswith("/r/catchup/.rss")


def test_origin_feed_probe_notices_site_scope(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/stories").mock(return_value=httpx.Response(
            200, content=fixture("no-feed.html"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(
            return_value=httpx.Response(404),
        )
        found = discover("https://site.example/stories")
    assert found.feed.feed_url == "https://site.example/feed"
    assert found.follows_site_feed_notice


def test_no_candidate_succeeds_and_probing_is_bounded(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/deep/path").mock(return_value=httpx.Response(
            200, content=fixture("no-feed.html"), headers={"content-type": "text/html"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/deep/path")
        called = [str(call.request.url) for call in router.calls]
    assert error.value.code == "no_feed"
    assert len(called) - 1 == 8
    assert all(url.startswith("https://site.example/") for url in called)


def test_probe_redirect_cannot_leave_origin_or_exceed_budget(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/deep/path").mock(return_value=httpx.Response(
            200, content=fixture("no-feed.html"), headers={"content-type": "text/html"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(
            302, headers={"location": "https://other.example/private"},
        ))
        with pytest.raises(FetchError, match="No supported feed"):
            discover("https://site.example/deep/path")
        called = [str(call.request.url) for call in router.calls]
    assert len(called) - 1 <= 8
    assert all(url.startswith("https://site.example/") for url in called)
