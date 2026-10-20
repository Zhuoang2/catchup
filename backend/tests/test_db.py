import warnings
from pathlib import Path

from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import SAWarning

from catchup.config import Settings
import catchup
from catchup.db import Base, make_engine, migrate
from catchup.main import create_app
import catchup.models  # noqa: F401 - register tables on Base


def test_startup_migrates_database_and_enables_wal(test_settings: Settings) -> None:
    with TestClient(create_app(test_settings)) as client:
        engine = client.app.state.engine
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version", "model_config", "app_settings", "sources", "items",
            "source_checks", "digest_runs", "digests", "digest_topics", "digest_items", "item_contexts",
        }
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
        assert inspect(engine).get_foreign_keys("digest_runs") == []
    assert (test_settings.data_dir / "catchup.sqlite3").exists()


def test_metadata_has_no_foreign_key_cycle() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", SAWarning)
        names = [table.name for table in Base.metadata.sorted_tables]
    assert names.index("digest_runs") < names.index("digests")


def test_migrations_live_inside_package() -> None:
    migrations = Path(catchup.__file__).resolve().parent / "migrations"
    assert (migrations / "env.py").is_file()
    assert (migrations / "script.py.mako").is_file()
    assert (migrations / "versions" / "0001_initial.py").is_file()
    assert (migrations / "versions" / "0002_transcripts.py").is_file()
    assert (migrations / "versions" / "0003_digest_snapshot.py").is_file()
    assert (migrations / "versions" / "0004_item_context.py").is_file()
    assert (migrations / "versions" / "0005_item_images.py").is_file()


def test_existing_database_at_old_revision_is_unchanged(tmp_path) -> None:
    engine = make_engine(tmp_path)
    try:
        # A pre-move installation has the same Alembic revision id and schema.
        migrate(engine)
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO app_settings (id, digest_language, updated_at) "
                     "VALUES (1, 'zh-Hans', '2026-10-04 00:00:00')")
            )
            before = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).scalars().all()
        migrate(engine)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0005_item_images"
            assert connection.execute(text("SELECT digest_language FROM app_settings WHERE id=1")).scalar_one() == "zh-Hans"
            assert connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).scalars().all() == before
    finally:
        engine.dispose()


def test_upgrade_existing_rows_and_downgrade(tmp_path) -> None:
    engine = make_engine(tmp_path)
    config = Config()
    config.set_main_option(
        "script_location", str(Path(catchup.__file__).resolve().parent / "migrations")
    )
    config.attributes["connection"] = engine
    try:
        command.upgrade(config, "0001_initial")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO app_settings (id, digest_language, updated_at) "
                "VALUES (1, 'en', '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO sources (id, title, site_url, feed_url, input_url, created_at) "
                "VALUES (1, 'Show', 'https://example.com', 'https://example.com/feed', "
                "'https://example.com/feed', '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO items (id, source_id, identity_key, link, title, discovered_at, "
                "content_text, content_origin, state) VALUES "
                "(1, 1, 'one', 'https://example.com/one', 'Episode', '2026-10-04', "
                "'text', 'feed', 'delivered')"
            ))
            connection.execute(text(
                "INSERT INTO digest_runs (id, status, items_total, items_done, started_at) "
                "VALUES (1, 'succeeded', 1, 1, '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO digests (id, run_id, created_at, model_id, item_count, source_count) "
                "VALUES (1, 1, '2026-10-04', 'model', 1, 1)"
            ))
            connection.execute(text(
                "INSERT INTO digest_topics (id, digest_id, position, title, overview) "
                "VALUES (1, 1, 0, 'Topic', 'Overview')"
            ))
            connection.execute(text(
                "INSERT INTO digest_items (id, digest_id, topic_id, position, item_id, title, "
                "link, source_name, summary_unavailable) VALUES "
                "(1, 1, 1, 0, 1, 'Episode', 'https://example.com/one', 'Show', 0)"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT kind FROM sources")).scalar_one() == "feed"
            assert connection.execute(text("SELECT transcript_status FROM items")).scalar_one() is None
            assert connection.execute(text("SELECT kind FROM digest_topics")).scalar_one() == "topic"
            assert connection.execute(text(
                "SELECT youtube_captions, youtube_skip_shorts FROM app_settings"
            )).one() == (0, 1)
            assert connection.execute(text("SELECT update_reason FROM digest_items")).scalar_one() is None
            assert connection.execute(text("SELECT language FROM digests")).scalar_one() is None
            assert connection.execute(text("SELECT source_kind FROM digest_items")).scalar_one() is None
        command.downgrade(config, "0001_initial")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial"
            assert "kind" not in {col["name"] for col in inspect(engine).get_columns("sources")}
            assert connection.execute(text("SELECT title FROM digest_items")).scalar_one() == "Episode"
    finally:
        engine.dispose()


def test_snapshot_migration_from_0002_preserves_existing_rows(tmp_path) -> None:
    engine = make_engine(tmp_path)
    config = Config()
    config.set_main_option("script_location", str(Path(catchup.__file__).resolve().parent / "migrations"))
    config.attributes["connection"] = engine
    try:
        command.upgrade(config, "0002_transcripts")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO digest_runs (id, status, items_total, items_done, started_at) "
                "VALUES (1, 'succeeded', 1, 1, '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO digests (id, run_id, created_at, model_id, item_count, source_count) "
                "VALUES (1, 1, '2026-10-04', 'model', 1, 1)"
            ))
            connection.execute(text(
                "INSERT INTO digest_topics (id, digest_id, position, title, overview) "
                "VALUES (1, 1, 0, 'Topic', 'Overview')"
            ))
            connection.execute(text(
                "INSERT INTO digest_items (id, digest_id, topic_id, position, title, link, "
                "source_name, summary_unavailable) VALUES "
                "(1, 1, 1, 0, 'Title', 'https://example.test/item', 'Source', 0)"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT language FROM digests")).scalar_one() is None
            assert connection.execute(text("SELECT source_kind FROM digest_items")).scalar_one() is None
        command.downgrade(config, "0002_transcripts")
        assert "language" not in {col["name"] for col in inspect(engine).get_columns("digests")}
        assert "source_kind" not in {col["name"] for col in inspect(engine).get_columns("digest_items")}
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title FROM digest_items")).scalar_one() == "Title"
    finally:
        engine.dispose()


def test_context_migration_from_0003_preserves_rows_and_downgrades(tmp_path) -> None:
    engine = make_engine(tmp_path)
    config = Config()
    config.set_main_option("script_location", str(Path(catchup.__file__).resolve().parent / "migrations"))
    config.attributes["connection"] = engine
    try:
        command.upgrade(config, "0003_digest_snapshot")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO sources (id, title, site_url, feed_url, input_url, created_at) "
                "VALUES (1, 'News', 'https://site.example', 'https://site.example/feed', "
                "'https://site.example/feed', '2026-10-01')"
            ))
            connection.execute(text(
                "INSERT INTO items (id, source_id, identity_key, link, title, discovered_at, "
                "content_text, content_origin, state) VALUES "
                "(1, 1, 'post', 'https://site.example/post', 'Post', '2026-10-01', "
                "'Text', 'feed', 'pending')"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title, context_status FROM items WHERE id=1")).one() == ("Post", None)
            assert connection.execute(text("SELECT context_total, context_done FROM digest_runs")).all() == []
            assert "item_contexts" in inspect(engine).get_table_names()
        command.downgrade(config, "0003_digest_snapshot")
        assert "item_contexts" not in inspect(engine).get_table_names()
        assert "context_status" not in {col["name"] for col in inspect(engine).get_columns("items")}
        assert "context_links" not in {col["name"] for col in inspect(engine).get_columns("digest_items")}
        assert "context_total" not in {col["name"] for col in inspect(engine).get_columns("digest_runs")}
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title FROM items WHERE id=1")).scalar_one() == "Post"
    finally:
        engine.dispose()


def test_image_migration_from_0004_preserves_rows_and_downgrades(tmp_path) -> None:
    engine = make_engine(tmp_path)
    config = Config()
    config.set_main_option("script_location", str(Path(catchup.__file__).resolve().parent / "migrations"))
    config.attributes["connection"] = engine
    try:
        command.upgrade(config, "0004_item_context")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO app_settings (id, digest_language, updated_at) "
                "VALUES (1, 'zh-Hans', '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO sources (id, title, site_url, feed_url, input_url, created_at) "
                "VALUES (1, 'News', 'https://site.example', 'https://site.example/feed', "
                "'https://site.example/feed', '2026-10-04')"
            ))
            connection.execute(text(
                "INSERT INTO items (id, source_id, identity_key, link, title, discovered_at, "
                "content_text, content_origin, state) VALUES "
                "(1, 1, 'one', 'https://site.example/one', 'Post', '2026-10-04', "
                "'Text', 'feed', 'pending')"
            ))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0005_item_images"
            assert connection.execute(text(
                "SELECT image_candidates, summary_images FROM items WHERE id=1"
            )).one() == (None, None)
            assert connection.execute(text(
                "SELECT digest_language, show_images FROM app_settings WHERE id=1"
            )).one() == ("zh-Hans", 1)
            assert "images" in {col["name"] for col in inspect(engine).get_columns("digest_items")}
        command.downgrade(config, "0004_item_context")
        assert "image_candidates" not in {c["name"] for c in inspect(engine).get_columns("items")}
        assert "summary_images" not in {c["name"] for c in inspect(engine).get_columns("items")}
        assert "images" not in {c["name"] for c in inspect(engine).get_columns("digest_items")}
        assert "show_images" not in {c["name"] for c in inspect(engine).get_columns("app_settings")}
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title FROM items WHERE id=1")).scalar_one() == "Post"
    finally:
        engine.dispose()
