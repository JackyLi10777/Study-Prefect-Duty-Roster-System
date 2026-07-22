"""RosterWorkflow-compatible adapter for an isolated guest workspace.

The adapter reuses the real roster policy and generator while keeping every
mutable fact inside :class:`GuestWorkspaceRegistry`.  It must never acquire a
database session, read or write a file, call a network service, invoke AI, or
schedule work.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import secrets
from statistics import median, pstdev
from typing import Any

from nicegui_app.access_context import AccessMode, Capability, PageContext
from nicegui_app.services.guest_workspace import (
    DEMO_FIXTURE_VERSION,
    GuestRevisionConflict,
    GuestWorkspaceRegistry,
    GuestWorkspaceView,
    demo_fixture,
)
from nicegui_app.services.workflow_types import (
    ASSIST_ASSIGNMENT_MODE_CODES,
    AssistAssignmentMode,
    DraftAssignmentUpdateResult,
    DutyAllocationEntry,
    FairnessDiscrepancy,
    FairnessReconciliationReport,
    FairnessTrendPoint,
    FLEXIBLE_WEEKLY,
    HandoverBackupPackage,
    LEGACY_FIXED_WEEKDAY,
    LeaveAdjustmentResult,
    PeriodSummaryReport,
    PrefectInput,
    PrefectPeriodContribution,
    ReportRosterSource,
    RosterWeekResult,
    RosterWithdrawalResult,
    WorkflowConflictError,
    WorkflowError,
)
from roster_core.generator import (
    RosterGenerationError,
    generate_weekly_roster,
    legacy_assist_weekday_mapping,
    validate_assignments,
)
from roster_core.models import Assignment, Prefect
from roster_policy import (
    DUTY_SERVICE_TIME_WINDOWS,
    DutyPost,
    PrefectRole,
    RosterPolicyError,
    SchoolDay,
    can_assign_role,
    is_chinese_display_name,
    required_posts_for_day,
)


DEMO_POLICY_VERSION = f"guest-demo-{DEMO_FIXTURE_VERSION}"
_DEMO_BACKUP_NAME = "DEMO_MEMORY_SNAPSHOT"


def _assist_assignment_mode_code(value: object) -> str:
    raw_value = getattr(value, "value", value)
    normalized = str(raw_value).strip()
    if normalized not in ASSIST_ASSIGNMENT_MODE_CODES:
        allowed = ", ".join(sorted(ASSIST_ASSIGNMENT_MODE_CODES))
        raise WorkflowError(
            f"Unsupported Assist assignment mode; expected one of: {allowed}."
        )
    return normalized


class _DemoMaintenanceStatus:
    active = False
    recovery_required = False
    reason = ""


class _DemoPath(str):
    """Path-shaped UI value which cannot perform filesystem operations."""

    @property
    def name(self) -> str:
        return str(self).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _datetime_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as error:
        raise WorkflowError("Guest demo state contains an invalid timestamp.") from error


def _distribution(values: list[float]) -> tuple[float, float, float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    minimum = min(values)
    maximum = max(values)
    return (
        round(minimum, 4),
        round(float(median(values)), 4),
        round(maximum, 4),
        round(maximum - minimum, 4),
        round(float(pstdev(values)), 4) if len(values) > 1 else 0.0,
    )


def _duty_minutes(post_code: str) -> int:
    start_text, end_text = DUTY_SERVICE_TIME_WINDOWS[DutyPost[post_code]]
    start = datetime.strptime(start_text, "%H:%M")
    end = datetime.strptime(end_text, "%H:%M")
    return int((end - start).total_seconds() // 60)


class GuestWorkspaceAdapter:
    """A bounded guest implementation of the page-facing workspace port."""

    def __init__(
        self,
        context: PageContext,
        registry: GuestWorkspaceRegistry,
        *,
        workspace_id: str | None,
        tab_id: str | None,
        initial_view: GuestWorkspaceView | None = None,
        snapshot_publisher: Callable[[GuestWorkspaceView], None] | None = None,
    ) -> None:
        if context.principal.mode is not AccessMode.GUEST:
            raise ValueError("GuestWorkspaceAdapter requires a verified guest principal.")
        context.require(Capability.DEMO_DATA_READ)
        session_id = context.principal.session_id
        if not session_id:
            raise ValueError("GuestWorkspaceAdapter requires a guest session ID.")
        self._context = context
        self._registry = registry
        self._session_id = session_id
        self._workspace_id = workspace_id or f"pending-{secrets.token_urlsafe(12)}"
        self._tab_id = tab_id or self._workspace_id
        self._initial_view = initial_view or GuestWorkspaceView(
            session_id=session_id,
            workspace_id=self._workspace_id,
            tab_id=self._tab_id,
            revision=0,
            expires_at=int(datetime.now(timezone.utc).timestamp()) + 30 * 60,
            state=demo_fixture(),
        )
        self._bound = bool(workspace_id and tab_id)
        self._snapshot_publisher = snapshot_publisher
        if self._bound:
            self._initial_view = self._registry.create_workspace(
                session_id=session_id,
                tab_id=self._tab_id,
                workspace_id=self._workspace_id,
            )

    @property
    def is_bound(self) -> bool:
        return self._bound

    def bind_workspace(self, *, workspace_id: str, tab_id: str) -> GuestWorkspaceView:
        """Attach a rendered page to NiceGUI's stable browser-tab identity.

        Initial page composition happens before the websocket handshake, so
        NiceGUI has not exposed its sessionStorage-backed ``tab_id`` yet.
        Event callbacks cannot run before the handshake; binding here therefore
        prevents provisional page clients from consuming the four-tab guest
        capacity while keeping all later mutations on the stable tab workspace.
        """

        self._context.require(Capability.DEMO_DATA_READ)
        view = self._registry.create_workspace(
            session_id=self._session_id,
            tab_id=tab_id,
            workspace_id=workspace_id,
        )
        self._workspace_id = workspace_id
        self._tab_id = tab_id
        self._initial_view = view
        self._bound = True
        return view

    @property
    def access_mode(self) -> AccessMode:
        """Make deny-by-default service boundaries explicit."""

        return AccessMode.GUEST

    @property
    def workspace_id(self) -> str:
        self._require_read()
        return self._workspace_id

    def validate_week_start(self, week_start: date) -> None:
        self._require_read()
        self._require_monday(week_start)

    def maintenance_status(self) -> _DemoMaintenanceStatus:
        self._require_read()
        return _DemoMaintenanceStatus()

    def prefect_loads(self) -> dict[str, float]:
        self._require_read()
        return {str(row["id"]): float(row["historyWeight"]) for row in self.prefects()}

    def prefects(self) -> list[dict[str, object]]:
        self._require_read()
        state = self._state()
        rows = [self._prefect_output(row) for row in state.get("prefects", []) if row.get("active", True)]
        return sorted(rows, key=lambda row: str(row["nameZh"]))

    def prefect(self, prefect_id: str) -> dict[str, object]:
        self._require_read()
        state = self._state()
        return self._prefect_output(self._prefect_record(state, prefect_id))

    def create_prefect(self, prefect_input: PrefectInput) -> dict[str, object]:
        self._require_modify()
        self._validate_prefect_input(prefect_input)
        view = self._view()
        state = view.state
        self._assert_name_available(state, prefect_input.name_zh)
        self._assert_assist_fixed_day_available(state, prefect_input)
        record = {
            "id": f"demo-prefect-{secrets.token_hex(6)}",
            "nameZh": prefect_input.name_zh.strip(),
            "nameEn": prefect_input.name_en.strip() if prefect_input.name_en else None,
            "form": prefect_input.form,
            "className": prefect_input.class_name.strip(),
            "roleCode": prefect_input.role_code,
            "availableDays": self._sorted_days(prefect_input.available_days),
            "historyWeight": float(prefect_input.history_weight),
            "historyDuties": int(prefect_input.history_duties),
            "historyWeightAnchor": float(prefect_input.history_weight),
            "historyDutiesAnchor": int(prefect_input.history_duties),
            "needsMentoring": bool(prefect_input.needs_mentoring),
            "fixedGeneralDuty": prefect_input.fixed_general_duty,
            "remarks": prefect_input.remarks.strip(),
            "version": 1,
            "active": True,
            "fictional": True,
        }
        state.setdefault("prefects", []).append(record)
        self._commit(view, state, "prefect-create")
        return self._prefect_output(record)

    def update_prefect(
        self,
        prefect_id: str,
        prefect_input: PrefectInput,
        *,
        expected_version: int | None = None,
    ) -> dict[str, object]:
        self._require_modify()
        self._validate_prefect_input(prefect_input)
        view = self._view()
        state = view.state
        record = self._prefect_record(state, prefect_id)
        if not record.get("active", True):
            raise WorkflowConflictError("This demo prefect was archived in another tab.")
        current_version = int(record.get("version", 1))
        reviewed_version = current_version if expected_version is None else expected_version
        if current_version != reviewed_version:
            raise WorkflowConflictError("This demo prefect changed in another tab.")
        self._assert_name_available(state, prefect_input.name_zh, exclude_prefect_id=prefect_id)
        self._assert_assist_fixed_day_available(
            state,
            prefect_input,
            exclude_prefect_id=prefect_id,
        )
        record.update(
            {
                "nameZh": prefect_input.name_zh.strip(),
                "nameEn": prefect_input.name_en.strip() if prefect_input.name_en else None,
                "form": prefect_input.form,
                "className": prefect_input.class_name.strip(),
                "roleCode": prefect_input.role_code,
                "availableDays": self._sorted_days(prefect_input.available_days),
                "needsMentoring": bool(prefect_input.needs_mentoring),
                "fixedGeneralDuty": prefect_input.fixed_general_duty,
                "remarks": prefect_input.remarks.strip(),
                "version": current_version + 1,
                "fictional": True,
            }
        )
        self._commit(view, state, "prefect-update")
        return self._prefect_output(record)

    def archive_prefect(self, prefect_id: str, *, expected_version: int | None = None) -> None:
        self._require_modify()
        view = self._view()
        state = view.state
        record = self._prefect_record(state, prefect_id)
        if not record.get("active", True):
            raise WorkflowError("Demo prefect is already archived.")
        current_version = int(record.get("version", 1))
        reviewed_version = current_version if expected_version is None else expected_version
        if current_version != reviewed_version:
            raise WorkflowConflictError("This demo prefect changed in another tab.")
        record["active"] = False
        record["version"] = current_version + 1
        self._commit(view, state, "prefect-archive")

    def import_prefects(self, prefect_inputs: Iterable[PrefectInput]) -> list[dict[str, object]]:
        """Retain UI shape while denying every guest import at the service edge."""

        del prefect_inputs
        self._context.require(Capability.DATA_IMPORT)
        raise AssertionError("guest data import capability must remain denied")

    def declare_leave(
        self,
        *,
        week_start: date,
        prefect_id: str,
        day: str,
        reason: str | None = None,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> dict[str, object]:
        self._require_modify()
        self._require_monday(week_start)
        if day not in SchoolDay.__members__:
            raise WorkflowError("Leave declaration contains an invalid weekday.")
        view = self._view()
        state = view.state
        prefect = self._prefect_record(state, prefect_id)
        if not prefect.get("active", True):
            raise WorkflowError("The selected demo prefect is not active.")
        existing_week = self._week_by_start(state, week_start)
        if existing_week is not None and existing_week["status"] == "published":
            raise WorkflowError("A published demo roster must use a post-publication leave adjustment.")
        now = _now()
        leaves = state.setdefault("preGenerationLeave", [])
        declaration = next(
            (
                row
                for row in leaves
                if row["weekStart"] == week_start.isoformat()
                and row["prefectId"] == prefect_id
                and row["day"] == day
            ),
            None,
        )
        if declaration is None:
            if expected_version not in {None, 0}:
                raise WorkflowConflictError("This demo leave declaration changed in another tab.")
            declaration = {
                "id": self._next_integer_id(leaves),
                "weekStart": week_start.isoformat(),
                "prefectId": prefect_id,
                "day": day,
                "reason": reason.strip() if reason else None,
                "active": True,
                "version": 1,
                "createdAt": _datetime_text(now),
                "updatedAt": _datetime_text(now),
            }
            leaves.append(declaration)
        else:
            current_version = int(declaration.get("version", 1))
            if expected_version is not None and current_version != expected_version:
                raise WorkflowConflictError("This demo leave declaration changed in another tab.")
            declaration["reason"] = reason.strip() if reason else None
            declaration["active"] = True
            declaration["version"] = current_version + 1
            declaration["updatedAt"] = _datetime_text(now)
        self._commit(view, state, command_id or "leave-declare")
        return self._leave_output(declaration, prefect)

    def cancel_pre_generation_leave(
        self,
        leave_declaration_id: int,
        *,
        expected_version: int | None = None,
        command_id: str | None = None,
    ) -> None:
        self._require_modify()
        view = self._view()
        state = view.state
        declaration = next(
            (
                row
                for row in state.get("preGenerationLeave", [])
                if int(row["id"]) == leave_declaration_id and row.get("active", True)
            ),
            None,
        )
        if declaration is None:
            raise WorkflowError("The demo leave declaration was not found.")
        current_version = int(declaration.get("version", 1))
        if expected_version is not None and current_version != expected_version:
            raise WorkflowConflictError("This demo leave declaration changed in another tab.")
        week = self._week_by_start(state, date.fromisoformat(str(declaration["weekStart"])))
        if week is not None and week["status"] == "published":
            raise WorkflowError("A published demo roster must use a post-publication leave adjustment.")
        declaration["active"] = False
        declaration["version"] = current_version + 1
        declaration["updatedAt"] = _datetime_text(_now())
        self._commit(view, state, command_id or "leave-cancel")

    def pre_generation_leaves(self, week_start: date) -> list[dict[str, object]]:
        self._require_read()
        self._require_monday(week_start)
        state = self._state()
        prefects = {str(row["id"]): row for row in state.get("prefects", [])}
        rows = [
            self._leave_output(row, prefects[str(row["prefectId"])])
            for row in state.get("preGenerationLeave", [])
            if row.get("active", True) and row["weekStart"] == week_start.isoformat()
        ]
        return sorted(rows, key=lambda row: (str(row["day"]), str(row["prefectName"])))

    def generation_requirements(self, week_start: date) -> list[dict[str, object]]:
        self._require_read()
        self._require_monday(week_start)
        state = self._state()
        prefects = self._active_prefects(state)
        leave_days = self._leave_days(state, week_start)
        requirements: list[dict[str, object]] = []
        for day in SchoolDay:
            slot_counts: dict[DutyPost, int] = defaultdict(int)
            for post in required_posts_for_day(day):
                slot_counts[post] += 1
                candidates = [
                    prefect
                    for prefect in prefects
                    if day in prefect.available_days
                    and day not in leave_days.get(prefect.id, set())
                    and can_assign_role(prefect.role, post)
                ]
                requirements.append(
                    {
                        "day": day.name,
                        "postCode": post.name,
                        "slotIndex": slot_counts[post],
                        "eligibleCount": len(candidates),
                        "hasVacancyRisk": not candidates,
                    }
                )
        return requirements

    def generate_and_save_draft(
        self,
        week_start: date,
        *,
        history_priority_multiplier: float = 1.0,
        assist_assignment_mode: AssistAssignmentMode | str = LEGACY_FIXED_WEEKDAY,
        expected_week_version: int | None = None,
        command_id: str | None = None,
    ) -> RosterWeekResult:
        self._require_modify()
        self._require_monday(week_start)
        normalized_assist_mode = _assist_assignment_mode_code(assist_assignment_mode)
        view = self._view()
        state = view.state
        prefects = self._active_prefects(state)
        leave_days = self._leave_days(state, week_start)
        previous_assist_assignments = self._previous_assist_weekday_assignments(
            state,
            week_start,
        )
        try:
            generated = generate_weekly_roster(
                prefects,
                leave_days=leave_days,
                history_priority_multiplier=history_priority_multiplier,
                assist_assignment_mode=normalized_assist_mode,
                assist_rotation_key=week_start.isoformat(),
                previous_assist_assignments=previous_assist_assignments,
            )
        except RosterGenerationError as error:
            raise WorkflowError(f"Demo draft generation needs attention: {error}") from error
        if normalized_assist_mode == LEGACY_FIXED_WEEKDAY:
            assist_days = legacy_assist_weekday_mapping(prefects)
            for record in state.get("prefects", []):
                prefect_id = str(record.get("id", ""))
                assigned_days = assist_days.get(prefect_id, [])
                if (
                    str(record.get("roleCode", record.get("role", "")))
                    == PrefectRole.ASSISTANT_HEAD.value
                    and str(record.get("fixedGeneralDuty", "NONE")) == "NONE"
                    and len(assigned_days) == 1
                ):
                    record["fixedGeneralDuty"] = assigned_days[0].name
                    record["version"] = int(record.get("version", 1)) + 1
        weeks = state.setdefault("weeks", [])
        week = self._week_by_start(state, week_start)
        current_version = int(week["version"]) if week is not None else 0
        if expected_week_version is not None and current_version != expected_week_version:
            raise WorkflowConflictError("This demo roster changed in another tab.")
        now = _now()
        if week is None:
            week = {
                "id": self._next_integer_id(weeks),
                "weekStart": week_start.isoformat(),
                "status": "draft",
                "version": 1,
                "policyVersion": DEMO_POLICY_VERSION,
                "historyPriorityMultiplier": float(history_priority_multiplier),
                "assistAssignmentMode": normalized_assist_mode,
                "generatedAt": _datetime_text(now),
                "publishedAt": None,
                "assignments": [],
                "adjustments": [],
            }
            weeks.append(week)
        elif week["status"] == "published":
            raise WorkflowError("This demo roster is already published; use a demo adjustment instead.")
        else:
            week["version"] = int(week["version"]) + 1
            week["historyPriorityMultiplier"] = float(history_priority_multiplier)
            week["assistAssignmentMode"] = normalized_assist_mode
            week["generatedAt"] = _datetime_text(now)
            week["assignments"] = []
        assignment_id = self._next_assignment_id(state)
        slot_counts: dict[tuple[str, str], int] = defaultdict(int)
        for assignment in generated:
            key = (assignment.day.name, assignment.post.name)
            slot_counts[key] += 1
            week["assignments"].append(
                {
                    "id": assignment_id,
                    "day": assignment.day.name,
                    "postCode": assignment.post.name,
                    "slotIndex": slot_counts[key],
                    "prefectId": assignment.prefect_id,
                    "prefectName": assignment.prefect_name,
                    "weight": float(assignment.weight),
                    "status": "active",
                }
            )
            assignment_id += 1
        self._commit(view, state, command_id or "draft-generate")
        return RosterWeekResult(
            id=int(week["id"]),
            week_start=week_start,
            status="draft",
            version=int(week["version"]),
            assignment_count=len(generated),
            backup_path=None,  # type: ignore[arg-type]
            history_priority_multiplier=float(week["historyPriorityMultiplier"]),
            assist_assignment_mode=str(week["assistAssignmentMode"]),
        )

    def roster_weeks(self) -> list[dict[str, object]]:
        self._require_read()
        return sorted(
            [self._week_output(row) for row in self._state().get("weeks", [])],
            key=lambda row: row["weekStart"],
            reverse=True,
        )

    def roster_week(self, roster_week_id: int) -> dict[str, object]:
        self._require_read()
        return self._week_output(self._week_record(self._state(), roster_week_id))

    def assignments(self, roster_week_id: int) -> list[dict[str, object]]:
        self._require_read()
        week = self._week_record(self._state(), roster_week_id)
        return [dict(row) for row in self._sorted_assignments(week)]

    def roster_schedule_snapshot(
        self,
        roster_week_id: int,
    ) -> tuple[dict[str, object], list[dict[str, object]]]:
        self._require_read()
        state = self._state()
        week = self._week_record(state, roster_week_id)
        return self._week_output(week), [dict(row) for row in self._sorted_assignments(week)]

    def draft_assignment_candidates(
        self,
        roster_week_id: int,
        assignment_id: int,
    ) -> list[dict[str, object]]:
        self._require_read()
        state = self._state()
        week = self._week_record(state, roster_week_id)
        if week["status"] != "draft":
            raise WorkflowError("Manual changes are available only for a demo draft.")
        return self._candidate_outputs(state, week, self._assignment_record(week, assignment_id))

    def update_draft_assignment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str,
        reason: str | None = None,
        expected_week_version: int | None = None,
        command_id: str | None = None,
    ) -> DraftAssignmentUpdateResult:
        self._require_modify()
        # The demo mirrors production: an operator may leave the explanatory
        # note blank, while the versioned command remains fully auditable.
        view = self._view()
        state = view.state
        week = self._week_record(state, roster_week_id)
        if week["status"] != "draft":
            raise WorkflowError("Only a demo draft can be changed manually.")
        current_version = int(week["version"])
        reviewed_version = current_version if expected_week_version is None else expected_week_version
        if current_version != reviewed_version:
            raise WorkflowConflictError("This demo draft changed in another tab.")
        assignment = self._assignment_record(week, assignment_id)
        candidates = {
            str(row["id"]): row for row in self._candidate_outputs(state, week, assignment)
        }
        if replacement_prefect_id not in candidates:
            raise WorkflowError("The selected demo prefect does not meet the current roster rules.")
        if assignment["prefectId"] == replacement_prefect_id:
            raise WorkflowError("Choose a different demo prefect.")
        replacement = self._prefect_record(state, replacement_prefect_id)
        assignment["prefectId"] = replacement_prefect_id
        assignment["prefectName"] = replacement["nameZh"]
        assignment["status"] = "active"
        week["version"] = current_version + 1
        self._validate_week_assignments(state, week)
        self._commit(view, state, command_id or "draft-assignment-update")
        return DraftAssignmentUpdateResult(
            roster_week_id=roster_week_id,
            assignment_id=assignment_id,
            version=int(week["version"]),
            backup_path=None,  # type: ignore[arg-type]
        )

    def publish(
        self,
        roster_week_id: int,
        *,
        expected_week_version: int,
        command_id: str | None = None,
    ) -> RosterWeekResult:
        self._require_modify()
        view = self._view()
        state = view.state
        week = self._week_record(state, roster_week_id)
        if week["status"] != "draft":
            raise WorkflowError("This demo roster is already published.")
        if int(week["version"]) != expected_week_version:
            raise WorkflowConflictError("This demo draft changed after review.")
        self._validate_week_assignments(state, week)
        prefects = {str(row["id"]): row for row in state.get("prefects", [])}
        events = state.setdefault("fairnessEvents", [])
        for assignment in week["assignments"]:
            if assignment["status"] != "active" or not assignment.get("prefectId"):
                raise WorkflowError("A demo roster with a vacancy cannot be published.")
            prefect = prefects[str(assignment["prefectId"])]
            self._ensure_history_anchor(prefect, state)
            prefect["historyWeight"] = round(
                float(prefect.get("historyWeight", 0.0)) + float(assignment["weight"]),
                4,
            )
            prefect["historyDuties"] = int(prefect.get("historyDuties", 0)) + 1
            events.append(
                {
                    "weekId": roster_week_id,
                    "assignmentId": int(assignment["id"]),
                    "prefectId": prefect["id"],
                    "delta": float(assignment["weight"]),
                    "dutyDelta": 1,
                    "eventType": "demo_roster_published",
                }
            )
        week["status"] = "published"
        week["publishedAt"] = _datetime_text(_now())
        self._commit(view, state, command_id or "roster-publish")
        return RosterWeekResult(
            id=roster_week_id,
            week_start=date.fromisoformat(str(week["weekStart"])),
            status="published",
            version=int(week["version"]),
            assignment_count=len(week["assignments"]),
            backup_path=None,  # type: ignore[arg-type]
            history_priority_multiplier=float(week["historyPriorityMultiplier"]),
            assist_assignment_mode=str(
                week.get("assistAssignmentMode", FLEXIBLE_WEEKLY)
            ),
        )

    def withdraw_published_roster(
        self,
        roster_week_id: int,
        *,
        expected_version: int,
        reason: str | None = None,
        command_id: str | None = None,
    ) -> RosterWithdrawalResult:
        """Run the same auditable-withdrawal semantics inside demo memory only."""

        self._require_modify()
        normalized_reason = (reason or "").strip()
        operation_id = command_id or f"demo-withdraw:{secrets.token_hex(12)}"
        if not operation_id.strip() or len(operation_id) > 64:
            raise WorkflowError("Demo withdrawal command ID is invalid.")
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "rosterWeekId": roster_week_id,
                    "expectedVersion": expected_version,
                    "reason": normalized_reason,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        view = self._view()
        state = view.state
        saved = state.setdefault("withdrawalReceipts", {}).get(operation_id)
        if saved is not None:
            if saved.get("fingerprint") != fingerprint:
                raise WorkflowConflictError(
                    "This demo withdrawal command ID was reused for a different request."
                )
            return RosterWithdrawalResult(
                roster_week_id=int(saved["rosterWeekId"]),
                week_start=date.fromisoformat(str(saved["weekStart"])),
                status=str(saved["status"]),
                version=int(saved["version"]),
                reason=str(saved["reason"]),
                backup_path=None,
                idempotent=True,
            )

        week = self._week_record(state, roster_week_id)
        if week["status"] != "published":
            raise WorkflowError("Only a published demo roster can be withdrawn.")
        if int(week["version"]) != expected_version:
            raise WorkflowConflictError("This demo roster changed in another tab.")

        prefects = {str(row["id"]): row for row in state.get("prefects", [])}
        net_by_entry: dict[tuple[str, int], list[float | int]] = defaultdict(lambda: [0.0, 0])
        for event in state.get("fairnessEvents", []):
            if int(event.get("weekId", -1)) != roster_week_id:
                continue
            key = (str(event["prefectId"]), int(event["assignmentId"]))
            total = net_by_entry[key]
            total[0] = float(total[0]) + float(event["delta"])
            total[1] = int(total[1]) + int(event["dutyDelta"])

        events = state.setdefault("fairnessEvents", [])
        for (prefect_id, assignment_id), (net_weight, net_duties) in net_by_entry.items():
            weight_delta = round(float(net_weight), 4)
            duty_delta = int(net_duties)
            if abs(weight_delta) <= 0.0001 and duty_delta == 0:
                continue
            prefect = prefects.get(prefect_id)
            if prefect is None:
                raise WorkflowError("A demo fairness prefect no longer exists.")
            self._ensure_history_anchor(prefect, state)
            prefect["historyWeight"] = round(float(prefect["historyWeight"]) - weight_delta, 4)
            prefect["historyDuties"] = int(prefect["historyDuties"]) - duty_delta
            events.append(
                {
                    "weekId": roster_week_id,
                    "assignmentId": assignment_id,
                    "prefectId": prefect_id,
                    "delta": -weight_delta,
                    "dutyDelta": -duty_delta,
                    "eventType": "demo_roster_withdrawn",
                }
            )

        week["status"] = "withdrawn"
        week["version"] = expected_version + 1
        week["withdrawnAt"] = _datetime_text(_now())
        week["withdrawalReason"] = normalized_reason
        receipt = {
            "fingerprint": fingerprint,
            "rosterWeekId": roster_week_id,
            "weekStart": week["weekStart"],
            "status": week["status"],
            "version": week["version"],
            "reason": normalized_reason,
        }
        state["withdrawalReceipts"][operation_id] = receipt
        self._commit(view, state, f"roster-withdraw:{operation_id}")
        return RosterWithdrawalResult(
            roster_week_id=roster_week_id,
            week_start=date.fromisoformat(str(week["weekStart"])),
            status="withdrawn",
            version=int(week["version"]),
            reason=normalized_reason,
            backup_path=None,
        )

    def recommend_substitutes(
        self,
        roster_week_id: int,
        assignment_id: int,
    ) -> list[dict[str, object]]:
        self._require_read()
        state = self._state()
        week = self._week_record(state, roster_week_id)
        if week["status"] != "published":
            raise WorkflowError("Substitute recommendations require a published demo roster.")
        return self._candidate_outputs(state, week, self._assignment_record(week, assignment_id))

    def apply_leave_adjustment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str | None = None,
        command_id: str | None = None,
        expected_week_version: int | None = None,
    ) -> LeaveAdjustmentResult:
        self._require_modify()
        normalized_reason = (reason or "").strip()
        operation_id = command_id or f"demo-leave:{secrets.token_hex(12)}"
        if len(operation_id) > 64 or not operation_id.strip():
            raise WorkflowError("Demo leave adjustment command ID is invalid.")
        fingerprint = self._adjustment_fingerprint(
            roster_week_id,
            assignment_id,
            replacement_prefect_id,
            normalized_reason,
        )
        view = self._view()
        state = view.state
        receipt = state.setdefault("adjustmentReceipts", {}).get(operation_id)
        if receipt is not None:
            if receipt["fingerprint"] != fingerprint:
                raise WorkflowConflictError(
                    "This demo leave-adjustment command ID was reused for a different request."
                )
            return self._adjustment_result(receipt, idempotent=True)
        week = self._week_record(state, roster_week_id)
        if week["status"] != "published":
            raise WorkflowError("A demo post-publication adjustment requires a published roster.")
        requested_version = int(week["version"]) if expected_week_version is None else expected_week_version
        if int(week["version"]) != requested_version:
            raise WorkflowConflictError("This demo roster changed in another tab.")
        assignment = self._assignment_record(week, assignment_id)
        if assignment["status"] != "active" or not assignment.get("prefectId"):
            raise WorkflowError("This demo assignment is no longer active.")
        candidates = {
            str(row["id"]): row for row in self._candidate_outputs(state, week, assignment)
        }
        if replacement_prefect_id and replacement_prefect_id not in candidates:
            raise WorkflowError("The selected demo substitute no longer meets roster rules.")
        prefects = {str(row["id"]): row for row in state.get("prefects", [])}
        original = prefects[str(assignment["prefectId"])]
        weight = float(assignment["weight"])
        self._ensure_history_anchor(original, state)
        original_name = str(assignment["prefectName"])
        original["historyWeight"] = round(float(original["historyWeight"]) - weight, 4)
        original["historyDuties"] = max(0, int(original["historyDuties"]) - 1)
        events = state.setdefault("fairnessEvents", [])
        events.append(
            {
                "weekId": roster_week_id,
                "assignmentId": assignment_id,
                "prefectId": original["id"],
                "delta": -weight,
                "dutyDelta": -1,
                "eventType": "demo_leave_adjustment_debit",
            }
        )
        status = "vacant"
        replacement_name = None
        if replacement_prefect_id:
            replacement = prefects[replacement_prefect_id]
            self._ensure_history_anchor(replacement, state)
            replacement["historyWeight"] = round(float(replacement["historyWeight"]) + weight, 4)
            replacement["historyDuties"] = int(replacement["historyDuties"]) + 1
            assignment["prefectId"] = replacement_prefect_id
            assignment["prefectName"] = replacement["nameZh"]
            assignment["status"] = "active"
            replacement_name = str(replacement["nameZh"])
            status = "replaced"
            events.append(
                {
                    "weekId": roster_week_id,
                    "assignmentId": assignment_id,
                    "prefectId": replacement["id"],
                    "delta": weight,
                    "dutyDelta": 1,
                    "eventType": "demo_leave_adjustment_credit",
                }
            )
        else:
            assignment["prefectId"] = None
            assignment["prefectName"] = "VACANT"
            assignment["status"] = "vacant"
        week["version"] = requested_version + 1
        adjustment = {
            "status": status,
            "reason": normalized_reason,
            "replacementPrefectId": replacement_prefect_id,
            "originalPrefectName": original_name,
            "replacementPrefectName": replacement_name,
        }
        week.setdefault("adjustments", []).append(adjustment)
        receipt = {
            "fingerprint": fingerprint,
            "rosterWeekId": roster_week_id,
            "assignmentId": assignment_id,
            "status": status,
            "version": int(week["version"]),
            "originalPrefectName": original_name,
            "replacementPrefectName": replacement_name,
            "weight": weight,
        }
        state["adjustmentReceipts"][operation_id] = receipt
        self._commit(view, state, f"leave-adjustment:{operation_id}")
        return self._adjustment_result(receipt, idempotent=False)

    def leave_adjustment_count(self, roster_week_id: int) -> int:
        self._require_read()
        return len(self._week_record(self._state(), roster_week_id).get("adjustments", []))

    def fairness_rows(self) -> list[dict[str, object]]:
        self._require_read()
        rows = [
            {
                "id": row["id"],
                "nameZh": row["nameZh"],
                "form": row["form"],
                "className": row["className"],
                "historyWeight": float(row.get("historyWeight", 0.0)),
                "historyDuties": int(row.get("historyDuties", 0)),
            }
            for row in self._state().get("prefects", [])
            if row.get("active", True)
        ]
        return sorted(rows, key=lambda row: (float(row["historyWeight"]), str(row["nameZh"])))

    def reconcile_fairness(self) -> FairnessReconciliationReport:
        self._require_read()
        state = self._state()
        event_totals: dict[str, list[float | int]] = defaultdict(lambda: [0.0, 0])
        for event in state.get("fairnessEvents", []):
            totals = event_totals[str(event["prefectId"])]
            totals[0] = float(totals[0]) + float(event["delta"])
            totals[1] = int(totals[1]) + int(event["dutyDelta"])
        discrepancies: list[FairnessDiscrepancy] = []
        for row in state.get("prefects", []):
            totals = event_totals[str(row["id"])]
            anchor_weight = float(
                row.get("historyWeightAnchor", float(row.get("historyWeight", 0.0)) - float(totals[0]))
            )
            anchor_duties = int(
                row.get("historyDutiesAnchor", int(row.get("historyDuties", 0)) - int(totals[1]))
            )
            expected_weight = round(anchor_weight + float(totals[0]), 4)
            expected_duties = anchor_duties + int(totals[1])
            actual_weight = float(row.get("historyWeight", 0.0))
            actual_duties = int(row.get("historyDuties", 0))
            if abs(expected_weight - actual_weight) > 0.0001 or expected_duties != actual_duties:
                discrepancies.append(
                    FairnessDiscrepancy(
                        prefect_id=str(row["id"]),
                        expected_weight=expected_weight,
                        actual_weight=actual_weight,
                        expected_duties=expected_duties,
                        actual_duties=actual_duties,
                    )
                )
        return FairnessReconciliationReport(len(state.get("prefects", [])), tuple(discrepancies))

    def build_period_report(
        self,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> PeriodSummaryReport:
        self._require_read()
        if period_start is not None:
            self._require_monday(period_start)
        if period_end is not None:
            self._require_monday(period_end)
        if period_start is not None and period_end is not None and period_start > period_end:
            raise WorkflowError("Report start date must not be after its end date.")
        state = self._state()
        weeks = [
            row
            for row in state.get("weeks", [])
            if row["status"] == "published"
            and (period_start is None or date.fromisoformat(str(row["weekStart"])) >= period_start)
            and (period_end is None or date.fromisoformat(str(row["weekStart"])) <= period_end)
        ]
        weeks.sort(key=lambda row: (str(row["weekStart"]), int(row["id"])))
        prefects = list(state.get("prefects", []))
        prefect_by_id = {str(row["id"]): row for row in prefects}
        values: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "dutyCount": 0,
                "points": 0.0,
                "minutes": 0,
                "assist": 0,
                "allocations": [],
                "nameZh": "",
                "roleCode": "",
            }
        )
        recorded = 0
        active = 0
        assist_required = 0
        assist_filled = 0
        adjustments: list[Mapping[str, Any]] = []
        for week in weeks:
            week_start = date.fromisoformat(str(week["weekStart"]))
            assignments = list(week.get("assignments", []))
            recorded += len(assignments)
            adjustments.extend(week.get("adjustments", []))
            for assignment in assignments:
                if assignment["postCode"] == DutyPost.ASSIST_IN_CHARGE.name:
                    assist_required += 1
                if assignment["status"] != "active" or not assignment.get("prefectId"):
                    continue
                active += 1
                if assignment["postCode"] == DutyPost.ASSIST_IN_CHARGE.name:
                    assist_filled += 1
                prefect_id = str(assignment["prefectId"])
                row = values[prefect_id]
                minutes = _duty_minutes(str(assignment["postCode"]))
                row["dutyCount"] += 1
                row["points"] = round(float(row["points"]) + float(assignment["weight"]), 4)
                row["minutes"] += minutes
                row["assist"] += int(assignment["postCode"] == DutyPost.ASSIST_IN_CHARGE.name)
                row["nameZh"] = assignment["prefectName"]
                row["roleCode"] = prefect_by_id[prefect_id].get(
                    "roleCode", prefect_by_id[prefect_id].get("role")
                )
                start_time, end_time = DUTY_SERVICE_TIME_WINDOWS[DutyPost[str(assignment["postCode"])]]
                row["allocations"].append(
                    DutyAllocationEntry(
                        roster_week_id=int(week["id"]),
                        roster_version=int(week["version"]),
                        policy_version=str(week.get("policyVersion", DEMO_POLICY_VERSION)),
                        assignment_id=int(assignment["id"]),
                        duty_date=week_start + timedelta(days=int(SchoolDay[str(assignment["day"])])),
                        day=str(assignment["day"]),
                        post_code=str(assignment["postCode"]),
                        start_time=start_time,
                        end_time=end_time,
                        scheduled_minutes=minutes,
                    )
                )
        contributions: list[PrefectPeriodContribution] = []
        for prefect in prefects:
            if not prefect.get("active", True) and str(prefect["id"]) not in values:
                continue
            row = values[str(prefect["id"])]
            role_code = str(prefect.get("roleCode", prefect.get("role")))
            status_codes: list[str] = []
            if float(prefect.get("historyWeight", 0.0)) == 0 and int(prefect.get("historyDuties", 0)) == 0:
                status_codes.append("new_prefect")
            if prefect.get("needsMentoring", False):
                status_codes.append("needs_mentoring")
            if role_code == PrefectRole.ASSISTANT_HEAD.value:
                status_codes.append("assistant_head")
            contributions.append(
                PrefectPeriodContribution(
                    prefect_id=str(prefect["id"]),
                    name_zh=str(row["nameZh"] or prefect["nameZh"]),
                    role_code=str(row["roleCode"] or role_code),
                    duty_count=int(row["dutyCount"]),
                    workload_points=float(row["points"]),
                    scheduled_minutes=int(row["minutes"]),
                    assist_in_charge_count=int(row["assist"]),
                    current_history_weight=float(prefect.get("historyWeight", 0.0)),
                    current_history_duties=int(prefect.get("historyDuties", 0)),
                    status_codes=tuple(status_codes),
                    allocations=tuple(
                        sorted(row["allocations"], key=lambda item: (item.duty_date, item.assignment_id))
                    ),
                )
            )
        contributions.sort(key=lambda row: (-row.duty_count, -row.workload_points, row.name_zh))
        trend = self._fairness_trend(state, weeks)
        active_weights = [
            float(row.get("historyWeight", 0.0)) for row in prefects if row.get("active", True)
        ]
        distribution = (
            (
                trend[-1].minimum,
                trend[-1].median,
                trend[-1].maximum,
                trend[-1].spread,
                trend[-1].population_stddev,
            )
            if trend
            else _distribution(active_weights)
        )
        reconciliation = self.reconcile_fairness()
        notes = ["service_is_not_performance", "scheduled_times_use_current_policy", "demo_data_only"]
        notes.append("ledger_reconciled" if reconciliation.balanced else "ledger_review_required")
        if not weeks:
            notes.append("no_published_rosters")
        elif recorded == active:
            notes.append("all_required_posts_covered")
        else:
            notes.append("vacancies_require_review")
        return PeriodSummaryReport(
            schema_version="1.0-demo",
            generated_at=_now(),
            period_start=date.fromisoformat(str(weeks[0]["weekStart"])) if weeks else period_start,
            period_end=date.fromisoformat(str(weeks[-1]["weekStart"])) if weeks else period_end,
            sources=tuple(
                ReportRosterSource(
                    int(week["id"]),
                    date.fromisoformat(str(week["weekStart"])),
                    int(week["version"]),
                    str(week.get("policyVersion", DEMO_POLICY_VERSION)),
                    float(week["historyPriorityMultiplier"]),
                )
                for week in weeks
            ),
            active_prefect_count=sum(1 for row in prefects if row.get("active", True)),
            published_week_count=len(weeks),
            recorded_slot_count=recorded,
            active_assignment_count=active,
            vacant_slot_count=recorded - active,
            coverage_rate=round(active / recorded * 100, 2) if recorded else None,
            workload_points=round(sum(row.workload_points for row in contributions), 4),
            scheduled_minutes=sum(row.scheduled_minutes for row in contributions),
            leave_adjustment_count=len(adjustments),
            replacement_count=sum(1 for row in adjustments if row["status"] == "replaced"),
            assist_required_count=assist_required,
            assist_filled_count=assist_filled,
            fairness_minimum=distribution[0],
            fairness_median=distribution[1],
            fairness_maximum=distribution[2],
            fairness_spread=distribution[3],
            fairness_population_stddev=distribution[4],
            fairness_ledger_balanced=reconciliation.balanced,
            contributions=tuple(contributions),
            trend=trend,
            note_codes=tuple(notes),
        )

    def backup_status(self) -> dict[str, object]:
        self._require_read()
        state = self._state()
        created_at = _parse_datetime(state.get("demoBackupAt"))
        path = _DemoPath(_DEMO_BACKUP_NAME) if created_at else None
        return {
            "databasePath": "DEMO · memory only",
            "backupDirectory": "DEMO · no durable storage",
            "latestSuccess": True if created_at else None,
            "latestPath": path,
            "latestCreatedAt": created_at,
            "latestVerification": (
                {
                    "valid": True,
                    "reasonCode": "demo_memory_only",
                    "integrity": "simulated",
                    "sha256": hashlib.sha256(self._workspace_id.encode("utf-8")).hexdigest(),
                }
                if created_at
                else None
            ),
        }

    def backup_inventory(self, limit: int = 12) -> dict[str, object]:
        self._require_read()
        del limit
        status = self.backup_status()
        items = []
        if status["latestPath"]:
            items.append(
                {
                    "path": status["latestPath"],
                    "createdAt": status["latestCreatedAt"],
                    "sizeBytes": 0,
                    "verification": status["latestVerification"],
                }
            )
        return {
            "items": items,
            "checkedCount": len(items),
            "verifiedCount": len(items),
            "invalidCount": 0,
            "invalidReasonCounts": {},
        }

    def create_verified_backup(self) -> _DemoPath:
        """Create only a reversible in-memory checkpoint marker."""

        self._require_modify()
        view = self._view()
        state = view.state
        state["demoBackupAt"] = _datetime_text(_now())
        state["demoBackupState"] = deepcopy(
            {key: value for key, value in state.items() if key not in {"demoBackupState"}}
        )
        self._commit(view, state, "demo-backup")
        return _DemoPath(_DEMO_BACKUP_NAME)

    def restore_backup(self, backup_path: object) -> dict[str, object]:
        """Restore only an in-memory demo checkpoint; never inspect a path."""

        self._require_modify()
        if str(backup_path) != _DEMO_BACKUP_NAME:
            raise WorkflowError("Only the in-memory demo checkpoint can be restored.")
        view = self._view()
        checkpoint = view.state.get("demoBackupState")
        restored = deepcopy(checkpoint) if isinstance(checkpoint, dict) else demo_fixture()
        restored["demoBackupAt"] = _datetime_text(_now())
        restored["demoBackupState"] = deepcopy(checkpoint) if isinstance(checkpoint, dict) else demo_fixture()
        self._commit(view, restored, "demo-restore")
        path = _DemoPath(_DEMO_BACKUP_NAME)
        return {
            "restoredFrom": path,
            "preRestoreBackup": path,
            "restoredBackup": path,
            "demo": True,
        }

    def build_verified_handover_package(self) -> HandoverBackupPackage:
        self._context.require(Capability.DEMO_RESULT_DOWNLOAD)
        status = self.backup_status()
        if not status["latestPath"]:
            raise WorkflowError("Create an in-memory demo checkpoint first.")
        content = json.dumps(
            {
                "demo": True,
                "fictional": True,
                "message": "No official or durable data is contained in this demonstration.",
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        return HandoverBackupPackage(
            filename="SYSS_DEMO_Handover.json",
            content=content,
            source_backup_path=status["latestPath"],  # type: ignore[arg-type]
        )

    def handover_readiness(self) -> dict[str, object]:
        self._require_read()
        status = self.backup_status()
        return {
            "activePrefectCount": len(self.prefects()),
            "rosterCount": len(self.roster_weeks()),
            "verifiedBackup": bool(status["latestVerification"]),
            "backupPath": status["latestPath"],
            "demo": True,
        }

    def prepare_new_school_year(self) -> dict[str, object]:
        self._require_modify()
        view = self._view()
        state = view.state
        active = [row for row in state.get("prefects", []) if row.get("active", True)]
        if not active:
            raise WorkflowError("The demo prefect directory is already empty.")
        active_ids = {str(row["id"]) for row in active}
        for row in active:
            row["active"] = False
            row["version"] = int(row.get("version", 1)) + 1
        cancelled = 0
        for leave in state.get("preGenerationLeave", []):
            if leave.get("active", True) and str(leave["prefectId"]) in active_ids:
                leave["active"] = False
                cancelled += 1
        self._commit(view, state, "demo-school-year-rollover")
        path = _DemoPath(_DEMO_BACKUP_NAME)
        return {
            "archivedPrefectCount": len(active),
            "cancelledLeaveCount": cancelled,
            "beforeBackup": path,
            "afterBackup": path,
            "demo": True,
        }

    def reset_demo_fixture(self) -> dict[str, object]:
        self._require_modify()
        view = self._view()
        self._commit(view, demo_fixture(), "demo-fixture-reset")
        return {"reset": True, "fixtureVersion": DEMO_FIXTURE_VERSION}

    def _require_read(self) -> None:
        self._context.require(Capability.DEMO_DATA_READ)

    def _require_modify(self) -> None:
        self._context.require(Capability.DEMO_STATE_MODIFY)

    def _view(self) -> GuestWorkspaceView:
        if not self._bound:
            return GuestWorkspaceView(
                session_id=self._initial_view.session_id,
                workspace_id=self._initial_view.workspace_id,
                tab_id=self._initial_view.tab_id,
                revision=self._initial_view.revision,
                expires_at=self._initial_view.expires_at,
                state=deepcopy(self._initial_view.state),
            )
        return self._registry.get_workspace(
            session_id=self._session_id,
            workspace_id=self._workspace_id,
            tab_id=self._tab_id,
        )

    def _state(self) -> dict[str, Any]:
        return self._view().state

    def _commit(
        self,
        view: GuestWorkspaceView,
        state: Mapping[str, Any],
        operation: str,
    ) -> GuestWorkspaceView:
        if not self._bound:
            raise WorkflowError("The demo workspace is still connecting. Try the action again.")
        try:
            updated = self._registry.replace_state(
                session_id=self._session_id,
                workspace_id=self._workspace_id,
                tab_id=self._tab_id,
                expected_revision=view.revision,
                command_id=f"{operation}:{secrets.token_hex(12)}",
                state=state,
            )
            self._initial_view = updated
            if self._snapshot_publisher is not None:
                self._snapshot_publisher(updated)
            return updated
        except GuestRevisionConflict as error:
            raise WorkflowConflictError("This demo workspace changed in another tab.") from error

    @staticmethod
    def _prefect_output(record: Mapping[str, Any]) -> dict[str, object]:
        return {
            "id": str(record["id"]),
            "nameZh": str(record["nameZh"]),
            "nameEn": record.get("nameEn"),
            "form": str(record["form"]),
            "className": str(record["className"]),
            "roleCode": str(record.get("roleCode", record.get("role"))),
            "historyWeight": float(record.get("historyWeight", 0.0)),
            "historyDuties": int(record.get("historyDuties", 0)),
            "availableDays": GuestWorkspaceAdapter._sorted_days(record.get("availableDays", [])),
            "needsMentoring": bool(record.get("needsMentoring", False)),
            "fixedGeneralDuty": str(record.get("fixedGeneralDuty", "NONE")),
            "remarks": str(record.get("remarks", "")),
            "version": int(record.get("version", 1)),
            "active": bool(record.get("active", True)),
            "fictional": True,
        }

    @staticmethod
    def _leave_output(
        declaration: Mapping[str, Any],
        prefect: Mapping[str, Any],
    ) -> dict[str, object]:
        return {
            "id": int(declaration["id"]),
            "weekStart": date.fromisoformat(str(declaration["weekStart"])),
            "prefectId": str(declaration["prefectId"]),
            "prefectName": str(prefect["nameZh"]),
            "day": str(declaration["day"]),
            "reason": declaration.get("reason"),
            "version": int(declaration.get("version", 1)),
            "createdAt": _parse_datetime(declaration.get("createdAt")),
            "updatedAt": _parse_datetime(declaration.get("updatedAt")),
        }

    @staticmethod
    def _week_output(week: Mapping[str, Any]) -> dict[str, object]:
        return {
            "id": int(week["id"]),
            "weekStart": date.fromisoformat(str(week["weekStart"])),
            "status": str(week["status"]),
            "version": int(week["version"]),
            "historyPriorityMultiplier": float(week["historyPriorityMultiplier"]),
            "assistAssignmentMode": str(
                week.get("assistAssignmentMode", FLEXIBLE_WEEKLY)
            ),
            "generatedAt": _parse_datetime(week.get("generatedAt")),
            "publishedAt": _parse_datetime(week.get("publishedAt")),
            "withdrawnAt": _parse_datetime(week.get("withdrawnAt")),
            "withdrawalReason": week.get("withdrawalReason"),
        }

    @staticmethod
    def _prefect_record(state: Mapping[str, Any], prefect_id: str) -> dict[str, Any]:
        record = next(
            (row for row in state.get("prefects", []) if str(row["id"]) == prefect_id),
            None,
        )
        if record is None:
            raise WorkflowError("Demo prefect was not found.")
        return record

    @staticmethod
    def _week_record(state: Mapping[str, Any], roster_week_id: int) -> dict[str, Any]:
        week = next(
            (row for row in state.get("weeks", []) if int(row["id"]) == roster_week_id),
            None,
        )
        if week is None:
            raise WorkflowError("Demo roster week was not found.")
        return week

    @staticmethod
    def _week_by_start(state: Mapping[str, Any], week_start: date) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in state.get("weeks", [])
                if str(row["weekStart"]) == week_start.isoformat()
                and str(row.get("status")) in {"draft", "published"}
            ),
            None,
        )

    @staticmethod
    def _previous_assist_weekday_assignments(
        state: Mapping[str, Any],
        week_start: date,
    ) -> dict[SchoolDay, str]:
        previous_week = GuestWorkspaceAdapter._week_by_start(
            state,
            week_start - timedelta(days=7),
        )
        if previous_week is None:
            return {}
        return {
            SchoolDay[str(row["day"])]: str(row["prefectId"])
            for row in previous_week.get("assignments", [])
            if row.get("status") == "active"
            and row.get("prefectId")
            and row.get("postCode") == "ASSIST_IN_CHARGE"
            and str(row.get("day")) in SchoolDay.__members__
        }

    @staticmethod
    def _assignment_record(week: Mapping[str, Any], assignment_id: int) -> dict[str, Any]:
        assignment = next(
            (row for row in week.get("assignments", []) if int(row["id"]) == assignment_id),
            None,
        )
        if assignment is None:
            raise WorkflowError("Demo roster assignment was not found.")
        return assignment

    @staticmethod
    def _sorted_assignments(week: Mapping[str, Any]) -> list[dict[str, Any]]:
        post_rank = {
            "ASSIST_IN_CHARGE": 0,
            "ROOM_302": 1,
            "ROOM_303": 2,
            "ROOM_202": 3,
        }
        return sorted(
            week.get("assignments", []),
            key=lambda row: (
                int(SchoolDay[str(row["day"])]),
                post_rank[str(row["postCode"])],
                int(row["slotIndex"]),
            ),
        )

    @staticmethod
    def _next_integer_id(rows: Iterable[Mapping[str, Any]]) -> int:
        return max((int(row["id"]) for row in rows), default=0) + 1

    @staticmethod
    def _next_assignment_id(state: Mapping[str, Any]) -> int:
        return (
            max(
                (
                    int(assignment["id"])
                    for week in state.get("weeks", [])
                    for assignment in week.get("assignments", [])
                ),
                default=0,
            )
            + 1
        )

    @staticmethod
    def _sorted_days(days: Iterable[str]) -> list[str]:
        return sorted((str(day) for day in days), key=lambda day: int(SchoolDay[day]))

    @staticmethod
    def _require_monday(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise WorkflowError("A demo roster week must start on Monday.")

    @staticmethod
    def _validate_prefect_input(prefect_input: PrefectInput) -> None:
        if not is_chinese_display_name(prefect_input.name_zh):
            raise WorkflowError("The authoritative demo prefect display name must be Chinese.")
        if prefect_input.form not in {"F.3", "F.4", "F.5", "F.6"}:
            raise WorkflowError("Form must be F.3, F.4, F.5, or F.6.")
        if not prefect_input.class_name.strip():
            raise WorkflowError("Class is required.")
        if prefect_input.role_code not in {role.value for role in PrefectRole}:
            raise WorkflowError("Role is not recognized.")
        if not prefect_input.available_days:
            raise WorkflowError("At least one available day is required.")
        if any(day not in SchoolDay.__members__ for day in prefect_input.available_days):
            raise WorkflowError("Availability contains an invalid weekday.")
        if len(set(prefect_input.available_days)) != len(prefect_input.available_days):
            raise WorkflowError("Availability contains duplicate weekdays.")
        if (
            prefect_input.fixed_general_duty != "NONE"
            and prefect_input.fixed_general_duty not in SchoolDay.__members__
        ):
            raise WorkflowError("Fixed duty contains an invalid weekday.")
        if (
            prefect_input.role_code == PrefectRole.ASSISTANT_HEAD.value
            and prefect_input.fixed_general_duty != "NONE"
            and prefect_input.fixed_general_duty not in prefect_input.available_days
        ):
            raise WorkflowError("Fixed duty must also be an available weekday.")
        if prefect_input.history_weight < 0 or prefect_input.history_duties < 0:
            raise WorkflowError("History values cannot be negative.")

    @staticmethod
    def _assert_name_available(
        state: Mapping[str, Any],
        name_zh: str,
        *,
        exclude_prefect_id: str | None = None,
    ) -> None:
        normalized = name_zh.strip()
        if any(
            row.get("active", True)
            and row["nameZh"] == normalized
            and str(row["id"]) != exclude_prefect_id
            for row in state.get("prefects", [])
        ):
            raise WorkflowError("A demo prefect with this Chinese name already exists.")

    @staticmethod
    def _assert_assist_fixed_day_available(
        state: Mapping[str, Any],
        prefect_input: PrefectInput,
        *,
        exclude_prefect_id: str | None = None,
    ) -> None:
        if (
            prefect_input.role_code != PrefectRole.ASSISTANT_HEAD.value
            or prefect_input.fixed_general_duty == "NONE"
        ):
            return
        if any(
            row.get("active", True)
            and str(row.get("roleCode", row.get("role", "")))
            == PrefectRole.ASSISTANT_HEAD.value
            and str(row.get("fixedGeneralDuty", "NONE"))
            == prefect_input.fixed_general_duty
            and str(row.get("id", "")) != exclude_prefect_id
            for row in state.get("prefects", [])
        ):
            raise WorkflowConflictError(
                "Another active Assistant Head Study Prefect already owns this fixed weekday."
            )

    @staticmethod
    def _active_prefects(state: Mapping[str, Any]) -> list[Prefect]:
        return [
            Prefect(
                id=str(row["id"]),
                name=str(row["nameZh"]),
                form=str(row["form"]),
                class_name=str(row["className"]),
                role=PrefectRole(str(row.get("roleCode", row.get("role")))),
                available_days=frozenset(SchoolDay[str(day)] for day in row.get("availableDays", [])),
                history_weight=float(row.get("historyWeight", 0.0)),
                history_duties=int(row.get("historyDuties", 0)),
                needs_mentoring=bool(row.get("needsMentoring", False)),
                fixed_general_duty=str(row.get("fixedGeneralDuty", "NONE")),
                remarks=str(row.get("remarks", "")),
            )
            for row in state.get("prefects", [])
            if row.get("active", True)
        ]

    @staticmethod
    def _leave_days(
        state: Mapping[str, Any],
        week_start: date,
    ) -> dict[str, set[SchoolDay]]:
        leave_days: dict[str, set[SchoolDay]] = defaultdict(set)
        for row in state.get("preGenerationLeave", []):
            if row.get("active", True) and row["weekStart"] == week_start.isoformat():
                leave_days[str(row["prefectId"])].add(SchoolDay[str(row["day"])])
        return leave_days

    def _validate_week_assignments(
        self,
        state: Mapping[str, Any],
        week: Mapping[str, Any],
    ) -> None:
        domain_rows = []
        for row in week.get("assignments", []):
            if row["status"] != "active" or not row.get("prefectId"):
                raise WorkflowError("A demo draft with missing assignments cannot be published.")
            domain_rows.append(
                Assignment(
                    day=SchoolDay[str(row["day"])],
                    post=DutyPost[str(row["postCode"])],
                    prefect_id=str(row["prefectId"]),
                    prefect_name=str(row["prefectName"]),
                    weight=float(row["weight"]),
                )
            )
        try:
            validate_assignments(
                domain_rows,
                self._active_prefects(state),
                leave_days=self._leave_days(state, date.fromisoformat(str(week["weekStart"]))),
            )
        except RosterPolicyError as error:
            raise WorkflowError(str(error)) from error

    def _candidate_outputs(
        self,
        state: Mapping[str, Any],
        week: Mapping[str, Any],
        assignment: Mapping[str, Any],
    ) -> list[dict[str, object]]:
        if assignment["status"] != "active" or not assignment.get("prefectId"):
            raise WorkflowError("Only an active demo assignment can be changed.")
        day = SchoolDay[str(assignment["day"])]
        post = DutyPost[str(assignment["postCode"])]
        assigned_today = {
            str(row["prefectId"])
            for row in week.get("assignments", [])
            if row["id"] != assignment["id"]
            and row["status"] == "active"
            and row["day"] == assignment["day"]
            and row.get("prefectId")
        }
        other_days: dict[str, set[SchoolDay]] = defaultdict(set)
        for row in week.get("assignments", []):
            if row["id"] != assignment["id"] and row["status"] == "active" and row.get("prefectId"):
                other_days[str(row["prefectId"])].add(SchoolDay[str(row["day"])])
        leave_days = self._leave_days(state, date.fromisoformat(str(week["weekStart"])))
        candidates = []
        for row in state.get("prefects", []):
            if not row.get("active", True) or str(row["id"]) == assignment["prefectId"]:
                continue
            prefect_id = str(row["id"])
            if prefect_id in assigned_today:
                continue
            if day.name not in row.get("availableDays", []):
                continue
            if day in leave_days.get(prefect_id, set()):
                continue
            role = PrefectRole(str(row.get("roleCode", row.get("role"))))
            if not can_assign_role(role, post):
                continue
            if any(abs(int(existing) - int(day)) == 1 for existing in other_days[prefect_id]):
                continue
            candidates.append(row)
        candidates.sort(
            key=lambda row: (
                float(row.get("historyWeight", 0.0)),
                int(str(row["form"]).removeprefix("F.")),
                int(row.get("historyDuties", 0)),
                str(row["nameZh"]),
            )
        )
        return [
            {
                "id": str(row["id"]),
                "nameZh": str(row["nameZh"]),
                "form": str(row["form"]),
                "className": str(row["className"]),
                "historyWeight": float(row.get("historyWeight", 0.0)),
            }
            for row in candidates
        ]

    @staticmethod
    def _ensure_history_anchor(prefect: dict[str, Any], state: Mapping[str, Any]) -> None:
        if "historyWeightAnchor" in prefect and "historyDutiesAnchor" in prefect:
            return
        events = [
            event
            for event in state.get("fairnessEvents", [])
            if str(event["prefectId"]) == str(prefect["id"])
        ]
        prefect["historyWeightAnchor"] = round(
            float(prefect.get("historyWeight", 0.0))
            - sum(float(event["delta"]) for event in events),
            4,
        )
        prefect["historyDutiesAnchor"] = int(prefect.get("historyDuties", 0)) - sum(
            int(event["dutyDelta"]) for event in events
        )

    @staticmethod
    def _adjustment_fingerprint(
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str,
    ) -> str:
        payload = {
            "assignmentId": assignment_id,
            "reason": reason,
            "replacementPrefectId": replacement_prefect_id,
            "rosterWeekId": roster_week_id,
            "schemaVersion": 1,
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _adjustment_result(
        receipt: Mapping[str, Any],
        *,
        idempotent: bool,
    ) -> LeaveAdjustmentResult:
        return LeaveAdjustmentResult(
            roster_week_id=int(receipt["rosterWeekId"]),
            assignment_id=int(receipt["assignmentId"]),
            status=str(receipt["status"]),
            backup_path=None,
            version=int(receipt["version"]),
            idempotent=idempotent,
            original_prefect_name=str(receipt["originalPrefectName"]),
            replacement_prefect_name=(
                str(receipt["replacementPrefectName"])
                if receipt.get("replacementPrefectName")
                else None
            ),
            weight=float(receipt["weight"]),
        )

    def _fairness_trend(
        self,
        state: Mapping[str, Any],
        weeks: list[Mapping[str, Any]],
    ) -> tuple[FairnessTrendPoint, ...]:
        events_by_prefect: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for event in state.get("fairnessEvents", []):
            events_by_prefect[str(event["prefectId"])].append(event)
        balances: dict[str, float] = {}
        for prefect in state.get("prefects", []):
            event_delta = sum(float(event["delta"]) for event in events_by_prefect[str(prefect["id"])])
            balances[str(prefect["id"])] = float(
                prefect.get(
                    "historyWeightAnchor",
                    float(prefect.get("historyWeight", 0.0)) - event_delta,
                )
            )
        week_date_by_id = {
            int(row["id"]): date.fromisoformat(str(row["weekStart"]))
            for row in state.get("weeks", [])
        }
        trend: list[FairnessTrendPoint] = []
        for week in weeks:
            point_date = date.fromisoformat(str(week["weekStart"]))
            point_balances = dict(balances)
            for event in state.get("fairnessEvents", []):
                event_date = week_date_by_id.get(int(event["weekId"]))
                if event_date is not None and event_date <= point_date:
                    prefect_id = str(event["prefectId"])
                    point_balances[prefect_id] = round(
                        point_balances.get(prefect_id, 0.0) + float(event["delta"]),
                        4,
                    )
            distribution = _distribution(list(point_balances.values()))
            trend.append(
                FairnessTrendPoint(
                    roster_week_id=int(week["id"]),
                    week_start=date.fromisoformat(str(week["weekStart"])),
                    version=int(week["version"]),
                    minimum=distribution[0],
                    median=distribution[1],
                    maximum=distribution[2],
                    spread=distribution[3],
                    population_stddev=distribution[4],
                )
            )
        return tuple(trend)


__all__ = ["DEMO_POLICY_VERSION", "GuestWorkspaceAdapter"]
