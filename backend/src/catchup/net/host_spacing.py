"""Space requests to each host for the lifetime of a digest run."""

from threading import Lock
from time import monotonic, sleep as _sleep
from typing import Callable
from urllib.parse import urlsplit


class HostSpacer:
    def __init__(self, *, min_interval: float = 1.0, clock: Callable[[], float] | None = None,
                 sleep: Callable[[float], None] | None = None):
        self.min_interval = min_interval
        self.clock = clock or monotonic
        self.sleep = sleep or _sleep
        self._lock = Lock()
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = (urlsplit(url).hostname or "").lower()
        with self._lock:
            now = self.clock()
            last = self._last.get(host)
            if last is not None:
                delay = max(0.0, self.min_interval - (now - last))
                if delay:
                    self.sleep(delay)
            self._last[host] = self.clock()
