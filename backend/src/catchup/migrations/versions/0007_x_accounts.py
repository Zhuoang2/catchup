"""Credentials, followed accounts, and X read counters."""

from alembic import op
import sqlalchemy as sa


revision = "0007_x_accounts"
down_revision = "0006_captures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "x_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_last4", sa.String(4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "x_accounts",
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(32), nullable=False),
        sa.Column("username", sa.String(15), nullable=False),
        sa.Column("newest_id", sa.String(32)),
        sa.Column("gap_since_id", sa.String(32)),
        sa.Column("gap_until_id", sa.String(32)),
        sa.Column("followed_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("digest_runs") as batch:
        batch.add_column(sa.Column("x_reads", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("x_waiting_accounts", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.execute("DELETE FROM sources WHERE kind = 'x'")
    op.drop_table("x_accounts")
    op.drop_table("x_credentials")
    with op.batch_alter_table("digest_runs", recreate="never") as batch:
        batch.drop_column("x_waiting_accounts")
        batch.drop_column("x_reads")
