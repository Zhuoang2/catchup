from catchup.net.feed_cache import FeedCache
from catchup.net.safe_fetch import FetchResponse


def response(index: int) -> FetchResponse:
    return FetchResponse(f"https://site.example/{index}", b"<rss/>", "application/rss+xml", 200)


def test_cache_ttl_and_single_use():
    now = [0.0]
    cache = FeedCache(clock=lambda: now[0])
    cache.put(response(1))
    assert cache.pop(response(1).url) == response(1)
    assert cache.pop(response(1).url) is None
    cache.put(response(1))
    now[0] = 600
    assert cache.pop(response(1).url) is None


def test_cache_eviction_is_oldest_entry():
    cache = FeedCache()
    for index in range(51):
        cache.put(response(index))
    assert cache.pop(response(0).url) is None
    assert cache.pop(response(1).url) == response(1)
    assert cache.pop(response(50).url) == response(50)
