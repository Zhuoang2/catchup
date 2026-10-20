import socket

import httpx
import pytest
import respx

from catchup.context.robots import RobotsCache


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port, *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))],
    )


def test_disallow_for_catchup_and_fetch_once_per_host(public_dns):
    budget = [5]
    calls = []

    class Spacer:
        def wait(self, url):
            calls.append(url)

    robots = RobotsCache(budget=budget, spacer=Spacer())
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(
            200, text="User-agent: CatchUp\nDisallow: /private\nAllow: /\n",
        ))
        assert not robots.allowed("https://site.example/private/post")
        assert robots.allowed("https://site.example/public")
        assert route.call_count == 1
    assert calls == ["https://site.example/robots.txt"]
    assert budget == [4]


@pytest.mark.parametrize("response,expected", [(404, True), (401, False), (403, False)])
def test_missing_or_restricted_robots(public_dns, response, expected):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(response))
        assert RobotsCache(budget=[2]).allowed("https://site.example/post") is expected


def test_failed_robots_request_allows(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(side_effect=httpx.ConnectTimeout("timeout"))
        assert RobotsCache(budget=[2]).allowed("https://site.example/post")


def test_robots_request_uses_shared_budget(public_dns):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(200, text=""))
        assert not RobotsCache(budget=[0]).allowed("https://site.example/post")
        assert route.call_count == 0


def test_robots_request_limits_response_to_512_kib(monkeypatch):
    captured = []

    class Response:
        content = b"User-agent: CatchUp\nAllow: /\n"

    def fetch(url, **kwargs):
        captured.append((url, kwargs))
        return Response()

    monkeypatch.setattr("catchup.context.robots.safe_fetch", fetch)
    assert RobotsCache(budget=[2]).allowed("https://site.example/post")
    assert captured[0][0] == "https://site.example/robots.txt"
    assert captured[0][1]["max_bytes"] == 512 * 1024
