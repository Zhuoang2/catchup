import socket
from datetime import datetime, timezone

import httpx
import pytest
import respx

from catchup.config import Settings
from catchup.main import create_app
from catchup.net.safe_fetch import FetchError, MAX_BYTES, parse_retry_after, safe_fetch

PUBLIC = "https://public.example/feed"


@pytest.fixture
def resolve(monkeypatch):
    addresses = {"public.example": ["8.8.8.8"]}

    def lookup(host, port, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
                for address in addresses.get(host, [])]

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    return addresses


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.1.1", "192.168.1.8", "169.254.169.254",
                                       "::1", "fc00::1", "0.0.0.0", "224.0.0.1"])
def test_rejects_non_public_addresses(resolve, address):
    resolve["public.example"] = [address]
    with pytest.raises(FetchError) as error:
        safe_fetch(PUBLIC)
    assert error.value.code == "blocked_address"


def test_rejects_mixed_dns_results(resolve):
    resolve["public.example"] = ["8.8.8.8", "10.0.0.1"]
    with pytest.raises(FetchError, match="not allowed"):
        safe_fetch(PUBLIC)


def test_nat64_embedded_private_address_blocked(resolve):
    resolve["public.example"] = ["64:ff9b::7f00:1"]
    with pytest.raises(FetchError) as error:
        safe_fetch(PUBLIC)
    assert error.value.code == "blocked_address"


def test_nat64_embedded_public_address_allowed(resolve):
    resolve["public.example"] = ["64:ff9b::808:808"]
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(200, content=b"public"))
        assert safe_fetch(PUBLIC).content == b"public"


def test_slow_drip_aborts_after_wall_clock_deadline(resolve, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("catchup.net.safe_fetch.monotonic", lambda: clock[0])

    class SlowChunks(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(4):
                clock[0] += 11.0
                yield b"x"

    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(200, stream=SlowChunks()))
        with pytest.raises(FetchError, match="timed out") as error:
            safe_fetch(PUBLIC)
    assert error.value.code == "fetch_failed"
    assert clock[0] > 130


def test_redirect_to_metadata_is_blocked_before_request(resolve):
    resolve["metadata.example"] = ["169.254.169.254"]
    with respx.mock(assert_all_mocked=True) as router:
        first = router.get(PUBLIC).mock(return_value=httpx.Response(
            302, headers={"location": "http://metadata.example/latest"},
        ))
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
        assert first.call_count == 1
    assert error.value.code == "blocked_address"


@pytest.mark.parametrize("url", ["file:///tmp/a", "http://user:pass@public.example/feed",
                                   "http://", "https://public.example:bad/feed"])
def test_rejects_invalid_urls(url):
    with pytest.raises(FetchError) as error:
        safe_fetch(url)
    assert error.value.code == "invalid_url"


def test_timeout(resolve):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(side_effect=httpx.ReadTimeout("timeout"))
        with pytest.raises(FetchError, match="timed out"):
            safe_fetch(PUBLIC)


def test_oversized_stream(resolve):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(200, content=b"x" * (MAX_BYTES + 1)))
        with pytest.raises(FetchError, match="5 MB"):
            safe_fetch(PUBLIC)


@pytest.mark.parametrize("content_length", [True, False])
def test_six_mb_feed_allowed_with_feed_limit(resolve, content_length):
    body = b"x" * (6 * 1024 * 1024)
    headers = {"content-length": str(len(body))} if content_length else {}
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(200, content=body, headers=headers))
        assert len(safe_fetch(PUBLIC, max_bytes=32 * 1024 * 1024).content) == len(body)
        with pytest.raises(FetchError, match="5 MB"):
            safe_fetch(PUBLIC)
        with pytest.raises(FetchError, match="4 MB"):
            safe_fetch(PUBLIC, max_bytes=4 * 1024 * 1024)


def test_public_response_and_relative_redirect(resolve):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(302, headers={"location": "/new-feed"}))
        router.get("https://public.example/new-feed").mock(
            return_value=httpx.Response(200, headers={"content-type": "application/rss+xml"}, content=b"<rss/>"),
        )
        result = safe_fetch(PUBLIC)
    assert result.content == b"<rss/>"
    assert result.content_type == "application/rss+xml"
    assert result.url == "https://public.example/new-feed"


def test_redirect_limit(resolve):
    with respx.mock(assert_all_mocked=True) as router:
        for i in range(6):
            router.get(f"https://public.example/{i}").mock(
                return_value=httpx.Response(302, headers={"location": f"/{i + 1}"}),
            )
        with pytest.raises(FetchError, match="too many"):
            safe_fetch("https://public.example/0")


def test_user_agent_on_page_redirect_and_contact(resolve, monkeypatch):
    monkeypatch.setattr("catchup.net.safe_fetch.version", lambda _package: "1.2.3")
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(return_value=httpx.Response(302, headers={"location": "/next"}))
        router.get("https://public.example/next").mock(return_value=httpx.Response(200))
        safe_fetch(PUBLIC)
        assert [call.request.headers["user-agent"] for call in router.calls] == [
            "CatchUp/1.2.3 (+https://github.com/Zhuoang2/catchup)"
        ] * 2
        monkeypatch.setenv("CATCHUP_USER_AGENT_CONTACT", "by /u/example")
        safe_fetch(PUBLIC)
        assert router.calls[-1].request.headers["user-agent"] == (
            "CatchUp/1.2.3 (+https://github.com/Zhuoang2/catchup; by /u/example)"
        )


def test_user_agent_fallback_and_invalid_contact(monkeypatch):
    from importlib.metadata import PackageNotFoundError
    from catchup.net.safe_fetch import user_agent

    def missing(_package):
        raise PackageNotFoundError

    monkeypatch.setattr("catchup.net.safe_fetch.version", missing)
    assert user_agent().startswith("CatchUp/0.0.0 ")
    for contact in ("evil\r\nX-Injected: yes", "\u2603", "x" * 101):
        monkeypatch.setenv("CATCHUP_USER_AGENT_CONTACT", contact)
        with pytest.raises(ValueError, match="CATCHUP_USER_AGENT_CONTACT"):
            Settings.from_env()
        with pytest.raises(ValueError, match="CATCHUP_USER_AGENT_CONTACT"):
            create_app()


@pytest.mark.parametrize("value,expected", [
    ("3", 3),
    ("Sun, 06 Nov 1994 08:49:40 GMT", 10),
    ("Sunday, 06-Nov-94 08:49:40 GMT", 10),
    ("Sun Nov  6 08:49:40 1994", 10),
    ("Sun, 06 Nov 1994 08:49:20 GMT", 0),
    (None, None), ("", None), ("garbage", None), ("+3", None), ("3.5", None),
])
def test_retry_after_formats(value, expected):
    assert parse_retry_after(value, now=datetime(1994, 11, 6, 8, 49, 30, tzinfo=timezone.utc)) == expected


@pytest.mark.parametrize("status,headers,expected_code,requests,delay", [
    (429, {"Retry-After": "120"}, "rate_limited", 1, 120),
    (429, {}, "rate_limited", 1, None),
    (503, {"Retry-After": "120"}, "rate_limited", 1, 120),
    (503, {}, "fetch_failed", 1, None),
    (503, {"Retry-After": "garbage"}, "fetch_failed", 1, None),
    (429, {"Retry-After": "3"}, None, 2, 3),
    (503, {"Retry-After": "3"}, None, 2, 3),
])
def test_rate_limit_policy(resolve, monkeypatch, status, headers, expected_code, requests, delay):
    clock = [100.0]
    sleeps = []
    monkeypatch.setattr("catchup.net.safe_fetch.monotonic", lambda: clock[0])

    def fake_sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr("catchup.net.safe_fetch.sleep", fake_sleep)
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(PUBLIC).mock(side_effect=[
            httpx.Response(status, headers=headers), httpx.Response(200, content=b"ok"),
        ])
        if expected_code:
            with pytest.raises(FetchError) as error:
                safe_fetch(PUBLIC)
            assert error.value.code == expected_code
            assert error.value.retry_after == (delay if expected_code == "rate_limited" else None)
            if expected_code == "rate_limited":
                assert "rate limiting" in str(error.value)
                assert ("120 seconds" in str(error.value)) == (delay == 120)
        else:
            assert safe_fetch(PUBLIC).content == b"ok"
        assert route.call_count == requests
    assert sleeps == ([3] if requests == 2 else [])


def test_retry_only_once_without_using_redirect_hop(resolve, monkeypatch):
    monkeypatch.setattr("catchup.net.safe_fetch.sleep", lambda _seconds: None)
    with respx.mock(assert_all_mocked=True) as router:
        limited = router.get(PUBLIC).mock(side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(302, headers={"location": "/next"}),
        ])
        router.get("https://public.example/next").mock(return_value=httpx.Response(200, content=b"ok"))
        budget = [3]
        assert safe_fetch(PUBLIC, budget=budget, same_origin="https://public.example").content == b"ok"
        assert limited.call_count == 2
        assert budget == [0]

    with respx.mock(assert_all_mocked=True) as router:
        limited = router.get(PUBLIC).mock(return_value=httpx.Response(429, headers={"Retry-After": "0"}))
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
        assert error.value.code == "rate_limited"
        assert limited.call_count == 2


def test_retry_requires_budget_and_deadline(resolve, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("catchup.net.safe_fetch.monotonic", lambda: clock[0])
    monkeypatch.setattr("catchup.net.safe_fetch.sleep", lambda _seconds: pytest.fail("unexpected sleep"))
    with respx.mock(assert_all_mocked=True) as router:
        def short_deadline(_request):
            clock[0] = 127.0
            return httpx.Response(429, headers={"Retry-After": "3"})

        route = router.get(PUBLIC).mock(side_effect=short_deadline)
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
        assert error.value.code == "rate_limited"
        assert error.value.retry_after == 3
        assert route.call_count == 1
    clock[0] = 100.0
    monkeypatch.setattr("catchup.net.safe_fetch.sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(PUBLIC).mock(return_value=httpx.Response(429, headers={"Retry-After": "3"}))
        with pytest.raises(FetchError, match="request limit"):
            safe_fetch(PUBLIC, budget=[1])
        assert route.call_count == 1
