"""Extract server-rendered author replies and their reader context."""

import feedparser
from lxml import html


def _text(element) -> str:
    if element is None:
        return ""
    return " ".join(" ".join(element.itertext()).split())[:600]


def _name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _bounded(replies: list[str]) -> list[str]:
    result = []
    for reply in replies[:10]:
        remaining = 4000 - len("\n\n".join(result)) - (2 if result else 0)
        if remaining <= 0:
            break
        result.append(reply[:remaining])
    return result


def author_replies(page: bytes, author: str | None, feed: bytes | None = None) -> list[str]:
    try:
        tree = html.fromstring(page)
        comments = tree.xpath(
            "//*[self::li or self::div][contains(concat(' ', normalize-space(@class), ' '), ' comment ')]"
        )
    except (ValueError, TypeError, html.ParserError):
        comments = []
    if comments:
        def within(node, selector):
            return [element for element in node.xpath(selector)
                    if next((ancestor for ancestor in element.iterancestors() if ancestor in comments), None) is node]

        content_selector = (
            ".//*[contains(concat(' ', normalize-space(@class), ' '), ' comment-content ')]"
        )
        marked = [
            node for node in comments
            if "bypostauthor" in (node.get("class") or "").split()
        ]
        selected = marked or [
            node for node in comments if author and (
                any(cls.startswith("comment-author-") and _name(cls[len("comment-author-"):]) == _name(author)
                    for cls in (node.get("class") or "").split())
                or any(_name(_text(name)) == _name(author) for name in within(node,
                    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' fn ')]"
                ))
            )
        ]
        replies = []
        for node in selected:
            body = within(node, content_selector)
            if not body:
                continue
            parent = next((
                ancestor for ancestor in node.iterancestors()
                if ancestor in comments
            ), None)
            if parent is None:
                for ancestor in node.iterancestors():
                    if ancestor.tag not in ("ol", "ul") or "children" not in (ancestor.get("class") or "").split():
                        continue
                    sibling = ancestor.getprevious()
                    while sibling is not None and sibling not in comments:
                        sibling = sibling.getprevious()
                    if sibling is not None:
                        parent = sibling
                        break
            if parent is None:
                for anchor in node.xpath(".//a[starts-with(@href, '#')]"):
                    target = tree.xpath("//*[@id=$ident]", ident=anchor.get("href", "")[1:])
                    if target and target[0] in comments and target[0] is not node:
                        parent = target[0]
                        break
            previous = within(parent, content_selector) if parent is not None else []
            prefix = f"In reply to: {_text(previous[0])}\n" if previous else ""
            replies.append(prefix + _text(body[0]))
        return _bounded(replies)
    if not feed or not author:
        return []
    parsed = feedparser.parse(feed)
    return _bounded([
        _text(html.fromstring(entry.get("summary", "")))
        for entry in parsed.entries[:10]
        if _name(entry.get("author") or "") == _name(author)
        and "pingback" not in (entry.get("title", "") + " " + entry.get("summary", "")).casefold()
        and entry.get("summary")
    ])
