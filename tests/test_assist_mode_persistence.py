from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import select

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.persistence.database import database_url
from nicegui_app.persistence.models import AuditEventRecord
from nicegui_app.services import guest_adapter as guest_adapter_module
from nicegui_app.services.workflow_parts import lifecycle as lifecycle_module
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import (
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
)


WEEK_START = date(2026, 9, 7)
SECOND_WEEK = date(2026, 9, 14)
THIRD_WEEK = date(2026, 9, 21)


def _alembic_config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    return config


def _workflow(tmp_path: Path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    return workflow


def test_0011_backfills_existing_weeks_and_enforces_stable_codes(tmp_path: Path) -> None:
    database_path = tmp_path / "pre-assist-mode.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "0010")
    timestamp = "2026-09-01 12:00:00"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO roster_weeks (
                week_start, status, version, policy_version,
                history_priority_multiplier, generated_at, created_at, updated_at
            ) VALUES (?, 'draft', 1, 'test-policy', 1.0, ?, ?, ?)
            """,
            (WEEK_START.isoformat(), timestamp, timestamp, timestamp),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone() == ("0011",)
        assert connection.execute(
            "SELECT assist_assignment_mode FROM roster_weeks WHERE week_start = ?",
            (WEEK_START.isoformat(),),
        ).fetchone() == ("legacy_fixed_weekday",)
        columns = {
            str(row[1]): row
            for row in connection.execute("PRAGMA table_info(roster_weeks)").fetchall()
        }
        assert columns["assist_assignment_mode"][3] == 1
        indexes = {
            str(row[1])
            for row in connection.execute("PRAGMA index_list(roster_weeks)").fetchall()
        }
        assert "uq_roster_weeks_active_week_start" in indexes
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE roster_weeks SET assist_assignment_mode = 'unsupported'"
            )


def test_workflow_snapshots_mode_in_results_reads_audit_and_publish(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)

    legacy = workflow.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
        command_id="assist-mode-legacy-draft",
    )
    flexible = workflow.generate_and_save_draft(
        SECOND_WEEK,
        assist_assignment_mode="flexible_weekly",
        expected_week_version=0,
        command_id="assist-mode-flexible-draft",
    )

    assert legacy.assist_assignment_mode == "legacy_fixed_weekday"
    assert flexible.assist_assignment_mode == "flexible_weekly"
    assert workflow.roster_week(legacy.id)["assistAssignmentMode"] == "legacy_fixed_weekday"
    assert workflow.roster_week(flexible.id)["assistAssignmentMode"] == "flexible_weekly"
    by_week = {
        row["weekStart"]: row["assistAssignmentMode"]
        for row in workflow.roster_weeks()
    }
    assert by_week == {
        WEEK_START: "legacy_fixed_weekday",
        SECOND_WEEK: "flexible_weekly",
    }
    schedule_week, _assignments = workflow.roster_schedule_snapshot(legacy.id)
    assert schedule_week["assistAssignmentMode"] == "legacy_fixed_weekday"
    fixed_by_id = {
        str(row["id"]): str(row["fixedGeneralDuty"])
        for row in workflow.prefects()
        if row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
    }
    assist_by_id = {
        str(row["prefectId"]): str(row["day"])
        for row in _assignments
        if row["postCode"] == "ASSIST_IN_CHARGE"
    }
    assert fixed_by_id
    assert fixed_by_id.items() <= assist_by_id.items()

    published = workflow.publish(
        legacy.id,
        expected_week_version=legacy.version,
        command_id="assist-mode-legacy-publish",
    )
    assert published.assist_assignment_mode == "legacy_fixed_weekday"

    assert workflow.sessions is not None
    with workflow.sessions() as session:
        audit_rows = session.scalars(
            select(AuditEventRecord)
            .where(AuditEventRecord.roster_week_id == legacy.id)
            .order_by(AuditEventRecord.id)
        ).all()
    audited_modes = {
        row.event_type: json.loads(row.metadata_json)["assistAssignmentMode"]
        for row in audit_rows
        if row.event_type in {"draft_generated", "roster_published"}
    }
    assert audited_modes == {
        "draft_generated": "legacy_fixed_weekday",
        "roster_published": "legacy_fixed_weekday",
    }


def test_mode_is_part_of_command_identity_and_default_is_legacy(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)

    default_draft = workflow.generate_and_save_draft(
        WEEK_START,
        expected_week_version=0,
        command_id="assist-mode-default-draft",
    )
    assert default_draft.assist_assignment_mode == "legacy_fixed_weekday"

    exact_retry = workflow.generate_and_save_draft(
        WEEK_START,
        expected_week_version=0,
        command_id="assist-mode-default-draft",
    )
    assert exact_retry.id == default_draft.id
    assert exact_retry.assist_assignment_mode == "legacy_fixed_weekday"

    with pytest.raises(WorkflowConflictError, match="different work"):
        workflow.generate_and_save_draft(
            WEEK_START,
            assist_assignment_mode="flexible_weekly",
            expected_week_version=0,
            command_id="assist-mode-default-draft",
        )

    with pytest.raises(WorkflowError, match="Unsupported Assist assignment mode"):
        workflow.generate_and_save_draft(
            SECOND_WEEK,
            assist_assignment_mode="not-a-mode",
        )
    assert {row["weekStart"] for row in workflow.roster_weeks()} == {WEEK_START}


def test_formal_workflow_passes_latest_active_week_assist_owners_across_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workflow = _workflow(tmp_path)
    observed: list[dict[str, str]] = []
    real_generator = lifecycle_module.generate_weekly_roster

    def capture_generator(*args, **kwargs):
        observed.append(
            {
                day.name: str(prefect_id)
                for day, prefect_id in kwargs["previous_assist_assignments"].items()
            }
        )
        return real_generator(*args, **kwargs)

    monkeypatch.setattr(lifecycle_module, "generate_weekly_roster", capture_generator)

    first = workflow.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
        command_id="formal-previous-assist-first",
    )
    _first_week, first_assignments = workflow.roster_schedule_snapshot(first.id)
    expected_previous = {
        str(row["day"]): str(row["prefectId"])
        for row in first_assignments
        if row["postCode"] == "ASSIST_IN_CHARGE" and row["status"] == "active"
    }
    workflow.generate_and_save_draft(
        THIRD_WEEK,
        assist_assignment_mode="flexible_weekly",
        expected_week_version=0,
        command_id="formal-previous-assist-after-gap",
    )

    assert observed == [{}, expected_previous]


def test_legacy_leave_substitute_never_becomes_a_persisted_fixed_owner(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    workflow.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
        command_id="legacy-owner-baseline",
    )
    before = {
        str(row["fixedGeneralDuty"]): str(row["id"])
        for row in workflow.prefects()
        if row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
    }
    assert set(before) == {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"}
    absent_id = before["MONDAY"]
    workflow.declare_leave(
        week_start=SECOND_WEEK,
        prefect_id=absent_id,
        day="MONDAY",
        reason="Fictional regression leave",
        command_id="legacy-owner-leave",
    )
    leave_week = workflow.generate_and_save_draft(
        SECOND_WEEK,
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
        command_id="legacy-owner-leave-draft",
    )
    _week, leave_assignments = workflow.roster_schedule_snapshot(leave_week.id)
    monday_assist = next(
        row for row in leave_assignments
        if row["day"] == "MONDAY" and row["postCode"] == "ASSIST_IN_CHARGE"
    )
    after = {
        str(row["fixedGeneralDuty"]): str(row["id"])
        for row in workflow.prefects()
        if row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
    }

    assert str(monday_assist["prefectId"]) != absent_id
    assert after == before

    restored = workflow.generate_and_save_draft(
        SECOND_WEEK + timedelta(days=7),
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
        command_id="legacy-owner-restored-draft",
    )
    _week, restored_assignments = workflow.roster_schedule_snapshot(restored.id)
    restored_monday = next(
        row for row in restored_assignments
        if row["day"] == "MONDAY" and row["postCode"] == "ASSIST_IN_CHARGE"
    )
    assert str(restored_monday["prefectId"]) == absent_id


def test_guest_mode_is_session_only_and_uses_latest_active_week_across_gap(monkeypatch) -> None:
    secret = b"assist-mode-guest-secret-is-at-least-32-bytes"
    registry = GuestWorkspaceRegistry(secret)
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:assist-mode-session",
            session_id="assist-mode-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="ASSIST-MODE-GUEST",
    )
    adapter = GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="assist-mode-workspace",
        tab_id="assist-mode-tab",
    )
    observed: list[tuple[str, str, dict[str, str]]] = []
    real_generator = guest_adapter_module.generate_weekly_roster

    def capture_generator(*args, **kwargs):
        observed.append(
            (
                str(getattr(kwargs["assist_assignment_mode"], "value", kwargs["assist_assignment_mode"])),
                str(kwargs["assist_rotation_key"]),
                {
                    day.name: str(prefect_id)
                    for day, prefect_id in kwargs["previous_assist_assignments"].items()
                },
            )
        )
        return real_generator(*args, **kwargs)

    monkeypatch.setattr(guest_adapter_module, "generate_weekly_roster", capture_generator)

    legacy = adapter.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
    )
    expected_previous = {
        str(row["day"]): str(row["prefectId"])
        for row in adapter.assignments(legacy.id)
        if row["postCode"] == "ASSIST_IN_CHARGE" and row["status"] == "active"
    }
    flexible = adapter.generate_and_save_draft(
        THIRD_WEEK,
        assist_assignment_mode="flexible_weekly",
    )

    assert observed == [
        ("legacy_fixed_weekday", WEEK_START.isoformat(), {}),
        ("flexible_weekly", THIRD_WEEK.isoformat(), expected_previous),
    ]
    assert legacy.assist_assignment_mode == "legacy_fixed_weekday"
    assert flexible.assist_assignment_mode == "flexible_weekly"
    assert adapter.roster_week(legacy.id)["assistAssignmentMode"] == "legacy_fixed_weekday"
    assert adapter.roster_schedule_snapshot(flexible.id)[0]["assistAssignmentMode"] == "flexible_weekly"
    published = adapter.publish(legacy.id, expected_week_version=legacy.version)
    assert published.assist_assignment_mode == "legacy_fixed_weekday"
    assert any(
        row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
        for row in adapter.prefects()
    )

    other_context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:other-session",
            session_id="other-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="ASSIST-MODE-GUEST-OTHER",
    )
    other_adapter = GuestWorkspaceAdapter(
        other_context,
        registry,
        workspace_id="other-workspace",
        tab_id="other-tab",
    )
    assert other_adapter.roster_weeks() == []


def test_guest_legacy_leave_substitute_does_not_change_session_fixed_owners() -> None:
    registry = GuestWorkspaceRegistry(b"guest-legacy-owner-regression-secret")
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:legacy-owner-regression",
            session_id="legacy-owner-regression",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="LEGACY-OWNER-GUEST",
    )
    adapter = GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="legacy-owner-workspace",
        tab_id="legacy-owner-tab",
    )
    adapter.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
    )
    before = {
        str(row["fixedGeneralDuty"]): str(row["id"])
        for row in adapter.prefects()
        if row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
    }
    absent_id = before["MONDAY"]
    adapter.declare_leave(
        week_start=SECOND_WEEK,
        prefect_id=absent_id,
        day="MONDAY",
        reason=None,
    )
    leave_week = adapter.generate_and_save_draft(
        SECOND_WEEK,
        assist_assignment_mode="legacy_fixed_weekday",
    )
    monday_assist = next(
        row for row in adapter.assignments(leave_week.id)
        if row["day"] == "MONDAY" and row["postCode"] == "ASSIST_IN_CHARGE"
    )
    after = {
        str(row["fixedGeneralDuty"]): str(row["id"])
        for row in adapter.prefects()
        if row["roleCode"] == "assistant_head" and row["fixedGeneralDuty"] != "NONE"
    }

    assert str(monday_assist["prefectId"]) != absent_id
    assert after == before
