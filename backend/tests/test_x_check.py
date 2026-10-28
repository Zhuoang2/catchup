"""Read X accounts atomically, preserving gaps and budget across checks."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select

from catchup.main import create_app
from catchup.models import DigestRun, Item, Source, SourceCheck, XAccount
from catchup.net.rate_limit import is_rate_limited
from catchup.sources.x_api import XClient
from catchup.sources.x_check import XReadBudget, check_x_account

UID = "1234567890123456789"
TOKEN = "test-" + "x" * 40


@pytest.fixture
def app(test_settings):
    with TestClient(create_app(test_settings)) as client:
        with client.app.state.session_factory() as session:
            source = Source(title="Writer", site_url="https://x.com/writer", feed_url=f"x:user:{UID}",
                            input_url="https://x.com/writer", kind="x")
            session.add(source)
            session.flush()
            session.add(XAccount(source_id=source.id, user_id=UID, username="writer",
                                 newest_id="100", followed_at=datetime.now(timezone.utc) - timedelta(days=1)))
            session.add(DigestRun(id=1, status="collecting"))
            session.commit()
        yield client


def x_post(post_id, *, root=None, reply_to=None, repost=False, text=None, photos=False):
    value = {"id": str(post_id), "text": text or f"New post {post_id} https://t.co/example",
             "created_at": (datetime.now(timezone.utc) - timedelta(seconds=1000 - int(post_id))).isoformat(),
             "conversation_id": str(root or post_id), "entities": {"urls": [
                 {"url": "https://t.co/example", "expanded_url": "https://blog.example/post"}]}}
    if photos:
        value["attachments"] = {"media_keys": ["3_photo"]}
    if reply_to is not None:
        value["in_reply_to_user_id"] = str(reply_to)
        value["referenced_tweets"] = [{"type": "replied_to", "id": str(root)}]
    if repost:
        value["referenced_tweets"] = [{"type": "retweeted", "id": "1"}]
    return value


def page(posts, next_token=None):
    return {"data": posts, "meta": {"result_count": len(posts), **(
        {"next_token": next_token} if next_token else {})},
        "includes": {"media": [{"media_key": "3_photo", "type": "photo",
                                "url": "https://pbs.twimg.com/media/photo.png", "alt_text": "Chart"}]}}


def check(app, budget, router):
    with app.app.state.session_factory() as session, XClient(TOKEN) as client:
        source_id = session.scalar(select(Source.id))
        return check_x_account(session, session.get(Source, source_id), session.get(XAccount, source_id),
                               1, client, budget)


def test_read_new_original_and_own_thread_replies_with_public_item_fields(app):
    posts = [x_post(105, root=105, photos=True), x_post(104, root=105, reply_to=UID),
             x_post(103, root=105, reply_to="another-user"), x_post(102, root=99, reply_to=UID),
             x_post(101, repost=True)]
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
            return_value=httpx.Response(200, json=page(posts)))
        budget = XReadBudget(remaining=10)
        result = check(app, budget, router)
    assert route.call_count == 1
    assert route.calls[0].request.url.params["since_id"] == "100"
    assert route.calls[0].request.url.params["exclude"] == "retweets"
    assert route.calls[0].request.url.params["max_results"] == "10"
    assert result.status == "new_items" and result.new_count == 1 and result.entries_seen == 5
    assert budget.remaining == 5 and budget.reads == 5
    with app.app.state.session_factory() as session:
        item = session.scalar(select(Item))
        assert (item.identity_key, item.link, item.site_name, item.content_origin, item.state) == (
            "105", "https://x.com/writer/status/105", "X · Writer", "x", "pending",
        )
        assert item.title.startswith("New post 105")
        assert item.content_text.endswith("https://blog.example/post")
        assert item.entry_links == [{"url": "https://blog.example/post", "text": ""}]
        assert item.image_candidates[0]["alt"] == "Chart"
        assert item.captured_replies == [
            "New post 103 https://blog.example/post", "New post 104 https://blog.example/post",
        ]
        assert session.scalar(select(XAccount)).newest_id == "105"


def test_zero_post_response_is_success_and_never_posted_uses_follow_time(app):
    with app.app.state.session_factory() as session:
        session.scalar(select(XAccount)).newest_id = None
        session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
            return_value=httpx.Response(200, json={"meta": {"result_count": 0}}))
        result = check(app, XReadBudget(remaining=5), router)
    assert result.status == "no_new_items" and result.entries_seen == 0
    assert "since_id" not in route.calls[0].request.url.params
    assert route.calls[0].request.url.params["start_time"]


def test_duplicate_post_is_not_inserted_twice(app):
    with app.app.state.session_factory() as session:
        session.add(Item(source_id=session.scalar(select(Source.id)), identity_key="105",
                         link="https://x.com/writer/status/105", title="Old",
                         content_text="", content_origin="x", state="delivered"))
        session.commit()
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
            return_value=httpx.Response(200, json=page([x_post(105)])))
        result = check(app, XReadBudget(remaining=5), router)
    assert result.status == "no_new_items" and result.new_count == 0
    with app.app.state.session_factory() as session:
        assert [item.identity_key for item in session.scalars(select(Item))] == ["105"]


def test_thread_replies_are_capped_at_ten_and_four_thousand_characters(app):
    posts = [x_post(400)] + [
        x_post(n, root=400, reply_to=UID, text="r" * 500) for n in range(399, 386, -1)
    ]
    with respx.mock(assert_all_mocked=True) as router:
        router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
            return_value=httpx.Response(200, json=page(posts)))
        check(app, XReadBudget(remaining=20), router)
    with app.app.state.session_factory() as session:
        replies = session.scalar(select(Item)).captured_replies
        assert len(replies) <= 10
        assert len("\n\n".join(replies)) == 4000


def test_error_after_page_rolls_back_items_and_ids_but_charges_reads(app):
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(
            side_effect=[httpx.Response(200, json=page([x_post(105)] * 5, "next")),
                         httpx.Response(429, headers={"x-rate-limit-reset": str(
                             int(datetime.now(timezone.utc).timestamp()) + 30)})])
        budget = XReadBudget(remaining=10)
        result = check(app, budget, router)
    assert route.call_count == 2
    assert result.status == "failed" and result.http_status == 429 and is_rate_limited(result)
    assert budget.reads == 5 and budget.remaining == 5
    with app.app.state.session_factory() as session:
        assert session.scalars(select(Item)).all() == []
        assert session.scalar(select(XAccount)).newest_id == "100"


def test_deferred_untouched_when_fewer_than_five_reads_remain(app):
    with app.app.state.session_factory() as session:
        source = session.scalar(select(Source))
        source.last_check_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
        session.commit()
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(return_value=httpx.Response(200))
        result = check(app, XReadBudget(remaining=4), router)
        assert route.call_count == 0
    assert result.status == "deferred"
    with app.app.state.session_factory() as session:
        assert session.scalar(select(Source)).last_check_at == datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_budget_exhaustion_creates_gap_then_reads_gap_before_new_posts(app):
    first_page = [x_post(n) for n in range(200, 150, -1)]
    seen = []
    def respond(request):
        params = request.url.params
        seen.append(dict(params))
        if len(seen) == 1:
            return httpx.Response(200, json=page(first_page, "more"))
        if len(seen) == 2:
            return httpx.Response(200, json=page([x_post(150)], "more-gap"))
        if len(seen) == 3:
            return httpx.Response(200, json=page([x_post(149)]))
        return httpx.Response(200, json=page([x_post(201)]))
    with respx.mock(assert_all_mocked=True) as router:
        route = router.get(f"https://api.x.com/2/users/{UID}/tweets").mock(side_effect=respond)
        first = XReadBudget(remaining=50)
        result = check(app, first, router)
        assert result.new_count == 50 and first.reads == 50
        with app.app.state.session_factory() as session:
            account = session.scalar(select(XAccount))
            assert (account.newest_id, account.gap_since_id, account.gap_until_id) == ("200", "100", "151")
        second = XReadBudget(remaining=5)
        check(app, second, router)
        with app.app.state.session_factory() as session:
            account = session.scalar(select(XAccount))
            assert (account.gap_since_id, account.gap_until_id) == ("100", "150")
        third = XReadBudget(remaining=10)
        check(app, third, router)
        assert route.call_count == 4
    assert seen[0]["since_id"] == "100" and seen[0]["max_results"] == "50"
    assert seen[1]["since_id"] == "100" and seen[1]["until_id"] == "151"
    assert seen[2]["since_id"] == "100" and seen[2]["until_id"] == "150"
    assert seen[3]["since_id"] == "200" and "until_id" not in seen[3]
    with app.app.state.session_factory() as session:
        account = session.scalar(select(XAccount))
        assert account.newest_id == "201"
        assert account.gap_since_id is account.gap_until_id is None
