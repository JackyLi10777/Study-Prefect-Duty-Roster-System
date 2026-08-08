"""Persist week-local unavailable roster slots as stable cell coordinates."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roster_slot_exceptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roster_week_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("post_code", sa.String(length=32), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.String(length=24),
            nullable=False,
            server_default="unavailable",
        ),
        sa.Column("reason_code", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "day IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY')",
            name="ck_roster_slot_exception_day",
        ),
        sa.CheckConstraint(
            "kind = 'unavailable'",
            name="ck_roster_slot_exception_kind",
        ),
        sa.CheckConstraint(
            "(post_code IN ('ASSIST_IN_CHARGE', 'ROOM_302') AND slot_index = 1) OR "
            "(post_code IN ('ROOM_303', 'ROOM_202') AND slot_index IN (1, 2))",
            name="ck_roster_slot_exception_cell",
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
            "post_code",
            "slot_index",
            name="uq_roster_slot_exception",
        ),
    )


def downgrade() -> None:
    op.drop_table("roster_slot_exceptions")
