from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowConflictError
from nicegui_app.services.workflow_types import DraftCellEdit, DraftDayEdit
from roster_core import Prefect, generate_weekly_roster, validate_assignments
from roster_policy import AssistAssignmentMode, DAYS, DutyPost, PrefectRole, SchoolDay


WEEK_START = date(2026, 9, 7)
GUEST_SECRET = b"draft-patch-integrity-secret-32-bytes"


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    service.bootstrap()
    return service


def _cell_key(row: dict[str, object]) -> str:
    return f"{row['day']}:{row['postCode']}:{int(row['slotIndex'])}"


def _directory() -> list[Prefect]:
    assistants = [
        Prefect(
            id=f"ahp-{index}",
            name=f"助理首席{index}",
            form="F.5",
            class_name="5A",
            role=PrefectRole.ASSISTANT_HEAD,
            available_days=frozenset(DAYS),
            history_weight=0.0,
            fixed_general_duty=day.name,
        )
        for index, day in enumerate(DAYS)
    ]
    ordinary = [
        Prefect(
            id=f"sp-{index}",
            name=f"導學風紀{index}",
            form="F.4",
            class_name="4A",
            role=PrefectRole.STUDY_PREFECT,
            available_days=frozenset(DAYS),
            history_weight=0.0,
        )
        for index in range(12)
    ]
    return [*assistants, *ordinary]


def _assist_by_day(assignments) -> dict[SchoolDay, str]:
    return {
        assignment.day: assignment.prefect_id
        for assignment in assignments
        if assignment.post is DutyPost.ASSIST_IN_CHARGE
    }


def _guest_context(session_id: str) -> PageContext:
    return PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject=f"guest:{session_id}",
            session_id=session_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference=f"GUEST-{session_id}",
    )


def test_explicit_vacancy_is_versioned_but_draft_fairness_stays_unchanged(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    target = next(
        row
        for row in workflow.assignments(draft.id)
        if row["day"] == "MONDAY" and row["postCode"] == DutyPost.ROOM_302.name
    )
    target_key = _cell_key(target)
    original_prefect_id = str(target["prefectId"])
    fairness_before = workflow.prefect_loads()
    assignment_count = len(workflow.assignments(draft.id))

    vacant = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        cell_edits=(DraftCellEdit(target_key, None),),
        command_id="explicit-vacancy",
    )

    assert vacant.changed_cell_count == 1
    assert len(workflow.assignments(draft.id)) == assignment_count - 1
    assert target_key not in {_cell_key(row) for row in workflow.assignments(draft.id)}
    assert workflow.prefect_loads() == fairness_before

    restored = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=vacant.version,
        cell_edits=(DraftCellEdit(target_key, original_prefect_id),),
        command_id="restore-explicit-vacancy",
    )
    assert workflow.prefect_loads() == fairness_before

    workflow.publish(
        draft.id,
        expected_week_version=restored.version,
        command_id="publish-restored-grid",
    )
    fairness_after_publish = workflow.prefect_loads()
    workflow.publish(
        draft.id,
        expected_week_version=restored.version,
        command_id="publish-restored-grid",
    )

    assert fairness_after_publish != fairness_before
    assert workflow.prefect_loads() == fairness_after_publish
    assert workflow.reconcile_fairness().balanced


def test_stale_mixed_patch_has_no_partial_write_and_does_not_poison_command_id(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    current = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        day_edits=(DraftDayEdit(day="THURSDAY", closed=True),),
        command_id="first-grid-change",
    )
    monday = next(
        row
        for row in workflow.assignments(draft.id)
        if row["day"] == "MONDAY" and row["postCode"] == DutyPost.ROOM_302.name
    )
    before_week = workflow.roster_week(draft.id)
    before_assignments = workflow.assignments(draft.id)
    before_fairness = workflow.prefect_loads()
    mixed_edits = (DraftCellEdit(_cell_key(monday), None),)
    mixed_days = (DraftDayEdit(day="FRIDAY", closed=True),)

    with pytest.raises(WorkflowConflictError, match="changed in another browser"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=draft.version,
            cell_edits=mixed_edits,
            day_edits=mixed_days,
            command_id="stale-mixed-grid-patch",
        )

    assert workflow.roster_week(draft.id) == before_week
    assert workflow.assignments(draft.id) == before_assignments
    assert workflow.prefect_loads() == before_fairness

    retried = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=current.version,
        cell_edits=mixed_edits,
        day_edits=mixed_days,
        command_id="stale-mixed-grid-patch",
    )

    assert retried.closed_days == ("THURSDAY", "FRIDAY")
    assert _cell_key(monday) not in {
        _cell_key(row) for row in workflow.assignments(draft.id)
    }
    assert workflow.prefect_loads() == before_fairness


def test_legacy_closed_day_is_skipped_not_shifted_and_flexible_uses_open_days_only() -> None:
    prefects = _directory()
    baseline = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key=WEEK_START.isoformat(),
    )
    legacy_closed = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key=WEEK_START.isoformat(),
        closed_days=(SchoolDay.WEDNESDAY,),
    )
    baseline_assist = _assist_by_day(baseline)
    closed_assist = _assist_by_day(legacy_closed)

    assert set(closed_assist) == set(DAYS) - {SchoolDay.WEDNESDAY}
    assert closed_assist == {
        day: prefect_id
        for day, prefect_id in baseline_assist.items()
        if day is not SchoolDay.WEDNESDAY
    }

    flexible_closed_days = (SchoolDay.TUESDAY, SchoolDay.FRIDAY)
    flexible = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key=WEEK_START.isoformat(),
        closed_days=flexible_closed_days,
    )
    open_days = set(DAYS) - set(flexible_closed_days)

    assert {assignment.day for assignment in flexible} == open_days
    assert set(_assist_by_day(flexible)) == open_days
    validate_assignments(
        flexible,
        prefects,
        closed_days=flexible_closed_days,
    )


def test_guest_day_closures_are_isolated_between_workspaces_in_one_session() -> None:
    registry = GuestWorkspaceRegistry(GUEST_SECRET)
    context = _guest_context("shared-session")
    first = GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="closure-workspace-a",
        tab_id="closure-tab-a",
    )
    second = GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="closure-workspace-b",
        tab_id="closure-tab-b",
    )
    first_draft = first.generate_and_save_draft(WEEK_START)
    second_draft = second.generate_and_save_draft(WEEK_START)
    second_before = second.assignments(second_draft.id)

    changed = first.apply_draft_patch(
        roster_week_id=first_draft.id,
        expected_week_version=first_draft.version,
        day_edits=(DraftDayEdit(day="MONDAY", closed=True),),
        command_id="guest-close-monday-isolated",
    )

    assert changed.closed_days == ("MONDAY",)
    assert first.roster_week(first_draft.id)["closedDays"] == ["MONDAY"]
    assert not any(row["day"] == "MONDAY" for row in first.assignments(first_draft.id))
    assert second.roster_week(second_draft.id)["closedDays"] == []
    assert second.assignments(second_draft.id) == second_before
