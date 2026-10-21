"""Browser connection tokens and saved-page metadata."""

from alembic import op
import sqlalchemy as sa


revision = "0006_captures"
down_revision = "0005_item_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extension_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    with op.batch_alter_table("items") as batch:
        batch.add_column(sa.Column("site_name", sa.String(200)))
        batch.add_column(sa.Column("captured_replies", sa.JSON()))


def downgrade() -> None:
    op.execute("DELETE FROM sources WHERE kind = 'capture'")
    with op.batch_alter_table("items", recreate="never") as batch:
        batch.drop_column("captured_replies")
        batch.drop_column("site_name")
    op.drop_table("extension_tokens")
