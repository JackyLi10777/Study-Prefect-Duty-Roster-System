"""Add stable roles, idempotent adjustments, and reconcilable fairness anchors."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("prefects") as batch:
        batch.add_column(sa.Column("history_weight_anchor", sa.Float(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("history_duties_anchor", sa.Integer(), nullable=False, server_default="0"))
        batch.create_check_constraint(
            "ck_prefect_role_code",
            "role_code IN ('assistant_head', 'study_prefect')",
        )

    with op.batch_alter_table("fairness_ledger") as batch:
        batch.add_column(sa.Column("duty_delta", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("source_type", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("source_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("operation_id", sa.String(length=64), nullable=True))

    op.execute(
        """
        UPDATE fairness_ledger
        SET duty_delta = CASE
            WHEN event_type IN ('roster_published', 'leave_adjustment_credit') THEN 1
            WHEN event_type = 'leave_adjustment_debit' THEN -1
            ELSE 0
        END,
        source_type = CASE
            WHEN event_type = 'roster_published' THEN 'roster_publish'
            ELSE 'legacy_adjustment'
        END,
        source_id = CAST(id AS TEXT),
        operation_id = 'legacy-ledger:' || CAST(id AS TEXT)
        """
    )
    op.execute(
        """
        UPDATE prefects
        SET history_weight_anchor = history_weight - COALESCE(
                (SELECT SUM(delta) FROM fairness_ledger WHERE fairness_ledger.prefect_id = prefects.id), 0
            ),
            history_duties_anchor = history_duties - COALESCE(
                (SELECT SUM(duty_delta) FROM fairness_ledger WHERE fairness_ledger.prefect_id = prefects.id), 0
            )
        """
    )

    with op.batch_alter_table("fairness_ledger") as batch:
        batch.alter_column("source_type", existing_type=sa.String(length=32), nullable=False)
        batch.alter_column("source_id", existing_type=sa.String(length=64), nullable=False)
        batch.alter_column("operation_id", existing_type=sa.String(length=64), nullable=False)
        batch.create_unique_constraint(
            "uq_fairness_operation_entry",
            ("operation_id", "assignment_id", "prefect_id", "event_type"),
        )

    with op.batch_alter_table("leave_adjustments") as batch:
        batch.add_column(sa.Column("command_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE leave_adjustments SET command_id = 'legacy-adjustment:' || CAST(id AS TEXT)")
    with op.batch_alter_table("leave_adjustments") as batch:
        batch.alter_column("command_id", existing_type=sa.String(length=64), nullable=False)
        batch.create_unique_constraint("uq_leave_adjustment_command", ("command_id",))


def downgrade() -> None:
    with op.batch_alter_table("leave_adjustments") as batch:
        batch.drop_constraint("uq_leave_adjustment_command", type_="unique")
        batch.drop_column("command_id")
    with op.batch_alter_table("fairness_ledger") as batch:
        batch.drop_constraint("uq_fairness_operation_entry", type_="unique")
        batch.drop_column("operation_id")
        batch.drop_column("source_id")
        batch.drop_column("source_type")
        batch.drop_column("duty_delta")
    with op.batch_alter_table("prefects") as batch:
        batch.drop_constraint("ck_prefect_role_code", type_="check")
        batch.drop_column("history_duties_anchor")
        batch.drop_column("history_weight_anchor")
