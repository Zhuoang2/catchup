"""Resolve the linked-page level against the server's context settings."""

from dataclasses import dataclass

from catchup.config import Settings


LINK_DEPTHS = ("off", "shallow", "normal", "deep")
SHALLOW_LINKS = 3
DEEP_FACTOR = 2
PAGE_CHARS = 3_000
ITEM_CHARS = 16_000
DEEP_PAGE_CHARS = 6_000
DEEP_ITEM_CHARS = 32_000


@dataclass(frozen=True)
class ContextLimits:
    links_per_item: int
    fetches_per_run: int
    author_replies: bool
    page_chars: int = PAGE_CHARS
    item_chars: int = ITEM_CHARS


def context_limits(level: str, settings: Settings) -> ContextLimits:
    if level == "off":
        return ContextLimits(0, 0, False)
    if level == "deep":
        return ContextLimits(
            DEEP_FACTOR * settings.links_per_item,
            DEEP_FACTOR * settings.context_fetches_per_run,
            settings.author_replies,
            DEEP_PAGE_CHARS,
            DEEP_ITEM_CHARS,
        )
    links = min(SHALLOW_LINKS, settings.links_per_item) if level == "shallow" else settings.links_per_item
    return ContextLimits(links, settings.context_fetches_per_run, settings.author_replies)


def link_depth_pages(settings: Settings) -> dict[str, int]:
    return {"off": 0, "shallow": min(SHALLOW_LINKS, settings.links_per_item),
            "normal": settings.links_per_item, "deep": DEEP_FACTOR * settings.links_per_item}
