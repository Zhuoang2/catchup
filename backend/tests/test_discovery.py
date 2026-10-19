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
from catchup.sources.feeds import FeedParseError, _entry_title, parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def public_dns(monkeypatch):
    def lookup(host, port, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


@pytest.fixture
def blocked_candidate_dns(public_dns, monkeypatch):
    def lookup(host, port, *_args, **_kwargs):
        address = "10.0.0.1" if host == "internal.example" else "8.8.8.8"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


def declared_html(*urls: str) -> bytes:
    links = "".join(
        f"<link rel='alternate' type='application/rss+xml' href='{url}'>" for url in urls
    )
    return f"<html><head>{links}</head></html>".encode()


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


@pytest.mark.parametrize("prefix,expected", [
    ("A" * 77 + "...", "A" * 77 + "…"),
    ("A" * 79 + "…", "A" * 79 + "…"),
])
def test_untitled_cut_text_ending_in_ellipsis_gets_only_one(prefix, expected):
    assert _entry_title("", prefix + " more text") == expected


@pytest.mark.parametrize("dots", ["。。。", "．．．", "⋯⋯"])
def test_untitled_cut_cjk_dots_gets_only_one_ellipsis(dots):
    prefix = "今" * (80 - len(dots)) + dots
    assert _entry_title("", prefix + "后续") == "今" * (80 - len(dots)) + "…"


def test_untitled_cut_keeps_part_of_long_word_if_word_boundary_is_only_dots():
    assert _entry_title("", "... " + "A" * 100) == "... " + "A" * 76 + "…"


def test_untitled_cut_preserves_word_boundary_before_long_word():
    assert _entry_title("", "word " * 15 + "supercalifragilistic tail") == "word " * 14 + "word…"


def test_untitled_cut_of_all_dots_is_a_single_ellipsis():
    assert _entry_title("", "." * 100) == "…"


def test_untitled_cut_of_cjk_full_stops_is_a_single_ellipsis():
    assert _entry_title("", "。" * 100) == "…"


def test_untitled_cut_of_dots_and_spaces_is_a_single_ellipsis():
    assert _entry_title("", ". " * 50) == "…"


def test_untitled_cut_with_space_before_dots_has_one_ellipsis():
    assert _entry_title("", "B" * 75 + " ... more text follows here") == "B" * 75 + "…"


def test_untitled_cut_just_over_80_characters_strips_dots_after_cut():
    assert _entry_title("", "A" * 78 + "..." + " more") == "A" * 78 + "…"


def test_untitled_cut_at_81_characters_strips_dots_after_cut():
    assert _entry_title("", "A" * 78 + "...") == "A" * 78 + "…"


def test_untitled_short_text_ending_in_dots_is_unchanged():
    text = "A" * 70 + "..."
    assert _entry_title("", text) == text


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
        assert all(call.request.headers["user-agent"].startswith("CatchUp/") for call in router.calls)
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
        assert all(call.request.headers["user-agent"].startswith("CatchUp/") for call in router.calls)
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


def test_refused_home_page_finds_feed(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(403))
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        found = discover("https://site.example/")
    assert found.feed.feed_url == "https://site.example/feed"
    assert not found.follows_site_feed_notice


def test_refused_deeper_page_notices_site_scope(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/blog/post").mock(return_value=httpx.Response(403))
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        found = discover("https://site.example/blog/post")
    assert found.feed.feed_url == "https://site.example/feed"
    assert found.follows_site_feed_notice


def test_refused_page_without_feed_keeps_original_http_error(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(403))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        called = [str(call.request.url) for call in router.calls]
    assert error.value.code == "fetch_failed"
    assert error.value.status_code == 403
    assert len(called) - 1 == 7
    assert all(url.startswith("https://site.example/") for url in called)


def test_server_error_without_retry_after_still_probes(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(503))
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        found = discover("https://site.example/")
    assert found.feed.feed_url == "https://site.example/feed"


def test_rate_limited_page_does_not_probe(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            429, headers={"retry-after": "120"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        assert len(router.calls) == 1
    assert error.value.code == "rate_limited"
    assert error.value.retry_after == 120


def test_timed_out_page_does_not_probe(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        assert len(router.calls) == 1
    assert error.value.code == "fetch_failed"
    assert error.value.status_code is None


def test_declared_feed_http_error_is_unavailable(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=fixture("declared.html"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(404))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 404


def test_declared_feed_timeout_is_unavailable_without_http_status(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=fixture("declared.html"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code is None


def test_declared_feed_over_size_limit_is_unavailable_without_http_status(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/feed.xml"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(
            200, content=b"x" * 128, headers={"content-type": "application/rss+xml"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/", max_feed_bytes=100)
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code is None


def test_declared_feed_redirect_without_location_is_unavailable_without_status(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/feed.xml"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(302))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code is None


def test_declared_feed_at_blocked_address_is_rejected(blocked_candidate_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("https://internal.example/feed.xml"),
            headers={"content-type": "text/html"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        assert len(router.calls) == 1
    assert error.value.code == "blocked_address"
    assert error.value.status_code is None


@pytest.mark.parametrize("first,second,code,status", [
    ("http_404", "timeout", "feed_unavailable", 404),
    ("timeout", "invalid", "not_a_feed", None),
    ("blocked", "timeout", "blocked_address", None),
    ("blocked", "http_404", "feed_unavailable", 404),
])
def test_declared_feed_failure_precedence(blocked_candidate_dns, first, second, code, status):
    outcomes = (first, second)
    urls = [
        "https://internal.example/one.xml" if first == "blocked" else "https://site.example/one.xml",
        "https://internal.example/two.xml" if second == "blocked" else "https://site.example/two.xml",
    ]
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html(*urls), headers={"content-type": "text/html"},
        ))
        for url, outcome in zip(urls, outcomes):
            if outcome == "http_404":
                router.get(url).mock(return_value=httpx.Response(404))
            elif outcome == "timeout":
                router.get(url).mock(side_effect=httpx.ConnectTimeout("timed out"))
            elif outcome == "invalid":
                router.get(url).mock(return_value=httpx.Response(200, content=b"not a feed"))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == code
    assert error.value.status_code == status


def test_last_declared_http_status_wins(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/first.xml", "/second.xml"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/first.xml").mock(return_value=httpx.Response(404))
        router.get("https://site.example/second.xml").mock(return_value=httpx.Response(410))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 410


def test_page_http_400_still_probes(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(400))
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        found = discover("https://site.example/")
    assert found.feed.feed_url == "https://site.example/feed"


def test_page_oversize_200_does_not_probe(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=b"x" * 128, headers={"content-type": "text/html"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/", max_feed_bytes=64)
        assert len(router.calls) == 1
    assert error.value.code == "fetch_failed"
    assert error.value.status_code == 200


def test_page_redirect_without_location_does_not_probe(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(302))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        assert len(router.calls) == 1
    assert error.value.code == "fetch_failed"
    assert error.value.status_code == 302


@pytest.mark.parametrize("feed_result,status", [
    (httpx.Response(404), 404),
    (httpx.ConnectTimeout("timed out"), None),
])
def test_apple_lookup_feed_failure_does_not_probe_another_feed(public_dns, feed_result, status):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "https://host.example/show.xml"}]},
        ))
        if isinstance(feed_result, httpx.Response):
            router.get("https://host.example/show.xml").mock(return_value=feed_result)
        else:
            router.get("https://host.example/show.xml").mock(side_effect=feed_result)
        router.get("https://host.example/feed").mock(return_value=httpx.Response(
            200, content=fixture("rss.xml"), headers={"content-type": "application/rss+xml"},
        ))
        router.get(re.compile(r"https://host\.example/.*")).mock(return_value=httpx.Response(404))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
        assert all(str(call.request.url) != "https://host.example/feed" for call in router.calls)
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == status


def test_apple_rate_limited_feed_keeps_retry_after(public_dns):
    """Mutation: remove rate_limited from the Apple pass-through tuple."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "https://host.example/show.xml"}]},
        ))
        router.get("https://host.example/show.xml").mock(return_value=httpx.Response(
            429, headers={"Retry-After": "120"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
    assert error.value.code == "rate_limited"
    assert error.value.retry_after == 120


def test_apple_blocked_feed_keeps_blocked_address(blocked_candidate_dns):
    """Mutation: remove blocked_address from the Apple pass-through tuple."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "https://internal.example/show.xml"}]},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
        assert len(router.calls) == 1
    assert error.value.code == "blocked_address"


def test_apple_feed_http_400_is_unavailable_with_status(public_dns):
    """Mutation: change the Apple HTTP status bound to > 400."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "https://host.example/show.xml"}]},
        ))
        router.get("https://host.example/show.xml").mock(return_value=httpx.Response(400))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 400


def test_apple_feed_redirect_without_location_has_no_http_status(public_dns):
    """Mutation: drop the Apple status bound so 302 is kept."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "https://host.example/show.xml"}]},
        ))
        router.get("https://host.example/show.xml").mock(return_value=httpx.Response(302))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code is None


def test_apple_invalid_feed_scheme_is_unavailable(public_dns):
    """Mutation: add invalid_url to the Apple pass-through tuple."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://itunes.apple.com/lookup?id=12345&entity=podcast").mock(return_value=httpx.Response(
            200, json={"resultCount": 1, "results": [{"feedUrl": "ftp://host.example/show.xml"}]},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://podcasts.apple.com/us/podcast/example/id12345")
        assert len(router.calls) == 1
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code is None


def test_declared_feed_http_400_is_unavailable(public_dns):
    """Mutation: change the declared-candidate HTTP status guard to > 400."""
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/feed.xml"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(400))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 400


@pytest.mark.parametrize("first", ["blocked", "unparseable"])
def test_unparseable_declared_feed_precedes_blocked_in_both_orders(blocked_candidate_dns, first):
    """Mutation: guard unparseable with `and blocked_error is None`."""
    urls = {
        "blocked": "https://internal.example/feed.xml",
        "unparseable": "https://site.example/invalid.xml",
    }
    second = "unparseable" if first == "blocked" else "blocked"
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html(urls[first], urls[second]), headers={"content-type": "text/html"},
        ))
        router.get(urls["unparseable"]).mock(return_value=httpx.Response(200, content=b"not a feed"))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "not_a_feed"


def test_unparseable_declared_feed_takes_precedence_over_http_error(public_dns):
    html = (b"<html><head>"
            b"<link rel='alternate' type='application/rss+xml' href='/missing.xml'>"
            b"<link rel='alternate' type='application/rss+xml' href='/invalid.xml'>"
            b"</head></html>")
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=html, headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/missing.xml").mock(return_value=httpx.Response(404))
        router.get("https://site.example/invalid.xml").mock(return_value=httpx.Response(
            200, content=b"not a feed", headers={"content-type": "text/plain"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "not_a_feed"


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
