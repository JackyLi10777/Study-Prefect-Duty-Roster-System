"""Persist the bounded history-priority setting used for draft generation."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("roster_weeks") as batch:
        batch.add_column(
            sa.Column(
                "history_priority_multiplier",
                sa.Float(),
                nullable=False,
                server_default="1.0",
            )
        )
        batch.create_check_constraint(
            "ck_roster_week_history_priority_multiplier",
            "history_priority_multiplier >= 0.8 AND history_priority_multiplier <= 2.0",
        )


def downgrade() -> None:
    with op.batch_alter_table("roster_weeks") as batch:
        batch.drop_constraint("ck_roster_week_history_priority_multiplier", type_="check")
        batch.drop_column("history_priority_multiplier")
