import pytest

from catchup.errors import AppError
from catchup.sources.x_accounts import is_x_host, x_username


@pytest.mark.parametrize("host", ["x.com.", "help.x.com.", "twitter.com.", "X.COM"])
def test_fully_qualified_and_case_insensitive_x_hosts(host):
    assert is_x_host(host)


@pytest.mark.parametrize("host", ["notx.com", "x.com.example.org"])
def test_lookalike_hosts_are_not_x_hosts(host):
    assert not is_x_host(host)


def test_fully_qualified_x_account_address():
    assert x_username("https://x.com./simonw") == "simonw"


@pytest.mark.parametrize("url", ["https://x.com./home", "https://help.x.com./en"])
def test_fully_qualified_x_pages_are_not_accounts(url):
    with pytest.raises(AppError) as error:
        x_username(url)
    assert error.value.code == "not_an_x_account"


@pytest.mark.parametrize(("url", "username"), [
    ("https://x.com/simonw", "simonw"),
    ("https://www.x.com/simonw/", "simonw"),
    ("https://mobile.x.com/simonw/media", "simonw"),
    ("https://twitter.com/simonw/status/123", "simonw"),
    ("http://x.com/Simon_W", "Simon_W"),
])
def test_account_addresses_identify_first_path_segment(url, username):
    assert x_username(url) == username


@pytest.mark.parametrize("url", [
    "https://x.com/home", "https://x.com/i/lists/1", "https://x.com/search?q=a",
    "https://twitter.com/HOME", "https://x.com/", "https://x.com/abcdefghijklmnop",
])
def test_x_pages_and_invalid_usernames_are_not_accounts(url):
    with pytest.raises(AppError) as error:
        x_username(url)
    assert error.value.code == "not_an_x_account"
    assert error.value.status_code == 422


@pytest.mark.parametrize("url", ["https://example.com/simonw", "https://notx.com/simonw"])
def test_non_x_addresses_keep_feed_discovery(url):
    assert x_username(url) is None


@pytest.mark.parametrize("url", [
    "https://help.x.com/en", "https://developer.x.com/", "https://api.twitter.com/2",
])
def test_other_x_owned_hosts_are_not_accounts(url):
    with pytest.raises(AppError) as error:
        x_username(url)
    assert error.value.code == "not_an_x_account"


@pytest.mark.parametrize("url", ["https://x.com.example.org/simonw", "https://notx.com/simonw"])
def test_lookalike_x_hosts_remain_non_x(url):
    assert x_username(url) is None
