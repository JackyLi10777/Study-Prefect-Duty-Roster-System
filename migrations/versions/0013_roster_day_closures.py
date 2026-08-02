"""Persist whole-day roster closures as stable weekday codes."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roster_day_closures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roster_week_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "day IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY')",
            name="ck_roster_day_closure_day",
        ),
        sa.ForeignKeyConstraint(
            ["roster_week_id"],
            ["roster_weeks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "roster_week_id",
            "day",
            name="uq_roster_day_closure",
        ),
    )


def downgrade() -> None:
    op.drop_table("roster_day_closures")
