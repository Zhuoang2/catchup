import socket
from dataclasses import replace

import httpx
import pytest
import respx
from sqlalchemy import select

from catchup.models import DigestRun, Item, ItemContext, Source
from catchup.net.host_spacing import HostSpacer
from test_digest_runner import environment, execute, seed, stub_collection


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
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        for i in range(3):
            router.get(links[i][0]).mock(return_value=httpx.Response(
                200, text=html(f"Page {i}", f"Context {i} " * 450),
            ))
        result = execute(environment)
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
    rows = sorted((row for row in environment.app.state.session_factory().scalars(select(ItemContext)).all()),
                  key=lambda row: row.position)
    assert sum(len(row.text) for row in rows) <= 16000
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
    rows = [row for row in environment.app.state.session_factory().scalars(select(ItemContext))]
    assert [(row.ref, row.kind) for row in rows] == [("A1", "author_replies")]
    assert "Reader asks why." in rows[0].text

    with environment.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        item.state = "pending"
        item.summary = None
        item.context_status = None
        session.query(ItemContext).delete()
        session.commit()
    environment.app.state.settings = replace(environment.app.state.settings, author_replies=False)
    with respx.mock(assert_all_mocked=True) as router:
        result = execute(environment)
        assert not router.calls
    assert result["status"] == "succeeded"


def test_robots_refusal_and_failed_pages_do_not_fail_run(environment, monkeypatch, public_dns):
    setup(environment, [(f"https://docs.example/{i}", str(i)) for i in range(3)])
    stub_collection(monkeypatch)
    with respx.mock(assert_all_mocked=True) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(
            200, text="User-agent: CatchUp\nDisallow: /0\n",
        ))
        router.get("https://docs.example/1").mock(return_value=httpx.Response(404))
        router.get("https://docs.example/2").mock(side_effect=httpx.ReadTimeout("timeout"))
        result = execute(environment)
    assert result["status"] == "succeeded"
    assert not list(environment.app.state.session_factory().scalars(select(ItemContext)))


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


def test_budget_spent_on_robots_keeps_item_eligible_for_next_run(environment, monkeypatch, public_dns):
    setup(environment, [("https://docs.example/one", "One")])
    stub_collection(monkeypatch)
    environment.app.state.settings = replace(environment.app.state.settings, context_fetches_per_run=1)
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get("https://docs.example/robots.txt").mock(return_value=httpx.Response(404))
        page = router.get("https://docs.example/one").mock(return_value=httpx.Response(200))
        assert execute(environment)["status"] == "succeeded"
        assert page.call_count == 0
    with environment.app.state.session_factory() as session:
        assert session.scalar(select(Item)).context_status is None
    with environment.app.state.session_factory() as session:
        session.scalar(select(Source)).kind = "youtube"
        session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        assert execute(environment)["context_total"] == 0
        assert not router.calls
