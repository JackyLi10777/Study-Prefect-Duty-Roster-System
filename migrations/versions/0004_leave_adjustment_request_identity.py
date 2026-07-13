"""Bind leave-adjustment idempotency keys to one canonical request."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("leave_adjustments") as batch:
        batch.add_column(sa.Column("request_fingerprint", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("committed_version", sa.Integer(), nullable=True))

    # Historical operations predate canonical request fingerprints. These
    # values cannot equal a SHA-256 fingerprint, so attempted legacy replay
    # fails closed instead of being mistaken for an exact retry.
    op.execute(
        "UPDATE leave_adjustments "
        "SET request_fingerprint = 'legacy-adjustment:' || CAST(id AS TEXT), "
        "committed_version = 0"
    )

    with op.batch_alter_table("leave_adjustments") as batch:
        batch.alter_column("request_fingerprint", existing_type=sa.String(length=64), nullable=False)
        batch.alter_column("committed_version", existing_type=sa.Integer(), nullable=False)
        batch.create_check_constraint("ck_leave_adjustment_committed_version", "committed_version >= 0")


def downgrade() -> None:
    with op.batch_alter_table("leave_adjustments") as batch:
        batch.drop_constraint("ck_leave_adjustment_committed_version", type_="check")
        batch.drop_column("committed_version")
        batch.drop_column("request_fingerprint")
