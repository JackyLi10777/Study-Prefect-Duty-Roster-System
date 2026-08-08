from __future__ import annotations

from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_presentation import RosterCellState, build_roster_presentation
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowConflictError, WorkflowError
from nicegui_app.services.workflow_types import DraftCellEdit, DraftSlotStateEdit
from roster_core import generate_weekly_roster, validate_assignments
from roster_core.loaders import load_prefect_seed
from roster_policy import DutyPost, SchoolDay


WEEK_START = date(2026, 9, 7)
TARGET_KEY = "MONDAY:ROOM_303:2"


@pytest.fixture
def workflow(tmp_path: Path) -> RosterWorkflow:
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
            subject="guest:slot-exception",
            session_id="slot-exception-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="GUEST-SLOT-EXCEPTION",
    )
    return GuestWorkspaceAdapter(
        context,
        GuestWorkspaceRegistry(b"slot-exception-secret-32-bytes-long"),
        workspace_id="slot-exception-workspace",
        tab_id="slot-exception-tab",
    )


def _target_assignment(rows: list[dict[str, object]]) -> dict[str, object]:
    return next(
        row
        for row in rows
        if row["day"] == "MONDAY"
        and row["postCode"] == "ROOM_303"
        and int(row["slotIndex"]) == 2
    )


def test_generator_excludes_exact_unavailable_slot_from_coverage() -> None:
    prefects = load_prefect_seed()
    unavailable = ((SchoolDay.MONDAY, DutyPost.ROOM_303, 2),)

    assignments = generate_weekly_roster(prefects, unavailable_slots=unavailable)

    monday_room_303 = [
        assignment
        for assignment in assignments
        if assignment.day is SchoolDay.MONDAY and assignment.post is DutyPost.ROOM_303
    ]
    assert len(monday_room_303) == 1
    validate_assignments(assignments, prefects, unavailable_slots=unavailable)


def test_presentation_applies_day_room_slot_priority_and_public_semantics() -> None:
    presentation = build_roster_presentation(
        {
            "id": 9,
            "weekStart": WEEK_START.isoformat(),
            "status": "draft",
            "version": 2,
            "closedDays": ["TUESDAY"],
            "slotExceptions": [
                {"cellKey": TARGET_KEY, "kind": "unavailable"},
                {"cellKey": "TUESDAY:ROOM_302:1", "kind": "unavailable"},
            ],
        },
        [],
    )

    unavailable = next(
        cell
        for row in presentation.rows
        if row.spec.post is DutyPost.ROOM_303 and row.spec.slot_index == 2
        for cell in row.cells
        if cell.day is SchoolDay.MONDAY
    )
    whole_day = next(
        cell
        for row in presentation.rows
        if row.spec.post is DutyPost.ROOM_302 and row.spec.slot_index == 1
        for cell in row.cells
        if cell.day is SchoolDay.TUESDAY
    )
    fixed_room = next(
        cell
        for row in presentation.rows
        if row.spec.post is DutyPost.ROOM_202 and row.spec.slot_index == 1
        for cell in row.cells
        if cell.day is SchoolDay.FRIDAY
    )

    assert unavailable.state is RosterCellState.UNAVAILABLE
    assert unavailable.editable is False
    assert whole_day.state is RosterCellState.DAY_CLOSED
    assert fixed_room.state is RosterCellState.ROOM_CLOSED
    public_row = next(
        row for row in presentation.to_public_dict()["rows"]
        if row["postCode"] == "ROOM_303" and row["slotIndex"] == 2
    )
    assert public_row["cells"][0] == {"status": "closed", "state": "unavailable"}


def test_official_slot_exception_is_atomic_idempotent_and_regeneration_safe(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    original = _target_assignment(workflow.assignments(draft.id))
    fairness_before = workflow.prefect_loads()

    closed = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        slot_edits=(DraftSlotStateEdit(TARGET_KEY, "unavailable", reason_code="other"),),
        command_id="slot-unavailable-official",
    )
    replay = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        slot_edits=(DraftSlotStateEdit(TARGET_KEY, "unavailable", reason_code="other"),),
        command_id="slot-unavailable-official",
    )

    assert closed.unavailable_slots == (TARGET_KEY,)
    assert replay.idempotent is True
    assert TARGET_KEY not in {
        f"{row['day']}:{row['postCode']}:{row['slotIndex']}"
        for row in workflow.assignments(draft.id)
    }
    assert workflow.prefect_loads() == fairness_before

    regenerated = workflow.generate_and_save_draft(
        WEEK_START,
        expected_week_version=closed.version,
        command_id="regenerate-with-unavailable-slot",
    )
    assert workflow.week_schedule_overrides(draft.id).unavailable_slots == (TARGET_KEY,)
    assert TARGET_KEY not in {
        f"{row['day']}:{row['postCode']}:{row['slotIndex']}"
        for row in workflow.assignments(draft.id)
    }
    workflow.publish(
        draft.id,
        expected_week_version=regenerated.version,
        command_id="publish-with-unavailable-slot",
    )
    assert workflow.reconcile_fairness().balanced

    with pytest.raises(WorkflowError, match="draft roster can be changed"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=regenerated.version,
            slot_edits=(DraftSlotStateEdit(TARGET_KEY, "open"),),
            command_id="cannot-reopen-published-slot",
        )

    assert original["prefectId"]


def test_official_reopen_returns_vacancy_and_stale_slot_patch_is_rejected(
    workflow: RosterWorkflow,
) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    original = _target_assignment(workflow.assignments(draft.id))
    closed = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        slot_edits=(DraftSlotStateEdit(TARGET_KEY, "unavailable"),),
        command_id="close-then-reopen-slot",
    )

    with pytest.raises(WorkflowConflictError, match="changed in another browser"):
        workflow.apply_draft_patch(
            roster_week_id=draft.id,
            expected_week_version=draft.version,
            slot_edits=(DraftSlotStateEdit(TARGET_KEY, "open"),),
            command_id="stale-reopen-slot",
        )

    reopened = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=closed.version,
        slot_edits=(DraftSlotStateEdit(TARGET_KEY, "open"),),
        command_id="reopen-slot",
    )
    assert reopened.unavailable_slots == ()
    assert TARGET_KEY not in {
        f"{row['day']}:{row['postCode']}:{row['slotIndex']}"
        for row in workflow.assignments(draft.id)
    }

    restored = workflow.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=reopened.version,
        cell_edits=(DraftCellEdit(TARGET_KEY, str(original["prefectId"])),),
        command_id="restore-reopened-slot",
    )
    workflow.publish(
        draft.id,
        expected_week_version=restored.version,
        command_id="publish-restored-slot",
    )


def test_guest_slot_exception_matches_contract_without_formal_persistence() -> None:
    adapter = _guest_adapter()
    draft = adapter.generate_and_save_draft(WEEK_START)

    result = adapter.apply_draft_patch(
        roster_week_id=draft.id,
        expected_week_version=draft.version,
        slot_edits=(DraftSlotStateEdit(TARGET_KEY, "unavailable"),),
        command_id="guest-slot-unavailable",
    )

    assert result.unavailable_slots == (TARGET_KEY,)
    assert adapter.week_schedule_overrides(draft.id).unavailable_slots == (TARGET_KEY,)
    week, _assignments = adapter.roster_schedule_snapshot(draft.id)
    assert week["slotExceptions"][0]["cellKey"] == TARGET_KEY
    assert result.backup_path is None


def test_0014_migration_round_trip_preserves_0013_database(tmp_path: Path) -> None:
    database_path = tmp_path / "slot-exception-migration.sqlite3"
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "0013")

    command.upgrade(config, "0014")
    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0014",)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(roster_slot_exceptions)")
        }
        assert {
            "roster_week_id",
            "day",
            "post_code",
            "slot_index",
            "kind",
            "reason_code",
            "note",
        }.issubset(columns)
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='roster_slot_exceptions'"
        ).fetchone()[0]
        assert "ASSIST_IN_CHARGE" in table_sql
        assert "ROOM_303" in table_sql
        assert "slot_index IN (1, 2)" in table_sql

    command.downgrade(config, "0013")
    with closing(sqlite3.connect(database_path)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0013",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='roster_slot_exceptions'"
        ).fetchone() is None
