"""Initial schema for the item ledger and digest snapshots."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_key_last4", sa.String(4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_language", sa.String(40), server_default="en", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("site_url", sa.Text(), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False, unique=True),
        sa.Column("input_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_check_at", sa.DateTime(timezone=True)),
        sa.Column("last_check_status", sa.String(32)),
    )
    op.create_table(
        "digest_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("items_total", sa.Integer(), nullable=False),
        sa.Column("items_done", sa.Integer(), nullable=False),
        sa.Column("error_kind", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("digest_id", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_origin", sa.String(16), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_language", sa.String(40)),
        sa.Column("state", sa.String(16), nullable=False),
        sa.UniqueConstraint("source_id", "identity_key"),
    )
    op.create_index("ix_items_source_link", "items", ["source_id", "link"])
    op.create_table(
        "source_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("digest_runs.id")),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("possible_gap", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("http_status", sa.Integer()),
        sa.Column("entries_seen", sa.Integer(), nullable=False),
        sa.Column("new_count", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("digest_runs.id"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "digest_topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_id", sa.Integer(), sa.ForeignKey("digests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
    )
    op.create_table(
        "digest_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("digest_id", sa.Integer(), sa.ForeignKey("digests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("digest_topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("summary", sa.Text()),
        sa.Column("summary_unavailable", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "digest_items", "digest_topics", "digests", "source_checks", "items",
        "digest_runs", "sources", "app_settings", "model_config",
    ):
        op.drop_table(table)
