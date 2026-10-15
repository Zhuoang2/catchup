"""Save digest language and source kinds as part of the snapshot."""

from alembic import op
import sqlalchemy as sa


revision = "0003_digest_snapshot"
down_revision = "0002_transcripts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("digests") as batch:
        batch.add_column(sa.Column("language", sa.String(40), nullable=True))
    with op.batch_alter_table("digest_items") as batch:
        batch.add_column(sa.Column("source_kind", sa.String(16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("digest_items", recreate="never") as batch:
        batch.drop_column("source_kind")
    with op.batch_alter_table("digests", recreate="never") as batch:
        batch.drop_column("language")
