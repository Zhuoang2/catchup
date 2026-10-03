from dataclasses import replace

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from catchup.config import Settings
from catchup.main import create_app


def test_startup_migrates_database_and_enables_wal(tmp_path) -> None:
    settings = replace(Settings.from_env(), data_dir=tmp_path)
    with TestClient(create_app(settings)) as client:
        engine = client.app.state.engine
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version", "model_config", "app_settings", "sources", "items",
            "source_checks", "digest_runs", "digests", "digest_topics", "digest_items",
        }
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    assert (tmp_path / "catchup.sqlite3").exists()
