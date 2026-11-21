"""Persist stage durations and the number of sources checked by a run."""

from alembic import op
import sqlalchemy as sa


revision = "0008_run_progress"
down_revision = "0007_x_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("digest_runs") as batch:
        batch.add_column(sa.Column("stage_seconds", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("sources_total", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        "UPDATE digest_runs SET sources_total = "
        "(SELECT COUNT(*) FROM source_checks WHERE source_checks.run_id = digest_runs.id)"
    )


def downgrade() -> None:
    with op.batch_alter_table("digest_runs", recreate="never") as batch:
        batch.drop_column("sources_total")
        batch.drop_column("stage_seconds")
