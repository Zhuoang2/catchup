import socket

import httpx
import pytest
import respx

from catchup.net.safe_fetch import FetchError, MAX_BYTES, safe_fetch

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
