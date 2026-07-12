"""Add auditable leave declarations used before roster generation."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leave_declarations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("prefect_id", sa.String(length=64), sa.ForeignKey("prefects.id"), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("week_start", "prefect_id", "day", name="uq_leave_declaration"),
    )


def downgrade() -> None:
    op.drop_table("leave_declarations")
