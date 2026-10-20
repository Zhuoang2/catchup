import socket
from dataclasses import replace

import httpx
import pytest
import respx
from sqlalchemy import select

from catchup.models import DigestRun, Item, ItemContext, Source
from catchup.net.host_spacing import HostSpacer
from test_digest_runner import FakeModel, environment, execute, seed, stub_collection


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port, *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port))],
    )


def setup(client, links, *, comments=0, kind="feed", audio=False):
    seed(client)
    with client.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        source.kind = kind
        item = session.scalar(select(Item))
        item.entry_links = [{"url": url, "text": title} for url, title in links]
        item.comment_count = comments
        if audio:
            item.transcript_status = "waiting"
        elif kind == "podcast":
            item.transcript_status = "text"
        session.commit()


def html(title, text):
    return f"<html><head><title>{title}</title></head><body><article><p>{text}</p></article></body></html>"


def test_runner_stores_three_links_in_order_and_ignores_tags(environment, monkeypatch, public_dns):
    links = [(f"https://docs.example/{i}", f"Anchor {i}") for i in range(3)]
    setup(environment, links + [
        ("https://s0.example/tags/one", "Tag"), ("https://s0.example/tags/two", "Tag"),
    ])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        tag_one = router.get("https://s0.example/tags/one").mock(return_value=httpx.Response(200))
        tag_two = router.get("https://s0.example/tags/two").mock(return_value=httpx.Response(200))
        for i in range(3):
            router.get(links[i][0]).mock(return_value=httpx.Response(
                200, text=html(f"Page {i}", f"Context {i} " * 450),
            ))
        result = execute(environment)
    assert tag_one.call_count == tag_two.call_count == 0
    assert result["status"] == "succeeded"
    assert (result["context_total"], result["context_done"]) == (3, 3)
    with environment.app.state.session_factory() as session:
        contexts = session.scalars(select(ItemContext).order_by(ItemContext.position)).all()
        assert [(row.ref, row.title) for row in contexts] == [
            ("L1", "Page 0"), ("L2", "Page 1"), ("L3", "Page 2"),
        ]
        assert all(0 < len(row.text) <= 3000 for row in contexts)
        assert session.scalar(select(Item)).context_status == "gathered"


def test_linked_context_stops_at_sixteen_thousand_chars(environment, monkeypatch, public_dns):
    setup(environment, [(f"https://docs.example/{i}", str(i)) for i in range(8)])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        for i in range(8):
            router.get(f"https://docs.example/{i}").mock(return_value=httpx.Response(
                200, text=html(str(i), "x" * 4000),
            ))
        result = execute(environment)
    assert result["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        rows = session.scalars(select(ItemContext).order_by(ItemContext.position)).all()
        lengths = [len(row.text) for row in rows]
    assert sum(lengths) <= 16000
    assert len(rows) <= 6


def test_author_reply_context_and_disable_switch(environment, monkeypatch, public_dns):
    setup(environment, [], comments=2)
    stub_collection(monkeypatch)
    post = "https://s0.example/0"
    body = ("<li class='comment'><div class='comment-content'>Reader asks why.</div>"
            "<ol><li class='comment bypostauthor'><div class='comment-content'>"
            "Because of the update.</div></li></ol></li>")
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get(post).mock(return_value=httpx.Response(200, text=body))
        assert execute(environment)["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        rows = session.scalars(select(ItemContext)).all()
        assert [(row.ref, row.kind) for row in rows] == [("A1", "author_replies")]
        assert rows[0].title == "Author replies (1)"
        assert "Reader asks why." in rows[0].text

    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        item.state = "pending"
        item.summary = None
        item.context_status = None
        session.query(ItemContext).delete()
        session.commit()
    environment.app.state.settings = replace(environment.app.state.settings, author_replies=False)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        disabled_post = router.get(post).mock(return_value=httpx.Response(200, text=body))
        result = execute(environment)
        assert disabled_post.call_count == 0
    assert result["status"] == "succeeded"


def test_comments_disabled_never_requests_post_on_first_run(environment, monkeypatch, public_dns):
    setup(environment, [], comments=2)
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, author_replies=False)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(
            200, text="<div class='comment bypostauthor'><div class='comment-content'>Reply.</div></div>",
        ))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert post.call_count == 0
    assert result["context_total"] == 0


def test_robots_refusal_and_failed_pages_do_not_fail_run(environment, monkeypatch, public_dns):
    setup(environment, [(f"https://docs.example/{i}", str(i)) for i in range(3)])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(
            200, text="User-agent: CatchUp\nDisallow: /0\n",
        ))
        refused = router.get("https://docs.example/0").mock(return_value=httpx.Response(200))
        router.get("https://docs.example/1").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/2").mock(side_effect=httpx.ReadTimeout("timeout"))
        result = execute(environment)
    assert refused.call_count == 0
    assert result["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        assert not session.scalars(select(ItemContext)).all()


def test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "First")])
    with environment.app.state.session_factory() as session:
        first = session.scalar(select(Item))
        session.add(Item(
            source_id=first.source_id, identity_key="second", link="https://s0.example/second",
            title="Second", content_text="Second", content_origin="feed", state="pending",
            entry_links=[{"url": "https://docs.example/two", "text": "Second"}],
        ))
        session.commit()
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=2)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        robots = router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        first_page = router.get("https://docs.example/one").mock(return_value=httpx.Response(
            200, text=html("First", "First context " * 20),
        ))
        second_page = router.get("https://docs.example/two").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert (robots.call_count, first_page.call_count, second_page.call_count) == (1, 1, 0)
    with environment.app.state.session_factory() as session:
        rows = session.scalars(select(Item).order_by(Item.id)).all()
        assert [row.context_status for row in rows] == ["gathered", None]
        for row in rows:
            row.state = "pending"
            row.summary = None
        session.commit()
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/two").mock(return_value=httpx.Response(
            200, text=html("Second", "Second context " * 20),
        ))
        assert execute(environment)["status"] == "succeeded"


def test_audio_podcast_and_youtube_items_are_not_fetched(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/one", "One")], kind="podcast", audio=True)
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        assert execute(environment)["context_total"] == 0
        assert not router.calls
    with environment.app.state.session_factory() as session:
        session.scalar(select(Source)).kind = "youtube"
        session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        assert execute(environment)["context_total"] == 0
        assert not router.calls


def test_budget_spent_on_robots_marks_attempted_item_none(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/one", "One")])
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=1)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        page = router.get("https://docs.example/one").mock(return_value=httpx.Response(200))
        assert execute(environment)["status"] == "succeeded"
        assert page.call_count == 0
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(Item)).context_status == "none"


def test_configured_two_link_limit_never_requests_third(environment, monkeypatch, public_dns):
    setup(environment, [(f"https://docs.example/{i}", str(i)) for i in range(3)])
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, links_per_item=2)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        first = router.get("https://docs.example/0").mock(return_value=httpx.Response(
            200, text=html("First", "A page with substance " * 30),
        ))
        second = router.get("https://docs.example/1").mock(return_value=httpx.Response(
            200, text=html("Second", "Another substantive page " * 30),
        ))
        third = router.get("https://docs.example/2").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["context_total"] == 2
    assert (first.call_count, second.call_count, third.call_count) == (1, 1, 0)


def test_comment_feed_fallback_counts_extra_fetch_and_saves_named_reply(
    environment, monkeypatch, public_dns,
):
    setup(environment, [], comments=1)
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        item.entry_author = "Writer"
        item.comment_feed_url = "https://s0.example/comments/feed"
        session.commit()
    feed = (b"<rss version='2.0' xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            b"<channel><item><title>By: Writer</title><dc:creator>Writer</dc:creator>"
            b"<description>Author clarifies the point.</description></item></channel></rss>")
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(
            200, text="<html><body><article>No comment markup here.</article></body></html>",
        ))
        comments = router.get("https://s0.example/comments/feed").mock(return_value=httpx.Response(
            200, content=feed,
        ))
        result = execute(environment)
    assert (post.call_count, comments.call_count) == (1, 1)
    assert (result["context_total"], result["context_done"]) == (2, 2)
    with environment.app.state.session_factory() as session:
        row = session.scalar(select(ItemContext))
        assert (row.ref, row.title, row.text) == (
            "A1", "Author replies (1)", "Author clarifies the point.",
        )


def test_comment_plan_counts_one_post_fetch(environment, monkeypatch, public_dns):
    setup(environment, [], comments=1)
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(
            200, text="<html><body>No comments found.</body></html>",
        ))
        result = execute(environment)
    assert post.call_count == 1
    assert (result["context_total"], result["context_done"]) == (1, 1)


def test_link_without_title_uses_anchor_text(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/notes", "Anchor title")])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/notes").mock(return_value=httpx.Response(
            200, text="<html><body><article><p>" +
            "Substantive document text. " * 40 + "</p></article></body></html>",
        ))
        assert execute(environment)["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(ItemContext)).title == "Anchor title"


def test_podcast_text_post_gathers_link(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/notes", "Notes")], kind="podcast")
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        page = router.get("https://docs.example/notes").mock(return_value=httpx.Response(
            200, text=html("Notes", "Podcast text post context " * 35),
        ))
        result = execute(environment)
    assert page.call_count == 1 and result["context_done"] == 1
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(ItemContext)).ref == "L1"


def test_link_redirecting_to_login_does_not_store_the_final_page(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/article", "Article")])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/article").mock(return_value=httpx.Response(
            302, headers={"location": "/login/"},
        ))
        login = router.get("https://docs.example/login/").mock(return_value=httpx.Response(
            200, text=html("Sign in", "Account required " * 50),
        ))
        assert execute(environment)["status"] == "succeeded"
        assert login.call_count == 1
    with environment.app.state.session_factory() as session:
        assert session.scalars(select(ItemContext)).all() == []


def test_robots_exhaustion_marks_comment_item_none(environment, monkeypatch, public_dns):
    setup(environment, [], comments=1)
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=1)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        robots = router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(
            200, text="<div class='comment bypostauthor'><div class='comment-content'>Reply.</div></div>",
        ))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert robots.call_count == 1 and post.call_count == 0
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(Item)).context_status == "none"
        assert session.scalars(select(ItemContext)).all() == []


def test_redirect_exhaustion_marks_item_none_without_stored_context(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/redirect", "Redirect")])
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=2)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        first = router.get("https://docs.example/redirect").mock(return_value=httpx.Response(
            302, headers={"location": "/destination"},
        ))
        destination = router.get("https://docs.example/destination").mock(return_value=httpx.Response(
            200, text=html("Destination", "Substantive content " * 50),
        ))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert first.call_count == 1 and destination.call_count == 0
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(Item)).context_status == "none"
        assert session.scalars(select(ItemContext)).all() == []


def test_budget_exhaustion_keeps_first_link_in_partial_item(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "One"), ("https://docs.example/two", "Two")])
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=2)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        first = router.get("https://docs.example/one").mock(return_value=httpx.Response(
            200, text=html("One", "First linked document " * 40),
        ))
        second = router.get("https://docs.example/two").mock(return_value=httpx.Response(
            200, text=html("Two", "Second linked document " * 40),
        ))
        assert execute(environment)["status"] == "succeeded"
    assert first.call_count == 1 and second.call_count == 0
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(Item)).context_status == "gathered"
        assert [(row.ref, row.title) for row in session.scalars(select(ItemContext)).all()] == [("L1", "One")]


def test_second_item_keeps_partial_context_in_successful_digest(
    environment, monkeypatch, public_dns,
):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        first, second = session.scalars(select(Item).order_by(Item.id)).all()
        first.entry_links = [{"url": "https://docs.example/first", "text": "First"}]
        second.entry_links = [
            {"url": "https://docs.example/second", "text": "Second"},
            {"url": "https://docs.example/never", "text": "Never"},
        ]
        session.commit()
        second_id = second.id

    class ContextModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            self.calls.append((messages, max_tokens))
            if '"summary"' in messages[0]["content"]:
                return {"summary": "Linked summary", "used": ["L1"]}
            return {"topics": [{"title": "Links", "overview": "Notes", "item_refs": ["i1", "i2"]}]}

    model = ContextModel()
    environment.app.state.model_client_factory = lambda *_: model
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=3)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/first").mock(return_value=httpx.Response(
            200, text=html("First", "First detailed notes " * 40),
        ))
        second_page = router.get("https://docs.example/second").mock(return_value=httpx.Response(
            200, text=html("Second", "Second detailed notes " * 40),
        ))
        never = router.get("https://docs.example/never").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert second_page.call_count == 1 and never.call_count == 0
    assert any("Title: Item 1" in call[0][1]["content"] and "Context L1" in call[0][1]["content"]
               for call in model.calls if len(call[0]) > 1)
    with environment.app.state.session_factory() as session:
        item = session.get(Item, second_id)
        assert item.context_status == "gathered"
        assert [(part.ref, part.title) for part in item.contexts] == [("L1", "Second")]
    digest = environment.get(f"/api/digests/{result['digest_id']}").json()
    saved = {item["title"]: item for item in digest["topics"][0]["items"]}
    assert saved["Item 1"]["also_read"] == [
        {"title": "Second", "url": "https://docs.example/second", "kind": "link"},
    ]


def test_comment_budget_cutoff_keeps_link_without_requesting_post(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "One")], comments=1)
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=2)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/one").mock(return_value=httpx.Response(
            200, text=html("One", "Useful linked text " * 40),
        ))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["status"] == "succeeded" and post.call_count == 0
    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.context_status == "gathered"
        assert [(part.ref, part.title) for part in item.contexts] == [("L1", "One")]


def test_comment_feed_budget_cutoff_keeps_link(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "One")], comments=1)
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        session.scalar(select(Item)).comment_feed_url = "https://s0.example/comments/feed"
        session.commit()
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=4)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/one").mock(return_value=httpx.Response(
            200, text=html("One", "Useful linked text " * 40),
        ))
        router.get("https://s0.example/robots.txt").mock(return_value=httpx.Response(404))
        post = router.get("https://s0.example/0").mock(return_value=httpx.Response(
            200, text="<html><body><p>No comment markup</p></body></html>",
        ))
        feed = router.get("https://s0.example/comments/feed").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert post.call_count == 1 and feed.call_count == 0
    assert (result["context_total"], result["context_done"]) == (3, 2)
    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.context_status == "gathered"
        assert [(part.ref, part.title) for part in item.contexts] == [("L1", "One")]


def test_exhaustion_without_a_row_keeps_cached_summary(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "One")])
    stub_collection(monkeypatch)
    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        item.summary = "Previously summarized"
        item.summary_language = "en"
        session.commit()
    model = FakeModel([
        {"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]},
    ])
    environment.app.state.model_client_factory = lambda *_: model
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=1)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        page = router.get("https://docs.example/one").mock(return_value=httpx.Response(200))
        result = execute(environment)
    assert result["status"] == "succeeded" and page.call_count == 0
    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert item.context_status == "none"
        assert (item.summary, item.summary_language) == ("Previously summarized", "en")
        assert item.contexts == []
    assert len(model.calls) == 1
    digest = environment.get(f"/api/digests/{result['digest_id']}").json()
    assert digest["topics"][0]["items"][0]["summary"] == "Previously summarized"


def test_deleted_item_during_context_plan_does_not_fail_run(environment, monkeypatch):
    setup(environment, [("https://docs.example/page", "Page")])
    stub_collection(monkeypatch)
    from catchup.context import gather

    original = gather.related_links

    def remove_source(*args, **kwargs):
        links = original(*args, **kwargs)
        with environment.app.state.session_factory() as session:
            session.delete(session.scalar(select(Source)))
            session.commit()
        return links

    monkeypatch.setattr(gather, "related_links", remove_source)
    assert execute(environment)["status"] == "no_new_content"


def test_deleted_item_during_context_fetch_does_not_fail_run(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/page", "Page")])
    stub_collection(monkeypatch)

    def remove_source(_request):
        with environment.app.state.session_factory() as session:
            session.delete(session.scalar(select(Source)))
            session.commit()
        return httpx.Response(200, text=html("Page", "Substantial text " * 30))

    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/page").mock(side_effect=remove_source)
        assert execute(environment)["status"] == "no_new_content"


def test_context_progress_is_committed_between_fetches_for_one_item(
    environment, monkeypatch, public_dns,
):
    setup(environment, [("https://docs.example/one", "One"), ("https://docs.example/two", "Two")])
    stub_collection(monkeypatch)
    visible = []

    def second(_request):
        with environment.app.state.session_factory() as session:
            visible.append(session.scalar(select(DigestRun).order_by(DigestRun.id.desc())).context_done)
        return httpx.Response(200, text=html("Two", "Second linked document " * 40))

    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/one").mock(return_value=httpx.Response(
            200, text=html("One", "First linked document " * 40),
        ))
        router.get("https://docs.example/two").mock(side_effect=second)
        assert execute(environment)["status"] == "succeeded"
    assert visible == [1]
