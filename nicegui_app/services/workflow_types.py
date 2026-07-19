"""Stable request, result, and error contracts for roster workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from roster_policy import PrefectRole


class WorkflowError(ValueError):
    """Raised when an operator action conflicts with roster workflow policy."""


class WorkflowConflictError(WorkflowError):
    """Raised when another client committed a newer roster decision first."""


class WorkflowMaintenanceError(WorkflowError):
    """Raised when a workflow request arrives during exclusive maintenance."""


class CommittedWriteBackupError(WorkflowError):
    """A durable write committed but its required snapshot failed."""

    def __init__(self, event_type: str, error_message: str | None = None) -> None:
        self.event_type = event_type
        self.error_message = error_message
        super().__init__(f"{event_type} committed, but automatic backup failed")


@dataclass(frozen=True)
class BackupResult:
    success: bool
    path: Path | None
    error_message: str | None = None


@dataclass(frozen=True)
class HandoverBackupPackage:
    filename: str
    content: bytes
    source_backup_path: Path


@dataclass(frozen=True)
class RosterWeekResult:
    id: int
    week_start: date
    status: str
    version: int
    assignment_count: int
    backup_path: Path
    history_priority_multiplier: float = 1.0


@dataclass(frozen=True)
class RosterWithdrawalResult:
    roster_week_id: int
    week_start: date
    status: str
    version: int
    reason: str
    backup_path: Path | None
    idempotent: bool = False
    share_ids_to_revoke: tuple[str, ...] = ()


@dataclass(frozen=True)
class LeaveAdjustmentResult:
    roster_week_id: int
    assignment_id: int
    status: str
    backup_path: Path | None
    version: int = 0
    idempotent: bool = False
    original_prefect_name: str = ""
    replacement_prefect_name: str | None = None
    weight: float = 0.0


@dataclass(frozen=True)
class FairnessDiscrepancy:
    prefect_id: str
    expected_weight: float
    actual_weight: float
    expected_duties: int
    actual_duties: int


@dataclass(frozen=True)
class FairnessReconciliationReport:
    checked_prefects: int
    discrepancies: tuple[FairnessDiscrepancy, ...]

    @property
    def balanced(self) -> bool:
        return not self.discrepancies


@dataclass(frozen=True)
class DraftAssignmentUpdateResult:
    roster_week_id: int
    assignment_id: int
    version: int
    backup_path: Path


@dataclass(frozen=True)
class ReportRosterSource:
    """One published roster version used to build a period report."""

    roster_week_id: int
    week_start: date
    version: int
    policy_version: str
    history_priority_multiplier: float


@dataclass(frozen=True)
class DutyAllocationEntry:
    """One final published duty used in an allocation-hours statement."""

    roster_week_id: int
    roster_version: int
    policy_version: str
    assignment_id: int
    duty_date: date
    day: str
    post_code: str
    start_time: str
    end_time: str
    scheduled_minutes: int


@dataclass(frozen=True)
class PrefectPeriodContribution:
    """Final, post-adjustment service contribution within a report period."""

    prefect_id: str
    name_zh: str
    role_code: str
    duty_count: int
    workload_points: float
    scheduled_minutes: int
    assist_in_charge_count: int
    current_history_weight: float
    current_history_duties: int
    status_codes: tuple[str, ...]
    allocations: tuple[DutyAllocationEntry, ...]


@dataclass(frozen=True)
class FairnessTrendPoint:
    """Anonymous cumulative fairness distribution after one published week."""

    roster_week_id: int
    week_start: date
    version: int
    minimum: float
    median: float
    maximum: float
    spread: float
    population_stddev: float


@dataclass(frozen=True)
class PeriodSummaryReport:
    """Single source shared by the Chinese preview, English PDF, and JSON evidence."""

    schema_version: str
    generated_at: datetime
    period_start: date | None
    period_end: date | None
    sources: tuple[ReportRosterSource, ...]
    active_prefect_count: int
    published_week_count: int
    recorded_slot_count: int
    active_assignment_count: int
    vacant_slot_count: int
    coverage_rate: float | None
    workload_points: float
    scheduled_minutes: int
    leave_adjustment_count: int
    replacement_count: int
    assist_required_count: int
    assist_filled_count: int
    fairness_minimum: float
    fairness_median: float
    fairness_maximum: float
    fairness_spread: float
    fairness_population_stddev: float
    fairness_ledger_balanced: bool
    contributions: tuple[PrefectPeriodContribution, ...]
    trend: tuple[FairnessTrendPoint, ...]
    note_codes: tuple[str, ...]


@dataclass(frozen=True)
class PrefectInput:
    """Validated identity and availability fields accepted from management pages."""

    name_zh: str
    form: str
    class_name: str
    role_code: str
    available_days: tuple[str, ...]
    name_en: str | None = None
    needs_mentoring: bool = False
    fixed_general_duty: str = "NONE"
    remarks: str = ""
    history_weight: float = 0.0
    history_duties: int = 0


ROLE_CODES = frozenset(role.value for role in PrefectRole)


__all__ = [name for name in globals() if not name.startswith("_")]
