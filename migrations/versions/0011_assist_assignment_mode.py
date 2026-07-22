"""Persist the Assist. in charge assignment policy selected for each week."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add an immutable-by-read roster snapshot with a safe legacy backfill."""

    with op.batch_alter_table("roster_weeks", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "assist_assignment_mode",
                sa.String(length=32),
                nullable=False,
                server_default="legacy_fixed_weekday",
            )
        )
        batch.create_check_constraint(
            "ck_roster_week_assist_assignment_mode",
            "assist_assignment_mode IN ('legacy_fixed_weekday', 'flexible_weekly')",
        )


def downgrade() -> None:
    legacy_weeks = int(
        op.get_bind().execute(
            sa.text(
                "SELECT COUNT(*) FROM roster_weeks "
                "WHERE assist_assignment_mode = 'legacy_fixed_weekday'"
            )
        ).scalar_one()
    )
    if legacy_weeks:
        raise RuntimeError(
            "Cannot downgrade Assist assignment modes while legacy fixed-weekday roster history exists."
        )
    with op.batch_alter_table("roster_weeks", recreate="always") as batch:
        batch.drop_constraint(
            "ck_roster_week_assist_assignment_mode",
            type_="check",
        )
        batch.drop_column("assist_assignment_mode")
