import socket
import ssl
from datetime import datetime, timezone
from threading import Thread
from types import SimpleNamespace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from catchup.config import Settings
from catchup.main import create_app
from catchup.net.safe_fetch import FetchError, MAX_BYTES, parse_retry_after, safe_fetch

PUBLIC = "https://public.example/feed"
REAL_CONNECT = socket.socket.connect


def _dns_answers(addresses, port):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
            for address in addresses]


@pytest.fixture
def failed_connections(monkeypatch):
    addresses = []

    def connect(address, *args, **kwargs):
        addresses.append(address)
        raise OSError("connection failed")

    monkeypatch.setattr(socket, "create_connection", connect)
    return addresses


def test_connection_rejects_dns_rebinding(monkeypatch, failed_connections):
    lookups = []

    def lookup(host, port, *args, **kwargs):
        lookups.append(host)
        return _dns_answers(["8.8.8.8" if len(lookups) == 1 else "127.0.0.1"], port)

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert (error.value.code, str(error.value), failed_connections) == (
        "blocked_address", "The source address is not allowed.", [],
    )


def test_connection_uses_checked_address(monkeypatch, failed_connections):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *args, **kwargs: _dns_answers(["8.8.8.8"], port))
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert failed_connections == [("8.8.8.8", 80)]
    assert error.value.code == "fetch_failed"
    assert str(error.value) == "The source could not be fetched."


def test_connection_tries_checked_answers_in_order(monkeypatch):
    addresses = []
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, port, *args, **kwargs: _dns_answers(["8.8.8.8", "8.8.4.4"], port))

    def connect(address, *args, **kwargs):
        addresses.append(address)
        if address[0] == "8.8.8.8":
            raise TimeoutError("connection timed out")
        raise OSError("connection failed")

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert addresses == [("8.8.8.8", 80), ("8.8.4.4", 80)]
    assert error.value.code == "fetch_failed"
    assert str(error.value) == "The source could not be fetched."


def test_connection_https_keeps_hostname_and_certificate_checks(monkeypatch):
    addresses = []
    tls = []
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *args, **kwargs: _dns_answers(["8.8.8.8"], port))
    with socket.socket() as sock:
        def connect(address, *args, **kwargs):
            addresses.append(address)
            return sock

        def wrap(self, sock, *args, **kwargs):
            tls.append((kwargs["server_hostname"], self.verify_mode == ssl.CERT_REQUIRED, self.check_hostname))
            raise ssl.SSLError("TLS failed")

        monkeypatch.setattr(socket, "create_connection", connect)
        monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap)
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
    assert addresses == [("8.8.8.8", 443)]
    assert tls == [("public.example", True, True)]
    assert error.value.code == "fetch_failed"


def test_connection_response_through_checked_address_keeps_host(monkeypatch):
    addresses = []
    requests = []
    server_errors = []
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *args, **kwargs: _dns_answers(["8.8.8.8"], port))
    monkeypatch.setattr(socket.socket, "connect", REAL_CONNECT)
    with socket.socket() as listener:
        listener.settimeout(2)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)

        def serve():
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    request = bytearray()
                    while b"\r\n\r\n" not in request:
                        chunk = connection.recv(4096)
                        if not chunk:
                            break
                        request.extend(chunk)
                    requests.append(bytes(request))
                    connection.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Length: 6\r\nConnection: close\r\n\r\npinned",
                    )
            except OSError as exc:
                server_errors.append(exc)

        def connect(address, *args, **kwargs):
            addresses.append(address)
            sock = socket.socket()
            try:
                sock.settimeout(2)
                sock.connect(listener.getsockname())
            except BaseException:
                sock.close()
                raise
            return sock

        monkeypatch.setattr(socket, "create_connection", connect)
        server = Thread(target=serve, daemon=True)
        server.start()
        try:
            assert safe_fetch("http://public.example/feed").content == b"pinned"
        finally:
            server.join(timeout=3)
        assert not server.is_alive()
    assert not server_errors
    assert addresses == [("8.8.8.8", 80)]
    assert len(requests) == 1
    assert b"Host: public.example" in requests[0].split(b"\r\n")


def test_connection_reports_unresolvable_host(monkeypatch, failed_connections):
    lookups = []

    def lookup(host, port, *args, **kwargs):
        lookups.append(host)
        if len(lookups) > 1:
            raise socket.gaierror("host not found")
        return _dns_answers(["8.8.8.8"], port)

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert (error.value.code, str(error.value), failed_connections) == (
        "fetch_failed", "The source host could not be resolved.", [],
    )


def test_connection_rejects_mixed_dns_answers(monkeypatch, failed_connections):
    lookups = []

    def lookup(host, port, *args, **kwargs):
        lookups.append(host)
        addresses = ["8.8.8.8"] if len(lookups) == 1 else ["8.8.8.8", "10.0.0.1"]
        return _dns_answers(addresses, port)

    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert (error.value.code, failed_connections) == ("blocked_address", [])


def test_connection_uses_the_answer_it_checked(monkeypatch, failed_connections):
    answers = iter([["8.8.8.8"], ["8.8.8.8"]])
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, port, *args, **kwargs: _dns_answers(next(answers, ["127.0.0.1"]), port))
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert (error.value.code, failed_connections) == ("fetch_failed", [("8.8.8.8", 80)])


def test_connection_tries_next_answer_after_refusal_with_connect_timeout(monkeypatch):
    calls = []
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda host, port, *args, **kwargs: _dns_answers(["8.8.8.8", "8.8.4.4"], port))

    def connect(address, timeout=None, *args, **kwargs):
        calls.append((address, timeout))
        raise (OSError if address[0] == "8.8.8.8" else TimeoutError)("connection failed")

    monkeypatch.setattr(socket, "create_connection", connect)
    with pytest.raises(FetchError) as error:
        safe_fetch("http://public.example/feed")
    assert calls == [(("8.8.8.8", 80), 5.0), (("8.8.4.4", 80), 5.0)]
    assert (error.value.code, str(error.value)) == ("fetch_failed", "The source fetch timed out.")


def test_address_check_runs_before_budget_and_spacing(resolve):
    resolve["public.example"] = ["127.0.0.1"]
    budget = [1]

    class Spacer:
        def wait(self, _url):
            pytest.fail("spacing waited before the address check")

    with pytest.raises(FetchError) as error:
        safe_fetch(PUBLIC, budget=budget, spacer=Spacer())
    assert (error.value.code, budget) == ("blocked_address", [1])


def test_refuses_to_fetch_when_the_connect_check_cannot_be_installed(resolve, monkeypatch, failed_connections):
    class Transport(httpx.HTTPTransport):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._pool = SimpleNamespace()

    monkeypatch.setattr(httpx, "HTTPTransport", Transport)
    with pytest.raises(RuntimeError, match="address check"):
        safe_fetch(PUBLIC)
    assert failed_connections == []


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


@pytest.mark.parametrize("url", ["https://x.com/a", "https://help.x.com./en"])
def test_x_host_is_blocked_before_dns(url):
    with pytest.raises(FetchError) as error:
        safe_fetch(url)
    assert error.value.code == "blocked_address"
    assert str(error.value) == "X pages are read only through the X API."


def test_redirect_to_x_is_blocked_before_request(resolve):
    resolve["x.com"] = ["8.8.4.4"]
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        first = router.get(PUBLIC).mock(side_effect=[
            httpx.Response(301, headers={"location": "https://x.com/someone/status/1"}),
            AssertionError("unexpected second request to public feed"),
        ])
        x_page = router.get("https://x.com/someone/status/1").mock(
            side_effect=AssertionError("X page must never be fetched"))
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
        assert first.call_count == 1
        assert x_page.call_count == 0
    assert error.value.code == "blocked_address"


def test_redirect_to_unparseable_location_is_invalid_url(resolve):
    with respx.mock(assert_all_mocked=True) as router:
        router.get(PUBLIC).mock(side_effect=[
            httpx.Response(301, headers={"location": "http://[abc/feed"}),
            AssertionError("unexpected second request to public feed"),
        ])
        with pytest.raises(FetchError) as error:
            safe_fetch(PUBLIC)
    assert error.value.code == "invalid_url"


def test_unparseable_current_url_is_invalid_url():
    with pytest.raises(FetchError) as error:
        safe_fetch("http://[abc/feed")
    assert error.value.code == "invalid_url"


def test_url_httpx_rejects_is_invalid_url_without_a_request(resolve):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.route(host="public.example").mock(
            side_effect=AssertionError("a URL httpx rejects must not be requested"),
        )
        with pytest.raises(FetchError) as error:
            safe_fetch("https://public.example/a\x7fb")
        assert route.call_count == 0
    assert error.value.code == "invalid_url"
    assert str(error.value) == "Enter a valid public HTTP or HTTPS URL."


def test_preview_of_url_httpx_rejects_is_invalid_url(resolve):
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.route(host="public.example").mock(
            side_effect=AssertionError("a URL httpx rejects must not be requested"),
        )
        with TestClient(create_app()) as client:
            response = client.post("/api/sources/preview", json={"url": "https://public.example/a\x7fb"})
        assert route.call_count == 0
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "invalid_url", "message": "Enter a valid public HTTP or HTTPS URL.",
    }


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
