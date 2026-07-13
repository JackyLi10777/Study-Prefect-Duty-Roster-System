from __future__ import annotations

from datetime import date

import pytest

from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowError


WEEK_START = date(2026, 9, 7)


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    service.bootstrap()
    return service


def test_pre_generation_leave_excludes_a_prefect_from_the_declared_day(workflow: RosterWorkflow) -> None:
    original = workflow.generate_and_save_draft(WEEK_START)
    monday_assignment = next(item for item in workflow.assignments(original.id) if item["day"] == "MONDAY")

    leave = workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=str(monday_assignment["prefectId"]),
        day="MONDAY",
        reason="Approved school activity",
    )
    regenerated = workflow.generate_and_save_draft(WEEK_START)

    monday_ids = {item["prefectId"] for item in workflow.assignments(regenerated.id) if item["day"] == "MONDAY"}
    assert leave["prefectId"] == monday_assignment["prefectId"]
    assert monday_assignment["prefectId"] not in monday_ids
    assert workflow.pre_generation_leaves(WEEK_START) == [leave]


def test_pre_generation_leave_is_rejected_after_the_week_is_published(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    prefect_id = str(workflow.prefects()[0]["id"])

    with pytest.raises(WorkflowError, match="published roster"):
        workflow.declare_leave(
            week_start=WEEK_START,
            prefect_id=prefect_id,
            day="MONDAY",
            reason="Late declaration",
        )


def test_publishing_requires_regeneration_when_a_new_leave_affects_an_existing_draft(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    monday_assignment = next(item for item in workflow.assignments(draft.id) if item["day"] == "MONDAY")
    workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=str(monday_assignment["prefectId"]),
        day="MONDAY",
        reason="Approved school activity",
    )

    with pytest.raises(ValueError, match="on leave"):
        workflow.publish(draft.id, expected_week_version=draft.version)


def test_published_leave_adjustment_never_recommends_or_accepts_a_prefect_with_declared_leave(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)
    assignment = next(item for item in workflow.assignments(draft.id) if item["postCode"] == "ROOM_302")
    candidate = workflow.draft_assignment_candidates(draft.id, int(assignment["id"]))[0]

    workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=str(candidate["id"]),
        day=str(assignment["day"]),
        reason="Approved school activity",
    )
    workflow.publish(draft.id, expected_week_version=draft.version)

    recommended_ids = {item["id"] for item in workflow.recommend_substitutes(draft.id, int(assignment["id"]))}
    assert candidate["id"] not in recommended_ids
    with pytest.raises(WorkflowError, match="no longer meets roster rules"):
        workflow.apply_leave_adjustment(
            roster_week_id=draft.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=str(candidate["id"]),
            reason="Late absence needs a substitute",
        )
