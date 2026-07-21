"""Index fairness-ledger reconciliation by prefect."""

from __future__ import annotations

from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_fairness_ledger_prefect_id",
        "fairness_ledger",
        ["prefect_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fairness_ledger_prefect_id",
        table_name="fairness_ledger",
    )
