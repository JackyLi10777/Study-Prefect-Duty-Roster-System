from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import nicegui_app.runtime as runtime
from nicegui_app.gateway_identity import OriginPrincipalError
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry


SECRET = b"guest-browser-snapshot-secret-is-long-enough"


def _isolated_runtime(
    monkeypatch: pytest.MonkeyPatch,
    registry: GuestWorkspaceRegistry,
) -> None:
    monkeypatch.setattr(runtime, "_guest_registry", registry)
    monkeypatch.setattr(runtime, "_guest_adapters", {})
    monkeypatch.setattr(runtime, "_client_guest_adapters", {})
    monkeypatch.setattr(runtime, "_active_guest_client_by_workspace", {})
    monkeypatch.setattr(runtime, "_guest_snapshot_nonces", {})
    monkeypatch.setattr(runtime, "_guest_cleanup_timers", {})
    monkeypatch.setattr(runtime, "_page_contexts", {})


def test_browser_bridge_restores_newer_same_tab_snapshot_and_rotates_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    _isolated_runtime(monkeypatch, registry)
    initial = registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    changed = deepcopy(initial.state)
    changed["preferences"]["theme"] = "dark"
    registry.replace_state(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
        expected_revision=0,
        command_id="theme",
        state=changed,
    )
    stored = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")

    registry.cleanup_workspace(session_id="sid", workspace_id="work")
    registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    runtime._active_guest_client_by_workspace[("sid", "work")] = "client"
    runtime._guest_snapshot_nonces[("sid", "work")] = "N" * 32

    result = runtime.restore_guest_browser_snapshot(
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
        nonce="N" * 32,
        token=stored,
    )

    assert result["accepted"] is True
    assert result["restored"] is True
    assert result["revision"] == 1
    opened = registry.verify_snapshot(
        str(result["token"]),
        session_id="sid",
        workspace_id="work",
        tab_id="tab",
    )
    assert opened.state["preferences"]["theme"] == "dark"


def test_browser_bridge_rejects_copied_or_tampered_snapshot_and_keeps_safe_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    _isolated_runtime(monkeypatch, registry)
    registry.create_workspace(session_id="sid", tab_id="source-tab", workspace_id="source")
    source_token = registry.seal_snapshot(
        session_id="sid",
        workspace_id="source",
        tab_id="source-tab",
    )
    target = registry.create_workspace(
        session_id="sid",
        tab_id="target-tab",
        workspace_id="target",
    )
    runtime._active_guest_client_by_workspace[("sid", "target")] = "target-client"
    runtime._guest_snapshot_nonces[("sid", "target")] = "T" * 32

    copied = runtime.restore_guest_browser_snapshot(
        session_id="sid",
        workspace_id="target",
        tab_id="target-tab",
        nonce="T" * 32,
        token=source_token,
    )
    tampered_token = source_token[:-1] + ("A" if source_token[-1] != "A" else "B")
    tampered = runtime.restore_guest_browser_snapshot(
        session_id="sid",
        workspace_id="target",
        tab_id="target-tab",
        nonce="T" * 32,
        token=tampered_token,
    )

    assert copied["accepted"] is False
    assert tampered["accepted"] is False
    assert copied["restored"] is tampered["restored"] is False
    assert copied["revision"] == tampered["revision"] == target.revision == 0
    current = registry.get_workspace(
        session_id="sid",
        workspace_id="target",
        tab_id="target-tab",
    )
    assert current.state["fictional"] is True
    assert current.state["preferences"]["theme"] == "light"


def test_browser_bridge_requires_live_connection_nonce_and_logout_clears_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    _isolated_runtime(monkeypatch, registry)
    registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    token = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")
    runtime._active_guest_client_by_workspace[("sid", "work")] = "client"
    runtime._guest_snapshot_nonces[("sid", "work")] = "N" * 32
    runtime._guest_adapters[("sid", "work")] = object()

    with pytest.raises(OriginPrincipalError, match="binding"):
        runtime.restore_guest_browser_snapshot(
            session_id="sid",
            workspace_id="work",
            tab_id="tab",
            nonce="wrong",
            token=token,
        )

    runtime.cleanup_guest_session("sid")

    assert registry.active_workspace_count("sid") == 0
    assert runtime._active_guest_client_by_workspace == {}
    assert runtime._guest_snapshot_nonces == {}
    assert runtime._guest_adapters == {}


def test_runtime_pushes_each_signed_revision_to_the_connected_tab(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    _isolated_runtime(monkeypatch, registry)
    view = registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    runtime._active_guest_client_by_workspace[("sid", "work")] = "client"
    runtime._guest_snapshot_nonces[("sid", "work")] = "N" * 32
    scripts: list[str] = []
    client = SimpleNamespace(run_javascript=scripts.append)
    monkeypatch.setattr(
        runtime.ui,
        "run_javascript",
        lambda _script: pytest.fail("snapshot publish used the ambient UI context"),
    )

    runtime._publish_guest_snapshot(client, "client", view)

    assert len(scripts) == 1
    assert "__syGuestSnapshotBridge.accept" in scripts[0]
    assert '"workspaceId":"work"' in scripts[0]
    assert '"tabId":"tab"' in scripts[0]
    assert '"revision":0' in scripts[0]
    token = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")
    assert token in scripts[0]


def test_runtime_can_publish_a_guest_snapshot_from_a_worker_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = GuestWorkspaceRegistry(SECRET, boot_id="boot-a", clock=lambda: 1_000)
    _isolated_runtime(monkeypatch, registry)
    view = registry.create_workspace(session_id="sid", tab_id="tab", workspace_id="work")
    runtime._active_guest_client_by_workspace[("sid", "work")] = "client"
    runtime._guest_snapshot_nonces[("sid", "work")] = "N" * 32
    scripts: list[str] = []
    client = SimpleNamespace(run_javascript=scripts.append)
    monkeypatch.setattr(
        runtime.ui,
        "run_javascript",
        lambda _script: pytest.fail("worker thread used the ambient UI context"),
    )

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(
            runtime._publish_guest_snapshot,
            client,
            "client",
            view,
        ).result(timeout=5)

    assert len(scripts) == 1
    assert "__syGuestSnapshotBridge.accept" in scripts[0]
    assert '"revision":0' in scripts[0]


def test_shared_shell_uses_only_session_storage_for_signed_guest_snapshots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "ui"
        / "shell.py"
    ).read_text(encoding="utf-8")

    assert "sing-yin-guest-workspace-snapshot-v1" in source
    assert "fetch('/api/guest/snapshot/restore'" in source
    assert "window.__syGuestSnapshotBridge" in source
    assert "sessionStorage.getItem(STORAGE_KEY)" in source
    assert "sessionStorage.setItem(STORAGE_KEY" in source
    bridge = source.split("def _install_guest_snapshot_bridge", 1)[1].split(
        "def _install_auth_status_monitor",
        1,
    )[0]
    assert "localStorage" not in bridge
    assert "indexedDB" not in bridge
    assert "caches." not in bridge
