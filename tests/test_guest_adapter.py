from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from nicegui_app.access_context import (
    AccessMode,
    CapabilityDeniedError,
    PageContext,
    Principal,
    PrincipalExpiredError,
)
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.workflow_types import PrefectInput, WorkflowConflictError, WorkflowError


WEEK_START = date(2026, 9, 7)
SECOND_WEEK = date(2026, 9, 14)
SECRET = b"guest-adapter-test-secret-is-thirty-two-bytes"


def _context(session_id: str = "guest-session") -> PageContext:
    return PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject=f"guest:{session_id}",
            session_id=session_id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        ),
        request_reference="GUEST-TEST",
    )


def _adapter(
    registry: GuestWorkspaceRegistry | None = None,
    *,
    session_id: str = "guest-session",
    workspace_id: str = "workspace-1",
    tab_id: str = "tab-1",
) -> GuestWorkspaceAdapter:
    registry = registry or GuestWorkspaceRegistry(SECRET)
    return GuestWorkspaceAdapter(
        _context(session_id),
        registry,
        workspace_id=workspace_id,
        tab_id=tab_id,
    )


def test_deferred_guest_adapter_is_read_only_until_stable_tab_binding() -> None:
    registry = GuestWorkspaceRegistry(SECRET)
    preview = registry.initial_view_for_unbound_page(
        session_id="guest-session",
        placeholder_id="pending-client",
    )
    adapter = GuestWorkspaceAdapter(
        _context(),
        registry,
        workspace_id=None,
        tab_id=None,
        initial_view=preview,
    )

    assert adapter.is_bound is False
    assert len(adapter.prefects()) == 18
    assert registry.active_workspace_count("guest-session") == 0
    with pytest.raises(WorkflowError, match="still connecting"):
        adapter.create_prefect(
            PrefectInput(
                name_zh="示範風紀",
                form="F.4",
                class_name="4A",
                role_code="study_prefect",
                available_days=("MONDAY",),
            )
        )

    adapter.bind_workspace(
        workspace_id="stable-workspace",
        tab_id="stable-tab",
    )

    assert adapter.is_bound is True
    assert registry.active_workspace_count("guest-session") == 1
    assert adapter.create_prefect(
        PrefectInput(
            name_zh="示範風紀",
            form="F.4",
            class_name="4A",
            role_code="study_prefect",
            available_days=("MONDAY",),
        )
    )["nameZh"] == "示範風紀"


def test_each_guest_mutation_publishes_the_new_signed_revision() -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="publisher-test")
    published = []
    adapter = GuestWorkspaceAdapter(
        _context(),
        registry,
        workspace_id="workspace",
        tab_id="tab",
        snapshot_publisher=published.append,
    )

    adapter.create_prefect(
        PrefectInput(
            name_zh="快照風紀",
            form="F.4",
            class_name="4A",
            role_code="study_prefect",
            available_days=("MONDAY",),
        )
    )
    adapter.reset_demo_fixture()

    assert [view.revision for view in published] == [1, 2]
    assert all(view.workspace_id == "workspace" for view in published)
    assert published[0].state["prefects"][-1]["nameZh"] == "快照風紀"
    assert len(published[1].state["prefects"]) == 18


def test_guest_role_change_preserves_inactive_legacy_assist_metadata() -> None:
    adapter = _adapter()
    assistant = next(row for row in adapter.prefects() if row["roleCode"] == "assistant_head")
    fixed_day = str(assistant["availableDays"][0])
    prepared = adapter.update_prefect(
        str(assistant["id"]),
        PrefectInput(
            name_zh=str(assistant["nameZh"]),
            name_en=str(assistant.get("nameEn") or "") or None,
            form=str(assistant["form"]),
            class_name=str(assistant["className"]),
            role_code="assistant_head",
            available_days=tuple(assistant["availableDays"]),
            fixed_general_duty=fixed_day,
        ),
        expected_version=int(assistant["version"]),
    )
    replacement_days = tuple(
        day for day in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")
        if day != fixed_day
    )

    updated = adapter.update_prefect(
        str(prepared["id"]),
        PrefectInput(
            name_zh=str(prepared["nameZh"]),
            name_en=str(prepared.get("nameEn") or "") or None,
            form=str(prepared["form"]),
            class_name=str(prepared["className"]),
            role_code="study_prefect",
            available_days=replacement_days,
            fixed_general_duty=fixed_day,
        ),
        expected_version=int(prepared["version"]),
    )

    assert updated["roleCode"] == "study_prefect"
    assert updated["fixedGeneralDuty"] == fixed_day
    assert fixed_day not in updated["availableDays"]


def test_guest_prefect_patch_matches_official_whitelist_and_cas() -> None:
    adapter = _adapter()
    original = adapter.prefects()[0]
    updated = adapter.patch_prefect(
        str(original["id"]),
        {
            "nameEn": "Fictional Prefect",
            "form": "F.5",
            "className": "5Z",
            "availableDays": ["TUESDAY", "FRIDAY"],
            "needsMentoring": True,
            "remarks": "Session-only inline edit",
        },
        expected_version=int(original["version"]),
        command_id="guest-patch-prefect",
    )

    assert updated["nameZh"] == original["nameZh"]
    assert updated["roleCode"] == original["roleCode"]
    assert updated["availableDays"] == ["TUESDAY", "FRIDAY"]
    assert updated["fictional"] is True
    assert updated["createdAt"] is not None
    with pytest.raises(WorkflowConflictError, match="changed in another tab"):
        adapter.patch_prefect(
            str(original["id"]),
            {"remarks": "stale"},
            expected_version=int(original["version"]),
        )
    with pytest.raises(WorkflowError, match="not allowed"):
        adapter.patch_prefect(
            str(original["id"]),
            {"roleCode": "assistant_head"},
            expected_version=int(updated["version"]),
        )


def test_complete_guest_roster_path_uses_real_policy_but_only_demo_fairness() -> None:
    adapter = _adapter()
    original = adapter.prefects()
    baseline_weight = sum(float(row["historyWeight"]) for row in original)
    absent = original[0]
    adapter.declare_leave(
        week_start=WEEK_START,
        prefect_id=str(absent["id"]),
        day="MONDAY",
        reason="虛構校隊活動",
    )

    requirements = adapter.generation_requirements(WEEK_START)
    assert len(requirements) == 26
    assert all(set(row) == {
        "day", "postCode", "slotIndex", "eligibleCount", "hasVacancyRisk"
    } for row in requirements)

    draft = adapter.generate_and_save_draft(WEEK_START, history_priority_multiplier=1.4)
    assignments = adapter.assignments(draft.id)
    assert len(assignments) == 26
    assert str(absent["id"]) not in {
        row["prefectId"] for row in assignments if row["day"] == "MONDAY"
    }
    target = assignments[0]
    candidates = adapter.draft_assignment_candidates(draft.id, int(target["id"]))
    assert candidates
    changed = adapter.update_draft_assignment(
        roster_week_id=draft.id,
        assignment_id=int(target["id"]),
        replacement_prefect_id=str(candidates[0]["id"]),
        reason="",
        expected_week_version=draft.version,
    )
    with pytest.raises(WorkflowConflictError):
        adapter.publish(draft.id, expected_week_version=draft.version)

    published = adapter.publish(draft.id, expected_week_version=changed.version)
    assert published.status == "published"
    assert adapter.reconcile_fairness().balanced
    assert sum(float(row["historyWeight"]) for row in adapter.prefects()) == pytest.approx(
        baseline_weight + 34.0
    )
    with pytest.raises(WorkflowError, match="already published"):
        adapter.publish(draft.id, expected_week_version=published.version)

    report = adapter.build_period_report()
    assert report.schema_version == "1.0-demo"
    assert report.published_week_count == 1
    assert report.recorded_slot_count == report.active_assignment_count == 26
    assert report.coverage_rate == 100.0
    assert report.scheduled_minutes == 26 * 80
    assert report.fairness_ledger_balanced
    assert "demo_data_only" in report.note_codes
    assert all(row.name_zh and not row.name_zh.isascii() for row in report.contributions)


def test_guest_post_publication_adjustment_is_policy_checked_and_idempotent() -> None:
    adapter = _adapter()
    draft = adapter.generate_and_save_draft(WEEK_START)
    published = adapter.publish(draft.id, expected_week_version=draft.version)
    assignment = next(
        row for row in adapter.assignments(draft.id) if row["postCode"] == "ROOM_302"
    )
    candidates = adapter.recommend_substitutes(draft.id, int(assignment["id"]))
    assert candidates
    original_before = next(
        row for row in adapter.fairness_rows() if row["id"] == assignment["prefectId"]
    )
    replacement_before = next(
        row for row in adapter.fairness_rows() if row["id"] == candidates[0]["id"]
    )

    first = adapter.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(candidates[0]["id"]),
        reason="",
        command_id="guest-adjustment-1",
        expected_week_version=published.version,
    )
    replay = adapter.apply_leave_adjustment(
        roster_week_id=draft.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=str(candidates[0]["id"]),
        reason="",
        command_id="guest-adjustment-1",
        expected_week_version=published.version,
    )

    assert first.status == "replaced"
    assert replay.idempotent is True
    assert replay.version == first.version
    assert adapter.leave_adjustment_count(draft.id) == 1
    rows = {str(row["id"]): row for row in adapter.fairness_rows()}
    assert rows[str(assignment["prefectId"])]["historyWeight"] == pytest.approx(
        float(original_before["historyWeight"]) - float(assignment["weight"])
    )
    assert rows[str(candidates[0]["id"])]["historyWeight"] == pytest.approx(
        float(replacement_before["historyWeight"]) + float(assignment["weight"])
    )
    assert adapter.reconcile_fairness().balanced

    with pytest.raises(WorkflowConflictError, match="different request"):
        adapter.apply_leave_adjustment(
            roster_week_id=draft.id,
            assignment_id=int(assignment["id"]),
            replacement_prefect_id=None,
            reason="另一個虛構要求",
            command_id="guest-adjustment-1",
            expected_week_version=first.version,
        )


def test_guest_withdrawal_is_memory_only_idempotent_and_reverses_fairness() -> None:
    adapter = _adapter()
    baseline = {
        str(row["id"]): (float(row["historyWeight"]), int(row["historyDuties"]))
        for row in adapter.fairness_rows()
    }
    draft = adapter.generate_and_save_draft(WEEK_START)
    published = adapter.publish(draft.id, expected_week_version=draft.version)

    result = adapter.withdraw_published_roster(
        draft.id,
        expected_version=published.version,
        reason="",
        command_id="guest-withdraw-1",
    )
    replay = adapter.withdraw_published_roster(
        draft.id,
        expected_version=published.version,
        reason="",
        command_id="guest-withdraw-1",
    )

    assert result.status == "withdrawn"
    assert replay.idempotent is True
    assert adapter.reconcile_fairness().balanced
    assert {
        str(row["id"]): (float(row["historyWeight"]), int(row["historyDuties"]))
        for row in adapter.fairness_rows()
    } == baseline
    assert adapter.roster_week(draft.id)["withdrawalReason"] == ""
    replacement = adapter.generate_and_save_draft(WEEK_START, expected_week_version=0)
    assert replacement.id != draft.id


def test_guest_directory_crud_is_chinese_name_first_and_import_is_denied() -> None:
    adapter = _adapter()
    created = adapter.create_prefect(
        PrefectInput(
            name_zh="測試風紀",
            form="F.4",
            class_name="4Z",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY"),
            remarks="純屬虛構",
        )
    )
    assert created["fictional"] is True
    assert created["version"] == 1

    updated = adapter.update_prefect(
        str(created["id"]),
        PrefectInput(
            name_zh="示範風紀",
            form="F.5",
            class_name="5Z",
            role_code="study_prefect",
            available_days=("TUESDAY", "THURSDAY"),
            remarks="仍屬虛構",
        ),
        expected_version=1,
    )
    assert updated["nameZh"] == "示範風紀"
    assert updated["version"] == 2
    with pytest.raises(WorkflowConflictError):
        adapter.update_prefect(
            str(created["id"]),
            PrefectInput(
                name_zh="示範風紀",
                form="F.5",
                class_name="5Z",
                role_code="study_prefect",
                available_days=("MONDAY",),
            ),
            expected_version=1,
        )
    adapter.archive_prefect(str(created["id"]), expected_version=2)
    assert str(created["id"]) not in {str(row["id"]) for row in adapter.prefects()}

    with pytest.raises(CapabilityDeniedError):
        adapter.import_prefects(
            [
                PrefectInput(
                    name_zh="匯入風紀",
                    form="F.4",
                    class_name="4Z",
                    role_code="study_prefect",
                    available_days=("MONDAY",),
                )
            ]
        )
    with pytest.raises(WorkflowError, match="must be Chinese"):
        adapter.create_prefect(
            PrefectInput(
                name_zh="English Name",
                form="F.4",
                class_name="4Z",
                role_code="study_prefect",
                available_days=("MONDAY",),
            )
        )


def test_guest_import_remains_fail_closed_if_capability_check_returns() -> None:
    adapter = _adapter()
    adapter._context = type(
        "UnexpectedImportContext",
        (),
        {"require": staticmethod(lambda _capability: None)},
    )()

    with pytest.raises(WorkflowError, match="Guest data import remains disabled"):
        adapter.import_prefects([])


def test_guest_sessions_are_isolated_and_backup_restore_is_only_a_memory_simulation() -> None:
    registry = GuestWorkspaceRegistry(SECRET)
    first = _adapter(
        registry,
        session_id="session-a",
        workspace_id="workspace-a",
        tab_id="tab-a",
    )
    second = _adapter(
        registry,
        session_id="session-b",
        workspace_id="workspace-b",
        tab_id="tab-b",
    )
    assert first.backup_inventory()["items"] == []
    checkpoint = first.create_verified_backup()
    assert first.backup_status()["latestVerification"]["reasonCode"] == "demo_memory_only"
    assert first.backup_inventory()["verifiedCount"] == 1
    package = first.build_verified_handover_package()
    assert package.filename == "SYSS_DEMO_Handover.json"
    assert b'"demo": true' in package.content

    original_count = len(first.prefects())
    created = first.create_prefect(
        PrefectInput(
            name_zh="暫存風紀",
            form="F.4",
            class_name="4Z",
            role_code="study_prefect",
            available_days=("MONDAY",),
        )
    )
    assert len(first.prefects()) == original_count + 1
    assert str(created["id"]) not in {str(row["id"]) for row in second.prefects()}
    result = first.restore_backup(checkpoint)
    assert result["demo"] is True
    assert len(first.prefects()) == original_count

    rollover = first.prepare_new_school_year()
    assert rollover["archivedPrefectCount"] == original_count
    assert first.prefects() == []
    first.reset_demo_fixture()
    assert len(first.prefects()) == original_count


def test_report_range_includes_prior_guest_fairness_history() -> None:
    adapter = _adapter()
    first = adapter.generate_and_save_draft(WEEK_START)
    adapter.publish(first.id, expected_week_version=first.version)
    second = adapter.generate_and_save_draft(SECOND_WEEK)
    adapter.publish(second.id, expected_week_version=second.version)

    full = adapter.build_period_report()
    second_only = adapter.build_period_report(period_start=SECOND_WEEK, period_end=SECOND_WEEK)

    assert len(full.trend) == 2
    assert len(second_only.trend) == 1
    assert second_only.trend[0] == full.trend[1]


def test_expired_principal_cannot_open_or_continue_a_guest_adapter() -> None:
    expired = PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:expired",
            session_id="expired",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
    )
    with pytest.raises(PrincipalExpiredError):
        GuestWorkspaceAdapter(
            expired,
            GuestWorkspaceRegistry(SECRET),
            workspace_id="workspace",
            tab_id="tab",
        )


def test_guest_adapter_has_no_durable_external_ai_or_background_dependencies() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "services"
        / "guest_adapter.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_fragments = (
        "sqlalchemy",
        "nicegui_app.persistence",
        "roster_workflow",
        "recovery",
        "backup",
        "public_roster_share",
        "prefect_import_assistant",
        "requests",
        "httpx",
        "aiohttp",
        "openai",
        "deepseek",
        "pathlib",
        "threading",
        "concurrent.futures",
    )
    assert not any(
        fragment in module
        for module in modules
        for fragment in forbidden_fragments
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "eval", "__import__"}
        for node in ast.walk(tree)
    )
