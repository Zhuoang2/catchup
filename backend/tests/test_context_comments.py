from catchup.context.comments import author_replies


def page(*comments: str) -> bytes:
    return ("<html><body><ol class='comment-list'>" + "".join(comments) + "</ol></body></html>").encode()


def comment(ident: str, author: str, text: str, *, classes: str = "", children: str = "") -> str:
    return (f"<li id='{ident}' class='comment {classes}'><span class='fn'>{author}</span>"
            f"<div class='comment-content'><p>{text}</p></div><ol>{children}</ol></li>")


def test_marked_author_replies_include_parent_text():
    html = page(
        comment("one", "Reader One", "Why was this changed?", children=comment(
            "two", "Writer", "The API changed.", classes="bypostauthor",
        )),
        comment("three", "Reader Two", "Is it stable?", children=comment(
            "four", "Writer", "Yes, it is stable.", classes="bypostauthor",
        )),
        comment("five", "Reader", "Unrelated", children=comment("six", "Other", "Not the author.")),
    )
    assert author_replies(html, "Writer") == [
        "In reply to: Why was this changed?\nThe API changed.",
        "In reply to: Is it stable?\nYes, it is stable.",
    ]


def test_author_name_matches_when_no_marked_comment():
    html = page(comment("one", "Reader", "Question", children=comment(
        "two", "Writer", "My answer.",
    )))
    assert author_replies(html, "Writer") == ["In reply to: Question\nMy answer."]


def test_comment_feed_fallback_skips_pingbacks_and_other_authors():
    feed = (b"<rss version='2.0' xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            b"<channel><item><title>By: Writer</title><dc:creator>Writer</dc:creator>"
            b"<description>Additional detail.</description></item>"
            b"<item><title>Pingback: Example</title><dc:creator>Writer</dc:creator>"
            b"<description>A mention.</description></item>"
            b"<item><title>By: Reader</title><dc:creator>Reader</dc:creator>"
            b"<description>Not mine.</description></item></channel></rss>")
    assert author_replies(page(), "Writer", feed) == ["Additional detail."]


def test_reply_limits_ten_and_four_thousand_chars_with_six_hundred_per_text():
    html = page(*(comment(str(i), "Writer", "A" * 700, classes="bypostauthor")
                  for i in range(20)))
    replies = author_replies(html, "Writer")
    assert len(replies) <= 10
    assert len("\n\n".join(replies)) <= 4000
    assert all(len(reply) <= 600 for reply in replies)


def test_no_author_replies_returns_empty():
    assert author_replies(page(comment("one", "Reader", "Nothing from the author.")), "Writer") == []
