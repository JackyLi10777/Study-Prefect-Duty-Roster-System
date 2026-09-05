from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from threading import Barrier

import pytest
from sqlalchemy import select

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.persistence.models import (
    FairnessLedgerRecord,
    LeaveAdjustmentRecord,
    RosterAssignmentRecord,
    RosterDayClosureRecord,
    RosterSlotExceptionRecord,
)
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.public_roster_share import PublicRosterShareService, PublicRosterShareSettings
from nicegui_app.services.roster_workflow import (
    BackupResult,
    CommittedWriteBackupError,
    PrefectInput,
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
)
from roster_policy import DutyPost, SchoolDay, is_room_open


WEEK_START = date(2026, 9, 7)


def guest_adapter(registry: GuestWorkspaceRegistry | None = None, *, session_id: str = "vacancy-guest"):
    return GuestWorkspaceAdapter(
        PageContext.create(
            Principal(
                mode=AccessMode.GUEST,
                subject="fictional-vacancy-test",
                session_id=session_id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            ),
            request_reference="VACANCY-TEST",
        ),
        registry or GuestWorkspaceRegistry(b"vacancy-recovery-fictional-test-key-32bytes"),
        workspace_id="vacancy-workspace",
        tab_id="vacancy-tab",
    )


@pytest.fixture
def official_workflow(tmp_path):
    guest = guest_adapter()
    service = RosterWorkflow(
        database_path=tmp_path / "fictional.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    service.bootstrap()
    # Reuse only the explicitly fictional Guest directory for both adapters.
    service.import_prefects(
        [
            PrefectInput(
                name_zh=str(row["nameZh"]),
                form=str(row["form"]),
                class_name=str(row["className"]),
                role_code=str(row["roleCode"]),
                available_days=tuple(row["availableDays"]),
                fixed_general_duty=str(row["fixedGeneralDuty"]),
            )
            for row in guest.prefects()
        ]
    )
    try:
        yield service
    finally:
        service._dispose_database_connections()


@pytest.fixture(params=["official", "guest"])
def workflow(request):
    return request.getfixturevalue("official_workflow") if request.param == "official" else guest_adapter()


def balances(workflow):
    return {
        str(row["id"]): (float(row["historyWeight"]), int(row["historyDuties"]))
        for row in workflow.fairness_rows()
    }


def published_assignment(workflow):
    draft = workflow.generate_and_save_draft(WEEK_START)
    published = workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(row for row in workflow.assignments(draft.id) if row["postCode"] == "ROOM_302")
    return published, assignment


def adjust(workflow, published, assignment, replacement, *, command, version=None):
    return workflow.apply_leave_adjustment(
        roster_week_id=published.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=replacement,
        reason="Fictional approved recovery",
        command_id=command,
        expected_week_version=published.version if version is None else version,
    )


def test_published_vacancy_can_be_filled_once_without_double_debit(workflow) -> None:
    published, assignment = published_assignment(workflow)
    roster_id = published.id
    baseline = balances(workflow)
    baseline_minutes = workflow.build_period_report().scheduled_minutes
    vacant = adjust(workflow, published, assignment, None, command="vacancy-1")
    assert workflow.build_period_report().scheduled_minutes == baseline_minutes - 80
    candidates = workflow.recommend_substitutes(roster_id, int(assignment["id"]))
    assert str(assignment["prefectId"]) in {str(row["id"]) for row in candidates}
    filled = adjust(
        workflow, published, assignment, str(assignment["prefectId"]),
        command="fill-1", version=vacant.version,
    )
    replay = adjust(
        workflow, published, assignment, str(assignment["prefectId"]),
        command="fill-1", version=vacant.version,
    )
    assert filled.status == replay.status == "replaced"
    assert filled.original_prefect_name == replay.original_prefect_name == "VACANT"
    assert filled.version == replay.version == vacant.version + 1
    assert replay.idempotent is True
    current = next(row for row in workflow.assignments(roster_id) if row["id"] == assignment["id"])
    assert current["status"] == "active"
    assert current["prefectId"] == assignment["prefectId"]
    assert balances(workflow) == baseline
    assert workflow.build_period_report().scheduled_minutes == baseline_minutes
    assert workflow.leave_adjustment_count(roster_id) == 2
    assert workflow.reconcile_fairness().balanced
    if isinstance(workflow, GuestWorkspaceAdapter):
        latest = workflow._week_record(workflow._state(), roster_id)["adjustments"][-1]
        assert latest["originalPrefectId"] is None
        assert latest["originalPrefectName"] == "VACANT"


def test_vacancy_can_be_filled_by_a_different_eligible_prefect(workflow) -> None:
    before_publish = balances(workflow)
    published, assignment = published_assignment(workflow)
    published_minutes = workflow.build_period_report().scheduled_minutes
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    candidates = workflow.recommend_substitutes(published.id, int(assignment["id"]))
    replacement = next(row for row in candidates if row["id"] != assignment["prefectId"])
    vacant_balances = balances(workflow)
    filled = adjust(
        workflow, published, assignment, str(replacement["id"]), command="fill-other", version=vacant.version,
    )
    replay = adjust(
        workflow, published, assignment, str(replacement["id"]), command="fill-other", version=vacant.version,
    )
    expected = dict(vacant_balances)
    weight, duties = expected[str(replacement["id"])]
    expected[str(replacement["id"])] = (round(weight + float(assignment["weight"]), 4), duties + 1)
    assert replay.idempotent
    assert balances(workflow) == expected
    assert workflow.build_period_report().scheduled_minutes == published_minutes
    workflow.withdraw_published_roster(published.id, expected_version=filled.version, command_id="withdraw-other")
    assert balances(workflow) == before_publish
    assert workflow.build_period_report().scheduled_minutes == 0
    assert workflow.reconcile_fairness().balanced


@pytest.mark.parametrize("ending", ["vacancy", "withdraw"])
def test_recovered_duty_can_be_removed_again_with_exact_accounting(workflow, ending) -> None:
    before_publish = balances(workflow)
    published, assignment = published_assignment(workflow)
    published_balances = balances(workflow)
    published_minutes = workflow.build_period_report().scheduled_minutes
    vacant = adjust(workflow, published, assignment, None, command="first-vacancy")
    vacant_balances = balances(workflow)
    filled = adjust(
        workflow, published, assignment, str(assignment["prefectId"]),
        command="recovery", version=vacant.version,
    )
    assert balances(workflow) == published_balances
    if ending == "vacancy":
        removed = adjust(workflow, published, assignment, None, command="second-vacancy", version=filled.version)
        replay = adjust(workflow, published, assignment, None, command="second-vacancy", version=filled.version)
        assert removed.version == filled.version + 1
        assert replay.idempotent
        assert balances(workflow) == vacant_balances
        assert workflow.build_period_report().scheduled_minutes == published_minutes - 80
        assert workflow.leave_adjustment_count(published.id) == 3
    else:
        withdrawn = workflow.withdraw_published_roster(
            published.id, expected_version=filled.version, reason="Fictional cancellation", command_id="withdraw",
        )
        assert balances(workflow) == before_publish
        assert workflow.build_period_report().scheduled_minutes == 0
        with pytest.raises(WorkflowError, match="published"):
            adjust(
                workflow, published, assignment, str(assignment["prefectId"]),
                command="fill-withdrawn", version=withdrawn.version,
            )
        with pytest.raises(WorkflowError, match="published"):
            workflow.recommend_substitutes(published.id, int(assignment["id"]))
    assert workflow.reconcile_fairness().balanced


def state_signature(workflow, roster_id):
    return (
        workflow.roster_week(roster_id)["version"],
        workflow.assignments(roster_id),
        balances(workflow),
        workflow.leave_adjustment_count(roster_id),
    )


@pytest.mark.parametrize("replacement", [None, "", " \t ", 123])
def test_vacancy_recovery_rejects_no_selection_without_writing(workflow, replacement) -> None:
    published, assignment = published_assignment(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    before = state_signature(workflow, published.id)
    with pytest.raises(WorkflowError, match="eligible|blank"):
        adjust(workflow, published, assignment, replacement, command="invalid", version=vacant.version)
    assert state_signature(workflow, published.id) == before


def test_recovery_revalidates_version_eligibility_and_command_payload(workflow) -> None:
    published, assignment = published_assignment(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    before = state_signature(workflow, published.id)
    with pytest.raises(WorkflowConflictError):
        adjust(workflow, published, assignment, str(assignment["prefectId"]), command="stale")
    same_day = next(
        row for row in workflow.assignments(published.id)
        if row["day"] == assignment["day"] and row["status"] == "active" and row["postCode"] == "ROOM_303"
    )
    with pytest.raises(WorkflowError, match="rules|eligible"):
        adjust(workflow, published, assignment, str(same_day["prefectId"]), command="duplicate", version=vacant.version)
    with pytest.raises(WorkflowError, match="rules|eligible"):
        adjust(workflow, published, assignment, "nonexistent-fictional-person", command="unknown", version=vacant.version)
    wrong_role = next(row for row in workflow.prefects() if row["roleCode"] == "assistant_head")
    with pytest.raises(WorkflowError, match="rules|eligible"):
        adjust(workflow, published, assignment, str(wrong_role["id"]), command="wrong-role", version=vacant.version)
    assert state_signature(workflow, published.id) == before
    recovered = adjust(
        workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
    )
    after = state_signature(workflow, published.id)
    with pytest.raises(WorkflowConflictError, match="different request"):
        adjust(workflow, published, assignment, None, command="fill", version=recovered.version)
    assert state_signature(workflow, published.id) == after


def test_recovery_uses_current_person_availability_not_stale_recommendation(workflow) -> None:
    published, assignment = published_assignment(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    person_id = str(assignment["prefectId"])
    assert person_id in {str(row["id"]) for row in workflow.recommend_substitutes(published.id, int(assignment["id"]))}
    person = workflow.prefect(person_id)
    workflow.patch_prefect(
        person_id,
        {"availableDays": [day for day in person["availableDays"] if day != assignment["day"]]},
        expected_version=int(person["version"]), command_id="person-unavailable",
    )
    before = state_signature(workflow, published.id)
    assert person_id not in {str(row["id"]) for row in workflow.recommend_substitutes(published.id, int(assignment["id"]))}
    with pytest.raises(WorkflowError, match="rules|eligible"):
        adjust(workflow, published, assignment, person_id, command="stale-choice", version=vacant.version)
    assert state_signature(workflow, published.id) == before


def install_unrecoverable_state(workflow, roster_id, assignment, condition):
    """Simulate a legacy/inconsistent stored slot; no public command creates these."""
    closed_day, closed_post = next(
        (day.name, post.name) for day in SchoolDay for post in DutyPost if not is_room_open(post, day)
    )
    if isinstance(workflow, GuestWorkspaceAdapter):
        view = workflow._view()
        week = workflow._week_record(view.state, roster_id)
        target = workflow._assignment_record(week, int(assignment["id"]))
        if condition == "residual-person":
            target["prefectId"] = assignment["prefectId"]
        elif condition in {"closed", "unavailable"}:
            target["status"] = condition
        elif condition == "room-closed":
            target.update(day=closed_day, postCode=closed_post, slotIndex=1)
        elif condition == "day-closed":
            week.setdefault("closedDays", []).append(assignment["day"])
        elif condition == "slot-unavailable":
            week.setdefault("slotExceptions", []).append({
                "cellKey": f"{assignment['day']}:{assignment['postCode']}:{assignment['slotIndex']}",
                "kind": "unavailable",
            })
        workflow._commit(view, view.state, "test-legacy-state")
        return
    with workflow._session() as session:
        target = session.get(RosterAssignmentRecord, int(assignment["id"]))
        if condition == "residual-person":
            target.prefect_id = str(assignment["prefectId"])
        elif condition in {"closed", "unavailable"}:
            target.status = condition
        elif condition == "room-closed":
            target.day, target.post_code, target.slot_index = closed_day, closed_post, 1
        else:
            values = dict(
                roster_week_id=roster_id, day=str(assignment["day"]),
                created_at=datetime.now(), updated_at=datetime.now(),
            )
            if condition == "day-closed":
                session.add(RosterDayClosureRecord(**values))
            elif condition == "slot-unavailable":
                session.add(RosterSlotExceptionRecord(
                    **values, post_code=str(assignment["postCode"]), slot_index=int(assignment["slotIndex"]),
                    kind="unavailable",
                ))
        session.commit()


@pytest.mark.parametrize("condition", [
    "residual-person", "closed", "unavailable", "room-closed", "day-closed", "slot-unavailable",
])
def test_recovery_does_not_confuse_closed_or_inconsistent_slots_with_vacancies(workflow, condition) -> None:
    published, assignment = published_assignment(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    install_unrecoverable_state(workflow, published.id, assignment, condition)
    before = state_signature(workflow, published.id)
    with pytest.raises(WorkflowError):
        workflow.recommend_substitutes(published.id, int(assignment["id"]))
    with pytest.raises(WorkflowError):
        adjust(
            workflow, published, assignment, str(assignment["prefectId"]), command="forbidden", version=vacant.version,
        )
    assert state_signature(workflow, published.id) == before


def test_concurrent_recoveries_have_only_one_version_and_credit_winner(workflow, tmp_path) -> None:
    published, assignment = published_assignment(workflow)
    baseline = balances(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    if isinstance(workflow, GuestWorkspaceAdapter):
        contender = guest_adapter(workflow._registry)
    else:
        contender = RosterWorkflow(database_path=tmp_path / "fictional.sqlite3", backup_dir=tmp_path / "backups")
        contender.bootstrap()
    start = Barrier(2)

    def recover(pair):
        service, command = pair
        start.wait(timeout=5)
        try:
            return adjust(
                service, published, assignment, str(assignment["prefectId"]), command=command, version=vacant.version,
            )
        except WorkflowError as error:
            return error

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(recover, ((workflow, "fill-a"), (contender, "fill-b"))))
    finally:
        if isinstance(contender, RosterWorkflow):
            contender._dispose_database_connections()
    assert sum(not isinstance(result, WorkflowError) for result in outcomes) == 1
    assert sum(isinstance(result, WorkflowConflictError) for result in outcomes) == 1
    assert workflow.roster_week(published.id)["version"] == vacant.version + 1
    assert workflow.leave_adjustment_count(published.id) == 2
    assert balances(workflow) == baseline
    assert workflow.reconcile_fairness().balanced


def test_guest_recovery_cannot_change_another_session_or_official_data(official_workflow) -> None:
    registry = GuestWorkspaceRegistry(b"vacancy-recovery-fictional-test-key-32bytes")
    guest = guest_adapter(registry)
    other = guest_adapter(registry, session_id="other-vacancy-guest")
    official_published, _ = published_assignment(official_workflow)
    other_published, _ = published_assignment(other)
    official_before = state_signature(official_workflow, official_published.id)
    other_before = state_signature(other, other_published.id)
    published, assignment = published_assignment(guest)
    vacant = adjust(guest, published, assignment, None, command="vacancy")
    adjust(guest, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version)
    assert state_signature(official_workflow, official_published.id) == official_before
    assert state_signature(other, other_published.id) == other_before


def test_official_recovery_backup_failure_retry_repairs_without_recredit(official_workflow, monkeypatch) -> None:
    workflow = official_workflow
    published, assignment = published_assignment(workflow)
    baseline = balances(workflow)
    baseline_minutes = workflow.build_period_report().scheduled_minutes
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    backup = workflow._create_and_record_backup
    monkeypatch.setattr(workflow, "_create_and_record_backup", lambda *_: BackupResult(False, None, "simulated device failure"))
    with pytest.raises(CommittedWriteBackupError):
        adjust(
            workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
        )
    assert workflow.pending_backup_obligation_count() == 1
    assert balances(workflow) == baseline
    assert workflow.build_period_report().scheduled_minutes == baseline_minutes
    with pytest.raises(WorkflowMaintenanceError, match="read-only"):
        adjust(
            workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
        )
    assert balances(workflow) == baseline
    assert workflow.leave_adjustment_count(published.id) == 2
    monkeypatch.setattr(workflow, "_create_and_record_backup", backup)
    workflow.repair_pending_backup_obligations()
    replay = adjust(
        workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
    )
    assert replay.idempotent
    assert replay.version == vacant.version + 1
    assert workflow.roster_week(published.id)["version"] == replay.version
    assert workflow.pending_backup_obligation_count() == 0
    assert balances(workflow) == baseline
    assert workflow.leave_adjustment_count(published.id) == 2
    with workflow._session() as session:
        record = session.scalar(select(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.command_id == "fill"))
        assert record.original_prefect_id is None
        assert record.original_prefect_name == "VACANT"
        ledger = session.scalars(select(FairnessLedgerRecord).where(FairnessLedgerRecord.operation_id == "fill")).all()
        assert [(entry.prefect_id, entry.delta, entry.duty_delta) for entry in ledger] == [
            (assignment["prefectId"], assignment["weight"], 1),
        ]
    assert workflow.reconcile_fairness().balanced


def test_official_recovery_revokes_obsolete_shares_but_replay_keeps_new_version(official_workflow) -> None:
    class Gateway:
        def create(self, payload):
            return {"shareId": payload["shareId"], "createdAt": payload["createdAt"]}

        def list(self):
            return []

        def revoke(self, _share_id):
            return None

    workflow = official_workflow
    published, assignment = published_assignment(workflow)
    vacant = adjust(workflow, published, assignment, None, command="vacancy")
    shares = PublicRosterShareService(
        workflow,
        settings=PublicRosterShareSettings(
            enabled=True, base_url="https://roster-view.example.workers.dev", admin_token="a" * 48,
        ),
        gateway=Gateway(), now=lambda: datetime(2026, 9, 7, 8, tzinfo=timezone.utc),
    )
    old_share = shares.create_share(published.id, command_id="vacant-share").share_id
    recovered = adjust(
        workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
    )
    assert recovered.share_ids_to_revoke == (old_share,)
    assert [row["shareId"] for row in workflow.pending_external_share_revocations()] == [old_share]
    shares.create_share(published.id, command_id="recovered-share")
    before_replay = state_signature(workflow, published.id)
    replay = adjust(
        workflow, published, assignment, str(assignment["prefectId"]), command="fill", version=vacant.version,
    )
    assert replay.idempotent
    assert replay.version == recovered.version == vacant.version + 1
    assert replay.share_ids_to_revoke == (old_share,)
    assert state_signature(workflow, published.id) == before_replay
    assert workflow.external_share_outbox("recovered-share")["status"] == "delivered"
