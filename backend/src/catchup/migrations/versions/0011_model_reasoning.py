"""Store the model Reasoning choice.

A downgrade loses the Reasoning choice, keeping the saved provider, URL,
model and key.
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_model_reasoning"
down_revision = "0010_link_depth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_config") as batch:
        batch.add_column(sa.Column(
            "reasoning", sa.String(16), nullable=False, server_default="default",
        ))


def downgrade() -> None:
    with op.batch_alter_table("model_config", recreate="never") as batch:
        batch.drop_column("reasoning")
