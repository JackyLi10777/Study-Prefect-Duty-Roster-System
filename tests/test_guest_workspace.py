from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from nicegui_app.services.guest_workspace import (
    DEFAULT_MAX_PREFECTS,
    GuestCapacityError,
    GuestRateLimitError,
    GuestRevisionConflict,
    GuestSnapshotCodec,
    GuestSnapshotError,
    GuestWorkspaceError,
    GuestWorkspaceRegistry,
    demo_fixture,
)


SECRET = b"guest-test-secret-is-at-least-thirty-two-bytes"


def test_demo_fixture_is_fresh_fictional_and_chinese_name_first() -> None:
    first = demo_fixture()
    second = demo_fixture()

    assert first is not second
    assert first["fictional"] is True
    assert len(first["prefects"]) == 18
    assert all(person["fictional"] is True for person in first["prefects"])
    assert all(person["nameZh"] and not person.get("nameEn") for person in first["prefects"])
    first["prefects"][0]["nameZh"] = "已修改"
    assert second["prefects"][0]["nameZh"] != "已修改"


def test_snapshot_round_trip_is_signed_bound_expiring_and_boot_scoped() -> None:
    codec = GuestSnapshotCodec(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    token = codec.seal(
        session_id="sid-a",
        workspace_id="work-a",
        tab_id="tab-a",
        revision=2,
        state={"prefects": [], "weeks": [], "value": "示範"},
    )

    opened = codec.open(
        token,
        expected_session_id="sid-a",
        expected_workspace_id="work-a",
        expected_tab_id="tab-a",
        minimum_revision=2,
    )
    assert opened.revision == 2
    assert opened.state["value"] == "示範"

    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(GuestSnapshotError, match="signature"):
        codec.open(
            tampered,
            expected_session_id="sid-a",
            expected_workspace_id="work-a",
            expected_tab_id="tab-a",
        )
    with pytest.raises(GuestSnapshotError, match="binding"):
        codec.open(
            token,
            expected_session_id="sid-other",
            expected_workspace_id="work-a",
            expected_tab_id="tab-a",
        )
    with pytest.raises(GuestSnapshotError, match="expired"):
        codec.open(
            token,
            expected_session_id="sid-a",
            expected_workspace_id="work-a",
            expected_tab_id="tab-a",
            now=2_800,
        )
    with pytest.raises(GuestSnapshotError, match="earlier application boot"):
        GuestSnapshotCodec(SECRET, boot_id="boot-b", clock=lambda: 1_000).open(
            token,
            expected_session_id="sid-a",
            expected_workspace_id="work-a",
            expected_tab_id="tab-a",
        )
    with pytest.raises(GuestSnapshotError, match="encoding"):
        codec.open(
            "中文.not-a-signature",
            expected_session_id="sid-a",
            expected_workspace_id="work-a",
            expected_tab_id="tab-a",
        )


def test_workspace_state_is_isolated_versioned_idempotent_and_copy_safe() -> None:
    registry = GuestWorkspaceRegistry(SECRET, clock=lambda: 1_000)
    first = registry.create_workspace(session_id="sid-a", tab_id="tab-a", workspace_id="work-a")
    second = registry.create_workspace(session_id="sid-b", tab_id="tab-b", workspace_id="work-b")
    changed = deepcopy(first.state)
    changed["preferences"]["theme"] = "dark"

    updated = registry.replace_state(
        session_id="sid-a",
        workspace_id="work-a",
        tab_id="tab-a",
        expected_revision=0,
        command_id="command-1",
        state=changed,
    )
    repeated = registry.replace_state(
        session_id="sid-a",
        workspace_id="work-a",
        tab_id="tab-a",
        expected_revision=0,
        command_id="command-1",
        state=changed,
    )

    assert updated.revision == repeated.revision == 1
    assert registry.get_workspace(
        session_id="sid-b", workspace_id="work-b", tab_id="tab-b"
    ).state["preferences"]["theme"] == "light"
    updated.state["preferences"]["theme"] = "tampered-client-copy"
    assert registry.get_workspace(
        session_id="sid-a", workspace_id="work-a", tab_id="tab-a"
    ).state["preferences"]["theme"] == "dark"

    with pytest.raises(GuestRevisionConflict):
        registry.replace_state(
            session_id="sid-a",
            workspace_id="work-a",
            tab_id="tab-a",
            expected_revision=0,
            command_id="command-2",
            state=changed,
        )
    different = deepcopy(changed)
    different["preferences"]["theme"] = "light"
    with pytest.raises(GuestWorkspaceError, match="different content"):
        registry.replace_state(
            session_id="sid-a",
            workspace_id="work-a",
            tab_id="tab-a",
            expected_revision=1,
            command_id="command-1",
            state=different,
        )


def test_tab_session_capacity_state_bounds_rate_limit_and_cleanup() -> None:
    registry = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: 1_000,
        max_sessions=1,
        max_tabs_per_session=1,
        max_commands_per_minute=1,
    )
    view = registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    assert registry.create_workspace(session_id="sid", tab_id="tab").workspace_id == "work"
    with pytest.raises(GuestCapacityError, match="tab"):
        registry.create_workspace(session_id="sid", tab_id="tab-2")
    with pytest.raises(GuestCapacityError, match="session"):
        registry.create_workspace(session_id="sid-2", tab_id="tab")

    changed = deepcopy(view.state)
    changed["preferences"]["musicEnabled"] = True
    registry.replace_state(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
        expected_revision=0,
        command_id="one",
        state=changed,
    )
    changed["preferences"]["theme"] = "dark"
    with pytest.raises(GuestRateLimitError):
        registry.replace_state(
            session_id="sid",
            workspace_id="work",
            tab_id="tab",
            expected_revision=1,
            command_id="two",
            state=changed,
        )

    too_many = demo_fixture()
    too_many["prefects"] = [{"nameZh": "示範"}] * (DEFAULT_MAX_PREFECTS + 1)
    with pytest.raises(GuestCapacityError, match="prefect"):
        registry.replace_state(
            session_id="sid",
            workspace_id="work",
            tab_id="tab",
            expected_revision=1,
            command_id="three",
            state=too_many,
            now=1_061,
        )

    assert registry.cleanup_session("sid") is True
    assert registry.cleanup_session("sid") is False
    assert registry.active_session_count == 0


def test_unbound_page_preview_does_not_consume_tab_capacity() -> None:
    registry = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: 1_000,
        max_tabs_per_session=1,
    )

    for index in range(20):
        preview = registry.initial_view_for_unbound_page(
            session_id="sid",
            placeholder_id=f"pending-{index}",
        )
        assert preview.revision == 0
        assert preview.state["fictional"] is True
        assert registry.active_workspace_count("sid") == 0

    registry.create_workspace(
        session_id="sid",
        tab_id="stable-tab",
        workspace_id="stable-workspace",
    )
    preview = registry.initial_view_for_unbound_page(
        session_id="sid",
        placeholder_id="next-page",
    )

    assert preview.workspace_id == "stable-workspace"
    assert registry.active_workspace_count("sid") == 1


def test_command_rate_limit_is_shared_by_all_tabs_in_one_session() -> None:
    registry = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: 1_000,
        max_tabs_per_session=2,
        max_commands_per_minute=1,
    )
    first = registry.create_workspace(session_id="sid", tab_id="tab-1", workspace_id="work-1")
    second = registry.create_workspace(session_id="sid", tab_id="tab-2", workspace_id="work-2")
    registry.replace_state(
        session_id="sid",
        workspace_id="work-1",
        tab_id="tab-1",
        expected_revision=0,
        command_id="first",
        state=first.state,
    )
    with pytest.raises(GuestRateLimitError):
        registry.replace_state(
            session_id="sid",
            workspace_id="work-2",
            tab_id="tab-2",
            expected_revision=0,
            command_id="second",
            state=second.state,
        )


def test_expiry_snapshot_and_demo_download_never_cross_workspaces() -> None:
    now = [1_000]
    registry = GuestWorkspaceRegistry(SECRET, clock=lambda: now[0])
    view = registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    token = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")
    snapshot = registry.verify_snapshot(
        token,
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
    )
    assert snapshot.revision == view.revision

    json_download = registry.build_demo_download(
        session_id="sid", workspace_id="work", tab_id="tab", file_type="json"
    )
    pdf_download = registry.build_demo_download(
        session_id="sid", workspace_id="work", tab_id="tab", file_type="pdf"
    )
    assert json_download.cache_control == "no-store, max-age=0"
    assert b'"demo":true' in json_download.content
    assert pdf_download.content.startswith(b"%PDF-1.4")
    assert "DEMO" in pdf_download.filename

    with pytest.raises(GuestWorkspaceError):
        registry.get_workspace(session_id="sid", workspace_id="work", tab_id="other")
    now[0] = 2_800
    assert registry.purge_expired() == 1
    assert registry.cleanup_workspace(session_id="sid", workspace_id="work") is False


def test_signed_snapshot_restores_only_a_newer_exactly_bound_revision() -> None:
    now = [1_000]
    registry = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: now[0],
        boot_id="boot-a",
    )
    first = registry.create_workspace(
        session_id="sid",
        tab_id="tab",
        workspace_id="work",
    )
    changed = deepcopy(first.state)
    changed["preferences"]["theme"] = "dark"
    changed_view = registry.replace_state(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
        expected_revision=0,
        command_id="change-theme",
        state=changed,
    )
    token = registry.seal_snapshot(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
    )

    assert registry.cleanup_workspace(session_id="sid", workspace_id="work") is True
    reset = registry.create_workspace(
        session_id="sid",
        tab_id="tab",
        workspace_id="work",
    )
    assert reset.revision == 0
    restored, changed_record = registry.restore_snapshot(
        token,
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
    )

    assert changed_record is True
    assert restored.revision == changed_view.revision == 1
    assert restored.state["preferences"]["theme"] == "dark"

    repeated, changed_record = registry.restore_snapshot(
        token,
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
    )
    assert changed_record is False
    assert repeated.revision == 1

    newer = deepcopy(restored.state)
    newer["preferences"]["musicEnabled"] = True
    registry.replace_state(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
        expected_revision=1,
        command_id="enable-music",
        state=newer,
    )
    with pytest.raises(GuestSnapshotError, match="stale"):
        registry.restore_snapshot(
            token,
            session_id="sid",
            workspace_id="work",
            tab_id="tab",
        )


def test_snapshot_restore_rejects_tampering_expiry_wrong_binding_and_old_boot() -> None:
    registry = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: 1_000,
        boot_id="boot-a",
    )
    registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    token = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    for candidate, expected_session, expected_workspace, expected_tab, now, message in (
        (tampered, "sid", "work", "tab", None, "signature"),
        (token, "other", "work", "tab", None, "binding"),
        (token, "sid", "other", "tab", None, "binding"),
        (token, "sid", "work", "other", None, "binding"),
        (token, "sid", "work", "tab", 2_800, "expired"),
    ):
        with pytest.raises(GuestSnapshotError, match=message):
            registry.restore_snapshot(
                candidate,
                session_id=expected_session,
                workspace_id=expected_workspace,
                tab_id=expected_tab,
                now=now,
            )

    old_boot = GuestWorkspaceRegistry(
        SECRET,
        clock=lambda: 1_000,
        boot_id="boot-b",
    )
    old_boot.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    with pytest.raises(GuestSnapshotError, match="earlier application boot"):
        old_boot.restore_snapshot(
            token,
            session_id="sid",
            workspace_id="work",
            tab_id="tab",
        )


def test_guest_workspace_module_has_no_durable_or_external_dependency_imports() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "services"
        / "guest_workspace.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert {
        "sqlalchemy",
        "requests",
        "httpx",
        "aiohttp",
        "openai",
        "deepseek",
        "pathlib",
    }.isdisjoint(imported_roots)
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "exec", "eval", "__import__"}
        for node in ast.walk(tree)
    )
