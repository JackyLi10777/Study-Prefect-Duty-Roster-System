"""SQLAlchemy records for persistent roster operations."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for the local SQLite schema."""


class PrefectRecord(Base):
    __tablename__ = "prefects"
    __table_args__ = (
        CheckConstraint("role_code IN ('assistant_head', 'study_prefect')", name="ck_prefect_role_code"),
        Index(
            "uq_prefects_active_name_zh",
            "name_zh",
            unique=True,
            sqlite_where=text("active = 1"),
        ),
        Index(
            "uq_prefects_active_assist_fixed_weekday",
            "fixed_general_duty",
            unique=True,
            sqlite_where=text(
                "active = 1 AND role_code = 'assistant_head' "
                "AND fixed_general_duty <> 'NONE'"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name_zh: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    form: Mapped[str] = mapped_column(String(8))
    class_name: Mapped[str] = mapped_column(String(16))
    role_code: Mapped[str] = mapped_column(String(32))
    history_weight: Mapped[float] = mapped_column(Float, default=0.0)
    history_duties: Mapped[int] = mapped_column(Integer, default=0)
    history_weight_anchor: Mapped[float] = mapped_column(Float, default=0.0)
    history_duties_anchor: Mapped[int] = mapped_column(Integer, default=0)
    needs_mentoring: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_general_duty: Mapped[str] = mapped_column(String(16), default="NONE")
    remarks: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class PrefectAvailabilityRecord(Base):
    __tablename__ = "prefect_availability"
    __table_args__ = (UniqueConstraint("prefect_id", "day", name="uq_prefect_availability"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prefect_id: Mapped[str] = mapped_column(ForeignKey("prefects.id", ondelete="CASCADE"))
    day: Mapped[str] = mapped_column(String(16))


class RosterWeekRecord(Base):
    __tablename__ = "roster_weeks"
    __table_args__ = (
        CheckConstraint(
            "history_priority_multiplier >= 0.8 AND history_priority_multiplier <= 2.0",
            name="ck_roster_week_history_priority_multiplier",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'withdrawn')",
            name="ck_roster_week_status",
        ),
        CheckConstraint(
            "assist_assignment_mode IN ('legacy_fixed_weekday', 'flexible_weekly')",
            name="ck_roster_week_assist_assignment_mode",
        ),
        Index(
            "uq_roster_weeks_active_week_start",
            "week_start",
            unique=True,
            sqlite_where=text("status IN ('draft', 'published')"),
        ),
        Index("ix_roster_weeks_status_week_start_id", "status", "week_start", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    policy_version: Mapped[str] = mapped_column(String(32))
    history_priority_multiplier: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    assist_assignment_mode: Mapped[str] = mapped_column(
        String(32),
        default="legacy_fixed_weekday",
        server_default="legacy_fixed_weekday",
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class RosterAssignmentRecord(Base):
    __tablename__ = "roster_assignments"
    __table_args__ = (UniqueConstraint("roster_week_id", "day", "post_code", "slot_index", name="uq_roster_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roster_week_id: Mapped[int] = mapped_column(ForeignKey("roster_weeks.id", ondelete="CASCADE"))
    day: Mapped[str] = mapped_column(String(16))
    post_code: Mapped[str] = mapped_column(String(32))
    slot_index: Mapped[int] = mapped_column(Integer, default=1)
    prefect_id: Mapped[str | None] = mapped_column(ForeignKey("prefects.id", ondelete="SET NULL"), nullable=True)
    prefect_name_snapshot: Mapped[str] = mapped_column(String(120))
    prefect_role_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weight: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="active")


class FairnessLedgerRecord(Base):
    __tablename__ = "fairness_ledger"
    __table_args__ = (
        Index("ix_fairness_ledger_prefect_id", "prefect_id"),
        Index(
            "ix_fairness_ledger_roster_week_created_id",
            "roster_week_id",
            "created_at",
            "id",
        ),
        UniqueConstraint(
            "operation_id",
            "assignment_id",
            "prefect_id",
            "event_type",
            name="uq_fairness_operation_entry",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prefect_id: Mapped[str] = mapped_column(ForeignKey("prefects.id"))
    roster_week_id: Mapped[int] = mapped_column(ForeignKey("roster_weeks.id"))
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("roster_assignments.id"), nullable=True)
    delta: Mapped[float] = mapped_column(Float)
    duty_delta: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(48))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(64))
    operation_id: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class LeaveAdjustmentRecord(Base):
    __tablename__ = "leave_adjustments"
    __table_args__ = (
        UniqueConstraint("command_id", name="uq_leave_adjustment_command"),
        Index(
            "ix_leave_adjustments_roster_week_created_id",
            "roster_week_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roster_week_id: Mapped[int] = mapped_column(ForeignKey("roster_weeks.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("roster_assignments.id"))
    original_prefect_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_prefect_name: Mapped[str] = mapped_column(String(120))
    replacement_prefect_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replacement_prefect_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))
    command_id: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    committed_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class LeaveDeclarationRecord(Base):
    """A pre-generation absence constraint for a specific roster week."""

    __tablename__ = "leave_declarations"
    __table_args__ = (
        UniqueConstraint("week_start", "prefect_id", "day", name="uq_leave_declaration"),
        CheckConstraint("version >= 1", name="ck_leave_declaration_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date)
    prefect_id: Mapped[str] = mapped_column(ForeignKey("prefects.id"))
    day: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_command_id", "command_id"),
        Index("ix_audit_events_request_reference", "request_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64))
    roster_week_id: Mapped[int | None] = mapped_column(ForeignKey("roster_weeks.id"), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    actor_subject: Mapped[str | None] = mapped_column(String(160), nullable=True)
    actor_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    command_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)


class BackupRunRecord(Base):
    __tablename__ = "backup_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64))
    roster_week_id: Mapped[int | None] = mapped_column(ForeignKey("roster_weeks.id"), nullable=True)
    backup_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


Index(
    "ix_backup_runs_created_id",
    BackupRunRecord.created_at.desc(),
    BackupRunRecord.id.desc(),
)


class OperationCommandRecord(Base):
    """A durable receipt binding one idempotency key to one canonical command."""

    __tablename__ = "operation_commands"

    command_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(64))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="committed", server_default="committed")
    result_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BackupObligationRecord(Base):
    """A recoverable obligation created atomically with a committed command."""

    __tablename__ = "backup_obligations"
    __table_args__ = (
        UniqueConstraint("command_id", name="uq_backup_obligation_command"),
        Index("ix_backup_obligations_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_id: Mapped[str] = mapped_column(
        ForeignKey("operation_commands.command_id", ondelete="CASCADE")
    )
    operation_type: Mapped[str] = mapped_column(String(64))
    roster_week_id: Mapped[int | None] = mapped_column(ForeignKey("roster_weeks.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")
    backup_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExternalShareOutboxRecord(Base):
    """A durable, replay-safe share request bound to roster version and digest."""

    __tablename__ = "external_share_outbox"
    __table_args__ = (
        UniqueConstraint("command_id", name="uq_external_share_outbox_command"),
        UniqueConstraint("share_id", name="uq_external_share_outbox_share"),
        CheckConstraint("roster_version >= 1", name="ck_external_share_outbox_roster_version"),
        CheckConstraint("attempts >= 0", name="ck_external_share_outbox_attempts"),
        Index("ix_external_share_outbox_status_updated", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_id: Mapped[str] = mapped_column(
        ForeignKey("operation_commands.command_id", ondelete="CASCADE")
    )
    share_id: Mapped[str] = mapped_column(String(64))
    roster_week_id: Mapped[int] = mapped_column(ForeignKey("roster_weeks.id"))
    roster_version: Mapped[int] = mapped_column(Integer)
    content_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
