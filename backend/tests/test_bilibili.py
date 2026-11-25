import base64
import json
import re
import socket
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
import respx

from catchup.errors import AppError
from catchup.net.safe_fetch import FetchError, FetchResponse
from catchup.sources.bilibili import fetch_uploader, parse_uploader_feed, uploader_mid
from catchup.sources.feeds import FeedParseError

MID = "2267573"
RSSHUB = "http://rsshub.test:1200"
ROUTE = RSSHUB + "/bilibili/user/video/2267573?format=json"
SRT_A = "1\n00:00:01,000 --> 00:00:04,000\nHello\n\n2\n00:00:04,000 --> 00:00:06,000\nworld\n"
BILIBILI = re.compile(r"https?://([^/]*\.)?(bilibili\.com|b23\.tv|hdslb\.com|bilivideo\.com)(:\d+)?/.*")


def uploader_body():
    return json.loads((Path(__file__).parent / "fixtures/rsshub-uploader.json").read_bytes())


def response(body=None):
    return FetchResponse(ROUTE, json.dumps(uploader_body() if body is None else body).encode(),
                         "application/feed+json", 200)


@pytest.mark.parametrize("url,configured,expected", [
    ("https://space.bilibili.com/2267573", RSSHUB, MID),
    ("https://space.bilibili.com/2267573/video?tid=0", RSSHUB, MID),
    ("https://space.bilibili.com/2267573/upload/video", RSSHUB, MID),
    ("http://space.bilibili.com/2267573#top", RSSHUB, MID),
    ("HTTPS://SPACE.BILIBILI.COM./2267573", RSSHUB, MID),
    ("https://m.bilibili.com/space/2267573", RSSHUB, MID),
    (ROUTE, RSSHUB, MID),
    (RSSHUB + "/bilibili/user/video/2267573/disableEmbed", RSSHUB, MID),
    ("https://example.com/feed", RSSHUB, None),
    (RSSHUB + "/github/repos/example", RSSHUB, None),
    (ROUTE, None, None),
], ids=["space", "section-query", "upload", "fragment", "case-dot", "mobile", "route",
        "route-embed", "other-site", "other-route", "route-unconfigured"])
def test_uploader_addresses(url, configured, expected):
    assert uploader_mid(url, configured) == expected


@pytest.mark.parametrize("url", [
    "https://www.bilibili.com/video/BV1xx411c7mD", "https://b23.tv/abc123",
    "https://space.bilibili.com/abc", "https://space.bilibili.com/" + "1" * 21,
    "https://www.bilibili.com/", "https://i0.hdslb.com/a.jpg",
], ids=["video", "short-link", "non-numeric", "too-long", "home", "image"])
def test_other_bilibili_addresses_are_refused(url):
    with pytest.raises(AppError) as error:
        uploader_mid(url, RSSHUB)
    assert (error.value.code, error.value.status_code, error.value.message) == (
        "not_a_bilibili_uploader", 422,
        "Paste the uploader's space address, such as https://space.bilibili.com/2267573.",
    )


def test_parse_uploader_feed():
    feed = parse_uploader_feed(response(), MID)
    assert (feed.feed_url, feed.site_url, feed.title, feed.kind) == (
        "bilibili:uploader:2267573", "https://space.bilibili.com/2267573", "Sample Uploader", "bilibili",
    )
    assert [entry.identity_key for entry in feed.entries] == [
        "bilibili:video:BV1aa411c7aA", "bilibili:video:BV1bb411c7bB", "bilibili:video:av170001",
    ]
    assert [entry.link for entry in feed.entries] == [item["url"] for item in uploader_body()["items"][:3]]
    assert feed.entries[0].published_at == datetime(2026, 11, 21, 10, tzinfo=timezone.utc)
    assert feed.entries[0].content_text == "Description A"
    for entry in feed.entries:
        assert (entry.links, entry.images, entry.comments_url, entry.comment_feed_url,
                entry.comment_count, entry.has_audio, entry.transcripts) == ((), (), None, None, None, False, ())


@pytest.mark.parametrize("title,authors,expected", [
    ("Sample Uploader 的 bilibili 空间", [{"name": "Sample Uploader"}], "Sample Uploader"),
    ("Plain Title", [{"name": "Sample Uploader"}], "Plain Title"),
    ("", [{"name": "Sample Uploader"}], "Sample Uploader"),
    ("", [], "Bilibili uploader 2267573"),
])
def test_uploader_title(title, authors, expected):
    body = uploader_body()
    body["title"] = title
    body["items"][0]["authors"] = authors
    assert parse_uploader_feed(response(body), MID).title == expected


def test_subtitles_from_data_attachment():
    feed = parse_uploader_feed(response(), MID)
    assert feed.entries[0].transcript_text == "Hello\n\nworld"
    assert "Second track" not in feed.entries[0].transcript_text
    assert feed.entries[1].transcript_text is None
    body = uploader_body()
    body["items"][0]["attachments"] = [{
        "url": "data:text/plain;base64," + base64.b64encode(SRT_A.encode()).decode(),
        "mime_type": "text/srt",
    }]
    assert parse_uploader_feed(response(body), MID).entries[0].transcript_text == "Hello\n\nworld"


@pytest.mark.parametrize("url", ["https://www.bilibili.com/sub.srt", "https://subs.example/sub.srt"])
def test_web_attachments_are_never_requested(monkeypatch, url):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])
    body = uploader_body()
    body["items"][0]["attachments"] = [{"url": url, "mime_type": "text/srt"}]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        web = router.get("https://subs.example/sub.srt").respond(200, text=SRT_A)
        blocked = router.get(BILIBILI).mock(side_effect=AssertionError("Bilibili must never be requested"))
        assert parse_uploader_feed(response(body), MID).entries[0].transcript_text is None
        assert web.call_count == blocked.call_count == 0


@pytest.mark.parametrize("body", [
    b"<html>Busy</html>", b"{}", b'{"version":"https://jsonfeed.org/version/1.1","items":"busy"}',
    b'{"version":"1.0","items":[]}', b"\xff not JSON",
])
def test_invalid_rsshub_answers(body):
    with pytest.raises(FeedParseError, match=r"^RSSHub could not read this uploader\.$"):
        parse_uploader_feed(FetchResponse(ROUTE, body, "text/html", 200), MID)


def test_fetch_uploader_uses_feed_limit_and_spacing(monkeypatch, test_settings):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port)),
    ])
    waited = []

    class Spacer:
        def wait(self, url):
            waited.append(url)

    settings = replace(test_settings, rsshub_url=RSSHUB, max_feed_bytes=6 * 1024 * 1024)
    body = b" " * (5 * 1024 * 1024 + 1)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get(ROUTE).respond(200, content=body)
        blocked = router.get(BILIBILI).mock(side_effect=AssertionError("Bilibili must never be requested"))
        assert fetch_uploader(MID, settings, spacer=Spacer()).content == body
        assert waited == [ROUTE]
        assert blocked.call_count == 0


@pytest.mark.parametrize("case", ["not-configured", "ok", "prefix", "http-error", "redirect-to-bilibili"])
def test_fetch_uploader(monkeypatch, test_settings, case):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port)),
    ])
    settings = replace(test_settings, rsshub_url=None if case == "not-configured" else
                       RSSHUB + "/hub" if case == "prefix" else RSSHUB)
    route_url = RSSHUB + "/hub/bilibili/user/video/2267573?format=json" if case == "prefix" else ROUTE
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get(route_url).respond(
            503 if case == "http-error" else 302 if case == "redirect-to-bilibili" else 200,
            content=response().content, headers={"location": "https://www.bilibili.com/"},
        )
        blocked = router.get(BILIBILI).mock(side_effect=AssertionError("Bilibili must never be requested"))
        if case in ("not-configured", "http-error", "redirect-to-bilibili"):
            with pytest.raises(FetchError) as error:
                fetch_uploader(MID, settings)
            assert error.value.code == {
                "not-configured": "rsshub_not_configured", "http-error": "rsshub_failed",
                "redirect-to-bilibili": "blocked_address",
            }[case]
            if case == "not-configured":
                assert str(error.value) == (
                    "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README."
                )
                assert route.call_count == 0
            elif case == "http-error":
                assert error.value.status_code == 503
                assert str(error.value) == "RSSHub could not read this uploader (HTTP 503)."
        else:
            assert fetch_uploader(MID, settings).content == response().content
            assert route.call_count == 1
            assert str(route.calls[0].request.url) == route_url
            assert route.calls[0].request.headers["user-agent"].startswith("CatchUp/")
        assert blocked.call_count == 0
