"""Store marks on saved digest items.

A downgrade loses every bookmark, like, rating, and note.
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_digest_item_marks"
down_revision = "0011_model_reasoning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digest_item_marks",
        sa.Column("digest_item_id", sa.Integer(),
                  sa.ForeignKey("digest_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bookmarked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("liked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating", sa.String(8), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("digest_item_marks")
