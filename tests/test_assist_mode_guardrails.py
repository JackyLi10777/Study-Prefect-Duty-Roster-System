from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.persistence.database import database_url
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import (
    PrefectInput,
    RosterWorkflow,
    WorkflowConflictError,
    WorkflowError,
)


WEEK_START = date(2026, 10, 5)
ALL_DAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")


def _workflow(tmp_path: Path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    return workflow


def _alembic_config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    return config


def _prefect_input(
    row: dict[str, object],
    *,
    role_code: str | None = None,
    fixed_day: str | None = None,
    name_zh: str | None = None,
) -> PrefectInput:
    return PrefectInput(
        name_zh=name_zh or str(row["nameZh"]),
        name_en=str(row["nameEn"]) if row.get("nameEn") else None,
        form=str(row["form"]),
        class_name=str(row["className"]),
        role_code=role_code or str(row["roleCode"]),
        available_days=tuple(str(day) for day in row["availableDays"]),  # type: ignore[arg-type]
        needs_mentoring=bool(row.get("needsMentoring", False)),
        fixed_general_duty=fixed_day if fixed_day is not None else str(row["fixedGeneralDuty"]),
        remarks="",
        history_weight=float(row.get("historyWeight", 0.0)),
        history_duties=int(row.get("historyDuties", 0)),
    )


def _assign_formal_monday_owner(workflow: RosterWorkflow) -> tuple[dict[str, object], list[dict[str, object]]]:
    assistants = [row for row in workflow.prefects() if row["roleCode"] == "assistant_head"]
    owner = assistants[0]
    updated = workflow.update_prefect(
        str(owner["id"]),
        _prefect_input(owner, fixed_day="MONDAY"),
        expected_version=int(owner["version"]),
        command_id="guardrail-formal-owner",
    )
    return updated, assistants[1:]


def _guest_adapter() -> GuestWorkspaceAdapter:
    registry = GuestWorkspaceRegistry(b"assist-mode-guardrails-secret-is-long-enough")
    context = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:assist-mode-guardrails",
            session_id="assist-mode-guardrails",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="ASSIST-MODE-GUARDRAILS",
    )
    return GuestWorkspaceAdapter(
        context,
        registry,
        workspace_id="assist-mode-guardrails-workspace",
        tab_id="assist-mode-guardrails-tab",
    )


def _assign_guest_monday_owner(adapter: GuestWorkspaceAdapter) -> tuple[dict[str, object], list[dict[str, object]]]:
    assistants = [row for row in adapter.prefects() if row["roleCode"] == "assistant_head"]
    owner = assistants[0]
    updated = adapter.update_prefect(
        str(owner["id"]),
        _prefect_input(owner, fixed_day="MONDAY"),
        expected_version=int(owner["version"]),
    )
    return updated, assistants[1:]


def test_formal_create_rejects_duplicate_active_assistant_fixed_day(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _owner, _other_assistants = _assign_formal_monday_owner(workflow)

    with pytest.raises(WorkflowConflictError, match="already owns"):
        workflow.create_prefect(
            PrefectInput(
                name_zh="測試助理首席",
                form="F.5",
                class_name="5Z",
                role_code="assistant_head",
                available_days=ALL_DAYS,
                fixed_general_duty="MONDAY",
            ),
            command_id="guardrail-formal-duplicate-create",
        )

    assert all(row["nameZh"] != "測試助理首席" for row in workflow.prefects())


def test_formal_update_rejects_duplicate_day_without_mutating_record(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _owner, other_assistants = _assign_formal_monday_owner(workflow)
    target = other_assistants[0]

    with pytest.raises(WorkflowConflictError, match="already owns"):
        workflow.update_prefect(
            str(target["id"]),
            _prefect_input(target, fixed_day="MONDAY"),
            expected_version=int(target["version"]),
            command_id="guardrail-formal-duplicate-update",
        )

    unchanged = workflow.prefect(str(target["id"]))
    assert unchanged["fixedGeneralDuty"] == "NONE"
    assert unchanged["version"] == target["version"]


def test_formal_role_change_cannot_claim_an_owned_assistant_day(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _owner, _other_assistants = _assign_formal_monday_owner(workflow)
    target = next(
        row
        for row in workflow.prefects()
        if row["roleCode"] == "study_prefect" and "MONDAY" in row["availableDays"]
    )

    with pytest.raises(WorkflowConflictError, match="already owns"):
        workflow.update_prefect(
            str(target["id"]),
            _prefect_input(target, role_code="assistant_head", fixed_day="MONDAY"),
            expected_version=int(target["version"]),
            command_id="guardrail-formal-role-change",
        )

    unchanged = workflow.prefect(str(target["id"]))
    assert unchanged["roleCode"] == "study_prefect"
    assert unchanged["version"] == target["version"]


def test_formal_import_rejects_duplicate_assistant_days_against_directory(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)
    _owner, _other_assistants = _assign_formal_monday_owner(workflow)

    with pytest.raises(WorkflowConflictError, match="already owns"):
        workflow.import_prefects(
            [
                PrefectInput(
                    name_zh="匯入助理首席",
                    form="F.5",
                    class_name="5Z",
                    role_code="assistant_head",
                    available_days=ALL_DAYS,
                    fixed_general_duty="MONDAY",
                )
            ],
            command_id="guardrail-formal-import-directory-conflict",
        )

    assert all(row["nameZh"] != "匯入助理首席" for row in workflow.prefects())


def test_formal_import_rejects_duplicate_assistant_days_within_batch(tmp_path: Path) -> None:
    workflow = _workflow(tmp_path)

    with pytest.raises(WorkflowError, match="Import contains duplicate Assistant Head"):
        workflow.import_prefects(
            [
                PrefectInput(
                    name_zh="匯入助理甲",
                    form="F.5",
                    class_name="5Y",
                    role_code="assistant_head",
                    available_days=ALL_DAYS,
                    fixed_general_duty="TUESDAY",
                ),
                PrefectInput(
                    name_zh="匯入助理乙",
                    form="F.5",
                    class_name="5Z",
                    role_code="assistant_head",
                    available_days=ALL_DAYS,
                    fixed_general_duty="TUESDAY",
                ),
            ],
            command_id="guardrail-formal-import-batch-conflict",
        )

    names = {row["nameZh"] for row in workflow.prefects()}
    assert "匯入助理甲" not in names
    assert "匯入助理乙" not in names


def test_guest_create_update_and_role_change_reject_duplicate_assistant_day() -> None:
    adapter = _guest_adapter()
    _owner, other_assistants = _assign_guest_monday_owner(adapter)

    with pytest.raises(WorkflowConflictError, match="already owns"):
        adapter.create_prefect(
            PrefectInput(
                name_zh="示範助理首席",
                form="F.5",
                class_name="5Z",
                role_code="assistant_head",
                available_days=ALL_DAYS,
                fixed_general_duty="MONDAY",
            )
        )

    update_target = other_assistants[0]
    with pytest.raises(WorkflowConflictError, match="already owns"):
        adapter.update_prefect(
            str(update_target["id"]),
            _prefect_input(update_target, fixed_day="MONDAY"),
            expected_version=int(update_target["version"]),
        )

    role_target = next(
        row
        for row in adapter.prefects()
        if row["roleCode"] == "study_prefect" and "MONDAY" in row["availableDays"]
    )
    with pytest.raises(WorkflowConflictError, match="already owns"):
        adapter.update_prefect(
            str(role_target["id"]),
            _prefect_input(role_target, role_code="assistant_head", fixed_day="MONDAY"),
            expected_version=int(role_target["version"]),
        )

    assert adapter.prefect(str(update_target["id"]))["fixedGeneralDuty"] == "NONE"
    assert adapter.prefect(str(role_target["id"]))["roleCode"] == "study_prefect"


def test_guest_legacy_auto_initialization_versions_records_and_rejects_stale_edit() -> None:
    adapter = _guest_adapter()
    before = {
        str(row["id"]): row
        for row in adapter.prefects()
        if row["roleCode"] == "assistant_head"
    }

    adapter.generate_and_save_draft(
        WEEK_START,
        assist_assignment_mode="legacy_fixed_weekday",
        expected_week_version=0,
    )

    after = {str(row["id"]): row for row in adapter.prefects() if row["id"] in before}
    initialized_ids = [
        prefect_id
        for prefect_id, old_row in before.items()
        if (
            old_row["fixedGeneralDuty"] == "NONE"
            and after[prefect_id]["fixedGeneralDuty"] != "NONE"
        )
    ]
    assert initialized_ids
    for prefect_id in initialized_ids:
        old_row = before[prefect_id]
        assert after[prefect_id]["version"] == int(old_row["version"]) + 1

    stale_id = initialized_ids[0]
    stale_row = before[stale_id]

    with pytest.raises(WorkflowConflictError, match="changed in another tab"):
        adapter.update_prefect(
            stale_id,
            _prefect_input(stale_row),
            expected_version=int(stale_row["version"]),
        )


@pytest.mark.parametrize(
    ("modes", "should_refuse"),
    [
        ((), False),
        (("legacy_fixed_weekday",), False),
        (("flexible_weekly",), True),
        (("legacy_fixed_weekday", "flexible_weekly"), True),
    ],
)
def test_0011_downgrade_preserves_non_legacy_assignment_provenance(
    tmp_path: Path,
    modes: tuple[str, ...],
    should_refuse: bool,
) -> None:
    database_path = tmp_path / f"assist-mode-downgrade-{len(modes)}-{should_refuse}.sqlite3"
    config = _alembic_config(database_path)
    command.upgrade(config, "head")
    timestamp = "2026-10-01 12:00:00"
    with sqlite3.connect(database_path) as connection:
        for index, mode in enumerate(modes):
            connection.execute(
                """
                INSERT INTO roster_weeks (
                    week_start, status, version, policy_version,
                    history_priority_multiplier, assist_assignment_mode,
                    generated_at, created_at, updated_at
                ) VALUES (?, 'draft', 1, 'test-policy', 1.0, ?, ?, ?, ?)
                """,
                ((WEEK_START + timedelta(days=index * 7)).isoformat(), mode, timestamp, timestamp, timestamp),
            )
        connection.commit()

    if should_refuse:
        with pytest.raises(RuntimeError, match="Cannot downgrade Assist assignment modes"):
            command.downgrade(config, "0010")
    else:
        command.downgrade(config, "0010")

    with sqlite3.connect(database_path) as connection:
        expected_revision = "0011" if should_refuse else "0010"
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            expected_revision,
        )
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(roster_weeks)").fetchall()
        }
        if should_refuse:
            assert "assist_assignment_mode" in columns
            assert [
                str(row[0])
                for row in connection.execute(
                    "SELECT assist_assignment_mode FROM roster_weeks ORDER BY week_start"
                ).fetchall()
            ] == list(modes)
        else:
            assert "assist_assignment_mode" not in columns
