import warnings
from pathlib import Path

from fastapi.testclient import TestClient
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
            "source_checks", "digest_runs", "digests", "digest_topics", "digest_items",
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
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001_initial"
            assert connection.execute(text("SELECT digest_language FROM app_settings WHERE id=1")).scalar_one() == "zh-Hans"
            assert connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).scalars().all() == before
    finally:
        engine.dispose()
