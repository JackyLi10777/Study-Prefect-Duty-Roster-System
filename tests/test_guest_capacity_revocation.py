from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import nicegui_app.main as main_module
import nicegui_app.runtime as runtime
from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.gateway_identity import OriginPrincipalError
from nicegui_app.services.guest_workspace import (
    GuestCapacityError,
    GuestWorkspaceRegistry,
)


def _principal(mode: AccessMode, session_id: str) -> Principal:
    return Principal(
        mode=mode,
        subject="guest" if mode is AccessMode.GUEST else "operator@syss.edu.hk",
        session_id=session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        auth_epoch=7,
        key_id="origin-v7",
    )


def _runtime_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_EPOCH", "7")
    monkeypatch.setenv("ORIGIN_PRINCIPAL_KID", "origin-v7")
    monkeypatch.setattr(runtime, "_revoked_sessions", {})
    monkeypatch.setattr(runtime, "_guest_adapters", {})
    monkeypatch.setattr(runtime, "_client_guest_adapters", {})
    monkeypatch.setattr(runtime, "_active_guest_client_by_workspace", {})
    monkeypatch.setattr(runtime, "_guest_snapshot_nonces", {})
    monkeypatch.setattr(runtime, "_guest_cleanup_timers", {})
    monkeypatch.setattr(runtime, "_page_contexts", {})


def test_guest_registry_enforces_tab_capacity_without_consuming_an_extra_workspace() -> None:
    registry = GuestWorkspaceRegistry(
        b"guest-capacity-test-secret-that-is-long-enough",
        max_tabs_per_session=1,
    )
    first = registry.create_workspace(
        session_id="guest-session",
        tab_id="tab-one",
        workspace_id="workspace-one",
    )

    with pytest.raises(GuestCapacityError, match="tab capacity"):
        registry.create_workspace(
            session_id="guest-session",
            tab_id="tab-two",
            workspace_id="workspace-two",
        )

    assert registry.active_workspace_count("guest-session") == 1
    assert (
        registry.create_workspace(
            session_id="guest-session",
            tab_id="tab-one",
            workspace_id="ignored",
        ).workspace_id
        == first.workspace_id
    )


def test_guest_websocket_binding_turns_capacity_overflow_into_bilingual_retry_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _runtime_environment(monkeypatch)
    principal = _principal(AccessMode.GUEST, "guest-session")
    context = PageContext.create(
        principal,
        metadata={
            "clientId": "client-two",
            "tabId": "pending-client-two",
            "workspaceId": "pending-client-two",
            "binding": "provisional",
        },
    )

    class FullAdapter:
        def bind_workspace(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise GuestCapacityError("guest tab capacity is full for this session")

    client = SimpleNamespace(tab_id="stable-tab-two")
    scripts: list[str] = []
    runtime._page_contexts["client-two"] = context
    runtime._client_guest_adapters["client-two"] = FullAdapter()
    runtime._guest_adapters[("guest-session", "pending-client-two")] = (
        runtime._client_guest_adapters["client-two"]
    )
    monkeypatch.setattr(runtime.ui, "run_javascript", scripts.append)

    runtime._bind_guest_client("client-two", client)

    assert len(scripts) == 1
    assert "示範工作區暫時未能開啟" in scripts[0]
    assert "The demo workspace is temporarily busy" in scripts[0]
    assert "重新嘗試 · Retry" in scripts[0]
    assert "sy-guest-capacity-state" in scripts[0]
    assert runtime._page_contexts["client-two"].metadata["binding"] == "capacity-denied"
    assert runtime._client_guest_adapters == {}


def test_capacity_state_has_a_keyboard_focus_and_reduced_motion_safe_surface() -> None:
    runtime_source = Path(runtime.__file__).read_text(encoding="utf-8")
    css_source = (
        Path(runtime.__file__).parent
        / "assets"
        / "css"
        / "sing-yin-components-v1.css"
    ).read_text(encoding="utf-8")

    assert "setAttribute('role', 'alert')" in runtime_source
    assert "aria-live" in runtime_source
    assert "sy-guest-capacity-retry')?.focus()" in runtime_source
    assert "#sy-guest-capacity-state" in css_source
    assert ".sy-guest-capacity-actions button:focus-visible" in css_source


def test_revoked_cached_context_and_captured_adapter_fail_immediately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _runtime_environment(monkeypatch)
    context = PageContext.create(_principal(AccessMode.ADMIN, "admin-session"))
    calls: list[str] = []

    class Delegate:
        def write(self) -> str:
            calls.append("write")
            return "ok"

    guarded = runtime._RuntimeGuardedAdapter(Delegate(), context)
    runtime._page_contexts["admin-client"] = context
    monkeypatch.setattr(
        runtime,
        "_current_client",
        lambda: SimpleNamespace(id="admin-client", request=None),
    )
    assert guarded.write() == "ok"
    runtime.revoke_authenticated_session(context)

    with pytest.raises(OriginPrincipalError, match="revoked"):
        runtime._cached_context_is_active(context)
    with pytest.raises(OriginPrincipalError, match="revoked"):
        runtime.current_page_context()
    with pytest.raises(OriginPrincipalError, match="revoked"):
        guarded.write()
    assert calls == ["write"]


def test_origin_revocation_endpoint_is_idempotent_and_cleans_guest_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _runtime_environment(monkeypatch)
    principal = _principal(AccessMode.GUEST, "guest-session")
    cleanup_calls: list[str] = []
    download_cleanup_calls: list[str] = []
    monkeypatch.setattr(main_module, "principal_from_request", lambda _request: principal)
    monkeypatch.setattr(main_module, "cleanup_guest_session", cleanup_calls.append)
    monkeypatch.setattr(
        main_module,
        "guest_download_registry",
        lambda: SimpleNamespace(cleanup_session=download_cleanup_calls.append),
    )

    first = main_module.revoke_origin_session(SimpleNamespace())
    second = main_module.revoke_origin_session(SimpleNamespace())

    assert first.status_code == second.status_code == 204
    assert cleanup_calls == ["guest-session", "guest-session"]
    assert download_cleanup_calls == ["guest-session", "guest-session"]
    with pytest.raises(OriginPrincipalError, match="revoked"):
        runtime.require_runtime_principal_active(principal)


def test_shell_logout_requires_confirmed_revocation_and_broadcasts_to_admin_tabs() -> None:
    shell_source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "ui"
        / "shell.py"
    ).read_text(encoding="utf-8")

    assert "const channel = 'BroadcastChannel' in window" in shell_source
    assert "if (!response.ok) throw new Error(`logout ${response.status}`)" in shell_source
    assert "登出尚未安全完成" in shell_source
    assert "The server could not confirm that this session was revoked" in shell_source
    assert "window.location.replace('/')" in shell_source
