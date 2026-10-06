"""Short-lived, per-application feed responses for preview-to-confirm reuse."""

from collections import OrderedDict
from threading import Lock
from time import monotonic
from typing import Callable

from catchup.net.safe_fetch import FetchResponse, MAX_BYTES


class FeedCache:
    def __init__(self, *, ttl: float = 600, max_entries: int = 50,
                 clock: Callable[[], float] = monotonic):
        self.ttl = ttl
        self.max_entries = max_entries
        self.clock = clock
        self._lock = Lock()
        self._entries: OrderedDict[str, tuple[float, FetchResponse]] = OrderedDict()

    def put(self, response: FetchResponse) -> None:
        if len(response.content) > MAX_BYTES:
            return
        with self._lock:
            self._entries.pop(response.url, None)
            self._entries[response.url] = (self.clock(), response)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def pop(self, url: str) -> FetchResponse | None:
        with self._lock:
            entry = self._entries.pop(url, None)
            if entry is None or self.clock() - entry[0] >= self.ttl:
                return None
            return entry[1]
