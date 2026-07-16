"""Add v1.2 concurrency receipts, recovery obligations, outbox, and audit context."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _assert_active_chinese_names_are_unique() -> None:
    duplicate_groups = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT name_zh
                FROM prefects
                WHERE active = 1
                GROUP BY name_zh
                HAVING COUNT(*) > 1
            ) AS duplicate_names
            """
        )
    ).scalar_one()
    if int(duplicate_groups) > 0:
        raise RuntimeError(
            "Cannot enforce active Chinese-name uniqueness because duplicate active names exist. "
            "Resolve the directory conflict before retrying the migration."
        )


def upgrade() -> None:
    _assert_active_chinese_names_are_unique()
    op.create_index(
        "uq_prefects_active_name_zh",
        "prefects",
        ["name_zh"],
        unique=True,
        sqlite_where=sa.text("active = 1"),
    )

    with op.batch_alter_table("leave_declarations") as batch:
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_check_constraint("ck_leave_declaration_version", "version >= 1")

    with op.batch_alter_table("audit_events") as batch:
        batch.add_column(sa.Column("actor_subject", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("actor_mode", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("command_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("request_reference", sa.String(length=128), nullable=True))
        batch.create_index("ix_audit_events_command_id", ["command_id"], unique=False)
        batch.create_index(
            "ix_audit_events_request_reference",
            ["request_reference"],
            unique=False,
        )

    op.create_table(
        "operation_commands",
        sa.Column("command_id", sa.String(length=64), primary_key=True),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="committed"),
        sa.Column("result_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "backup_obligations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "command_id",
            sa.String(length=64),
            sa.ForeignKey("operation_commands.command_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id"), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("backup_path", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("command_id", name="uq_backup_obligation_command"),
    )
    op.create_index(
        "ix_backup_obligations_status_created",
        "backup_obligations",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "external_share_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "command_id",
            sa.String(length=64),
            sa.ForeignKey("operation_commands.command_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("share_id", sa.String(length=64), nullable=False),
        sa.Column("roster_week_id", sa.Integer(), sa.ForeignKey("roster_weeks.id"), nullable=False),
        sa.Column("roster_version", sa.Integer(), nullable=False),
        sa.Column("content_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "roster_version >= 1",
            name="ck_external_share_outbox_roster_version",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_external_share_outbox_attempts",
        ),
        sa.UniqueConstraint("command_id", name="uq_external_share_outbox_command"),
        sa.UniqueConstraint("share_id", name="uq_external_share_outbox_share"),
    )
    op.create_index(
        "ix_external_share_outbox_status_updated",
        "external_share_outbox",
        ["status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_external_share_outbox_status_updated",
        table_name="external_share_outbox",
    )
    op.drop_table("external_share_outbox")
    op.drop_index(
        "ix_backup_obligations_status_created",
        table_name="backup_obligations",
    )
    op.drop_table("backup_obligations")
    op.drop_table("operation_commands")

    with op.batch_alter_table("audit_events") as batch:
        batch.drop_index("ix_audit_events_request_reference")
        batch.drop_index("ix_audit_events_command_id")
        batch.drop_column("request_reference")
        batch.drop_column("command_id")
        batch.drop_column("actor_mode")
        batch.drop_column("actor_subject")

    with op.batch_alter_table("leave_declarations") as batch:
        batch.drop_constraint("ck_leave_declaration_version", type_="check")
        batch.drop_column("version")

    op.drop_index("uq_prefects_active_name_zh", table_name="prefects")
