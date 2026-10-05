"""Source kinds, transcript states, creator updates and model usage."""

from alembic import op
import sqlalchemy as sa


revision = "0002_transcripts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sources") as batch:
        batch.add_column(sa.Column("kind", sa.String(16), nullable=False, server_default="feed"))
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("transcript_status", sa.String(16)))
    with op.batch_alter_table("app_settings") as batch:
        batch.add_column(sa.Column("youtube_captions", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("youtube_skip_shorts", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("model_config") as batch:
        batch.add_column(sa.Column("context_window", sa.Integer()))
    with op.batch_alter_table("digest_runs") as batch:
        batch.add_column(sa.Column("prompt_tokens", sa.Integer()))
        batch.add_column(sa.Column("completion_tokens", sa.Integer()))
        batch.add_column(sa.Column("waiting_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("deferred_count", sa.Integer(), nullable=False, server_default="0"))
    with op.batch_alter_table("digests") as batch:
        batch.add_column(sa.Column("transcript_wait_days", sa.Integer(), nullable=False, server_default="7"))
    with op.batch_alter_table("digest_topics") as batch:
        batch.add_column(sa.Column("kind", sa.String(16), nullable=False, server_default="topic"))
    with op.batch_alter_table("digest_items") as batch:
        batch.add_column(sa.Column("update_reason", sa.String(16)))


def downgrade() -> None:
    for table, columns in (
        ("digest_items", ("update_reason",)),
        ("digest_topics", ("kind",)),
        ("digests", ("transcript_wait_days",)),
        ("digest_runs", ("deferred_count", "waiting_count", "completion_tokens", "prompt_tokens")),
        ("model_config", ("context_window",)),
        ("app_settings", ("youtube_skip_shorts", "youtube_captions")),
        ("items", ("transcript_status",)),
        ("sources", ("kind",)),
    ):
        # DROP COLUMN is supported by current SQLite, and avoiding a table
        # rebuild preserves referenced parent rows while foreign keys are on.
        with op.batch_alter_table(table, recreate="never") as batch:
            for column in columns:
                batch.drop_column(column)
