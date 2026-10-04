from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from catchup.main import create_app
from catchup.models import Digest, DigestItem, DigestRun, DigestTopic, Item, Source, SourceCheck


def seed_history(client):
    with client.app.state.session_factory() as session:
        source = Source(title="Live source", site_url="https://example.test",
                        feed_url="https://example.test/feed", input_url="https://example.test/feed")
        session.add(source)
        session.flush()
        item = Item(source_id=source.id, identity_key="entry",
                    link="https://example.test/live", title="Live title", content_text="text",
                    content_origin="feed", state="delivered")
        session.add(item)
        session.flush()
        for index, stamp in enumerate((
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            datetime(2026, 10, 2, tzinfo=timezone.utc),
            datetime(2026, 10, 2, tzinfo=timezone.utc),
        )):
            run = DigestRun(status="succeeded")
            session.add(run)
            session.flush()
            digest = Digest(run_id=run.id, created_at=stamp, model_id="test",
                            item_count=index + 1, source_count=1)
            session.add(digest)
            session.flush()
            if index == 0:
                # Insert out of order to prove retrieval uses stored positions, not IDs.
                later = DigestTopic(digest_id=digest.id, position=1, title="Second", overview="Later")
                first = DigestTopic(digest_id=digest.id, position=0, title="First", overview="Earlier")
                session.add_all([later, first])
                session.flush()
                session.add_all([
                    DigestItem(digest_id=digest.id, topic_id=first.id, position=1,
                               item_id=item.id, title="Saved second",
                               link="https://example.test/second", source_name="Saved source",
                               summary=None, summary_unavailable=True),
                    DigestItem(digest_id=digest.id, topic_id=first.id, position=0,
                               item_id=item.id, title="Saved first",
                               link="https://example.test/first", source_name="Saved source",
                               published_at=stamp, summary="Saved summary", summary_unavailable=False),
                    DigestItem(digest_id=digest.id, topic_id=later.id, position=0,
                               title="Other item", link="https://example.test/other",
                               source_name="Another source", summary="Another summary",
                               summary_unavailable=False),
                ])
        session.commit()
        return source.id


def test_history_lists_three_newest_first_with_counts(test_settings):
    with TestClient(create_app(test_settings)) as client:
        assert client.get("/api/digests").json() == []
        seed_history(client)
        response = client.get("/api/digests")
        assert response.status_code == 200
        rows = response.json()
        assert [row["id"] for row in rows] == [3, 2, 1]
        assert [row["item_count"] for row in rows] == [3, 2, 1]
        assert [row["source_count"] for row in rows] == [1, 1, 1]
        assert rows[0]["created_at"] == "2026-10-02T00:00:00Z"


def test_digest_detail_uses_snapshot_positions_and_survives_source_deletion(test_settings):
    with TestClient(create_app(test_settings)) as client:
        source_id = seed_history(client)
        response = client.get("/api/digests/1")
        assert response.status_code == 200
        before = response.json()
        assert before["model_id"] == "test"
        assert [topic["title"] for topic in before["topics"]] == ["First", "Second"]
        assert [item["title"] for item in before["topics"][0]["items"]] == [
            "Saved first", "Saved second",
        ]
        assert before["topics"][0]["overview"] == "Earlier"
        assert before["topics"][0]["items"][0] == {
            "title": "Saved first", "link": "https://example.test/first",
            "source_name": "Saved source", "published_at": before["created_at"],
            "summary": "Saved summary", "summary_unavailable": False,
        }
        assert before["topics"][0]["items"][1]["summary_unavailable"] is True
        assert before["topics"][1]["items"][0]["link"] == "https://example.test/other"
        assert client.delete(f"/api/sources/{source_id}").status_code == 204
        assert client.get("/api/digests/1").json() == before
        assert client.get("/api/digests/999").json()["error"]["code"] == "not_found"


def test_digest_history_survives_new_app_on_same_data_directory(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        before_list = client.get("/api/digests").json()
        before_detail = client.get("/api/digests/1").json()
    with TestClient(create_app(test_settings)) as restarted:
        assert restarted.get("/api/digests").json() == before_list
        assert restarted.get("/api/digests/1").json() == before_detail


def test_stored_timestamps_are_utc_across_endpoints(test_settings):
    local_offset = timezone(timedelta(hours=-7))
    local_time = datetime(2026, 10, 2, 3, tzinfo=local_offset)
    with TestClient(create_app(test_settings)) as client:
        source_id = seed_history(client)
        with client.app.state.session_factory() as session:
            source = session.get(Source, source_id)
            source.last_check_at = local_time
            session.add(SourceCheck(source_id=source_id, status="no_new_items", checked_at=local_time))
            run = session.get(DigestRun, 1)
            run.started_at = local_time
            run.finished_at = local_time
            session.commit()
        source = client.get("/api/sources").json()[0]
        run = client.get("/api/digest-runs/1").json()
        history = client.get("/api/digests").json()
        digest = client.get("/api/digests/1").json()
        for value in (
            source["last_check_at"], run["started_at"], run["finished_at"],
            *(row["created_at"] for row in history), digest["created_at"],
            digest["topics"][0]["items"][0]["published_at"],
        ):
            assert datetime.fromisoformat(value).utcoffset() == timedelta(0)
        assert source["last_check_at"] == run["started_at"] == run["finished_at"] == "2026-10-02T10:00:00Z"
        with client.app.state.session_factory() as session:
            assert session.get(Source, source_id).last_check_at.tzinfo == timezone.utc
            assert session.get(DigestRun, 1).started_at.tzinfo == timezone.utc
