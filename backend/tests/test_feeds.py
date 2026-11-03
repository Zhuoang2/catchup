"""Feed parsing keeps an entry whose addresses cannot all be parsed."""

import html

from catchup.net.safe_fetch import FetchResponse
from catchup.sources.feeds import EntryImage, filter_image_urls, parse_feed

GARDEN_FEED = "https://garden.example/feed"


def malformed_entry_feed() -> bytes:
    """Entry 1 has a bad image, a bad media image and a bad link; entry 2 is ordinary."""
    body = ("<p>Release notes for the garden planner.</p>"
            "<img src=\"https://[object Object]\">"
            "<img src=\"/images/planner.png\" alt=\"Planner\">"
            "<a href=\"http://&#91;x\">bad</a> "
            "<a href=\"https://docs.example/planner\">Docs</a>"
            + "<p>" + "The planner now plans seasons. " * 20 + "</p>")
    return ("<rss version='2.0' xmlns:media='http://search.yahoo.com/mrss/'><channel>"
            "<title>Garden</title><link>https://garden.example/</link>"
            "<item><guid>entry-1</guid><title>Planner 2.0</title>"
            "<link>https://garden.example/planner-2</link>"
            f"<description>{html.escape(body)}</description>"
            "<media:content url='http://[x' medium='image'/>"
            "<media:content url='https://cdn.example/cover.png' medium='image'/>"
            "</item>"
            "<item><guid>entry-2</guid><title>Seeds</title>"
            "<link>https://garden.example/seeds</link>"
            f"<description>{'Seed catalog for the spring season. ' * 20}</description></item>"
            "</channel></rss>").encode()


def test_filter_image_urls_skips_addresses_that_cannot_be_joined():
    candidates = [
        EntryImage("https://[object Object]"),
        EntryImage("http://[x"),
        EntryImage("/images/good.png", alt="Good"),
    ]
    kept = filter_image_urls(candidates, base="https://blog.example/post")
    assert [(image.url, image.alt) for image in kept] == [("https://blog.example/images/good.png", "Good")]


def test_parse_feed_keeps_entry_with_malformed_image_media_and_link():
    feed = parse_feed(FetchResponse(GARDEN_FEED, malformed_entry_feed(), "application/rss+xml", 200))
    assert [entry.identity_key for entry in feed.entries] == ["entry-1", "entry-2"]
    first, second = feed.entries
    assert first.title == "Planner 2.0"
    assert first.content_text.startswith("Release notes for the garden planner.")
    assert "The planner now plans seasons." in first.content_text
    assert [(link.url, link.text) for link in first.links] == [("https://docs.example/planner", "Docs")]
    assert [(image.url, image.origin) for image in first.images] == [
        ("https://garden.example/images/planner.png", "html"),
        ("https://cdn.example/cover.png", "media"),
    ]
    assert second.title == "Seeds"
    assert second.link == "https://garden.example/seeds"
