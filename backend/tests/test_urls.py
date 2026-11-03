"""Parsing addresses that may be malformed never raises."""

import pytest

from catchup.net.urls import join_url, split_url


@pytest.mark.parametrize("base,href", [
    ("https://blog.example/post", "https://[object Object]"),
    ("https://blog.example/", "http://[x"),
])
def test_join_url_gives_none_for_an_address_that_cannot_be_parsed(base, href):
    assert join_url(base, href) is None


def test_split_url_gives_none_for_an_address_that_cannot_be_parsed():
    assert split_url("http://[x") is None


@pytest.mark.parametrize("base,href,expected", [
    ("https://blog.example/posts/one", "two", "https://blog.example/posts/two"),
    ("https://blog.example/posts/one", "/about", "https://blog.example/about"),
    ("https://blog.example/posts/one", "../img/a.png", "https://blog.example/img/a.png"),
    ("https://blog.example/posts/one", "https://cdn.example/a.png", "https://cdn.example/a.png"),
    ("https://blog.example/posts/one", "//cdn.example/a.png", "https://cdn.example/a.png"),
    ("", "/relative", "/relative"),
])
def test_join_url_matches_ordinary_joins(base, href, expected):
    assert join_url(base, href) == expected


def test_split_url_matches_an_ordinary_split():
    parts = split_url("https://blog.example:8443/posts/one?q=1#top")
    assert (parts.scheme, parts.hostname, parts.port, parts.path, parts.query, parts.fragment) == (
        "https", "blog.example", 8443, "/posts/one", "q=1", "top",
    )
