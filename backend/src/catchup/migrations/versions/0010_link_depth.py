"""Store the linked-page level."""

from alembic import op
import sqlalchemy as sa

revision = "0010_link_depth"
down_revision = "0009_model_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("app_settings") as batch:
        batch.add_column(sa.Column(
            "link_depth", sa.String(16), nullable=False, server_default="normal",
        ))


def downgrade() -> None:
    with op.batch_alter_table("app_settings", recreate="never") as batch:
        batch.drop_column("link_depth")
