"""Create the local-first roster, fairness, audit, and backup tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prefects",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name_zh", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120)),
        sa.Column("form", sa.String(length=8), nullable=False),
        sa.Column("class_name", sa.String(length=16), nullable=False),
        sa.Column("role_code", sa.String(length=32), nullable=False),
        sa.Column("history_weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("history_duties", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("needs_mentoring", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fixed_general_duty", sa.String(length=16), nullable=False, server_default="NONE"),
        sa.Column("remarks", sa.Text(), nullable=False, server_default=""),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "prefect_availability",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prefect_id", sa.String(length=64), sa.ForeignKey("prefects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.UniqueConstraint("prefect_id", "day", name="uq_prefect_availability"),
    )
    op.create_table(
        "roster_weeks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.Date(), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "roster_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.String(length=16), nullable=False),
        sa.Column("post_code", sa.String(length=32), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prefect_id", sa.String(length=64), sa.ForeignKey("prefects.id", ondelete="SET NULL")),
        sa.Column("prefect_name_snapshot", sa.String(length=120), nullable=False),
        sa.Column("prefect_role_snapshot", sa.String(length=32)),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.UniqueConstraint("roster_week_id", "day", "post_code", "slot_index", name="uq_roster_slot"),
    )
    op.create_table(
        "fairness_ledger",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prefect_id", sa.String(length=64), sa.ForeignKey("prefects.id"), nullable=False),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("roster_assignments.id")),
        sa.Column("delta", sa.Float(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "leave_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id"), nullable=False),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("roster_assignments.id"), nullable=False),
        sa.Column("original_prefect_id", sa.String(length=64)),
        sa.Column("original_prefect_name", sa.String(length=120), nullable=False),
        sa.Column("replacement_prefect_id", sa.String(length=64)),
        sa.Column("replacement_prefect_name", sa.String(length=120)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id")),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "backup_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id")),
        sa.Column("backup_path", sa.Text()),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("backup_runs")
    op.drop_table("audit_events")
    op.drop_table("leave_adjustments")
    op.drop_table("fairness_ledger")
    op.drop_table("roster_assignments")
    op.drop_table("roster_weeks")
    op.drop_table("prefect_availability")
    op.drop_table("prefects")
