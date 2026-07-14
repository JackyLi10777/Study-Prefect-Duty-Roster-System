from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowConflictError, WorkflowError


WEEK_START = date(2026, 9, 7)


@pytest.fixture
def workflow(tmp_path):
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    service.bootstrap()
    return service


def test_week_start_validation_is_owned_by_the_workflow(workflow: RosterWorkflow) -> None:
    workflow.validate_week_start(WEEK_START)

    with pytest.raises(WorkflowError, match="Monday"):
        workflow.validate_week_start(date(2026, 9, 8))


def test_assignment_read_distinguishes_a_stale_roster_id_from_an_empty_roster(workflow: RosterWorkflow) -> None:
    with pytest.raises(WorkflowError, match="Roster week was not found"):
        workflow.assignments(999_999)


def test_generation_saves_and_replaces_a_draft_with_automatic_backups(workflow: RosterWorkflow) -> None:
    before_loads = workflow.prefect_loads()
    first = workflow.generate_and_save_draft(WEEK_START)
    second = workflow.generate_and_save_draft(WEEK_START)

    assert first.status == "draft"
    assert first.assignment_count == 26
    assert second.id == first.id
    assert second.version == 2
    assert second.backup_path.exists()
    assert len(list(second.backup_path.parent.glob("*.sqlite3"))) == 2
    assert workflow.prefect_loads() == before_loads


def test_concurrent_draft_generation_serializes_versions_without_lost_updates(workflow: RosterWorkflow, tmp_path) -> None:
    contender = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    contender.bootstrap()
    start = Barrier(2)

    def generate(service: RosterWorkflow):
        start.wait(timeout=5)
        return service.generate_and_save_draft(WEEK_START)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(generate, (workflow, contender)))

    assert {item.version for item in outcomes} == {1, 2}
    assert len({item.id for item in outcomes}) == 1
    assert workflow.roster_week(outcomes[0].id)["version"] == 2


def test_publishing_posts_each_assignment_weight_once(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    before = workflow.prefect_loads()

    published = workflow.publish(draft.id, expected_week_version=draft.version)
    after_first_publish = workflow.prefect_loads()

    assert published.status == "published"
    assert sum(after_first_publish.values()) - sum(before.values()) == pytest.approx(34.0)
    with pytest.raises(WorkflowError, match="already published"):
        workflow.publish(draft.id, expected_week_version=draft.version)
    assert workflow.prefect_loads() == after_first_publish


def test_concurrent_publish_attempts_have_one_database_level_winner(workflow: RosterWorkflow, tmp_path) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    contender = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    contender.bootstrap()
    before = workflow.prefect_loads()
    start = Barrier(2)

    def publish_at_the_same_time(service: RosterWorkflow):
        start.wait(timeout=5)
        try:
            return service.publish(draft.id, expected_week_version=draft.version)
        except WorkflowError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(publish_at_the_same_time, (workflow, contender)))

    successes = [outcome for outcome in outcomes if not isinstance(outcome, WorkflowError)]
    errors = [outcome for outcome in outcomes if isinstance(outcome, WorkflowError)]
    after = workflow.prefect_loads()

    assert len(successes) == 1
    assert len(errors) == 1
    assert "already published" in str(errors[0])
    assert sum(after.values()) - sum(before.values()) == pytest.approx(34.0)
    assert workflow.roster_week(draft.id)["status"] == "published"


def test_stale_reviewed_version_cannot_publish_a_newer_two_client_draft(
    workflow: RosterWorkflow, tmp_path
) -> None:
    reviewed = workflow.generate_and_save_draft(WEEK_START)
    second_client = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    second_client.bootstrap()
    loads_before_publish = workflow.prefect_loads()

    newer = second_client.generate_and_save_draft(WEEK_START)
    assert newer.id == reviewed.id
    assert newer.version == reviewed.version + 1

    with pytest.raises(WorkflowConflictError, match="changed after it was reviewed"):
        workflow.publish(reviewed.id, expected_week_version=reviewed.version)

    current = workflow.roster_week(reviewed.id)
    assert current["status"] == "draft"
    assert current["version"] == newer.version
    assert workflow.prefect_loads() == loads_before_publish

    published = workflow.publish(reviewed.id, expected_week_version=newer.version)
    assert published.status == "published"
    assert sum(workflow.prefect_loads().values()) - sum(loads_before_publish.values()) == pytest.approx(34.0)


def test_published_leave_adjustment_transfers_weight_and_keeps_audit_trail(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    candidates = workflow.recommend_substitutes(draft.id, assignment["id"])
    replacement = candidates[0]
    before = workflow.prefect_loads()

    outcome = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=assignment["id"],
        replacement_prefect_id=replacement["id"],
        reason="Approved school activity",
        command_id="test-adjustment-transfer",
        expected_week_version=int(workflow.roster_week(draft.id)["version"]),
    )
    after = workflow.prefect_loads()

    assert outcome.status == "replaced"
    assert after[assignment["prefectId"]] == pytest.approx(before[assignment["prefectId"]] - assignment["weight"])
    assert after[replacement["id"]] == pytest.approx(before[replacement["id"]] + assignment["weight"])
    assert workflow.leave_adjustment_count(draft.id) == 1
    assert outcome.backup_path.exists()
    assert workflow.reconcile_fairness().balanced


def test_repeated_leave_adjustment_command_is_idempotent(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    replacement = workflow.recommend_substitutes(draft.id, int(assignment["id"]))[0]
    before_version = int(workflow.roster_week(draft.id)["version"])

    first = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="Approved school activity",
        command_id="same-browser-command",
        expected_week_version=before_version,
    )
    after_first = workflow.prefect_loads()
    assert first.backup_path is not None
    backups_after_first = tuple(first.backup_path.parent.glob("*.sqlite3"))
    second = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="Approved school activity",
        command_id="same-browser-command",
        expected_week_version=before_version,
    )

    assert first.idempotent is False
    assert second.idempotent is True
    assert second.backup_path is None
    assert second.version == first.version
    assert first.original_prefect_name == second.original_prefect_name == assignment["prefectName"]
    assert first.replacement_prefect_name == second.replacement_prefect_name == replacement["nameZh"]
    assert first.weight == second.weight == assignment["weight"]
    assert tuple(first.backup_path.parent.glob("*.sqlite3")) == backups_after_first
    assert workflow.prefect_loads() == after_first
    assert workflow.leave_adjustment_count(draft.id) == 1
    assert workflow.reconcile_fairness().balanced


def test_leave_adjustment_command_reuse_with_different_payload_is_rejected(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    candidates = workflow.recommend_substitutes(draft.id, int(assignment["id"]))
    replacement = candidates[0]
    other_replacement = candidates[1]
    version = int(workflow.roster_week(draft.id)["version"])

    first = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="Approved school activity",
        command_id="bound-command",
        expected_week_version=version,
    )
    assert first.backup_path is not None
    backups_after_first = tuple(first.backup_path.parent.glob("*.sqlite3"))

    with pytest.raises(WorkflowConflictError, match="different request"):
        workflow.apply_leave_adjustment(
            roster_week_id=draft.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=str(other_replacement["id"]),
            reason="Approved school activity",
            command_id="bound-command",
            expected_week_version=version,
        )
    with pytest.raises(WorkflowConflictError, match="different request"):
        workflow.apply_leave_adjustment(
            roster_week_id=draft.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=str(replacement["id"]),
            reason="Different reason",
            command_id="bound-command",
            expected_week_version=version,
        )

    assert tuple(first.backup_path.parent.glob("*.sqlite3")) == backups_after_first
    assert workflow.leave_adjustment_count(draft.id) == 1
    assert workflow.reconcile_fairness().balanced


def test_leave_adjustment_command_cannot_be_reused_for_another_week(workflow: RosterWorkflow) -> None:
    first_week = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(first_week.id, expected_week_version=first_week.version)
    first_assignment = next(
        item for item in workflow.assignments(first_week.id) if item["postCode"] == "ROOM_302"
    )
    first_replacement = workflow.recommend_substitutes(first_week.id, int(first_assignment["id"]))[0]
    workflow.apply_leave_adjustment(
        roster_week_id=first_week.id,
        assignment_id=int(first_assignment["id"]),
        replacement_prefect_id=str(first_replacement["id"]),
        reason="Approved school activity",
        command_id="cross-week-command",
        expected_week_version=int(workflow.roster_week(first_week.id)["version"]),
    )

    second_week = workflow.generate_and_save_draft(date(2026, 9, 14))
    workflow.publish(second_week.id, expected_week_version=second_week.version)
    second_assignment = next(
        item for item in workflow.assignments(second_week.id) if item["postCode"] == "ROOM_302"
    )
    with pytest.raises(WorkflowConflictError, match="different request"):
        workflow.apply_leave_adjustment(
            roster_week_id=second_week.id,
            assignment_id=int(second_assignment["id"]),
            replacement_prefect_id=None,
            reason="Approved school activity",
            command_id="cross-week-command",
            expected_week_version=int(workflow.roster_week(second_week.id)["version"]),
        )

    assert workflow.leave_adjustment_count(first_week.id) == 1
    assert workflow.leave_adjustment_count(second_week.id) == 0
    assert workflow.reconcile_fairness().balanced


def test_concurrent_distinct_adjustments_have_one_version_winner(workflow: RosterWorkflow, tmp_path) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    replacement = workflow.recommend_substitutes(draft.id, int(assignment["id"]))[0]
    contender = RosterWorkflow(database_path=tmp_path / "sing-yin.sqlite3", backup_dir=tmp_path / "backups")
    contender.bootstrap()
    version = int(workflow.roster_week(draft.id)["version"])
    start = Barrier(2)

    def adjust(service: RosterWorkflow, command_id: str):
        start.wait(timeout=5)
        try:
            return service.apply_leave_adjustment(
                roster_week_id=draft.id,
                assignment_id=int(assignment["id"]),
                replacement_prefect_id=str(replacement["id"]),
                reason="Approved school activity",
                command_id=command_id,
                expected_week_version=version,
            )
        except WorkflowError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda args: adjust(*args), ((workflow, "tab-a"), (contender, "tab-b"))))

    assert len([item for item in outcomes if not isinstance(item, WorkflowError)]) == 1
    conflicts = [item for item in outcomes if isinstance(item, WorkflowConflictError)]
    assert len(conflicts) == 1
    assert workflow.leave_adjustment_count(draft.id) == 1
    assert workflow.reconcile_fairness().balanced


def test_manual_draft_change_stays_policy_valid_auditable_and_does_not_post_fairness(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    assignment = workflow.assignments(draft.id)[0]
    candidates = workflow.draft_assignment_candidates(draft.id, int(assignment["id"]))
    replacement = next(candidate for candidate in candidates if candidate["id"] != assignment["prefectId"])
    before_loads = workflow.prefect_loads()

    result = workflow.update_draft_assignment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacement["id"]),
        reason="Approved manual correction after roster review",
        expected_week_version=draft.version,
    )
    changed = next(item for item in workflow.assignments(draft.id) if item["id"] == assignment["id"])

    assert result.version == 2
    assert result.backup_path.exists()
    assert changed["prefectId"] == replacement["id"]
    assert workflow.prefect_loads() == before_loads


def test_stale_manual_draft_editor_cannot_overwrite_a_newer_change(workflow: RosterWorkflow, tmp_path) -> None:
    reviewed = workflow.generate_and_save_draft(WEEK_START)
    assignment = workflow.assignments(reviewed.id)[0]
    replacements = [
        item
        for item in workflow.draft_assignment_candidates(reviewed.id, int(assignment["id"]))
        if item["id"] != assignment["prefectId"]
    ]
    contender = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    contender.bootstrap()
    saved = contender.update_draft_assignment(
        roster_week_id=reviewed.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(replacements[0]["id"]),
        reason="First browser saved a reviewed correction",
        expected_week_version=reviewed.version,
    )

    with pytest.raises(WorkflowConflictError, match="another browser"):
        workflow.update_draft_assignment(
            roster_week_id=reviewed.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=str(replacements[-1]["id"]),
            reason="Stale browser attempted to overwrite it",
            expected_week_version=reviewed.version,
        )

    current = next(item for item in workflow.assignments(reviewed.id) if item["id"] == assignment["id"])
    assert current["prefectId"] == replacements[0]["id"]
    assert workflow.roster_week(reviewed.id)["version"] == saved.version


def test_generation_requirements_expose_every_slot_before_generation(workflow: RosterWorkflow) -> None:
    requirements = workflow.generation_requirements(WEEK_START)

    assert len(requirements) == 26
    assert {item["day"] for item in requirements} == {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"}
    assert all(item["eligibleCount"] >= 0 for item in requirements)
