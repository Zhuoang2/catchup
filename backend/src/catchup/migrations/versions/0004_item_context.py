"""Keep gathered item context and its digest citations."""

from alembic import op
import sqlalchemy as sa


revision = "0004_item_context"
down_revision = "0003_digest_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("entry_links", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("comments_url", sa.Text(), nullable=True))
        batch.add_column(sa.Column("comment_feed_url", sa.Text(), nullable=True))
        batch.add_column(sa.Column("comment_count", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("entry_author", sa.Text(), nullable=True))
        batch.add_column(sa.Column("context_status", sa.String(16), nullable=True))
    op.create_table(
        "item_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ref", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="0"),
    )
    with op.batch_alter_table("digest_items") as batch:
        batch.add_column(sa.Column("context_links", sa.JSON(), nullable=True))
    with op.batch_alter_table("digest_runs") as batch:
        batch.add_column(sa.Column("context_total", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("context_done", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("digest_runs", recreate="never") as batch:
        batch.drop_column("context_done")
        batch.drop_column("context_total")
    with op.batch_alter_table("digest_items", recreate="never") as batch:
        batch.drop_column("context_links")
    op.drop_table("item_contexts")
    with op.batch_alter_table("items", recreate="never") as batch:
        for name in ("context_status", "entry_author", "comment_count", "comment_feed_url",
                     "comments_url", "entry_links"):
            batch.drop_column(name)
