"""Run-local robots.txt decisions for public context fetches."""

from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from catchup.net.safe_fetch import FetchError, safe_fetch


class RobotsCache:
    def __init__(self, *, budget: list[int], spacer=None):
        self.budget = budget
        self.spacer = spacer
        self._rules: dict[str, RobotFileParser | bool] = {}

    def allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._rules:
            if self.budget[0] <= 0:
                return False
            try:
                response = safe_fetch(
                    f"{origin}/robots.txt", budget=self.budget, spacer=self.spacer,
                    max_bytes=512 * 1024,
                )
                parser = RobotFileParser()
                parser.parse(response.content.decode("utf-8", errors="replace").splitlines())
                self._rules[origin] = parser
            except FetchError as exc:
                self._rules[origin] = exc.status_code not in (401, 403)
        rule = self._rules[origin]
        return rule if isinstance(rule, bool) else rule.can_fetch("CatchUp", url)
