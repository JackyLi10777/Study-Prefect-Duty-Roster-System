"""Process-local application services and verified request composition."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import os
import secrets
from threading import RLock, Timer
from typing import Any

from nicegui import ui

from nicegui_app.access_context import AccessMode, PageContext
from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.gateway_identity import (
    OriginPrincipalError,
    configured_auth_epoch,
    configured_key_id,
    principal_from_request,
)
from nicegui_app.observability import current_request_reference
from nicegui_app.services.guest_preferences import GuestPreferenceRegistry
from nicegui_app.services.guest_workspace import (
    GuestCapacityError,
    GuestSnapshotError,
    GuestWorkspaceRegistry,
    GuestWorkspaceView,
)
from nicegui_app.services.operation_context import PageContextWorkflowAdapter
from nicegui_app.services.roster_workflow import RosterWorkflow


_workflow: RosterWorkflow | None = None
_guest_registry: GuestWorkspaceRegistry | None = None
_guest_preference_registry = GuestPreferenceRegistry()
_guest_adapters: dict[tuple[str, str], Any] = {}
_client_guest_adapters: dict[str, Any] = {}
_active_guest_client_by_workspace: dict[tuple[str, str], str] = {}
_guest_snapshot_nonces: dict[tuple[str, str], str] = {}
_guest_cleanup_timers: dict[tuple[str, str], Timer] = {}
_page_contexts: dict[str, PageContext] = {}
_revoked_sessions: dict[tuple[AccessMode, str], datetime | None] = {}
_disconnect_registered: set[str] = set()
_runtime_lock = RLock()
_GUEST_DISCONNECT_GRACE_SECONDS = 12.0


def get_admin_workflow() -> RosterWorkflow:
    global _workflow
    if _workflow is None:
        profile = current_application_mode()
        # Demonstration seed data belongs only to the fully isolated local
        # practice profile.  An official database must be allowed to remain
        # genuinely empty after a controlled first-use reset.
        _workflow = RosterWorkflow(
            database_path=profile.database_path,
            backup_dir=profile.backup_dir,
            seed_path=None if profile.mode == "official" else PREFECT_SEED_PATH,
        )
        _workflow.bootstrap()
    return _workflow


def _guest_secret() -> bytes:
    configured = os.getenv("SING_YIN_GUEST_SNAPSHOT_SECRET", "").strip()
    if configured:
        if len(configured) < 32:
            raise RuntimeError("SING_YIN_GUEST_SNAPSHOT_SECRET must contain at least 32 characters.")
        return configured.encode("utf-8")
    origin_secret = os.getenv("ORIGIN_PRINCIPAL_SECRET", "").strip()
    if len(origin_secret) >= 32:
        return hashlib.sha256(
            b"sing-yin-guest-snapshot-v1\0" + origin_secret.encode("utf-8")
        ).digest()
    # Local-only development may run without the remote gateway. This random
    # process secret intentionally invalidates all guest snapshots on restart.
    return secrets.token_bytes(32)


def get_guest_registry() -> GuestWorkspaceRegistry:
    global _guest_registry
    with _runtime_lock:
        if _guest_registry is None:
            _guest_registry = GuestWorkspaceRegistry(_guest_secret())
        return _guest_registry


def _unified_guest_enabled() -> bool:
    return os.getenv("SING_YIN_UNIFIED_GUEST", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _current_client() -> Any | None:
    try:
        return ui.context.client
    except RuntimeError:
        return None


def _purge_revoked_sessions_locked(now: datetime) -> None:
    expired = [
        key
        for key, expires_at in _revoked_sessions.items()
        if expires_at is not None and expires_at <= now
    ]
    for key in expired:
        _revoked_sessions.pop(key, None)


def revoke_authenticated_session(context_or_principal: PageContext | Any) -> None:
    """Immediately invalidate one verified gateway session in this process.

    Cookie removal happens at the gateway, but existing NiceGUI callbacks may
    already hold a page context or workflow adapter. Keeping this short-lived
    deny-list makes the next callback fail closed without waiting for the
    browser's periodic status poll.
    """

    principal = (
        context_or_principal.principal
        if isinstance(context_or_principal, PageContext)
        else context_or_principal
    )
    if (
        principal.mode not in {AccessMode.ADMIN, AccessMode.GUEST}
        or not principal.session_id
    ):
        raise OriginPrincipalError("only authenticated sessions may be revoked")
    now = datetime.now(timezone.utc)
    with _runtime_lock:
        _purge_revoked_sessions_locked(now)
        _revoked_sessions[(principal.mode, principal.session_id)] = principal.expires_at


def require_runtime_principal_active(principal: Any) -> None:
    """Reject expired, rotated, epoch-stale, or process-revoked principals."""

    principal.require_active()
    if principal.mode in {AccessMode.ADMIN, AccessMode.GUEST}:
        if principal.auth_epoch != configured_auth_epoch(os.environ):
            raise OriginPrincipalError("the authenticated session has been revoked")
        if principal.key_id != configured_key_id(os.environ):
            raise OriginPrincipalError("the authenticated key has been rotated")
        now = datetime.now(timezone.utc)
        with _runtime_lock:
            _purge_revoked_sessions_locked(now)
            if (principal.mode, principal.session_id) in _revoked_sessions:
                raise OriginPrincipalError("the authenticated session has been revoked")


def _cached_context_is_active(context: PageContext) -> bool:
    require_runtime_principal_active(context.principal)
    return True


class _RuntimeGuardedAdapter:
    """Recheck a cached page identity before every captured adapter access."""

    def __init__(self, delegate: Any, context: PageContext) -> None:
        self._delegate = delegate
        self._context = context

    def __getattr__(self, name: str) -> Any:
        _cached_context_is_active(self._context)
        attribute = getattr(self._delegate, name)
        if not callable(attribute):
            return attribute

        @wraps(attribute)
        def invoke(*args: Any, **kwargs: Any) -> Any:
            _cached_context_is_active(self._context)
            return attribute(*args, **kwargs)

        return invoke


def _guest_capacity_script() -> str:
    """Render an accessible bilingual terminal state for a bounded guest."""

    return r"""
    (() => {
      const show = () => {
        window.__syGuestSnapshotBridge?.destroy?.();
        document.body.dataset.syGuestCapacity = 'busy';
        const main = document.getElementById('main-content');
        if (main) {
          main.setAttribute('inert', '');
          main.setAttribute('aria-hidden', 'true');
        }
        let state = document.getElementById('sy-guest-capacity-state');
        if (!state) {
          state = document.createElement('section');
          state.id = 'sy-guest-capacity-state';
          state.setAttribute('role', 'alert');
          state.setAttribute('aria-live', 'assertive');
          state.innerHTML = `
            <div class="sy-guest-capacity-card">
              <span class="sy-guest-capacity-mark" aria-hidden="true">候</span>
              <p class="sy-guest-capacity-kicker">DEMO WORKSPACE · 暫時繁忙</p>
              <h1>示範工作區暫時未能開啟</h1>
              <p>這個訪客工作階段目前已有太多分頁，或示範容量已滿。請關閉另一個試用分頁後重試；你的正式資料不會受到影響。</p>
              <p lang="en">The demo workspace is temporarily busy or this guest session has too many open tabs. Close another trial tab, then retry. Official data is unaffected.</p>
              <div class="sy-guest-capacity-actions">
                <button id="sy-guest-capacity-retry" type="button">重新嘗試 · Retry</button>
                <button id="sy-guest-capacity-exit" type="button">離開示範 · Exit demo</button>
              </div>
            </div>`;
          document.body.appendChild(state);
        }
        document.getElementById('sy-guest-capacity-retry')?.addEventListener(
          'click',
          () => window.location.reload(),
          {once: true},
        );
        document.getElementById('sy-guest-capacity-exit')?.addEventListener(
          'click',
          async () => {
            try {
              const response = await fetch('/auth/logout', {
                method: 'POST',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: {'Accept': 'application/json'},
              });
              if (!response.ok) throw new Error(`logout ${response.status}`);
              window.location.replace('/');
            } catch {
              state.dataset.logout = 'retry';
            }
          },
          {once: true},
        );
        document.getElementById('sy-guest-capacity-retry')?.focus();
      };
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', show, {once: true});
      } else {
        show();
      }
    })();
    """


def _cancel_guest_cleanup(key: tuple[str, str]) -> None:
    timer = _guest_cleanup_timers.pop(key, None)
    if timer is not None:
        timer.cancel()


def _finish_guest_cleanup(key: tuple[str, str], client_id: str) -> None:
    session_id, workspace_id = key
    with _runtime_lock:
        if _active_guest_client_by_workspace.get(key) != client_id:
            return
        _guest_cleanup_timers.pop(key, None)
        _active_guest_client_by_workspace.pop(key, None)
        _guest_snapshot_nonces.pop(key, None)
        _guest_adapters.pop(key, None)
    get_guest_registry().cleanup_workspace(
        session_id=session_id,
        workspace_id=workspace_id,
    )


def _schedule_guest_cleanup(key: tuple[str, str], client_id: str) -> None:
    _cancel_guest_cleanup(key)
    timer = Timer(
        _GUEST_DISCONNECT_GRACE_SECONDS,
        _finish_guest_cleanup,
        args=(key, client_id),
    )
    timer.daemon = True
    _guest_cleanup_timers[key] = timer
    timer.start()


def _guest_snapshot_script(action: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        "(() => {"
        f"const payload={encoded};"
        f"if (window.__syGuestSnapshotBridge) window.__syGuestSnapshotBridge.{action}(payload);"
        f"else window.__syPendingGuestSnapshot{action.title()}=payload;"
        "})();"
    )


def _publish_guest_snapshot(
    client: Any,
    client_id: str,
    view: GuestWorkspaceView,
) -> None:
    """Push the latest signed revision to the exact connected browser tab."""

    key = (view.session_id, view.workspace_id)
    with _runtime_lock:
        if _active_guest_client_by_workspace.get(key) != client_id:
            return
        nonce = _guest_snapshot_nonces.get(key)
    if not nonce:
        return
    token = get_guest_registry().seal_snapshot(
        session_id=view.session_id,
        workspace_id=view.workspace_id,
        tab_id=view.tab_id,
    )
    client.run_javascript(
        _guest_snapshot_script(
            "accept",
            {
                "nonce": nonce,
                "revision": view.revision,
                "tabId": view.tab_id,
                "token": token,
                "workspaceId": view.workspace_id,
            },
        )
    )


def _bootstrap_guest_snapshot_bridge(
    client: Any,
    client_id: str,
    view: GuestWorkspaceView,
) -> None:
    key = (view.session_id, view.workspace_id)
    with _runtime_lock:
        if _active_guest_client_by_workspace.get(key) != client_id:
            return
        nonce = _guest_snapshot_nonces.get(key)
    if not nonce:
        return
    token = get_guest_registry().seal_snapshot(
        session_id=view.session_id,
        workspace_id=view.workspace_id,
        tab_id=view.tab_id,
    )
    client.run_javascript(
        _guest_snapshot_script(
            "bind",
            {
                "nonce": nonce,
                "revision": view.revision,
                "tabId": view.tab_id,
                "token": token,
                "workspaceId": view.workspace_id,
            },
        )
    )


def _bind_guest_client(client_id: str, client: Any) -> None:
    """Promote a provisional page to NiceGUI's stable browser-tab identity."""

    stable_tab_id = str(getattr(client, "tab_id", "") or "")
    if not stable_tab_id:
        return
    with _runtime_lock:
        context = _page_contexts.get(client_id)
        adapter = _client_guest_adapters.get(client_id)
        if (
            context is None
            or adapter is None
            or context.principal.mode is not AccessMode.GUEST
            or not context.principal.session_id
        ):
            return
        session_id = context.principal.session_id
        workspace_id = hashlib.sha256(
            f"{session_id}\0{stable_tab_id}".encode("utf-8")
        ).hexdigest()[:32]
        key = (session_id, workspace_id)
        _cancel_guest_cleanup(key)
        initial_view = context.workspace
        try:
            bound_view = adapter.bind_workspace(
                workspace_id=workspace_id,
                tab_id=stable_tab_id,
            )
        except GuestCapacityError:
            previous_workspace_id = context.metadata.get("workspaceId", "")
            _guest_adapters.pop((session_id, previous_workspace_id), None)
            _client_guest_adapters.pop(client_id, None)
            _page_contexts[client_id] = PageContext.create(
                context.principal,
                workspace=None,
                preference_store=context.preference_store,
                request_reference=context.request_reference,
                metadata={
                    **context.metadata,
                    "tabId": stable_tab_id,
                    "workspaceId": workspace_id,
                    "binding": "capacity-denied",
                },
            )
            ui.run_javascript(_guest_capacity_script())
            return
        previous_workspace_id = context.metadata.get("workspaceId", "")
        _guest_adapters.pop((session_id, previous_workspace_id), None)
        _guest_adapters[key] = adapter
        _active_guest_client_by_workspace[key] = client_id
        _guest_snapshot_nonces[key] = secrets.token_urlsafe(24)
        _page_contexts[client_id] = PageContext.create(
            context.principal,
            workspace=bound_view,
            preference_store=context.preference_store,
            request_reference=context.request_reference,
            metadata={
                **context.metadata,
                "tabId": stable_tab_id,
                "workspaceId": workspace_id,
                "binding": "stable",
            },
        )
    _bootstrap_guest_snapshot_bridge(client, client_id, bound_view)
    if (
        initial_view is not None
        and (
            int(getattr(initial_view, "revision", -1)) != bound_view.revision
            or getattr(initial_view, "state", None) != bound_view.state
        )
    ):
        # A duplicated browser tab initially composed from the only existing
        # fictional workspace. Reload once after the handshake so its newly
        # isolated fixture is rendered, rather than briefly showing stale
        # content from the source tab.
        ui.navigate.reload()


def restore_guest_browser_snapshot(
    *,
    session_id: str,
    workspace_id: str,
    tab_id: str,
    nonce: str,
    token: str,
) -> dict[str, object]:
    """Validate and restore one signed sessionStorage snapshot.

    The per-connection nonce prevents a copied browser tab from presenting the
    source tab's workspace binding. Invalid, expired, old-boot, wrong-binding,
    or stale snapshots are rejected and replaced in the browser by a fresh
    token for the already-isolated fixture/live workspace.
    """

    key = (session_id, workspace_id)
    with _runtime_lock:
        active_client = _active_guest_client_by_workspace.get(key)
        expected_nonce = _guest_snapshot_nonces.get(key)
        if (
            not active_client
            or not expected_nonce
            or not secrets.compare_digest(expected_nonce, nonce)
        ):
            raise OriginPrincipalError("guest snapshot binding is unavailable")
    registry = get_guest_registry()
    accepted = True
    try:
        view, restored = registry.restore_snapshot(
            token,
            session_id=session_id,
            workspace_id=workspace_id,
            tab_id=tab_id,
        )
    except GuestSnapshotError:
        accepted = False
        restored = False
        view = registry.get_workspace(
            session_id=session_id,
            workspace_id=workspace_id,
            tab_id=tab_id,
        )
    fresh_token = registry.seal_snapshot(
        session_id=session_id,
        workspace_id=workspace_id,
        tab_id=tab_id,
    )
    return {
        "accepted": accepted,
        "restored": restored,
        "revision": view.revision,
        "tabId": tab_id,
        "token": fresh_token,
        "workspaceId": workspace_id,
    }


def cleanup_guest_session(session_id: str) -> None:
    """Idempotently clear all process-local state for a signed-out guest."""

    with _runtime_lock:
        keys = {
            key
            for key in (
                set(_active_guest_client_by_workspace)
                | set(_guest_adapters)
                | set(_guest_snapshot_nonces)
                | set(_guest_cleanup_timers)
            )
            if key[0] == session_id
        }
        for key in keys:
            timer = _guest_cleanup_timers.pop(key, None)
            if timer is not None:
                timer.cancel()
            _active_guest_client_by_workspace.pop(key, None)
            _guest_snapshot_nonces.pop(key, None)
            _guest_adapters.pop(key, None)
        for client_id, context in list(_page_contexts.items()):
            if (
                context.principal.mode is AccessMode.GUEST
                and context.principal.session_id == session_id
            ):
                _client_guest_adapters.pop(client_id, None)
    get_guest_registry().cleanup_session(session_id)
    _guest_preference_registry.cleanup_session(session_id)


def _cleanup_client_context(client_id: str) -> None:
    with _runtime_lock:
        context = _page_contexts.pop(client_id, None)
        _client_guest_adapters.pop(client_id, None)
        _disconnect_registered.discard(client_id)
        if context is None or context.principal.mode is not AccessMode.GUEST:
            return
        session_id = context.principal.session_id
        workspace_id = context.metadata.get("workspaceId", "")
        if (
            session_id
            and workspace_id
            and context.metadata.get("binding") == "stable"
        ):
            key = (session_id, workspace_id)
            if _active_guest_client_by_workspace.get(key) == client_id:
                _schedule_guest_cleanup(key, client_id)
        elif session_id and workspace_id:
            _guest_adapters.pop((session_id, workspace_id), None)


def _compose_page_context(request: Any, client_id: str) -> PageContext:
    principal = principal_from_request(request)
    require_runtime_principal_active(principal)
    workspace = None
    metadata: dict[str, str] = {}
    if principal.mode is AccessMode.GUEST:
        if not _unified_guest_enabled():
            raise OriginPrincipalError("the unified guest workspace is not enabled")
        if not client_id or not principal.session_id:
            raise OriginPrincipalError("guest pages require a bound browser client")
        workspace_id = f"pending-{client_id}"
        workspace = get_guest_registry().initial_view_for_unbound_page(
            session_id=principal.session_id,
            placeholder_id=workspace_id,
        )
        metadata = {
            "clientId": client_id,
            "tabId": workspace_id,
            "workspaceId": workspace_id,
            "binding": "provisional",
        }
    context = PageContext.create(
        principal,
        workspace=workspace,
        preference_store=(
            _guest_preference_registry.store_for(
                principal.session_id,
                expires_at=principal.expires_at,
            )
            if principal.mode is AccessMode.GUEST and principal.session_id
            else None
        ),
        request_reference=current_request_reference(),
        metadata=metadata,
    )
    return context


def current_page_context() -> PageContext:
    """Return the verified context for the active NiceGUI page or callback."""

    client = _current_client()
    try:
        request = client.request if client is not None else None
    except RuntimeError:
        # NiceGUI exposes an auto-index client while tests and startup code run
        # outside an actual browser request. Treat that composition edge as the
        # local console rather than caching context on the synthetic client.
        client = None
        request = None
    client_id = str(getattr(client, "id", "")) if client is not None else ""
    if not client_id:
        return _compose_page_context(request, "")

    with _runtime_lock:
        cached = _page_contexts.get(client_id)
        if cached is not None:
            _cached_context_is_active(cached)
            return cached
        context = _compose_page_context(request, client_id)
        _page_contexts[client_id] = context
        if client_id not in _disconnect_registered:
            client.on_connect(lambda: _bind_guest_client(client_id, client))
            client.on_disconnect(lambda: _cleanup_client_context(client_id))
            _disconnect_registered.add(client_id)
        return context


def get_workflow() -> Any:
    """Resolve the official workflow or the isolated adapter for this client."""

    context = current_page_context()
    if context.principal.mode in {
        AccessMode.ADMIN,
        AccessMode.LOCAL_MAINTENANCE,
    }:
        return _RuntimeGuardedAdapter(
            PageContextWorkflowAdapter(get_admin_workflow(), context),
            context,
        )
    if context.principal.mode is AccessMode.PUBLIC:
        raise OriginPrincipalError("public traffic cannot resolve an application workflow")
    session_id = context.principal.session_id
    workspace_id = context.metadata.get("workspaceId", "")
    if not session_id or not workspace_id:
        raise OriginPrincipalError("guest workspace identity is incomplete")
    key = (session_id, workspace_id)
    client = _current_client()
    client_id = str(getattr(client, "id", "")) if client is not None else ""
    with _runtime_lock:
        adapter = _guest_adapters.get(key)
        if adapter is None:
            from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter

            adapter = GuestWorkspaceAdapter(
                registry=get_guest_registry(),
                context=context,
                tab_id=context.metadata["tabId"],
                workspace_id=(
                    workspace_id
                    if context.metadata.get("binding") == "stable"
                    else None
                ),
                initial_view=context.workspace,
                snapshot_publisher=(
                    (lambda view, bound_client=client, bound_client_id=client_id: _publish_guest_snapshot(
                        bound_client,
                        bound_client_id,
                        view,
                    ))
                    if client_id
                    else None
                ),
            )
            _guest_adapters[key] = adapter
        if client_id:
            _client_guest_adapters[client_id] = adapter
        return _RuntimeGuardedAdapter(adapter, context)


def runtime_readiness() -> dict[str, object]:
    """Return data-free process readiness for the monitoring endpoint."""

    workflow = get_admin_workflow()
    maintenance = workflow.maintenance_status()
    pending_obligations = (
        0
        if maintenance.active or workflow.sessions is None
        else workflow.pending_backup_obligation_count()
    )
    workflow_initialized = workflow.sessions is not None and not workflow.diagnostic_only
    return {
        "workflowInitialized": workflow_initialized,
        "maintenance": maintenance.active,
        "recoveryRequired": maintenance.recovery_required,
        "pendingBackupObligations": pending_obligations,
        "backupRepairFailed": bool(workflow.backup_repair_error),
        "guestSessions": get_guest_registry().active_session_count if _guest_registry is not None else 0,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }


__all__ = [
    "cleanup_guest_session",
    "current_page_context",
    "get_admin_workflow",
    "get_guest_registry",
    "get_workflow",
    "require_runtime_principal_active",
    "revoke_authenticated_session",
    "restore_guest_browser_snapshot",
    "runtime_readiness",
]
