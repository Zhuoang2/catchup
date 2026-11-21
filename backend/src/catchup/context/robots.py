"""Run-local robots.txt decisions for public context fetches."""

from threading import Lock
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from catchup.net.safe_fetch import BudgetExhausted, FetchError, safe_fetch


def origin(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname
    if parts.scheme not in ("http", "https") or not host or parts.username or parts.password:
        raise ValueError("invalid URL")
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    suffix = f":{port}" if port is not None and port != {"http": 80, "https": 443}[parts.scheme] else ""
    return f"{parts.scheme}://{host}{suffix}"


class RobotsCache:
    def __init__(self, *, budget: list[int], spacer=None):
        self.budget = budget
        self.spacer = spacer
        self._rules: dict[str, RobotFileParser | bool] = {}
        self._lock = Lock()
        self._origins: dict[str, Lock] = {}

    def verdict(self, url: str) -> bool | None:
        rule = self._rules.get(origin(url))
        return rule if rule is None or isinstance(rule, bool) else rule.can_fetch("CatchUp", url)

    def allowed(self, url: str) -> bool:
        stored = self.verdict(url)
        if stored is not None:
            return stored
        key = origin(url)
        with self._lock:
            lock = self._origins.setdefault(key, Lock())
        with lock:
            stored = self.verdict(url)
            if stored is not None:
                return stored
            if self.budget[0] <= 0:
                raise BudgetExhausted()
            try:
                response = safe_fetch(
                    f"{key}/robots.txt", budget=self.budget, spacer=self.spacer,
                    max_bytes=512 * 1024,
                )
                parser = RobotFileParser()
                parser.parse(response.content.decode("utf-8", errors="replace").splitlines())
                self._rules[key] = parser
            except BudgetExhausted:
                raise
            except FetchError as exc:
                self._rules[key] = exc.status_code is not None and 400 <= exc.status_code < 500 and exc.status_code not in (401, 403)
        return self.verdict(url)
