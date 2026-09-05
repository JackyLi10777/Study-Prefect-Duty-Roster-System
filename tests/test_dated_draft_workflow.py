import pytest
from sqlalchemy import text

from nicegui_app.services.roster_workflow import RosterWorkflow
from nicegui_app.services.workflow_types import BackupResult, WorkflowConflictError, WorkflowError, WorkflowMaintenanceError
from tests.test_policy_workflow import admin, workflow, custom
from tests.test_dated_weekly_draft import MONDAY


def seed_directory(operator):
    from nicegui_app.services.workflow_types import PrefectInput
    from tests.test_dated_weekly_draft import people
    for index, person in enumerate(people()):
        operator.create_prefect(PrefectInput(name_zh=person.name, name_en=None, form="F.4", class_name="4A",
                                             role_code=person.role.value, available_days=tuple(day.name for day in person.available_days)),
                                 command_id=f"person-{index}")


def test_create_reopen_edit_regenerate_and_explicit_policy_adoption(workflow):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert first.snapshot.version == 1 and first.backup_status == "verified"
    identity = first.snapshot.schedule_id
    assert len(first.snapshot.draft.cells) == 30
    operator.save_policy(2026, custom(), expected_revision=1, command_id="new-policy")
    regenerated = operator.regenerate_dated_draft(identity, expected_version=1, command_id="regenerate")
    assert regenerated.snapshot.draft.policy_ref.revision == 1
    adopted = operator.adopt_dated_draft_policy(identity, 2, expected_version=2, command_id="adopt")
    assert adopted.snapshot.version == 3 and adopted.snapshot.draft.policy_ref.policy == custom()
    reopened = RosterWorkflow(database_path=workflow.database_path, backup_dir=workflow.backup_dir)
    reopened.bootstrap()
    other = admin(reopened)
    assert other.dated_draft_snapshot(identity) == adopted.snapshot
    assert other.dated_draft_snapshot(identity, version=1) == first.snapshot
    assert other.dated_draft_command_result(command_id="create").snapshot == first.snapshot
    assert other.dated_draft_command_result(command_id="missing") is None
    assert other.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create").snapshot == first.snapshot
    assert other.adopt_dated_draft_policy(identity, 2, expected_version=2, command_id="adopt").replayed
    with pytest.raises(WorkflowConflictError):
        other.regenerate_dated_draft(identity, expected_version=1, command_id="stale")


def test_raw_identity_rejected_and_failed_backup_preserves_replay(workflow, monkeypatch):
    with pytest.raises(PermissionError):
        workflow.create_dated_weekly_draft(2026, 1, MONDAY, command_id="raw")
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    original = workflow._create_and_record_backup
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *_: BackupResult(False, None, "fictional"))
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert first.backup_status == "pending"
    assert operator.dated_draft_command_result(command_id="create").backup_status == "pending"
    with pytest.raises(WorkflowMaintenanceError):
        operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="new")
    monkeypatch.setattr(workflow, "_create_and_record_backup", original)
    repaired = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert repaired.replayed and repaired.backup_status == "verified"
    assert repaired.snapshot == first.snapshot
    with workflow._session() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM dated_draft_revisions")) == 1


def test_new_identity_cannot_enter_old_publish_or_export_snapshot(workflow):
    from nicegui_app.services.roster_export import build_roster_pdf
    from nicegui_app.services.roster_image_export import build_roster_png_bundle
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    identity = first.snapshot.schedule_id
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        operator.publish(identity, expected_week_version=1, command_id="forbidden")
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        operator.roster_schedule_snapshot(identity)
    for build in (build_roster_pdf, build_roster_png_bundle):
        with pytest.raises(WorkflowError, match="Dated drafts cannot"):
            build(operator, identity)
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        operator.apply_leave_adjustment(roster_week_id=identity, assignment_id=1, replacement_prefect_id=None,
                                        expected_week_version=1, command_id="forbidden-adjust")
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        operator.queue_external_share(command_id="forbidden-share", roster_week_id=identity, roster_version=1,
                                      content_digest="a" * 64, share_id="unused", delivery_payload={}, share_key="unused", receipt_metadata={})
    with workflow._session() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM roster_weeks")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM fairness_ledger")) == 0


def test_lost_response_lookup_does_not_follow_a_redirected_receipt(workflow):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="regen")
    with workflow._session() as session:
        raw = session.scalar(text("SELECT result_json FROM operation_commands WHERE command_id='regen'"))
        session.execute(text("UPDATE operation_commands SET result_json=:receipt WHERE command_id='create'"), {"receipt": raw})
        session.commit()
    with pytest.raises(WorkflowError):
        operator.dated_draft_command_result(command_id="create")
    with pytest.raises(WorkflowError):
        operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")


@pytest.mark.parametrize("failure", ["audit", "receipt", "commit"])
def test_draft_transaction_failure_rolls_back_history_pointer_and_command(workflow, monkeypatch, failure):
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")

    def fail(*args, **kwargs):
        raise RuntimeError("fictional interrupted transaction")

    if failure == "commit":
        event.listen(Session, "before_commit", fail)
    else:
        monkeypatch.setattr(workflow, "_audit" if failure == "audit" else "_commit_operation_command", fail)
    try:
        with pytest.raises(RuntimeError, match="fictional interrupted"):
            operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    finally:
        if failure == "commit":
            event.remove(Session, "before_commit", fail)
    with workflow._session() as session:
        for table in ("dated_draft_revisions", "dated_draft_current"):
            assert session.scalar(text(f"SELECT COUNT(*) FROM {table}")) == 0
        assert session.scalar(text("SELECT COUNT(*) FROM operation_commands")) == 1
        assert session.scalar(text("SELECT COUNT(*) FROM backup_obligations")) == 1


def test_simultaneous_draft_creation_has_one_winner(workflow):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    barrier = Barrier(2)

    def create(command):
        barrier.wait(timeout=5)
        try:
            return admin(workflow).create_dated_weekly_draft(2026, 1, MONDAY, command_id=command)
        except WorkflowConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ("first", "second")))
    assert sum(result is not None for result in results) == 1
    with workflow._session() as session:
        assert session.scalar(text("SELECT COUNT(*) FROM dated_draft_revisions")) == 1


def test_real_directory_generation_edit_inactivation_and_fixed_ownership(workflow):
    from nicegui_app.services.workflow_types import PrefectInput
    from roster_core.dated_draft import DraftError
    from roster_policy.configurable import BusinessId
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    seed_directory(operator)
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert sum(cell.state == "assigned" for cell in first.snapshot.draft.cells) == 20
    initial_assist = {cell.key: cell.prefect_id for cell in first.snapshot.draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE}
    for person in first.snapshot.draft.people:
        if person.id in initial_assist.values():
            assert person.fixed_general_duty != "NONE"
    operator.create_prefect(PrefectInput(name_zh="測新甲", name_en=None, form="F.4", class_name="4A", role_code="assistant_head",
                                         available_days=("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")), command_id="added-ahp")
    second = operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="regen")
    assert {cell.key: cell.prefect_id for cell in second.snapshot.draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE} == initial_assist
    person_id = next(cell.prefect_id for cell in second.snapshot.draft.cells if cell.key.business is BusinessId.STUDY_ROOM)
    operator.archive_prefect(person_id, command_id="archive")
    with pytest.raises(DraftError):
        operator.edit_dated_draft(first.snapshot.schedule_id, {}, expected_version=2, command_id="stale-eligibility")
    edits = {cell.key: None for cell in second.snapshot.draft.cells if cell.prefect_id == person_id}
    cleared = operator.edit_dated_draft(first.snapshot.schedule_id, edits, expected_version=2, command_id="clear-inactive")
    assert all(cell.prefect_id != person_id for cell in cleared.snapshot.draft.cells)
    assert operator.dated_draft_snapshot(first.snapshot.schedule_id, version=1) == first.snapshot


def test_failed_draft_commit_does_not_initialize_fixed_ownership(workflow, monkeypatch):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    seed_directory(operator)
    before = operator.prefects()

    def fail(*args, **kwargs):
        raise RuntimeError("fictional receipt interruption")

    monkeypatch.setattr(workflow, "_commit_operation_command", fail)
    with pytest.raises(RuntimeError, match="fictional receipt"):
        operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert operator.prefects() == before


def test_policy_adoption_keeps_fixed_ownership_and_retry_never_regenerates(workflow, monkeypatch):
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    seed_directory(operator)
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    directory = operator.prefects()
    operator.save_policy(2026, custom(), expected_revision=1, command_id="new-policy")
    adopted = operator.adopt_dated_draft_policy(first.snapshot.schedule_id, 2, expected_version=1, command_id="adopt")
    assert operator.prefects() == directory
    assert adopted.snapshot.draft.assist_mode == first.snapshot.draft.assist_mode

    def forbidden(*args, **kwargs):
        raise AssertionError("Exact replay must not rerun generation or ownership")

    monkeypatch.setattr(workflow, "_generate_dated", forbidden)
    assert operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create").snapshot == first.snapshot
    assert operator.prefects() == directory


@pytest.mark.parametrize("legacy_date,use_legacy", [("2026-09-21", True), ("2026-08-31", False), ("2026-09-07", False)])
def test_flexible_history_selects_actual_latest_week_across_both_sources(workflow, legacy_date, use_legacy):
    from datetime import date
    from roster_policy import AssistAssignmentMode, SchoolDay
    from roster_policy.configurable import BusinessId
    from nicegui_app.persistence.models import RosterAssignmentRecord, RosterWeekRecord
    operator = admin(workflow)
    operator.initialize_policy(2026, command_id="init")
    seed_directory(operator)
    dated = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="dated", assist_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY)
    heads = [cell.prefect_id for cell in dated.snapshot.draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE]
    assert len(set(heads)) == 5
    shifted = heads[1:] + heads[:1]
    names = {person.id: person.name for person in dated.snapshot.draft.people}
    with workflow._session() as session:
        now = workflow._now()
        legacy = RosterWeekRecord(week_start=date.fromisoformat(legacy_date), status="draft", version=1,
                                   policy_version="fictional-prior", generated_at=now, created_at=now, updated_at=now)
        session.add(legacy)
        session.flush()
        for day, identity in zip(SchoolDay, shifted, strict=True):
            session.add(RosterAssignmentRecord(roster_week_id=legacy.id, day=day.name, post_code="ASSIST_IN_CHARGE",
                                               slot_index=1, prefect_id=identity, prefect_name_snapshot=names[identity],
                                               prefect_role_snapshot="assistant_head", weight=1, status="active"))
        session.commit()
    target = operator.create_dated_weekly_draft(2026, 1, date(2026, 9, 28), command_id="target", assist_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY)
    assert dict(target.snapshot.draft.previous_assist) == dict(zip(SchoolDay, shifted if use_legacy else heads, strict=True))


@pytest.mark.parametrize("backend", ["official", "guest"])
def test_real_published_source_blocks_adjacent_day_and_manual_edit(workflow, backend):
    from datetime import timedelta
    from roster_core.dated_draft import DraftError, DutyCommitment
    from roster_policy import SchoolDay
    from roster_policy.configurable import BusinessId, ScheduleExceptions, ScheduleMode, SeatKey
    from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
    from tests.test_guest_policy_workflow import SECRET, adapter

    operator = admin(workflow) if backend == "official" else adapter(GuestWorkspaceRegistry(SECRET))
    operator.initialize_policy(2026, command_id="init")
    if backend == "official":
        seed_directory(operator)
    legacy = operator.generate_and_save_draft(MONDAY, closed_days=tuple(SchoolDay(day) for day in (1, 2, 3, 4)),
                                                command_id="legacy-create")
    first = operator.create_dated_weekly_draft(2026, 1, MONDAY, command_id="dated-create",
                                               exceptions=ScheduleExceptions(closed_dates=(MONDAY,)))
    assert first.snapshot.draft.occupied == ()  # An unpublished draft is not a commitment.
    published = operator.publish(legacy.id, expected_week_version=legacy.version, command_id="legacy-publish")
    assert published.status == "published"
    rows = [row for row in operator.assignments(legacy.id) if row["status"] == "active" and row["prefectId"]]
    assert rows and all(row["day"] == "MONDAY" for row in rows)
    expected = {DutyCommitment(row["prefectId"], MONDAY, ScheduleMode.WEEKLY) for row in rows}
    result = operator.regenerate_dated_draft(first.snapshot.schedule_id, expected_version=1, command_id="dated-regen")
    assert set(result.snapshot.draft.occupied) == expected
    assert not any(cell.prefect_id in {item.person_id for item in expected}
                   and cell.key.duty_date == MONDAY + timedelta(days=1) for cell in result.snapshot.draft.cells)
    assert operator.dated_draft_snapshot(first.snapshot.schedule_id) == result.snapshot
    assert operator.dated_draft_snapshot(first.snapshot.schedule_id, version=1) == first.snapshot
    for post, business in (("ROOM_302", BusinessId.STUDY_ROOM), ("ASSIST_IN_CHARGE", BusinessId.ASSIST_IN_CHARGE)):
        who = next(row["prefectId"] for row in rows if row["postCode"] == post)
        with pytest.raises(DraftError, match="not eligible"):
            operator.edit_dated_draft(first.snapshot.schedule_id,
                                       {SeatKey(MONDAY + timedelta(days=1), business, 1): who},
                                       expected_version=2, command_id="bad-edit-" + post)
        assert operator.dated_draft_snapshot(first.snapshot.schedule_id) == result.snapshot
