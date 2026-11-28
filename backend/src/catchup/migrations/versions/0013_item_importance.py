"""Store item importance and the digest reading limit."""

from alembic import op
import sqlalchemy as sa

revision = "0013_item_importance"
down_revision = "0012_digest_item_marks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("importance", sa.Integer(), nullable=True))
    with op.batch_alter_table("digest_items") as batch:
        batch.add_column(sa.Column("importance", sa.Integer(), nullable=True))
    with op.batch_alter_table("app_settings") as batch:
        batch.add_column(sa.Column("top_items", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("app_settings", recreate="never") as batch:
        batch.drop_column("top_items")
    with op.batch_alter_table("digest_items", recreate="never") as batch:
        batch.drop_column("importance")
    with op.batch_alter_table("items", recreate="never") as batch:
        batch.drop_column("importance")
