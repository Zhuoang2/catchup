from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import event

from catchup.main import create_app
from catchup.models import AppSettings, Digest, DigestItem, DigestRun, DigestTopic, Item, ItemContext, Source, SourceCheck


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


def test_latest_digest_is_null_without_history(test_settings):
    with TestClient(create_app(test_settings)) as client:
        response = client.get("/api/digests/latest")
        assert response.status_code == 200
        assert response.json() is None


def test_latest_digest_matches_detail_with_all_saved_fields(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        with client.app.state.session_factory() as session:
            digest = session.get(Digest, 3)
            digest.language = "zh-Hans"
            digest.transcript_wait_days = 10
            run = session.get(DigestRun, digest.run_id)
            run.prompt_tokens = 81
            run.completion_tokens = 23
            topic = DigestTopic(digest_id=3, position=0, title="Technology", overview="Saved")
            creator = DigestTopic(digest_id=3, position=1, title="Creator updates",
                                  overview="", kind="creator_updates")
            session.add_all([topic, creator])
            session.flush()
            session.add_all([
                DigestItem(digest_id=3, topic_id=topic.id, position=0, title="Article",
                           link="https://example.test/article", source_name="Blog",
                           summary="Summary", summary_unavailable=False),
                DigestItem(digest_id=3, topic_id=creator.id, position=0, title="Episode",
                           link="https://example.test/episode", source_name="Show",
                           source_kind="podcast", update_reason="no_transcript",
                           summary_unavailable=True),
            ])
            session.commit()
        response = client.get("/api/digests/latest")
        assert response.status_code == 200
        detail = client.get("/api/digests/3")
        assert detail.status_code == 200
        assert response.json() == detail.json()
        assert response.json()["language"] == "zh-Hans"
        assert response.json()["transcript_wait_days"] == 10
        assert (response.json()["prompt_tokens"], response.json()["completion_tokens"]) == (81, 23)
        assert response.json()["topics"][0]["items"][0]["title"] == "Article"
        assert response.json()["creator_updates"][0]["items"][0]["title"] == "Episode"
        assert client.get("/api/digests/1").json()["id"] == 1


def test_latest_returns_creator_updates_only_digest(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        with client.app.state.session_factory() as session:
            creator = DigestTopic(digest_id=3, position=0, title="Creator updates",
                                  overview="", kind="creator_updates")
            session.add(creator)
            session.flush()
            session.add(DigestItem(digest_id=3, topic_id=creator.id, position=0,
                                   title="Video", link="https://example.test/video",
                                   source_name="Channel", source_kind="youtube",
                                   update_reason="captions_off", summary_unavailable=True))
            session.commit()
        latest = client.get("/api/digests/latest")
        assert latest.status_code == 200
        assert latest.json() == client.get("/api/digests/3").json()
        assert latest.json()["topics"] == []
        assert latest.json()["creator_updates"][0]["items"][0]["title"] == "Video"


def test_latest_breaks_creation_time_ties_with_higher_id(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        assert client.get("/api/digests/latest").json()["id"] == 3
        assert client.get("/api/digests/2").json()["id"] == 2


def test_latest_prefers_newer_creation_time_over_higher_id(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        with client.app.state.session_factory() as session:
            session.get(Digest, 1).created_at = datetime(2026, 10, 3, tzinfo=timezone.utc)
            session.commit()
        rows = client.get("/api/digests").json()
        latest = client.get("/api/digests/latest")
        assert [row["id"] for row in rows] == [1, 3, 2]
        assert latest.status_code == 200
        assert latest.json() == client.get("/api/digests/1").json()
        assert latest.json()["id"] == rows[0]["id"]


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
        assert rows[0]["language"] is None
        assert rows[0]["topics"] == []
        assert rows[0]["creator_updates_only"] is False
        assert rows[2]["topics"] == ["First", "Second"]


def test_history_lists_snapshot_language_topics_and_creator_only(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        with client.app.state.session_factory() as session:
            session.get(Digest, 1).language = "zh-Hans"
            creator = DigestTopic(digest_id=2, position=0, title="Creator updates",
                                  overview="", kind="creator_updates")
            session.add(creator)
            session.flush()
            session.add(DigestItem(digest_id=2, topic_id=creator.id, position=0,
                                   title="New episode", link="https://example.test/episode",
                                   source_name="Saved show", summary_unavailable=True))
            session.commit()
        rows = client.get("/api/digests").json()
        assert [(row["language"], row["topics"], row["creator_updates_only"]) for row in rows] == [
            (None, [], False),
            (None, [], True),
            ("zh-Hans", ["First", "Second"], False),
        ]


def test_history_list_query_count_is_constant(test_settings):
    with TestClient(create_app(test_settings)) as client:
        with client.app.state.session_factory() as session:
            engine = session.get_bind()

        def count_queries():
            statements = []

            def record(_conn, _cursor, statement, _params, _context, _executemany):
                if statement.lstrip().upper().startswith("SELECT"):
                    statements.append(statement)

            event.listen(engine, "before_cursor_execute", record)
            try:
                assert client.get("/api/digests").status_code == 200
            finally:
                event.remove(engine, "before_cursor_execute", record)
            return len(statements)

        with client.app.state.session_factory() as session:
            for _ in range(5):
                run = DigestRun(status="succeeded")
                session.add(run)
                session.flush()
                digest = Digest(run_id=run.id, model_id="test", item_count=1, source_count=1)
                session.add(digest)
                session.flush()
                session.add(DigestTopic(digest_id=digest.id, position=0,
                                        title=f"Topic {digest.id}", overview="Saved"))
                if digest.id == 1:
                    session.commit()
                    one = count_queries()
            session.commit()
        five = count_queries()
        assert one == five == 2


def test_history_list_loads_all_topics_without_bound_digest_ids(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        with client.app.state.session_factory() as session:
            engine = session.get_bind()
        topic_queries = []

        def record(_conn, _cursor, statement, params, _context, _executemany):
            if "FROM digest_topics" in statement:
                topic_queries.append((statement, params))

        event.listen(engine, "before_cursor_execute", record)
        try:
            rows = client.get("/api/digests")
        finally:
            event.remove(engine, "before_cursor_execute", record)
        assert rows.status_code == 200
        assert rows.json()[-1]["topics"] == ["First", "Second"]
        assert len(topic_queries) == 1
        assert not topic_queries[0][1]


def test_history_list_ignores_a_digest_saved_between_its_two_queries(test_settings):
    with TestClient(create_app(test_settings)) as client:
        seed_history(client)
        factory = client.app.state.session_factory
        with factory() as session:
            engine = session.get_bind()
        saved = []

        def save_digest_first(_conn, _cursor, statement, _params, _context, _executemany):
            # A run finishing while History loads commits between the digest and topic SELECTs.
            if "FROM digest_topics" in statement and not saved:
                with factory() as other:
                    run = DigestRun(status="succeeded")
                    other.add(run)
                    other.flush()
                    digest = Digest(run_id=run.id, model_id="test", item_count=1, source_count=1)
                    other.add(digest)
                    other.flush()
                    other.add(DigestTopic(digest_id=digest.id, position=0, title="Late", overview="Saved"))
                    other.commit()
                    saved.append(digest.id)

        event.listen(engine, "before_cursor_execute", save_digest_first)
        try:
            rows = client.get("/api/digests")
        finally:
            event.remove(engine, "before_cursor_execute", save_digest_first)
        assert saved
        assert rows.status_code == 200
        assert [row["id"] for row in rows.json()] == [3, 2, 1]
        assert rows.json()[-1]["topics"] == ["First", "Second"]
        assert client.get("/api/digests").json()[0]["topics"] == ["Late"]

def test_digest_detail_uses_snapshot_positions_and_survives_source_deletion(test_settings):
    with TestClient(create_app(test_settings)) as client:
        source_id = seed_history(client)
        response = client.get("/api/digests/1")
        assert response.status_code == 200
        before = response.json()
        assert before["model_id"] == "test"
        assert before["language"] is None
        assert before["item_count"] == 1
        assert before["source_count"] == 1
        assert [topic["title"] for topic in before["topics"]] == ["First", "Second"]
        assert [item["title"] for item in before["topics"][0]["items"]] == [
            "Saved first", "Saved second",
        ]
        assert before["topics"][0]["overview"] == "Earlier"
        assert before["topics"][0]["items"][0] == {
            "title": "Saved first", "link": "https://example.test/first",
            "source_name": "Saved source", "source_kind": None, "published_at": before["created_at"],
            "summary": "Saved summary", "summary_unavailable": False, "also_read": [],
        }
        assert before["topics"][0]["items"][1]["summary_unavailable"] is True
        assert before["topics"][1]["items"][0]["link"] == "https://example.test/other"
        assert client.delete(f"/api/sources/{source_id}").status_code == 204
        assert client.get("/api/digests/1").json() == before
        assert client.get("/api/digests/999").json()["error"]["code"] == "not_found"


def test_snapshot_keeps_only_used_context_after_source_deletion(test_settings, monkeypatch):
    from dataclasses import replace
    from sqlalchemy import select
    from catchup.crypto import encrypt_key
    from catchup.digest.runner import run_digest, start_run
    from catchup.models import ModelConfig
    from test_digest_runner import FakeModel, stub_collection

    settings = replace(test_settings, secret_key="test-only-context-secret")
    with TestClient(create_app(settings)) as client:
        with client.app.state.session_factory() as session:
            session.add(ModelConfig(
                id=1, base_url="https://model.example", model_id="test",
                api_key_encrypted=encrypt_key("dummy", settings.secret_key), api_key_last4="ummy",
            ))
            source = Source(title="Blog", site_url="https://site.example",
                            feed_url="https://site.example/feed", input_url="https://site.example/feed")
            session.add(source)
            session.flush()
            item = Item(source_id=source.id, identity_key="post", link="https://site.example/post",
                        title="Post", content_text="Announcement", content_origin="feed",
                        state="pending", context_status="gathered")
            session.add(item)
            session.flush()
            source_id = source.id
            session.add_all([
                ItemContext(item_id=item.id, ref=ref, kind="link", url=f"https://docs.example/{ref}",
                            title=title, text="Details", position=position)
                for position, (ref, title) in enumerate([("L1", "Release"), ("L2", "Unrelated")], 1)
            ])
            session.commit()
        stub_collection(monkeypatch)
        client.app.state.model_client_factory = lambda *_: FakeModel([
            {"summary": "The release.", "used": ["L1", "unknown"]},
            {"topics": [{"title": "News", "overview": "Recent", "item_refs": ["i1"]}]},
        ])
        run = start_run(client.app, background=False)
        run_digest(client.app, run.id)
        assert client.get(f"/api/digest-runs/{run.id}").json()["status"] == "succeeded"
        digest_id = client.get(f"/api/digest-runs/{run.id}").json()["digest_id"]
        saved = client.get(f"/api/digests/{digest_id}").json()
        assert saved["topics"][0]["items"][0]["also_read"] == [
            {"title": "Release", "url": "https://docs.example/L1", "kind": "link"},
        ]
        assert client.delete(f"/api/sources/{source_id}").status_code == 204
        assert client.get(f"/api/digests/{digest_id}").json() == saved


def test_saved_language_and_kind_survive_setting_change_and_source_deletion(test_settings):
    with TestClient(create_app(test_settings)) as client:
        source_id = seed_history(client)
        with client.app.state.session_factory() as session:
            session.get(Digest, 1).language = "zh-Hans"
            session.add(AppSettings(id=1, digest_language="zh-Hans"))
            session.query(DigestItem).filter(DigestItem.digest_id == 1).update(
                {"source_kind": "podcast"}
            )
            session.commit()
        saved = client.get("/api/digests/1").json()
        assert saved["language"] == "zh-Hans"
        assert saved["topics"][0]["items"][0]["source_kind"] == "podcast"
        with client.app.state.session_factory() as session:
            session.get(AppSettings, 1).digest_language = "en"
            session.commit()
        assert client.delete(f"/api/sources/{source_id}").status_code == 204
        assert client.get("/api/digests/1").json() == saved


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
