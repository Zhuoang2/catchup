import warnings

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import SAWarning

from catchup.config import Settings
from catchup.db import Base
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
