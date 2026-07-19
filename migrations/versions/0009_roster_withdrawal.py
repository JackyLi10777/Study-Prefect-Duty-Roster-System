"""Add auditable published-roster withdrawal and active-week uniqueness."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


_NAMING_CONVENTION = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def upgrade() -> None:
    with op.batch_alter_table(
        "roster_weeks",
        naming_convention=_NAMING_CONVENTION,
        recreate="always",
    ) as batch:
        batch.drop_constraint("uq_roster_weeks_week_start", type_="unique")
        batch.add_column(sa.Column("withdrawn_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("withdrawal_reason", sa.Text(), nullable=True))
        batch.create_check_constraint(
            "ck_roster_week_status",
            "status IN ('draft', 'published', 'withdrawn')",
        )
    op.create_index(
        "uq_roster_weeks_active_week_start",
        "roster_weeks",
        ["week_start"],
        unique=True,
        sqlite_where=sa.text("status IN ('draft', 'published')"),
    )


def downgrade() -> None:
    withdrawn = int(
        op.get_bind().execute(
            sa.text("SELECT COUNT(*) FROM roster_weeks WHERE status = 'withdrawn'")
        ).scalar_one()
    )
    if withdrawn:
        raise RuntimeError(
            "Cannot downgrade roster withdrawal while withdrawn roster history exists."
        )
    op.drop_index("uq_roster_weeks_active_week_start", table_name="roster_weeks")
    with op.batch_alter_table(
        "roster_weeks",
        naming_convention=_NAMING_CONVENTION,
        recreate="always",
    ) as batch:
        batch.drop_constraint("ck_roster_week_status", type_="check")
        batch.drop_column("withdrawal_reason")
        batch.drop_column("withdrawn_at")
        batch.create_unique_constraint("uq_roster_weeks_week_start", ["week_start"])
