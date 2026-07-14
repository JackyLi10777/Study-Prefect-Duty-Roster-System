"""Allow a pre-generation leave declaration without a supplied reason."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("leave_declarations") as batch:
        batch.alter_column("reason", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE leave_declarations SET reason = '' WHERE reason IS NULL")
    with op.batch_alter_table("leave_declarations") as batch:
        batch.alter_column("reason", existing_type=sa.Text(), nullable=False)
