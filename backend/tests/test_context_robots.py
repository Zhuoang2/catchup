import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
import respx

from catchup.context.robots import RobotsCache
from catchup.net.safe_fetch import BudgetExhausted


@pytest.mark.parametrize("url", [
    "/comments/feed",
    "ftp://site.example:21/feed",
    "https://site.example:abc/x",
    "https://site.example:99999/x",
    "https://user:secret@site.example/x",
    "mailto:a@site.example",
], ids=["relative", "non_http", "bad_port", "large_port", "user_info", "mailto"])
def test_origin_refuses_addresses_that_safe_fetch_refuses(url):
    from catchup.context.robots import origin

    with pytest.raises(ValueError):
        origin(url)


def test_origin_ignores_case_and_default_port():
    from catchup.context.robots import origin

    assert origin("https://SITE.example:443/a") == origin("https://site.example/b") == "https://site.example"
    assert origin("http://site.example:8080/x") == "http://site.example:8080"
    assert origin("https://[2001:db8::1]/x") == "https://[2001:db8::1]"


def test_verdict_never_requests_and_reads_stored_rules(public_dns):
    robots = RobotsCache(budget=[10])
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://site.example/robots.txt").respond(
            200, text="User-agent: *\nDisallow: /private\n",
        )
        router.get("https://unavailable.example/robots.txt").respond(503)
        router.get("https://missing.example/robots.txt").respond(404)
        assert robots.verdict("https://site.example/private/x") is None
        assert len(router.calls) == 0
        assert robots.allowed("https://site.example/ok") is True
        assert robots.verdict("https://site.example/private/x") is False
        assert robots.verdict("https://site.example/ok") is True
        assert route.call_count == 1
        assert robots.allowed("https://unavailable.example/p") is False
        assert robots.verdict("https://unavailable.example/p") is False
        assert robots.allowed("https://missing.example/p") is True
        assert robots.verdict("https://missing.example/p") is True


def test_robots_is_read_once_when_two_threads_ask_at_once(public_dns):
    robots = RobotsCache(budget=[10])
    barrier = threading.Barrier(2)

    def response(_request):
        time.sleep(0.2)
        return httpx.Response(404)

    def allowed(url):
        barrier.wait(timeout=5)
        return robots.allowed(url)

    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://site.example/robots.txt").mock(side_effect=response)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(allowed, ("https://site.example/a", "https://SITE.example/b")))
    assert results == [True, True]
    assert route.call_count == 1


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


@pytest.mark.parametrize("response,expected", [
    (400, True), (404, True), (401, False), (403, False), (410, True), (429, True), (499, True),
    (500, False), (502, False), (503, False),
])
def test_missing_or_restricted_robots(public_dns, response, expected):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(response))
        assert RobotsCache(budget=[2]).allowed("https://site.example/post") is expected


@pytest.mark.parametrize("side_effect", [
    httpx.ConnectTimeout("timeout"), httpx.ConnectError("connection failed"),
    httpx.ReadTimeout("timeout"),
])
def test_unreachable_robots_disallows(public_dns, side_effect):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(side_effect=side_effect)
        assert RobotsCache(budget=[2]).allowed("https://site.example/post") is False


def test_unresolvable_robots_host_disallows(monkeypatch):
    def unresolvable(*_args, **_kwargs):
        raise socket.gaierror("host not found")

    monkeypatch.setattr(socket, "getaddrinfo", unresolvable)
    budget = [2]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(200))
        assert RobotsCache(budget=budget).allowed("https://site.example/post") is False
        assert not route.called
    assert budget == [2]


def test_rate_limited_server_error_disallows(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(
            503, headers={"Retry-After": "120"},
        ))
        assert RobotsCache(budget=[2]).allowed("https://site.example/post") is False


@pytest.mark.parametrize("response", [
    httpx.Response(302), httpx.Response(200, content=b"x" * (512 * 1024 + 1)),
])
def test_unreadable_robots_response_disallows(public_dns, response):
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://site.example/robots.txt").mock(return_value=response)
        assert RobotsCache(budget=[2]).allowed("https://site.example/post") is False


def test_unreachable_robots_is_cached_for_the_run(public_dns):
    budget = [5]
    robots = RobotsCache(budget=budget)
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(503))
        assert robots.allowed("https://site.example/a") is False
        assert robots.allowed("https://site.example/b") is False
        assert route.call_count == 1
    assert budget == [4]


def test_robots_request_uses_shared_budget(public_dns):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(200, text=""))
        with pytest.raises(BudgetExhausted):
            RobotsCache(budget=[0]).allowed("https://site.example/post")
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


def test_one_robots_read_for_three_spellings(public_dns):
    budget = [5]
    robots = RobotsCache(budget=budget)
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(
            200, text="User-agent: *\nDisallow: /b\n",
        ))
        assert [
            robots.allowed("https://SITE.example/a"),
            robots.allowed("https://site.example:443/b"),
            robots.allowed("https://site.example/c"),
        ] == [True, False, True]
        assert route.call_count == 1
    assert budget == [4]


def test_scheme_and_other_ports_stay_separate_origins(public_dns):
    robots = RobotsCache(budget=[5])
    with respx.mock(assert_all_mocked=True) as router:
        other_port = router.get("https://site.example:8443/robots.txt").mock(return_value=httpx.Response(404))
        secure = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(404))
        plain = router.get("http://site.example/robots.txt").mock(return_value=httpx.Response(404))
        for url in (
            "https://site.example:8443/x", "https://site.example/x",
            "http://site.example/x", "http://site.example:80/x",
        ):
            assert robots.allowed(url)
        assert [other_port.call_count, secure.call_count, plain.call_count] == [1, 1, 1]


def test_ipv6_host_keeps_its_brackets(public_dns):
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get("https://[2001:db8::1]/robots.txt").mock(return_value=httpx.Response(404))
        assert RobotsCache(budget=[2]).allowed("https://[2001:DB8::1]/x") is True
        assert route.call_count == 1


def test_budget_running_out_in_a_robots_redirect_propagates(public_dns):
    robots = RobotsCache(budget=[1])
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get("https://site.example/robots.txt").mock(return_value=httpx.Response(
            302, headers={"location": "/robots-moved.txt"},
        ))
        moved = router.get("https://site.example/robots-moved.txt").mock(return_value=httpx.Response(200))
        for _ in range(2):
            with pytest.raises(BudgetExhausted):
                robots.allowed("https://site.example/post")
        assert route.call_count == 1
        assert not moved.called
