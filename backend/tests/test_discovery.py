import hashlib
import html
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


def test_atom_keeps_body_links_in_order_with_resolved_urls_and_unique_targets():
    html = ("<p>Release <a href='https://github.com/example/tool/releases/tag/v1'>GitHub release</a>"
            " and <a href='/project'>Project page</a>,"
            " <a href='https://docs.example/changelog'>Changelog</a>."
            " <a href='/tags/python'>Python</a> <a href='/tags/tools'>Tools</a>"
            " <a href='/project'>Duplicate project</a></p>")
    import html as html_module
    raw = (f"<feed xmlns='http://www.w3.org/2005/Atom'><title>Tools</title>"
           f"<entry><id>one</id><title>Update</title>"
           f"<link href='https://site.example/post'/>"
           f"<content type='html'>{html_module.escape(html)}</content></entry></feed>").encode()
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert [(link.url, link.text) for link in entry.links] == [
        ("https://github.com/example/tool/releases/tag/v1", "GitHub release"),
        ("https://site.example/project", "Project page"),
        ("https://docs.example/changelog", "Changelog"),
        ("https://site.example/tags/python", "Python"),
        ("https://site.example/tags/tools", "Tools"),
    ]


def test_rss_keeps_comment_pointers_count_and_creator():
    raw = (b"<rss version='2.0' xmlns:wfw='http://wellformedweb.org/CommentAPI/' "
           b"xmlns:slash='http://purl.org/rss/1.0/modules/slash/' "
           b"xmlns:dc='http://purl.org/dc/elements/1.1/'><channel><title>Notes</title>"
           b"<item><title>Post</title><link>https://site.example/post</link>"
           b"<comments>https://site.example/post#comments</comments>"
           b"<wfw:commentRss>https://site.example/post/comments/feed</wfw:commentRss>"
           b"<slash:comments>12</slash:comments><dc:creator>Writer</dc:creator>"
           b"</item></channel></rss>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert (entry.comments_url, entry.comment_feed_url, entry.comment_count, entry.author) == (
        "https://site.example/post#comments", "https://site.example/post/comments/feed", 12, "Writer",
    )


def test_entry_without_links_or_comments_has_empty_defaults():
    raw = (b"<rss version='2.0'><channel><title>Notes</title>"
           b"<item><title>Post</title><link>https://site.example/post</link></item>"
           b"</channel></rss>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.links == ()
    assert (entry.comments_url, entry.comment_feed_url, entry.comment_count, entry.author) == (
        None, None, None, None,
    )


def image_feed(body: str, *, media: str = "", channel: str = "", enclosure: str = "",
               url: str = "https://site.example/feed") -> bytes:
    return (f"<rss version='2.0' xmlns:media='http://search.yahoo.com/mrss/' "
            f"xmlns:itunes='http://www.itunes.com/dtds/podcast-1.0.dtd'><channel>"
            f"<title>Pictures</title>{channel}<item><title>Post</title>"
            f"<link>https://site.example/post</link><description>{html.escape(body)}</description>"
            f"{media}{enclosure}</item></channel></rss>").encode()


def test_entry_html_keeps_images_in_order_with_figure_caption():
    raw = image_feed("<p><img src='/chart.png' alt='Growth chart'></p>"
                     "<figure><img src='https://cdn.example/screen.png' alt='New interface'>"
                     "<figcaption>Settings screen</figcaption></figure>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert [(i.url, i.alt, i.caption, i.origin) for i in entry.images] == [
        ("https://site.example/chart.png", "Growth chart", "", "html"),
        ("https://cdn.example/screen.png", "New interface", "Settings screen", "html"),
    ]


def test_wordpress_media_skips_avatars_and_channel_blavatar():
    raw = image_feed("", channel="<image><url>https://site.example/blavatar/42</url></image>",
                     media="<media:content url='https://gravatar.com/avatar/abc' medium='image'/>"
                           "<media:content url='https://cdn.example/post.png' type='image/png'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert [(i.url, i.origin) for i in entry.images] == [("https://cdn.example/post.png", "media")]


def test_youtube_thumbnail_is_candidate_and_podcast_cover_is_not():
    video = image_feed("", media="<media:thumbnail url='https://img.example/thumb.jpg'/>")
    entry = parse_feed(FetchResponse("https://www.youtube.com/feeds/videos.xml", video, "", 200)).entries[0]
    assert [(i.url, i.origin) for i in entry.images] == [("https://img.example/thumb.jpg", "thumbnail")]
    podcast = image_feed("", media="<itunes:image href='https://cdn.example/cover.png'/>",
                         enclosure="<enclosure url='https://cdn.example/episode.mp3' type='audio/mpeg'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", podcast, "", 200)).entries[0]
    assert entry.images == ()


def test_image_filters_duplicates_pixels_and_caps_at_eight():
    body = ("<img src='data:image/png;base64,aaa'>"
            "<img src='/pixel.png' width='1' height='1'>"
            "<img src='/one.png' alt='first'><img src='/one.png?size=large'>"
            + "".join(f"<img src='/picture-{n}.png'>" for n in range(12)))
    entry = parse_feed(FetchResponse("https://site.example/feed", image_feed(body), "", 200)).entries[0]
    assert [i.url for i in entry.images] == [
        "https://site.example/one.png",
        "https://site.example/one.png?size=large",
        *[f"https://site.example/picture-{n}.png" for n in range(6)],
    ]


def test_image_query_identifies_distinct_images():
    body = ("<img src='https://example.com/image.php?id=1'>"
            "<img src='https://example.com/image.php?id=2'>")
    entry = parse_feed(FetchResponse("https://site.example/feed", image_feed(body), "", 200)).entries[0]
    assert [image.url for image in entry.images] == [
        "https://example.com/image.php?id=1",
        "https://example.com/image.php?id=2",
    ]


def test_image_fragment_does_not_make_new_candidate():
    body = ("<img src='https://example.com/image.php?id=1'>"
            "<img src='https://example.com/image.php?id=1#view'>")
    entry = parse_feed(FetchResponse("https://site.example/feed", image_feed(body), "", 200)).entries[0]
    assert [image.url for image in entry.images] == ["https://example.com/image.php?id=1"]


def test_image_fragment_first_keeps_first_candidate_only():
    body = ("<img src='https://example.com/a.png#x'>"
            "<img src='https://example.com/a.png'>")
    entry = parse_feed(FetchResponse("https://site.example/feed", image_feed(body), "", 200)).entries[0]
    assert [image.url for image in entry.images] == ["https://example.com/a.png#x"]


def test_ftp_media_image_is_dropped():
    raw = image_feed("", media="<media:content url='ftp://cdn.example/photo.jpg' type='image/jpeg'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.images == ()


def test_wordpress_entry_blavatar_is_dropped_even_without_channel_match():
    raw = image_feed("", media="<media:content url='https://s0.wp.com/i/blavatar/writer.png' "
                               "medium='image'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.images == ()


def test_html_image_matching_channel_image_is_dropped():
    image = "https://site.example/site-banner.jpg"
    raw = image_feed(f"<img src='{image}'>", channel=f"<image><url>{image}</url></image>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.images == ()


def test_audio_entry_ignores_html_and_media_images():
    raw = image_feed("<img src='https://site.example/diagram.jpg'>",
                     media="<media:content url='https://cdn.example/photo.jpg' medium='image'/>",
                     enclosure="<enclosure url='https://cdn.example/episode.mp3' type='audio/mpeg'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.has_audio is True
    assert entry.images == ()


def test_video_media_content_is_not_an_image():
    raw = image_feed("", media="<media:content url='https://cdn.example/clip.mp4' "
                               "medium='video' type='video/mp4'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.images == ()


def test_pdf_enclosure_is_not_an_image():
    raw = image_feed("", enclosure="<enclosure url='https://cdn.example/report.pdf' "
                                   "type='application/pdf'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert entry.images == ()


def test_jpeg_enclosure_keeps_image_and_origin():
    raw = image_feed("", enclosure="<enclosure url='https://cdn.example/photo.jpg' "
                                   "type='image/jpeg'/>")
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert [(image.url, image.origin) for image in entry.images] == [
        ("https://cdn.example/photo.jpg", "enclosure"),
    ]


def test_html_images_come_before_xml_media_regardless_of_element_order():
    raw = ("<rss version='2.0' xmlns:media='http://search.yahoo.com/mrss/'><channel>"
           "<title>Pictures</title><item><title>Post</title>"
           "<link>https://site.example/post</link>"
           "<media:content url='https://cdn.example/lead.png' medium='image'/>"
           f"<description>{html.escape('<img src=\"https://site.example/diagram.png\">')}</description>"
           "</item></channel></rss>").encode()
    entry = parse_feed(FetchResponse("https://site.example/feed", raw, "", 200)).entries[0]
    assert [(image.url, image.origin) for image in entry.images] == [
        ("https://site.example/diagram.png", "html"),
        ("https://cdn.example/lead.png", "media"),
    ]


def test_discovery_does_not_fetch_images(public_dns):
    raw = image_feed("<img src='https://cdn.example/chart.png'>")
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/feed").mock(return_value=httpx.Response(
            200, content=raw, headers={"content-type": "application/rss+xml"},
        ))
        found = discover("https://site.example/feed")
        assert [str(call.request.url) for call in router.calls] == ["https://site.example/feed"]
    assert found.feed.entries[0].images[0].url == "https://cdn.example/chart.png"


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
    assert str(error.value) == "The site's feed is temporarily unavailable."


def test_declared_feed_http_error_precedes_oversized_candidate(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/missing.xml", "/oversized.xml"),
            headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/missing.xml").mock(return_value=httpx.Response(404))
        router.get("https://site.example/oversized.xml").mock(return_value=httpx.Response(
            200, content=b"x" * 1024, headers={"content-type": "application/rss+xml"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/", max_feed_bytes=512)
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 404


def test_declared_feed_blocked_address_precedes_oversized_candidate(blocked_candidate_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("https://internal.example/feed.xml", "/oversized.xml"),
            headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/oversized.xml").mock(return_value=httpx.Response(
            200, content=b"x" * 1024, headers={"content-type": "application/rss+xml"},
        ))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/", max_feed_bytes=512)
        assert len(router.calls) == 2
    assert error.value.code == "blocked_address"


def test_declared_feed_status_600_is_unavailable(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(
            200, content=declared_html("/feed.xml"), headers={"content-type": "text/html"},
        ))
        router.get("https://site.example/feed.xml").mock(return_value=httpx.Response(600))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
    assert error.value.code == "feed_unavailable"
    assert error.value.status_code == 600


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


def test_page_307_without_location_does_not_probe(public_dns):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://site.example/").mock(return_value=httpx.Response(307))
        router.get(re.compile(r"https://site\.example/.*")).mock(return_value=httpx.Response(404))
        with pytest.raises(FetchError) as error:
            discover("https://site.example/")
        assert len(router.calls) == 1
    assert error.value.code == "fetch_failed"
    assert error.value.status_code == 307


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
