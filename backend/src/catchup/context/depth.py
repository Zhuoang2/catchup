"""Resolve the linked-page level against the server's context settings."""

from dataclasses import dataclass

from catchup.config import Settings


LINK_DEPTHS = ("off", "shallow", "normal")
SHALLOW_LINKS = 3


@dataclass(frozen=True)
class ContextLimits:
    links_per_item: int
    fetches_per_run: int
    author_replies: bool


def context_limits(level: str, settings: Settings) -> ContextLimits:
    if level == "off":
        return ContextLimits(0, 0, False)
    links = min(SHALLOW_LINKS, settings.links_per_item) if level == "shallow" else settings.links_per_item
    return ContextLimits(links, settings.context_fetches_per_run, settings.author_replies)


def link_depth_pages(settings: Settings) -> dict[str, int]:
    return {"off": 0, "shallow": min(SHALLOW_LINKS, settings.links_per_item),
            "normal": settings.links_per_item}
