from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import (
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
)
from nicegui_app.services.workflow_types import DraftCellEdit, DraftDayEdit
from roster_core import Prefect, generate_weekly_roster, validate_assignments
from roster_policy import DAYS, DutyPost, PrefectRole, RosterPolicyError, SchoolDay


WEEK_START = date(2026, 9, 7)
SECRET = b"day-closure-guest-test-secret-32-bytes"


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    service.bootstrap()
    return service


def _guest_adapter() -> GuestWorkspaceAdapter:
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:day-closure",
            session_id="day-closure",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="GUEST-DAY-CLOSURE",
    )
    return GuestWorkspaceAdapter(
        context,
        GuestWorkspaceRegistry(SECRET),
        workspace_id="day-closure-workspace",
        tab_id="day-closure-tab",
    )


def _core_directory() -> list[Prefect]:
    return [
        *(
            Prefect(
                id=f"ahp-{index}",
                name=f"助理首席{index}",
                form="F.5",
                class_name="5A",
                role=PrefectRole.ASSISTANT_HEAD,
                available_days=frozenset(DAYS),
                history_weight=0.0,
            )
            for index in range(5)
        ),
        *(
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
        ),
    ]


def _cell_key(row: dict[str, object]) -> str:
    return f"{row['day']}:{row['postCode']}:{int(row['slotIndex'])}"


def test_core_accepts_a_fully_closed_week_as_an_intentional_empty_roster() -> None:
    prefects = _core_directory()

    assignments = generate_weekly_roster(prefects, closed_days=DAYS)

    assert assignments == []
    validate_assignments(assignments, prefects, closed_days=DAYS)
    with pytest.raises(ValueError, match="stable SchoolDay"):
        validate_assignments([], prefects, closed_days=("MONDAY",))  # type: ignore[arg-type]


def test_closed_days_are_persisted_and_publish_only_posts_open_day_fairness(
    workflow: RosterWorkflow,
) -> None:
    before = workflow.prefect_loads()
    draft = workflow.generate_and_save_draft(
        WEEK_START,
        closed_days=("TUESDAY", SchoolDay.FRIDAY),
        command_id="generate-with-closures",
    )

    assert draft.assignment_count == 18
    assert workflow.roster_week(draft.id)["closedDays"] == ["TUESDAY", "FRIDAY"]
    assert workflow.week_schedule_overrides(draft.id).closed_days == (
        "TUESDAY",
        "FRIDAY",
    )
    assert {row["day"] for row in workflow.assignments(draft.id)} == {
        "MONDAY",
        "WEDNESDAY",
        "THURSDAY",
    }

    published = workflow.publish(
        draft.id,
        expected_week_version=draft.version,
        command_id="publish-with-closures",
    )
    after = workflow.prefect_loads()

    assert published.assignment_count == 18
    assert sum(after.values()) - sum(before.values()) == pytest.approx(24.0)
    assert workflow.reconcile_fairness().balanced


def test_a_fully_closed_week_publishes_without_posting_fairness(
    workflow: RosterWorkflow,
) -> None:
    before = workflow.prefect_loads()
    draft = workflow.generate_and_save_draft(
        WEEK_START,
        closed_days=DAYS,
        command_id="generate-fully-closed-week",
    )

    assert draft.assignment_count == 0
    assert workflow.roster_week(draft.id)["closedDays"] == [day.name for day in DAYS]
    published = workflow.publish(
        draft.id,
        expected_week_version=draft.version,
        command_id="publish-fully-closed-week",
    )

    assert published.assignment_count == 0
    assert workflow.prefect_loads() == before
    assert workflow.reconcile_fairness().balanced


def test_close_then_reopen_and_restore_a_day_is_one_replay_safe_patch(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    fairness_before = workflow.prefect_loads()
    monday = [row for row in workflow.assignments(draft.id) if row["day"] == "MONDAY"]

    closed = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        day_edits=(
            DraftDayEdit(
                day="MONDAY",
                closed=True,
                reason_code="school_event",
                note="Whole-school event",
            ),
        ),
        command_id="close-monday",
    )

    assert closed.closed_days == ("MONDAY",)
    assert len(workflow.assignments(draft.id)) == 20
    assert workflow.draft_cell_candidates(
        draft.id,
        "MONDAY:ROOM_302:1",
    ) == []
    assert workflow.draft_cell_candidates(
        draft.id,
        "MONDAY:ROOM_302:1",
        day_edits=(DraftDayEdit(day="MONDAY", closed=False),),
    )
    restored = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=closed.version,
        day_edits=(DraftDayEdit(day="MONDAY", closed=False),),
        cell_edits=tuple(
            DraftCellEdit(
                cell_key=_cell_key(row),
                replacement_prefect_id=str(row["prefectId"]),
            )
            for row in monday
        ),
        reason="Reopen after timetable confirmation",
        command_id="reopen-and-restore-monday",
    )
    replay = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=closed.version,
        day_edits=(DraftDayEdit(day="MONDAY", closed=False),),
        cell_edits=tuple(
            DraftCellEdit(
                cell_key=_cell_key(row),
                replacement_prefect_id=str(row["prefectId"]),
            )
            for row in monday
        ),
        reason="Reopen after timetable confirmation",
        command_id="reopen-and-restore-monday",
    )

    assert restored.version == closed.version + 1
    assert restored.closed_days == ()
    assert replay.idempotent is True
    assert replay.version == restored.version
    assert len(workflow.assignments(draft.id)) == 26
    assert workflow.prefect_loads() == fairness_before


def test_reopening_without_cell_edits_leaves_vacancies_and_publish_stays_blocked(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    closed = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        day_edits=(DraftDayEdit(day="MONDAY", closed=True),),
        command_id="close-monday-before-vacant-reopen",
    )

    reopened = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=closed.version,
        day_edits=(DraftDayEdit(day="MONDAY", closed=False),),
        command_id="reopen-monday-as-vacant",
    )

    assert reopened.closed_days == ()
    assert len(workflow.assignments(draft.id)) == 20
    with pytest.raises(
        RosterPolicyError,
        match=r"^Incorrect post coverage on MONDAY\.$",
    ):
        workflow.publish(
            draft.id,
            expected_week_version=reopened.version,
            command_id="publish-vacant-reopened-day",
        )


def test_atomic_swap_candidates_are_marked_and_patch_replays_without_double_write(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    room_303 = [
        row
        for row in workflow.assignments(draft.id)
        if row["day"] == "MONDAY" and row["postCode"] == DutyPost.ROOM_303.name
    ]
    first, second = sorted(room_303, key=lambda row: int(row["slotIndex"]))
    candidates = workflow.draft_cell_candidates(draft.id, _cell_key(first))
    swap_candidate = next(
        candidate for candidate in candidates if candidate["id"] == second["prefectId"]
    )

    assert swap_candidate["requiresSwap"] is True
    assert swap_candidate["occupiedCellKey"] == _cell_key(second)

    edits = (
        DraftCellEdit(_cell_key(first), str(second["prefectId"])),
        DraftCellEdit(_cell_key(second), str(first["prefectId"])),
    )
    changed = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        cell_edits=edits,
        command_id="swap-room-303",
    )
    replay = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        cell_edits=edits,
        command_id="swap-room-303",
    )
    rows = {_cell_key(row): row for row in workflow.assignments(draft.id)}

    assert changed.version == draft.version + 1
    assert rows[_cell_key(first)]["prefectId"] == second["prefectId"]
    assert rows[_cell_key(second)]["prefectId"] == first["prefectId"]
    assert replay.idempotent is True
    assert replay.version == changed.version
    with pytest.raises(WorkflowConflictError, match="different"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=draft.version,
            cell_edits=(DraftCellEdit(_cell_key(first), None),),
            command_id="swap-room-303",
        )
    with pytest.raises(WorkflowConflictError, match="changed in another browser"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=draft.version,
            cell_edits=(DraftCellEdit(_cell_key(first), str(first["prefectId"])),),
            command_id="stale-grid-patch",
        )


def test_published_roster_rejects_draft_patch_without_changing_fairness(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    published = workflow.publish(
        draft.id,
        expected_week_version=draft.version,
        command_id="publish-before-invalid-patch",
    )
    fairness_before = workflow.prefect_loads()
    first = workflow.assignments(draft.id)[0]

    with pytest.raises(WorkflowError, match="Only a draft"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=published.version,
            cell_edits=(DraftCellEdit(_cell_key(first), None),),
            command_id="patch-published-week",
        )

    assert workflow.prefect_loads() == fairness_before


def test_guest_closures_and_atomic_swap_match_the_official_contract() -> None:
    adapter = _guest_adapter()
    draft = adapter.generate_and_save_draft(
        WEEK_START,
        closed_days=("TUESDAY", "FRIDAY"),
    )

    assert draft.assignment_count == 18
    assert adapter.roster_week(draft.id)["closedDays"] == ["TUESDAY", "FRIDAY"]

    open_draft = adapter.generate_and_save_draft(
        WEEK_START,
        closed_days=(),
        expected_week_version=draft.version,
    )
    room_303 = [
        row
        for row in adapter.assignments(open_draft.id)
        if row["day"] == "MONDAY" and row["postCode"] == DutyPost.ROOM_303.name
    ]
    first, second = sorted(room_303, key=lambda row: int(row["slotIndex"]))
    candidate = next(
        row
        for row in adapter.draft_cell_candidates(open_draft.id, _cell_key(first))
        if row["id"] == second["prefectId"]
    )
    assert candidate["requiresSwap"] is True
    assert candidate["occupiedCellKey"] == _cell_key(second)

    edits = (
        DraftCellEdit(_cell_key(first), str(second["prefectId"])),
        DraftCellEdit(_cell_key(second), str(first["prefectId"])),
    )
    changed = adapter.apply_draft_patch(
        roster_week_id=open_draft.id,
        expected_week_version=open_draft.version,
        cell_edits=edits,
        command_id="guest-swap-room-303",
    )
    replay = adapter.apply_draft_patch(
        roster_week_id=open_draft.id,
        expected_week_version=open_draft.version,
        cell_edits=edits,
        command_id="guest-swap-room-303",
    )

    assert changed.version == open_draft.version + 1
    assert replay.idempotent is True
    assert replay.version == changed.version
    with pytest.raises(WorkflowConflictError, match="different"):
        adapter.apply_draft_patch(
            roster_week_id=open_draft.id,
            expected_week_version=open_draft.version,
            cell_edits=(DraftCellEdit(_cell_key(first), None),),
            command_id="guest-swap-room-303",
        )


def test_guest_failed_patch_does_not_leak_partial_mutation() -> None:
    adapter = _guest_adapter()
    draft = adapter.generate_and_save_draft(WEEK_START)
    room_303 = next(
        row
        for row in adapter.assignments(draft.id)
        if row["day"] == "MONDAY" and row["postCode"] == DutyPost.ROOM_303.name
    )
    assistant = next(
        row
        for row in adapter.prefects()
        if row["roleCode"] == PrefectRole.ASSISTANT_HEAD.value
    )
    before_week = adapter.roster_week(draft.id)
    before_assignments = adapter.assignments(draft.id)
    before_fairness = adapter.prefect_loads()

    with pytest.raises(
        WorkflowError,
        match=rf"^{re.escape(str(assistant['nameZh']))} cannot be assigned to Room 303\.$",
    ):
        adapter.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=draft.version,
            day_edits=(DraftDayEdit(day="FRIDAY", closed=True),),
            cell_edits=(
                DraftCellEdit(_cell_key(room_303), str(assistant["id"])),
            ),
            command_id="guest-invalid-role-after-closure",
        )

    assert adapter.roster_week(draft.id) == before_week
    assert adapter.assignments(draft.id) == before_assignments
    assert adapter.prefect_loads() == before_fairness
