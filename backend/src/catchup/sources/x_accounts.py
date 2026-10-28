"""Recognize public X profile and post addresses before feed discovery."""

import re
from collections import OrderedDict
from dataclasses import asdict
from threading import Lock
from time import monotonic
from typing import Callable
from urllib.parse import urlsplit

from catchup.errors import AppError
from catchup.models import Item
from catchup.sources.feeds import EntryImage, _entry_title, filter_image_urls
from catchup.sources.x_api import XPage, XPost, XUser


RESERVED = {
    "home", "explore", "search", "i", "settings", "notifications", "messages",
    "compose", "login", "logout", "signup", "tos", "privacy", "hashtag", "intent",
    "share", "account", "jobs",
}
USERNAME = re.compile(r"[A-Za-z0-9_]{1,15}\Z")
HOSTS = {"x.com", "twitter.com", "www.x.com", "www.twitter.com", "mobile.x.com",
         "mobile.twitter.com"}


def is_x_host(host: str | None) -> bool:
    return bool(host and any(host == domain or host.endswith("." + domain)
                             for domain in ("x.com", "twitter.com")))


def x_username(url: str) -> str | None:
    try:
        parts = urlsplit(url)
        host = parts.hostname
        if not is_x_host(host):
            return None
    except ValueError:
        return None
    if host not in HOSTS:
        raise AppError("not_an_x_account", "This is not an X account address.", 422)
    first = parts.path.strip("/").split("/", 1)[0]
    if not USERNAME.fullmatch(first) or first.lower() in RESERVED:
        raise AppError("not_an_x_account", "This is not an X account address.", 422)
    return first


class XPreviewCache:
    def __init__(self, *, ttl: float = 600, max_entries: int = 50,
                 clock: Callable[[], float] = monotonic):
        self.ttl = ttl
        self.max_entries = max_entries
        self.clock = clock
        self._lock = Lock()
        self._entries: OrderedDict[str, tuple[float, XUser, XPage]] = OrderedDict()

    def put(self, feed_url: str, user: XUser, page: XPage) -> None:
        with self._lock:
            self._entries.pop(feed_url, None)
            self._entries[feed_url] = (self.clock(), user, page)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def pop(self, feed_url: str) -> tuple[XUser, XPage] | None:
        with self._lock:
            entry = self._entries.pop(feed_url, None)
            if entry is None or self.clock() - entry[0] >= self.ttl:
                return None
            return entry[1], entry[2]


def post_item(post: XPost, *, source_id: int, user: XUser, replies: list[str] | None = None) -> Item:
    link = f"https://x.com/{user.username}/status/{post.id}"
    images = filter_image_urls([
        EntryImage(photo.url, alt=photo.alt, origin="html") for photo in post.photos
    ])
    return Item(
        source_id=source_id, identity_key=post.id, link=link,
        title=_entry_title("", post.text), published_at=post.created_at,
        content_text=post.text[:16000], content_origin="x", state="pending",
        site_name=f"X · {user.name}"[:200], entry_author=f"{user.name} @{user.username}",
        entry_links=[{"url": url, "text": ""} for url in post.urls],
        image_candidates=[asdict(image) for image in images],
        captured_replies=replies,
    )
