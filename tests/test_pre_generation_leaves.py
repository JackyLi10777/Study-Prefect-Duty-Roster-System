from __future__ import annotations

from datetime import date

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.roster_workflow import (
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
)


WEEK_START = date(2026, 9, 7)


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
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


def test_pre_generation_leave_reason_is_optional_and_round_trips_as_null(workflow: RosterWorkflow) -> None:
    prefect_id = str(workflow.prefects()[0]["id"])

    leave = workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=prefect_id,
        day="MONDAY",
    )

    assert leave["reason"] is None
    assert workflow.pre_generation_leaves(WEEK_START)[0]["reason"] is None


def test_leave_command_replays_and_stale_editor_cannot_overwrite(
    workflow: RosterWorkflow,
) -> None:
    prefect_id = str(workflow.prefects()[0]["id"])
    first = workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=prefect_id,
        day="MONDAY",
        reason="First reason",
        expected_version=0,
        command_id="leave-command-replay",
    )
    replay = workflow.declare_leave(
        week_start=WEEK_START,
        prefect_id=prefect_id,
        day="MONDAY",
        reason="First reason",
        expected_version=0,
        command_id="leave-command-replay",
    )

    assert replay == first
    assert first["version"] == 1

    with pytest.raises(WorkflowConflictError, match="changed in another browser"):
        workflow.declare_leave(
            week_start=WEEK_START,
            prefect_id=prefect_id,
            day="MONDAY",
            reason="Stale overwrite",
            expected_version=0,
            command_id="leave-command-stale",
        )

    workflow.cancel_pre_generation_leave(
        int(first["id"]),
        expected_version=1,
        command_id="leave-cancel-replay",
    )
    workflow.cancel_pre_generation_leave(
        int(first["id"]),
        expected_version=1,
        command_id="leave-cancel-replay",
    )
    assert workflow.pre_generation_leaves(WEEK_START) == []


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
