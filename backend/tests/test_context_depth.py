from dataclasses import replace

import pytest

from catchup.context.depth import LINK_DEPTHS, ContextLimits, context_limits, link_depth_pages


def test_link_depths():
    assert LINK_DEPTHS == ("off", "shallow", "normal")


@pytest.mark.parametrize(
    "level,links_per_item,context_fetches_per_run,author_replies,expected",
    [
        ("off", 8, 60, True, ContextLimits(0, 0, False, 3000, 16000)),
        ("shallow", 8, 60, True, ContextLimits(3, 60, True, 3000, 16000)),
        ("shallow", 2, 60, True, ContextLimits(2, 60, True, 3000, 16000)),
        ("shallow", 8, 60, False, ContextLimits(3, 60, False, 3000, 16000)),
        ("normal", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000)),
        ("normal", 5, 40, False, ContextLimits(5, 40, False, 3000, 16000)),
        ("deep", 8, 60, True, ContextLimits(16, 120, True, 6000, 32000)),
        ("deep", 5, 40, True, ContextLimits(10, 80, True, 6000, 32000)),
        ("deep", 8, 60, False, ContextLimits(16, 120, False, 6000, 32000)),
        ("maximum", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000)),
        ("", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000)),
    ],
    ids=["off", "shallow", "shallow_under_2", "shallow_no_replies", "normal",
         "normal_server", "deep", "deep_server", "deep_no_replies", "unknown", "empty"],
)
def test_context_limits(test_settings, level, links_per_item, context_fetches_per_run,
                        author_replies, expected):
    settings = replace(test_settings, links_per_item=links_per_item,
                       context_fetches_per_run=context_fetches_per_run,
                       author_replies=author_replies)
    assert context_limits(level, settings) == expected


@pytest.mark.parametrize("links_per_item,expected", [
    (8, {"off": 0, "shallow": 3, "normal": 8}),
    (5, {"off": 0, "shallow": 3, "normal": 5}),
    (2, {"off": 0, "shallow": 2, "normal": 2}),
    (1, {"off": 0, "shallow": 1, "normal": 1}),
])
def test_link_depth_pages(test_settings, links_per_item, expected):
    assert link_depth_pages(replace(test_settings, links_per_item=links_per_item)) == expected
