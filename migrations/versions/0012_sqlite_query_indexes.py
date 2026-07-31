"""Add measured SQLite query indexes and fixed-weekday integrity."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _assert_unique_active_assist_weekdays() -> None:
    conflict = op.get_bind().execute(
        sa.text(
            "SELECT fixed_general_duty, COUNT(*) AS total "
            "FROM prefects "
            "WHERE active = 1 AND role_code = 'assistant_head' "
            "AND fixed_general_duty <> 'NONE' "
            "GROUP BY fixed_general_duty HAVING COUNT(*) > 1 "
            "ORDER BY fixed_general_duty LIMIT 1"
        )
    ).first()
    if conflict is not None:
        raise RuntimeError(
            "Migration stopped safely: more than one active Assistant Head Study Prefect "
            f"owns fixed weekday {conflict[0]}. Review the directory and keep one owner "
            "before retrying; no student record was changed automatically."
        )


def upgrade() -> None:
    _assert_unique_active_assist_weekdays()
    op.create_index(
        "uq_prefects_active_assist_fixed_weekday",
        "prefects",
        ["fixed_general_duty"],
        unique=True,
        sqlite_where=sa.text(
            "active = 1 AND role_code = 'assistant_head' "
            "AND fixed_general_duty <> 'NONE'"
        ),
    )
    op.create_index(
        "ix_roster_weeks_status_week_start_id",
        "roster_weeks",
        ["status", "week_start", "id"],
    )
    op.create_index(
        "ix_fairness_ledger_roster_week_created_id",
        "fairness_ledger",
        ["roster_week_id", "created_at", "id"],
    )
    op.create_index(
        "ix_leave_adjustments_roster_week_created_id",
        "leave_adjustments",
        ["roster_week_id", "created_at", "id"],
    )
    op.execute(
        "CREATE INDEX ix_backup_runs_created_id "
        "ON backup_runs (created_at DESC, id DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_backup_runs_created_id", table_name="backup_runs")
    op.drop_index(
        "ix_leave_adjustments_roster_week_created_id",
        table_name="leave_adjustments",
    )
    op.drop_index(
        "ix_fairness_ledger_roster_week_created_id",
        table_name="fairness_ledger",
    )
    op.drop_index("ix_roster_weeks_status_week_start_id", table_name="roster_weeks")
    op.drop_index(
        "uq_prefects_active_assist_fixed_weekday",
        table_name="prefects",
    )
