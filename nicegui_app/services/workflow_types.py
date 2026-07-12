"""Stable request, result, and error contracts for roster workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True)
class LeaveAdjustmentResult:
    roster_week_id: int
    assignment_id: int
    status: str
    backup_path: Path
    version: int = 0
    idempotent: bool = False


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
