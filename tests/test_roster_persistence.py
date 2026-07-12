from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest

from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowError


WEEK_START = date(2026, 9, 7)


@pytest.fixture
def workflow(tmp_path):
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
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


def test_publishing_posts_each_assignment_weight_once(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    before = workflow.prefect_loads()

    published = workflow.publish(draft.id)
    after_first_publish = workflow.prefect_loads()

    assert published.status == "published"
    assert sum(after_first_publish.values()) - sum(before.values()) == pytest.approx(34.0)
    with pytest.raises(WorkflowError, match="already published"):
        workflow.publish(draft.id)
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
            return service.publish(draft.id)
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


def test_published_leave_adjustment_transfers_weight_and_keeps_audit_trail(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    candidates = workflow.recommend_substitutes(draft.id, assignment["id"])
    replacement = candidates[0]
    before = workflow.prefect_loads()

    outcome = workflow.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=assignment["id"],
        replacement_prefect_id=replacement["id"],
        reason="Approved school activity",
    )
    after = workflow.prefect_loads()

    assert outcome.status == "replaced"
    assert after[assignment["prefectId"]] == pytest.approx(before[assignment["prefectId"]] - assignment["weight"])
    assert after[replacement["id"]] == pytest.approx(before[replacement["id"]] + assignment["weight"])
    assert workflow.leave_adjustment_count(draft.id) == 1
    assert outcome.backup_path.exists()


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
    )
    changed = next(item for item in workflow.assignments(draft.id) if item["id"] == assignment["id"])

    assert result.version == 2
    assert result.backup_path.exists()
    assert changed["prefectId"] == replacement["id"]
    assert workflow.prefect_loads() == before_loads


def test_generation_requirements_expose_every_slot_before_generation(workflow: RosterWorkflow) -> None:
    requirements = workflow.generation_requirements(WEEK_START)

    assert len(requirements) == 26
    assert {item["day"] for item in requirements} == {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"}
    assert all(item["eligibleCount"] >= 0 for item in requirements)
