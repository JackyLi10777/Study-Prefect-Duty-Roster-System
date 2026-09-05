"""Stable request, result, and error contracts for roster workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from roster_policy import AssistAssignmentMode, PrefectRole


LEGACY_FIXED_WEEKDAY = AssistAssignmentMode.LEGACY_FIXED_WEEKDAY.value
FLEXIBLE_WEEKLY = AssistAssignmentMode.FLEXIBLE_WEEKLY.value
ASSIST_ASSIGNMENT_MODE_CODES = frozenset({LEGACY_FIXED_WEEKDAY, FLEXIBLE_WEEKLY})


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
    assist_assignment_mode: str = LEGACY_FIXED_WEEKDAY


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
    share_ids_to_revoke: tuple[str, ...] = ()


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
class DraftCellEdit:
    """One explicit stable-code cell decision in a draft patch.

    ``replacement_prefect_id=None`` is an explicit vacancy.  Callers must not
    translate an empty text field into this value implicitly.
    """

    cell_key: str
    replacement_prefect_id: str | None

    @classmethod
    def from_parts(
        cls,
        *,
        day: str,
        post_code: str,
        slot_index: int,
        replacement_prefect_id: str | None,
    ) -> "DraftCellEdit":
        return cls(
            cell_key=f"{day}:{post_code}:{slot_index}",
            replacement_prefect_id=replacement_prefect_id,
        )


@dataclass(frozen=True)
class DraftDayEdit:
    """Open or close one whole weekday without overloading assignment text."""

    day: str
    closed: bool
    reason_code: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class DraftSlotStateEdit:
    """Open or close one week-local duty slot without overloading vacancy."""

    cell_key: str
    state: str
    reason_code: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class DraftCellTarget:
    """The final state of one cell, rather than ordered partial mutations."""

    cell_key: str
    state: str
    prefect_id: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {"assigned", "vacant", "unavailable"}:
            raise WorkflowError("A draft target must be assigned, vacant or unavailable.")
        if self.state == "assigned":
            if not isinstance(self.prefect_id, str) or not self.prefect_id.strip():
                raise WorkflowError("An assigned target requires a prefect identifier.")
        elif self.prefect_id is not None:
            raise WorkflowError("A vacant or unavailable target cannot contain a prefect.")


@dataclass(frozen=True)
class DraftPatchCommand:
    """Frozen user intent: every retry includes the same reason and payload."""

    roster_week_id: int
    expected_week_version: int
    command_id: str
    targets: tuple[DraftCellTarget, ...] = ()
    days: tuple[DraftDayEdit, ...] = ()
    reason: str | None = None

    def workflow_arguments(self) -> dict[str, object]:
        cells = tuple(DraftCellEdit(target.cell_key, target.prefect_id)
                      for target in self.targets if target.state != "unavailable")
        slots = tuple(DraftSlotStateEdit(target.cell_key, "unavailable" if target.state == "unavailable" else "open")
                      for target in self.targets)
        return {"roster_week_id": self.roster_week_id,
                "expected_week_version": self.expected_week_version,
                "command_id": self.command_id, "cell_edits": cells,
                "day_edits": self.days, "slot_edits": slots, "reason": self.reason}


@dataclass(frozen=True)
class WeekScheduleOverrides:
    """Stable-code schedule exceptions stored with one roster week."""

    closed_days: tuple[str, ...] = ()
    unavailable_slots: tuple[str, ...] = ()


@dataclass(frozen=True)
class DraftPatchResult:
    roster_week_id: int
    version: int
    changed_cell_count: int
    closed_days: tuple[str, ...]
    unavailable_slots: tuple[str, ...]
    backup_path: Path | None
    idempotent: bool = False


@dataclass(frozen=True)
class FairnessAuditSnapshot:
    """Detached audit facts captured in one database or guest-workspace read.

    The containers belong to the caller; none retain live storage references.
    Rendering this value must not perform any further workflow reads.
    """

    week: dict[str, object]
    active_assignment_count: int
    fairness_rows: tuple[dict[str, object], ...]


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


PREFECT_PATCH_FIELDS = frozenset(
    {
        "nameEn",
        "form",
        "className",
        "availableDays",
        "needsMentoring",
        "fixedGeneralDuty",
        "remarks",
    }
)


@dataclass(frozen=True)
class PrefectPatch:
    """One versioned, low-risk prefect-directory edit in a batch intent."""

    prefect_id: str
    changes: Mapping[str, object]
    expected_version: int


def prefect_input_from_patch(
    current: Mapping[str, object],
    patch: PrefectPatch,
) -> PrefectInput:
    """Apply the shared inline-field contract without mutating either input."""

    changes = dict(patch.changes)
    if not changes:
        raise WorkflowError("No prefect changes were provided.")
    unsupported = sorted(set(changes) - PREFECT_PATCH_FIELDS)
    if unsupported:
        raise WorkflowError(
            f"Inline editing is not allowed for: {', '.join(unsupported)}."
        )
    merged = dict(current)
    merged.update(changes)
    available_days = merged.get("availableDays", ())
    if not isinstance(available_days, (list, tuple)) or any(
        not isinstance(day, str) for day in available_days
    ):
        raise WorkflowError("Available days must be a list of weekday codes.")
    if not isinstance(merged.get("needsMentoring"), bool):
        raise WorkflowError("needsMentoring must be true or false.")
    for text_field in ("form", "className", "fixedGeneralDuty", "remarks"):
        if not isinstance(merged.get(text_field), str):
            raise WorkflowError(f"{text_field} must be text.")
    if merged.get("nameEn") is not None and not isinstance(merged.get("nameEn"), str):
        raise WorkflowError("nameEn must be text or empty.")
    return PrefectInput(
        name_zh=str(current["nameZh"]),
        name_en=(str(merged["nameEn"]).strip() or None)
        if merged.get("nameEn") is not None
        else None,
        form=str(merged["form"]),
        class_name=str(merged["className"]),
        role_code=str(current["roleCode"]),
        available_days=tuple(str(day) for day in available_days),
        needs_mentoring=bool(merged["needsMentoring"]),
        fixed_general_duty=str(merged["fixedGeneralDuty"]),
        remarks=str(merged["remarks"]),
        history_weight=float(current["historyWeight"]),
        history_duties=int(current["historyDuties"]),
    )


ROLE_CODES = frozenset(role.value for role in PrefectRole)


__all__ = [
    "ASSIST_ASSIGNMENT_MODE_CODES",
    "BackupResult",
    "CommittedWriteBackupError",
    "DraftAssignmentUpdateResult",
    "DraftCellEdit",
    "DraftDayEdit",
    "DraftPatchResult",
    "DraftSlotStateEdit",
    "DutyAllocationEntry",
    "FairnessDiscrepancy",
    "FairnessReconciliationReport",
    "FairnessTrendPoint",
    "FLEXIBLE_WEEKLY",
    "HandoverBackupPackage",
    "LeaveAdjustmentResult",
    "LEGACY_FIXED_WEEKDAY",
    "PeriodSummaryReport",
    "PREFECT_PATCH_FIELDS",
    "PrefectInput",
    "PrefectPatch",
    "PrefectPeriodContribution",
    "ReportRosterSource",
    "ROLE_CODES",
    "RosterWeekResult",
    "RosterWithdrawalResult",
    "WorkflowConflictError",
    "WorkflowError",
    "WorkflowMaintenanceError",
    "WeekScheduleOverrides",
    "prefect_input_from_patch",
]
