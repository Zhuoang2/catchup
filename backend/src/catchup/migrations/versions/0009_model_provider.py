"""Store the model provider.

A downgrade turns Anthropic configurations into OpenAI-compatible ones,
keeping the saved URL, model and key. Test again with the right provider and key.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_model_provider"
down_revision = "0008_run_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("model_config") as batch:
        batch.add_column(sa.Column(
            "provider", sa.String(32), nullable=False, server_default="openai_compatible",
        ))


def downgrade() -> None:
    with op.batch_alter_table("model_config", recreate="never") as batch:
        batch.drop_column("provider")
