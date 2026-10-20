"""Keep feed image candidates, summary choices, and digest images."""

from alembic import op
import sqlalchemy as sa


revision = "0005_item_images"
down_revision = "0004_item_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("image_candidates", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("summary_images", sa.JSON(), nullable=True))
    with op.batch_alter_table("digest_items") as batch:
        batch.add_column(sa.Column("images", sa.JSON(), nullable=True))
    with op.batch_alter_table("app_settings") as batch:
        batch.add_column(sa.Column("show_images", sa.Boolean(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("app_settings", recreate="never") as batch:
        batch.drop_column("show_images")
    with op.batch_alter_table("digest_items", recreate="never") as batch:
        batch.drop_column("images")
    with op.batch_alter_table("items", recreate="never") as batch:
        batch.drop_column("summary_images")
        batch.drop_column("image_candidates")
