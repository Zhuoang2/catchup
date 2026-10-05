from pathlib import Path

import pytest

from catchup.net.safe_fetch import FetchResponse
from catchup.sources.feeds import (
    FeedParseError, TranscriptCandidate, _transcript_candidates, ordered_candidates, parse_feed,
)

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://site.example/feed"


def feed(filename: str):
    return parse_feed(FetchResponse(URL, (FIXTURES / filename).read_bytes(), "application/rss+xml", 200))


def test_multiple_candidates_and_preference():
    candidates = feed("podcast-multi.xml").entries[0].transcripts
    assert len(candidates) == 4
    assert [candidate.type for candidate in candidates] == [
        "text/vtt", "application/x-subrip", "application/json", "text/html",
    ]
    assert ordered_candidates((
        TranscriptCandidate("other", "text/vtt", "de"),
        TranscriptCandidate("preferred", "text/vtt", "en"),
        TranscriptCandidate("plain", "text/plain", "de"),
    ), "en")[0].url == "plain"
    assert ordered_candidates((
        TranscriptCandidate("other", "text/vtt", "de"),
        TranscriptCandidate("preferred", "text/vtt", "en"),
    ), "en")[0].url == "preferred"


def test_odd_namespace_and_srt_alias():
    assert feed("podcast-oddns.xml").entries[0].transcripts == (
        TranscriptCandidate("https://site.example/a.srt", "application/srt"),)


def test_recovery_and_no_tags():
    assert feed("podcast-entity.xml").entries[0].transcripts[0].type == "text/vtt"
    assert feed("podcast-none.xml").entries[0].transcripts == ()


def test_internal_entity_does_not_expand():
    body = b'''<!DOCTYPE rss [<!ENTITY secret "https://example.com/private">]>
    <rss xmlns:podcast="https://podcastindex.org/namespace/1.0"><channel>
    <item><guid>ep1</guid><title>&secret;</title>
    <podcast:transcript url="&secret;" type="text/vtt"/></item>
    </channel></rss>'''
    assert _transcript_candidates(body) == {}
    candidates = parse_feed(FetchResponse(URL, body, "", 200)).entries[0].transcripts
    assert all(candidate.url != "https://example.com/private" for candidate in candidates)


def test_garbage_does_not_yield_candidates():
    assert _transcript_candidates(b"\x00\xff nonsense") == {}
    with pytest.raises(FeedParseError):
        parse_feed(FetchResponse(URL, b"\x00\xff nonsense", "", 200))


def test_feedparser_fallback_when_xml_parser_fails(monkeypatch):
    monkeypatch.setattr("catchup.sources.feeds._transcript_candidates", lambda _body: {})
    assert feed("podcast-multi.xml").entries[0].transcripts
    assert len(feed("podcast-multi.xml").entries[0].transcripts) == 1
