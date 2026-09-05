from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import asyncio
import threading

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry, demo_fixture
from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.workflow_types import DraftCellEdit, DraftSlotStateEdit
from nicegui_app.services.draft_editor import DraftEditor, DraftCommittedWithoutBackup
from nicegui_app.services.workflow_types import BackupResult
from nicegui_app.services.workflow_types import CommittedWriteBackupError, WorkflowError
from nicegui_app.services.draft_rules import DraftState, draft_candidates
from roster_core import Prefect
from roster_policy import DAYS, PrefectRole


@pytest.fixture(params=("formal", "guest"))
def editing_workflow(request, tmp_path):
    """Both persistence adapters exercise the same fictional directory."""
    if request.param == "guest":
        context = PageContext.create(Principal(
            mode=AccessMode.GUEST, subject="guest:draft-final-state",
            session_id="draft-final-state",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ), request_reference="DRAFT-FINAL-STATE")
        return GuestWorkspaceAdapter(
            context, GuestWorkspaceRegistry(b"draft-final-state-test-secret-32-bytes"),
            workspace_id="draft-final-state", tab_id="draft-final-state",
        )
    rows = [dict(row, name=row["nameZh"], **{"class": row["className"]})
            for row in demo_fixture()["prefects"]]
    seed = tmp_path / "fictional.json"
    seed.write_text(json.dumps({"prefects": rows}), encoding="utf-8")
    workflow = RosterWorkflow(database_path=tmp_path / "test.sqlite3",
                              backup_dir=tmp_path / "backups", seed_path=seed)
    workflow.bootstrap()
    return workflow


def test_reopen_and_assign_is_one_reviewed_atomic_decision(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    row = next(row for row in workflow.assignments(draft.id)
               if row["day"] == "MONDAY" and row["postCode"] == "ROOM_302")
    key = f"{row['day']}:{row['postCode']}:{row['slotIndex']}"
    closed = workflow.apply_draft_patch(
        roster_week_id=draft.id, expected_week_version=draft.version,
        slot_edits=(DraftSlotStateEdit(key, "unavailable"),), command_id="close-slot",
    )
    reopened = workflow.apply_draft_patch(
        roster_week_id=draft.id, expected_week_version=closed.version,
        slot_edits=(DraftSlotStateEdit(key, "open"),),
        cell_edits=(DraftCellEdit(key, str(row["prefectId"])),),
        command_id="reopen-and-assign",
    )
    assert reopened.version == closed.version + 1
    assert key not in reopened.unavailable_slots
    restored = next(item for item in workflow.assignments(draft.id)
                    if item["day"] == row["day"] and item["postCode"] == row["postCode"]
                    and item["slotIndex"] == row["slotIndex"])
    assert restored["prefectId"] == row["prefectId"]


def test_candidates_use_pending_overlay_not_persisted_adjacent_day(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    monday = next(row for row in workflow.assignments(draft.id)
                  if row["day"] == "MONDAY" and row["postCode"] == "ROOM_302")
    target = "TUESDAY:ROOM_302:1"
    original = str(monday["prefectId"])
    # Clearing every other duty for this fictional person isolates the adjacent
    # day rule from Wednesday/Thursday placements in a generated roster.
    overlay = tuple(DraftCellEdit(f"{r['day']}:{r['postCode']}:{r['slotIndex']}", None)
                    for r in workflow.assignments(draft.id) if r["prefectId"] == original)
    assert original not in {item["id"] for item in workflow.draft_cell_candidates(draft.id, target)}
    candidates = workflow.draft_cell_candidates(draft.id, target, cell_edits=overlay)
    assert original in {item["id"] for item in candidates}
    assert any(r["prefectId"] == original and r["day"] == "MONDAY"
               for r in workflow.assignments(draft.id)), "preview must not persist the overlay"


def test_editor_save_accepts_one_snapshot_without_reload_and_preserves_selection(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    key = next(key for key, value in editor.original_assignments.items() if value and ":ROOM_302:" in key)
    editor.selected_cell = key
    editor.stage_candidate(key, None)
    command = editor.prepare_save("fictional test")
    assert editor.stage_candidate(key, "cannot-edit-during-save").kind == "blocked"
    assert editor.undo() is False
    outcome = editor.persist(command)
    editor.finish_save(outcome)
    assert editor.reviewed_version == draft.version + 1
    assert editor.effective_assignment(key) is None
    assert editor.selected_cell == key
    assert editor.dirty is False and editor.can_undo is False
    replay = editor.persist(command)
    assert replay.receipt.idempotent is True
    assert replay.receipt.version == outcome.receipt.version


def test_command_retries_freeze_reason_but_new_reason_is_new_intent():
    editor = DraftEditor({"MONDAY:ROOM_302:1": "fictional-a"}, set(), set(), 1)
    editor.stage_candidate("MONDAY:ROOM_302:1", None)
    first = editor.prepare_save("first reason")
    editor.finish_save(None)
    assert editor.prepare_save("first reason") is first
    editor.finish_save(None)
    second = editor.prepare_save("second reason")
    assert second.command_id != first.command_id
    assert first.reason == "first reason" and second.reason == "second reason"


def test_candidates_deduplicate_and_discard_stale_completion():
    class Port:
        calls = 0
        entered = threading.Event()
        released = threading.Event()

        def draft_cell_candidates(self, *args, **kwargs):
            self.calls += 1
            self.entered.set()
            assert self.released.wait(5)
            return [{"id": "fictional-b", "nameZh": "虛構乙"}]

    async def scenario():
        port = Port()
        editor = DraftEditor({"MONDAY:ROOM_302:1": "fictional-a"}, set(), set(), 1, port, 1)
        first = asyncio.create_task(editor.candidates("MONDAY:ROOM_302:1"))
        second = asyncio.create_task(editor.candidates("MONDAY:ROOM_302:1"))
        assert await asyncio.to_thread(port.entered.wait, 5)
        editor.stage_candidate("MONDAY:ROOM_302:1", None)
        port.released.set()
        assert await first is None and await second is None
        assert port.calls == 1 and editor.candidate_cache == {}
        assert await editor.candidates("MONDAY:ROOM_302:1")
        assert port.calls == 2
        assert await editor.candidates("MONDAY:ROOM_302:1")
        assert port.calls == 2
        editor.close()
        assert await editor.candidates("MONDAY:ROOM_302:1") is None

    asyncio.run(scenario())


def test_rebase_adopts_latest_base_while_retaining_only_local_intent(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    keys = [key for key, person in editor.original_assignments.items() if person and ":ROOM_302:" in key]
    editor.stage_candidate(keys[0], None)
    workflow.apply_draft_patch(roster_week_id=draft.id, expected_week_version=draft.version,
                               cell_edits=(DraftCellEdit(keys[1], None),), command_id="other-browser")
    editor.remember_latest(workflow.roster_schedule_snapshot(draft.id))
    assert editor.reapply_conflict()
    assert editor.reviewed_version == draft.version + 1
    assert editor.effective_assignment(keys[1]) is None
    assert editor.pending_cells == {keys[0]: None}
    assert not editor.can_undo


@pytest.mark.parametrize("status", ("published", "withdrawn"))
def test_rebase_of_terminal_roster_preserves_local_comparison_without_mutating_editor(editing_workflow, status):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    editor.stage_slot("MONDAY:ROOM_302:1", True)
    before = editor.patch_edits()
    latest_week, rows = workflow.roster_schedule_snapshot(draft.id)
    latest_week.update(status=status, version=draft.version + 1)
    editor.remember_latest((latest_week, rows))
    assert not editor.can_reapply_conflict
    assert editor.reapply_conflict() is False
    assert editor.patch_edits() == before
    assert editor.reviewed_version == draft.version
    assert editor.roster_status == "draft"
    assert editor.last_saved_version is None
    assert editor.latest_snapshot[0]["status"] == status


def test_candidate_checks_reciprocal_role_and_atomic_adjacent_move():
    people = (
        Prefect("head", "虛構甲", "F.5", "5A", PrefectRole.ASSISTANT_HEAD, frozenset(DAYS), 0),
        Prefect("member", "虛構乙", "F.4", "4A", PrefectRole.STUDY_PREFECT, frozenset(DAYS), 0),
    )
    state = DraftState({"MONDAY:ASSIST_IN_CHARGE:1": "head", "MONDAY:ROOM_302:1": "member"})
    assert not draft_candidates(state, "MONDAY:ROOM_302:1", people, leave_days={}), "member cannot be swapped into Assist"
    move_state = DraftState({"MONDAY:ROOM_302:1": "member"})
    assert "member" not in {row["id"] for row in draft_candidates(move_state, "TUESDAY:ROOM_302:1", people, leave_days={})}
    assert "member" in {row["id"] for row in draft_candidates(move_state, "TUESDAY:ROOM_302:1", people,
                                                             leave_days={}, source_key="MONDAY:ROOM_302:1")}


def test_committed_backup_failure_clears_intent_and_freezes_editor(editing_workflow, monkeypatch):
    workflow = editing_workflow
    if isinstance(workflow, GuestWorkspaceAdapter):
        pytest.skip("Guest never creates disk backups")
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    key = next(key for key, person in editor.original_assignments.items() if person and ":ROOM_302:" in key)
    editor.stage_candidate(key, None)
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *args: BackupResult(False, None, "test backup failure"))
    with pytest.raises(DraftCommittedWithoutBackup):
        asyncio.run(editor.save())
    assert editor.reviewed_version == draft.version + 1
    assert editor.effective_assignment(key) is None
    assert editor.dirty is False and editor.can_undo is False
    assert editor.recovery_required is True
    assert editor.stage_candidate(key, "fictional-new").kind == "blocked"


def test_restoring_original_person_requires_current_working_candidates(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    original_key = "MONDAY:ROOM_302:1"
    person = editor.effective_assignment(original_key)
    assert person is not None
    # Release all original duties, then make an eligible new Tuesday decision.
    for key, assigned in tuple(editor.original_assignments.items()):
        if assigned == person:
            editor.stage_candidate(key, None)
    target_key = "TUESDAY:ROOM_302:1"
    candidates = asyncio.run(editor.candidates(target_key))
    assert person in {row["id"] for row in candidates}
    assert editor.stage_candidate(target_key, person).kind == "assign"
    choices = asyncio.run(editor.candidates(original_key))
    assert person not in {row["id"] for row in choices}, "Tuesday now blocks adjacent Monday"
    before = editor.patch_edits()
    revision = editor.local_revision
    assert editor.stage_candidate(original_key, person).kind == "invalid"
    assert editor.patch_edits() == before
    assert editor.local_revision == revision


def test_selecting_current_person_is_a_noop_without_loaded_candidates(editing_workflow):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    editor = DraftEditor.from_snapshot(workflow, draft.id, workflow.roster_schedule_snapshot(draft.id))
    key, person = next((key, person) for key, person in editor.original_assignments.items() if person)
    assert editor.candidate_cache == {}
    revision = editor.local_revision
    assert editor.stage_candidate(key, person).kind == "noop"
    assert editor.local_revision == revision
    assert editor.dirty is False and editor.can_undo is False


@pytest.mark.parametrize("partial_backup", (False, True))
def test_known_commit_remains_committed_when_another_client_publishes_before_refresh(
    editing_workflow, partial_backup,
):
    workflow = editing_workflow
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))

    class PublishBeforeRefresh:
        """Real persistence with a deterministic interleaving at the read seam."""

        def roster_schedule_snapshot(self, roster_week_id):
            return workflow.roster_schedule_snapshot(roster_week_id)

        def apply_draft_patch(self, **kwargs):
            receipt = workflow.apply_draft_patch(**kwargs)
            workflow.publish(draft.id, expected_week_version=receipt.version,
                             command_id="other-client-publish-before-refresh")
            if partial_backup:
                # The narrow wrapper injects the committed-backup error after a
                # real durable command and real publication, not before a write.
                raise CommittedWriteBackupError("draft_patch_applied", "test backup failure")
            return receipt

    port = PublishBeforeRefresh()
    editor = DraftEditor.from_snapshot(port, draft.id, port.roster_schedule_snapshot(draft.id))
    key = "MONDAY:ROOM_302:1"
    editor.stage_slot(key, True)
    if partial_backup:
        with pytest.raises(DraftCommittedWithoutBackup):
            asyncio.run(editor.save())
    else:
        outcome = asyncio.run(editor.save())
        assert outcome.snapshot[0]["status"] == "published"
    assert editor.roster_status == "published"
    assert editor.reviewed_version == workflow.roster_week(draft.id)["version"]
    assert editor.read_only is True
    assert editor.recovery_required is partial_backup
    assert editor.dirty is False and editor.can_undo is False and editor.saving is False
    assert editor.stage_candidate(key, None).kind == "blocked"
    with pytest.raises(WorkflowError):
        editor.prepare_save()


@pytest.mark.parametrize("snapshot", (
    None,
    ({"version": "invalid", "status": "published"}, []),
    ({"version": 2, "status": "unknown"}, []),
    ({"version": 1, "status": "draft"}, []),
))
def test_partial_commit_freezes_even_when_snapshot_cannot_be_adopted(snapshot):
    editor = DraftEditor({"MONDAY:ROOM_302:1": "fictional-a"}, set(), set(), 1)
    editor.stage_candidate("MONDAY:ROOM_302:1", None)
    command = editor.prepare_save()
    error = DraftCommittedWithoutBackup(
        CommittedWriteBackupError("draft_patch_applied", "test backup failure"), command, snapshot,
    )
    editor.finish_partial_save(error)
    assert editor.recovery_required is True and editor.read_only is True
    assert editor.snapshot_refresh_failed is True
    assert editor.dirty is False and editor.can_undo is False and editor.saving is False
    assert editor.command_id is None
    assert editor.stage_candidate("MONDAY:ROOM_302:1", None).kind == "blocked"
    with pytest.raises(WorkflowError):
        editor.prepare_save()
