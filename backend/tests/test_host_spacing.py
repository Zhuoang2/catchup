import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
import respx

from catchup.net.host_spacing import HostSpacer
from catchup.net.safe_fetch import safe_fetch


def test_other_hosts_do_not_wait_while_one_host_sleeps():
    entered, release = threading.Event(), threading.Event()

    def blocking_sleep(_seconds):
        entered.set()
        assert release.wait(timeout=5)

    spacer = HostSpacer(min_interval=1.0, sleep=blocking_sleep)
    spacer.wait("https://a.example/1")
    first = threading.Thread(target=spacer.wait, args=("https://a.example/2",))
    other = threading.Thread(target=spacer.wait, args=("https://b.example/1",))
    first.start()
    try:
        assert entered.wait(timeout=5)
        other.start()
        other.join(timeout=1)
        assert not other.is_alive()
        assert not release.is_set()
    finally:
        release.set()
        first.join(timeout=5)
        if other.ident is not None:
            other.join(timeout=5)


def test_same_host_waits_are_spaced_across_threads():
    spacer = HostSpacer(min_interval=0.2, sleep=time.sleep)
    barrier = threading.Barrier(3)

    def wait(_index):
        barrier.wait(timeout=5)
        spacer.wait("https://h.example/x")
        return time.monotonic()

    with ThreadPoolExecutor(max_workers=3) as pool:
        times = sorted(pool.map(wait, range(3)))
    assert all(later - earlier >= 0.19 for earlier, later in zip(times, times[1:]))


@pytest.fixture
def resolve(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda _host, port, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
    ])


def test_host_spacing_case_insensitive_and_independent():
    now = [10.0]
    sleeps = []

    def advance(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    spacer = HostSpacer(clock=lambda: now[0], sleep=advance)
    spacer.wait("https://Site.Example/first")
    spacer.wait("https://other.example/feed")
    assert sleeps == []
    now[0] += 0.25
    spacer.wait("https://site.example/second")
    assert sleeps == [0.75]
    spacer.wait("https://OTHER.EXAMPLE/second")
    assert sleeps == [0.75]


def test_fetch_uses_spacer_for_redirect_and_retry(resolve, monkeypatch):
    now = [0.0]
    sleeps = []

    def advance(seconds):
        now[0] += seconds
        sleeps.append(seconds)

    spacer = HostSpacer(clock=lambda: now[0], sleep=advance)
    monkeypatch.setattr("catchup.net.safe_fetch.sleep", advance)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://public.example/feed").mock(return_value=httpx.Response(
            302, headers={"location": "/next"},
        ))
        router.get("https://public.example/next").mock(side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200),
        ])
        assert safe_fetch("https://public.example/feed", spacer=spacer).status_code == 200
    assert sleeps == [1.0, 1.0]
