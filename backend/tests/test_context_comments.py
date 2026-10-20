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


def test_sibling_wordpress_thread_resolves_parent_comment():
    html = page(
        "<div id='comment-1' class='comment'><span class='fn'>Reader</span>"
        "<div class='comment-content'>A reader question.</div></div>"
        "<ul class='children'><div id='comment-2' class='comment bypostauthor'>"
        "<span class='fn'>Writer</span>"
        "<div class='comment-content'>The author's answer.</div></div></ul>"
    )
    assert author_replies(html, "Writer") == [
        "In reply to: A reader question.\nThe author's answer.",
    ]


def test_top_level_author_self_link_is_not_a_parent():
    html = page(
        "<div id='comment-2' class='comment bypostauthor'>"
        "<span class='fn'>Writer</span><a href='#comment-2'>Permalink</a>"
        "<div class='comment-content'>Original thought.</div></div>"
    )
    assert author_replies(html, "Writer") == ["Original thought."]


def test_nested_reply_anchor_does_not_supply_parent_for_top_level_author():
    html = page(
        "<li id='comment-2' class='comment bypostauthor'>"
        "<span class='fn'>Writer</span>"
        "<div class='comment-content'>Original thought.</div>"
        "<ol><li id='comment-3' class='comment'>"
        "<span class='fn'>Reader</span><a href='#comment-9'>In reply to another reader</a>"
        "<div class='comment-content'>Separate question.</div></li></ol></li>",
        comment("comment-9", "Other reader", "An unrelated parent."),
    )
    assert author_replies(html, "Writer") == ["Original thought."]


def test_entry_author_whitespace_is_normalized_for_comment_names():
    html = page(comment("one", "Terence Tao", "A reply."))
    assert author_replies(html, "Terence  Tao") == ["A reply."]


def test_reply_count_cap_keeps_exactly_ten_short_replies():
    html = page(*(comment(str(i), "Writer", f"Reply {i}", classes="bypostauthor")
                  for i in range(12)))
    assert author_replies(html, "Writer") == [f"Reply {i}" for i in range(10)]


def test_reply_character_cap_keeps_exactly_four_thousand():
    html = page(*(comment(str(i), "Writer", "A" * 600, classes="bypostauthor")
                  for i in range(6)), comment("last", "Writer", "B" * 500, classes="bypostauthor"))
    replies = author_replies(html, "Writer")
    assert len("\n\n".join(replies)) == 4000
    assert replies[-1] == "B" * 388


def test_feed_fallback_limits_input_to_ten_entries(monkeypatch):
    # Isolate the feed's input cap from the independent output cap in _bounded.
    monkeypatch.setattr("catchup.context.comments._bounded", lambda replies: replies)
    feed = ("<rss><channel>" + "".join(
        f"<item><title>By: Writer</title><author>Writer</author><description>Reply {i}</description></item>"
        for i in range(11)
    ) + "</channel></rss>").encode()
    assert author_replies(page(), "Writer", feed) == [f"Reply {i}" for i in range(10)]
