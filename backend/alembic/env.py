"""Alembic environment; application startup supplies its configured engine."""

from alembic import context

from catchup.db import Base
import catchup.models  # noqa: F401 - register model metadata


target_metadata = Base.metadata
engine = context.config.attributes["connection"]

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
