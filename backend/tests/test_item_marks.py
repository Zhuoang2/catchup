from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from catchup.main import create_app
from catchup.models import Digest, DigestItem, DigestItemMark, DigestRun, DigestTopic, Item, Source
import catchup.api.marks as marks
from test_digest_runner import environment, seed, stub_collection, execute, FakeModel


@pytest.fixture
def client(test_settings):
    with TestClient(create_app(test_settings)) as client:
        yield client


def seed_digest(client, *, created_at=None, language="en"):
    with client.app.state.session_factory() as session:
        suffix = session.query(Digest).count() + 1
        source = Source(title="Blog", site_url="https://example.test",
                        feed_url=f"https://example.test/{suffix}/feed",
                        input_url=f"https://example.test/{suffix}/feed")
        run = DigestRun(status="succeeded")
        session.add_all([source, run])
        session.flush()
        digest = Digest(run_id=run.id, model_id="test", language=language,
                        item_count=3, source_count=1, **({"created_at": created_at} if created_at else {}))
        session.add(digest)
        session.flush()
        run.digest_id = digest.id
        topic = DigestTopic(digest_id=digest.id, position=0, title="News", overview="Overview")
        creator = DigestTopic(digest_id=digest.id, position=1, title="Creator updates",
                              overview="", kind="creator_updates")
        session.add_all([topic, creator])
        session.flush()
        result = {"source": source.id, "digest": digest.id}
        for position, letter in enumerate("ABC"):
            title = f"Article {letter}" if letter != "C" else "Episode C"
            stored = Item(source_id=source.id, identity_key=letter, title=title,
                          link=f"https://example.test/{letter}", content_text="Text",
                          content_origin="feed", state="delivered")
            session.add(stored)
            session.flush()
            item = DigestItem(
                digest_id=digest.id, topic_id=creator.id if letter == "C" else topic.id,
                item_id=stored.id, position=position, title=title, link=stored.link,
                source_name="Blog", source_kind="feed",
                summary="Summary A" if letter == "A" else None,
                summary_unavailable=letter == "B",
                update_reason="no_transcript" if letter == "C" else None,
            )
            session.add(item)
            session.flush()
            result[letter] = item.id
        session.commit()
        return result


def path(ids, mark, letter="A"):
    return f"/api/digest-items/{ids[letter]}/{mark}"


def answer(item_id, **changes):
    return {"id": item_id, "bookmarked": False, "liked": False,
            "rating": None, "note": None, **changes}


def test_digest_answer_carries_unmarked_ids(client):
    ids = seed_digest(client)
    detail = client.get(f"/api/digests/{ids['digest']}").json()
    items = detail["topics"][0]["items"]
    for letter, item in zip("AB", items):
        assert {key: item[key] for key in answer(ids[letter])} == answer(ids[letter])
    assert client.get("/api/digests/latest").json() == detail
    assert "id" not in detail["creator_updates"][0]["items"][0]


def test_bookmark_and_like_are_saved_and_returned(client):
    ids = seed_digest(client)
    response = client.put(path(ids, "bookmark"))
    assert response.status_code == 200
    assert response.json() == answer(ids["A"], bookmarked=True)
    assert client.put(path(ids, "like")).json() == answer(ids["A"], bookmarked=True, liked=True)
    items = client.get(f"/api/digests/{ids['digest']}").json()["topics"][0]["items"]
    assert items[0]["bookmarked"] is items[0]["liked"] is True
    assert items[1]["bookmarked"] is items[1]["liked"] is False


def test_repeated_bookmark_keeps_its_first_time(client, monkeypatch):
    ids = seed_digest(client)
    times = iter(datetime(2026, 11, 25, hour, tzinfo=timezone.utc) for hour in (9, 10, 11))
    monkeypatch.setattr(marks, "utc_now", lambda: next(times))
    assert client.put(path(ids, "bookmark")).status_code == 200
    assert client.put(path(ids, "bookmark")).status_code == 200
    with client.app.state.session_factory() as session:
        row = session.get(DigestItemMark, ids["A"])
        assert row.bookmarked_at == datetime(2026, 11, 25, 9, tzinfo=timezone.utc)
        assert row.updated_at == datetime(2026, 11, 25, 10, tzinfo=timezone.utc)
    response = client.delete(path(ids, "like"))
    assert response.status_code == 200
    assert response.json() == answer(ids["A"], bookmarked=True)


def test_removing_marks_keeps_an_empty_row(client):
    ids = seed_digest(client)
    client.put(path(ids, "bookmark"))
    client.put(path(ids, "like"))
    assert client.delete(path(ids, "bookmark")).json() == answer(ids["A"], liked=True)
    assert client.delete(path(ids, "like")).json() == answer(ids["A"])
    with client.app.state.session_factory() as session:
        rows = session.scalars(select(DigestItemMark)).all()
        assert len(rows) == 1
        assert rows[0].digest_item_id == ids["A"]
        assert all(getattr(rows[0], col) is None for col in (
            "bookmarked_at", "liked_at", "rating", "note", "rated_at",
        ))


@pytest.mark.parametrize("mark", ["bookmark", "like"])
@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_unknown_item_and_creator_updates_are_refused(client, mark, method):
    ids = seed_digest(client)
    for item_id, status, code, message in [
        (999, 404, "not_found", "Digest item not found."),
        (ids["C"], 422, "not_markable", "Items in Creator updates cannot be bookmarked or rated."),
    ]:
        response = client.request(method, f"/api/digest-items/{item_id}/{mark}")
        assert response.status_code == status
        assert response.json()["error"] == {"code": code, "message": message}
    with client.app.state.session_factory() as session:
        assert session.scalars(select(DigestItemMark)).all() == []


def test_unavailable_summary_can_be_bookmarked_and_liked(client):
    ids = seed_digest(client)
    for mark, field in [("bookmark", "bookmarked"), ("like", "liked")]:
        response = client.put(path(ids, mark, "B"))
        assert response.status_code == 200
        assert response.json()[field] is True


def test_marks_survive_source_deletion_and_restart(client, test_settings):
    ids = seed_digest(client)
    client.put(path(ids, "bookmark"))
    client.put(path(ids, "like"))
    assert client.put(path(ids, "feedback"), json={"rating": "poor", "note": "Kept"}).status_code == 200
    assert client.delete(f"/api/sources/{ids['source']}").status_code == 204
    before = client.get(f"/api/digests/{ids['digest']}").json()
    assert before["topics"][0]["items"][0]["bookmarked"] is True
    assert before["topics"][0]["items"][0]["liked"] is True
    assert before["topics"][0]["items"][0]["rating"] == "poor"
    assert before["topics"][0]["items"][0]["note"] == "Kept"
    with TestClient(create_app(test_settings)) as restarted:
        after = restarted.get(f"/api/digests/{ids['digest']}").json()
        assert after == before
        assert after["topics"][0]["items"][0]["rating"] == "poor"
        assert after["topics"][0]["items"][0]["note"] == "Kept"


@pytest.mark.parametrize("mark", ["bookmark", "like", "feedback"])
@pytest.mark.parametrize("method", ["PUT", "DELETE"])
@pytest.mark.parametrize("refusal", ["origin", "fetch-site", "extension"])
def test_cross_site_and_extension_token_cannot_mark(client, mark, method, refusal):
    ids = seed_digest(client)
    expected = answer(ids["A"])
    if method == "DELETE":
        assert client.put(path(ids, "bookmark")).status_code == 200
        assert client.put(path(ids, "like")).status_code == 200
        assert client.put(path(ids, "feedback"), json={"rating": "good"}).status_code == 200
        expected = answer(ids["A"], bookmarked=True, liked=True, rating="good")
    if refusal == "extension":
        token = client.post("/api/settings/extension-tokens", json={"name": "Chrome"}).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
    elif refusal == "fetch-site":
        headers = {"Sec-Fetch-Site": "cross-site"}
    else:
        headers = {"Origin": "http://localhost:3000"}
    options = {"json": {"rating": "good"}} if mark == "feedback" and method == "PUT" else {}
    response = client.request(method, path(ids, mark), headers=headers, **options)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "cross_site_request"
    item = client.get(f"/api/digests/{ids['digest']}").json()["topics"][0]["items"][0]
    assert {key: item[key] for key in expected} == expected


def test_digest_answer_loads_marks_in_one_query(client):
    ids = seed_digest(client)
    client.put(path(ids, "bookmark"))
    client.put(path(ids, "like", "B"))
    statements = []
    def record(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)
    engine = client.app.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        assert client.get(f"/api/digests/{ids['digest']}").status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert sum("FROM digest_item_marks" in statement for statement in statements) == 1


def test_feedback_is_saved_stripped_and_replaced(client):
    ids = seed_digest(client)
    client.put(path(ids, "bookmark"))
    response = client.put(path(ids, "feedback"), json={"rating": "poor", "note": "  Misses the price  "})
    assert response.status_code == 200
    assert response.json() == answer(ids["A"], bookmarked=True, rating="poor", note="Misses the price")
    assert client.put(path(ids, "feedback"), json={"rating": "good"}).json() == answer(
        ids["A"], bookmarked=True, rating="good",
    )
    assert client.put(path(ids, "feedback"), json={"rating": "good", "note": "   "}).json()["note"] is None
    response = client.delete(path(ids, "feedback"))
    assert response.status_code == 200
    assert response.json() == answer(ids["A"], bookmarked=True)
    with client.app.state.session_factory() as session:
        assert session.get(DigestItemMark, ids["A"]).rated_at is None


def test_note_of_500_characters_after_trimming_is_kept(client):
    ids = seed_digest(client)
    response = client.put(path(ids, "feedback"), json={"rating": "good", "note": " " + "x" * 500 + " "})
    assert response.status_code == 200
    assert response.json()["note"] == "x" * 500


@pytest.mark.parametrize("body,code,message", [
    ({"rating": "excellent"}, "invalid_feedback", "Choose Good or Poor for the summary."),
    ({"rating": "good", "note": "x" * 501}, "invalid_feedback", "Keep the note to 500 characters or fewer."),
    ({"rating": 1}, "invalid_request", None),
    ({"note": "x"}, "invalid_request", None),
])
def test_invalid_feedback_changes_nothing(client, body, code, message):
    ids = seed_digest(client)
    assert client.put(path(ids, "feedback"), json={"rating": "poor", "note": "Earlier"}).status_code == 200
    response = client.put(path(ids, "feedback"), json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    if message:
        assert response.json()["error"]["message"] == message
    item = client.get(f"/api/digests/{ids['digest']}").json()["topics"][0]["items"][0]
    assert (item["rating"], item["note"]) == ("poor", "Earlier")


def test_feedback_needs_a_markable_item_with_a_summary(client):
    ids = seed_digest(client)
    for item_id, status, code in [(ids["B"], 422, "no_summary"), (ids["C"], 422, "not_markable"),
                                  (999, 404, "not_found")]:
        response = client.put(f"/api/digest-items/{item_id}/feedback", json={"rating": "good"})
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
        if code == "no_summary":
            assert response.json()["error"]["message"] == "This item has no summary to rate."


def test_marks_are_not_sent_to_the_model(environment, monkeypatch):
    seed(environment, count=2)
    stub_collection(monkeypatch)
    first = execute(environment)
    assert first["status"] == "succeeded"
    with environment.app.state.session_factory() as session:
        item_id = session.scalar(select(DigestItem.id).order_by(DigestItem.id))
        source_id = session.scalar(select(Source.id).order_by(Source.id))
    base = f"/api/digest-items/{item_id}"
    assert environment.put(base + "/feedback", json={"rating": "poor", "note": "NOTE-MARKER-41"}).status_code == 200
    assert environment.put(base + "/bookmark").status_code == 200
    assert environment.put(base + "/like").status_code == 200
    with environment.app.state.session_factory() as session:
        session.add(Item(source_id=source_id, identity_key="new", title="New",
                         link="https://s0.example/new", content_text="New content",
                         content_origin="feed", state="pending"))
        session.commit()
    model = FakeModel()
    environment.app.state.model_client_factory = lambda *_: model
    assert execute(environment)["status"] == "succeeded"
    assert model.calls
    assert all("NOTE-MARKER-41" not in message["content"]
               for messages, _tokens in model.calls for message in messages)


def bookmarks(client):
    response = client.get("/api/bookmarks")
    assert response.status_code == 200
    return response.json()


def test_bookmarks_list_newest_first_with_digest(client, monkeypatch):
    first = seed_digest(client, language="zh-Hans")
    second = seed_digest(client)
    times = iter(datetime(2026, 11, 25, hour, tzinfo=timezone.utc) for hour in (9, 10))
    monkeypatch.setattr(marks, "utc_now", lambda: next(times))
    assert client.put(path(first, "bookmark")).status_code == 200
    assert client.put(path(second, "bookmark")).status_code == 200
    entries = bookmarks(client)
    assert [entry["id"] for entry in entries] == [second["A"], first["A"]]
    detail = client.get(f"/api/digests/{first['digest']}").json()
    assert entries[1] == {
        **detail["topics"][0]["items"][0], "bookmarked": True,
        "bookmarked_at": "2026-11-25T09:00:00Z",
        "digest": {"id": 1, "created_at": detail["created_at"], "language": "zh-Hans"},
    }


def test_bookmarks_list_breaks_ties_by_higher_id(client, monkeypatch):
    ids = seed_digest(client)
    monkeypatch.setattr(marks, "utc_now", lambda: datetime(2026, 11, 25, 9, tzinfo=timezone.utc))
    assert client.put(path(ids, "bookmark")).status_code == 200
    assert client.put(path(ids, "bookmark", "B")).status_code == 200
    assert [entry["id"] for entry in bookmarks(client)] == [ids["B"], ids["A"]]


def test_bookmarks_list_holds_only_bookmarked_items(client):
    ids = seed_digest(client)
    assert bookmarks(client) == []
    assert client.put(path(ids, "like")).status_code == 200
    assert client.put(path(ids, "feedback"), json={"rating": "good"}).status_code == 200
    assert bookmarks(client) == []
    assert client.put(path(ids, "bookmark")).status_code == 200
    assert client.put(path(ids, "bookmark", "B")).status_code == 200
    assert client.delete(path(ids, "bookmark", "B")).status_code == 200
    assert [entry["id"] for entry in bookmarks(client)] == [ids["A"]]


def test_bookmarks_list_filters_images_like_the_digest(client):
    ids = seed_digest(client)
    with client.app.state.session_factory() as session:
        session.get(DigestItem, ids["A"]).images = [
            {"url": "http://192.168.1.2/a.png", "alt": "Local"},
            {"url": "https://cdn.example/b.png", "alt": "Chart"},
        ]
        session.commit()
    assert client.put(path(ids, "bookmark")).status_code == 200
    assert bookmarks(client)[0]["images"] == [{"url": "https://cdn.example/b.png", "alt": "Chart"}]
