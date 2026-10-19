from catchup.context.links import related_links
from catchup.sources.feeds import EntryLink


ITEM = "https://site.example/posts/one"
SITE = "https://site.example/"


def test_filters_navigation_share_login_media_and_non_http_but_keeps_discussions():
    rejected = [
        ITEM + "/#comments", "https://site.example/tags/python",
        "https://site.example/tag/python", "https://site.example/category/news",
        "https://site.example/categories/news", "https://site.example/author/name",
        "https://site.example/page/2", "https://site.example/search?q=hello",
        "https://site.example/archive/2026", "https://claude.ai/code/thread",
        "https://chatgpt.com/share/abc", "https://site.example/share?post=1",
        "https://site.example/login", "https://x.com/user/status/1",
        "https://twitter.com/user", "https://mobile.twitter.com/user",
        "https://docs.example/chart.png", "https://docs.example/report.pdf",
        "mailto:me@site.example", "javascript:alert(1)",
    ]
    accepted = "https://news.ycombinator.com/item?id=123"
    links = [EntryLink(url, str(index)) for index, url in enumerate(rejected + [accepted])]
    assert related_links(ITEM, SITE, links, 8) == [links[-1]]


def test_keeps_body_order_and_applies_limit_after_filtering():
    links = [
        EntryLink("https://site.example/tags/news", "Tag"),
        EntryLink("https://github.com/example/tool/releases/tag/v1", "Release"),
        EntryLink("https://site.example/project", "Project"),
        EntryLink("https://docs.example/changelog", "Changelog"),
        EntryLink("https://site.example/tags/tools", "Tools"),
    ]
    assert related_links(ITEM, SITE, links, 8) == links[1:4]
    assert related_links(ITEM, SITE, links, 2) == links[1:3]
