import socket

import pytest

from catchup.config import Settings


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CATCHUP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CATCHUP_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
    monkeypatch.delenv("CATCHUP_SECRET_KEY", raising=False)

    def no_network(*_args, **_kwargs):
        raise AssertionError("Tests must mock DNS and network connections")

    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    # Tests with meaningful delays inject clocks; all other sleeps stay virtual.
    monkeypatch.setattr("catchup.net.host_spacing._sleep", lambda _seconds: None)
    monkeypatch.setattr("catchup.net.safe_fetch.sleep", no_network)


@pytest.fixture
def test_settings() -> Settings:
    return Settings.from_env()
