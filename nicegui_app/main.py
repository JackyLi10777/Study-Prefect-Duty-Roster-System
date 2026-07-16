"""Local NiceGUI entry point for the Sing Yin Study Prefect Duty Roster System."""

from __future__ import annotations

import json
import os
import re
from urllib.parse import quote

from nicegui import app, ui
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from nicegui_app.access_context import AccessMode
from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import BRAND_ASSET_DIR, FAVICON_CREST_PATH, MUSIC_DIR, PROJECT_ROOT
from nicegui_app.deployment import (
    DeploymentSettings,
    health_snapshot,
    install_trusted_host_protection,
    resolve_storage_secret,
)
from nicegui_app.observability import (
    configure_local_logging,
    install_asyncio_exception_handler,
    install_exception_hooks,
    install_request_tracing,
    logger,
)
from nicegui_app.process_lock import acquire_origin_process_lock
from nicegui_app.gateway_identity import OriginPrincipalError, principal_from_request
from nicegui_app.runtime import (
    cleanup_guest_session,
    get_admin_workflow,
    restore_guest_browser_snapshot,
    runtime_readiness,
)
from nicegui_app.services.guest_downloads import (
    GuestDownloadError,
    guest_download_registry,
)
from nicegui_app.services.guest_workspace import DEFAULT_MAX_SNAPSHOT_BYTES
from nicegui_app.ui import pages as _pages  # noqa: F401 - registers @ui.page routes


@app.get("/healthz", include_in_schema=False)
def healthz() -> JSONResponse:
    """Return a data-free local health result suitable for future host monitoring."""
    application_mode = current_application_mode()
    payload = health_snapshot(application_mode.database_path)
    e2e_run_id = os.getenv("SING_YIN_E2E_RUN_ID", "").strip()
    if os.getenv("SING_YIN_E2E_ISOLATED") == "1" and re.fullmatch(r"E2E-[A-F0-9]{12}", e2e_run_id):
        payload = {**payload, "e2eRunId": e2e_run_id}
    maintenance = get_admin_workflow().maintenance_status()
    if maintenance.active:
        payload = {**payload, "status": "maintenance", "maintenance": True}
    return JSONResponse(
        payload,
        status_code=200 if payload["status"] == "ok" else 503,
        headers={"Cache-Control": "no-store"},
    )


def compose_readiness_payload(
    health: dict[str, str],
    runtime: dict[str, object],
) -> tuple[dict[str, object], int]:
    """Combine data-free storage and process evidence into one readiness result."""

    ready = (
        health.get("status") == "ok"
        and not bool(runtime.get("maintenance"))
        and not bool(runtime.get("recoveryRequired"))
        and int(runtime.get("pendingBackupObligations") or 0) == 0
        and not bool(runtime.get("backupRepairFailed"))
    )
    return (
        {
            **health,
            **runtime,
            "status": "ready" if ready else "degraded",
            "writeReady": ready,
        },
        200 if ready else 503,
    )


@app.get("/readyz", include_in_schema=False)
def readyz() -> JSONResponse:
    """Report whether this origin may safely accept a new write."""

    application_mode = current_application_mode()
    payload, status_code = compose_readiness_payload(
        health_snapshot(application_mode.database_path),
        runtime_readiness(),
    )
    return JSONResponse(
        payload,
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


def _guest_download_not_found() -> JSONResponse:
    return JSONResponse(
        {"error": "not_found"},
        status_code=404,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.post("/api/guest/snapshot/restore", include_in_schema=False)
async def restore_guest_snapshot(request: Request) -> Response:
    """Restore one signed, tab-bound browser snapshot without durable writes."""

    try:
        content_length = int(request.headers.get("content-length", "0") or 0)
    except ValueError:
        return _guest_download_not_found()
    if content_length > DEFAULT_MAX_SNAPSHOT_BYTES + 2_048:
        return _guest_download_not_found()
    try:
        principal = principal_from_request(request)
        principal.require_active()
        body = await request.body()
        if len(body) > DEFAULT_MAX_SNAPSHOT_BYTES + 2_048:
            return _guest_download_not_found()
        payload = json.loads(body)
    except (OriginPrincipalError, PermissionError, UnicodeDecodeError, ValueError):
        return _guest_download_not_found()
    if principal.mode is not AccessMode.GUEST or not principal.session_id:
        return _guest_download_not_found()
    if not isinstance(payload, dict) or set(payload) != {
        "nonce",
        "tabId",
        "token",
        "workspaceId",
    }:
        return _guest_download_not_found()
    nonce = payload.get("nonce")
    tab_id = payload.get("tabId")
    token = payload.get("token")
    workspace_id = payload.get("workspaceId")
    if not (
        isinstance(nonce, str)
        and 16 <= len(nonce) <= 128
        and isinstance(tab_id, str)
        and 1 <= len(tab_id) <= 256
        and isinstance(workspace_id, str)
        and 1 <= len(workspace_id) <= 256
        and isinstance(token, str)
        and 1 <= len(token.encode("utf-8")) <= DEFAULT_MAX_SNAPSHOT_BYTES
    ):
        return _guest_download_not_found()
    try:
        result = restore_guest_browser_snapshot(
            session_id=principal.session_id,
            workspace_id=workspace_id,
            tab_id=tab_id,
            nonce=nonce,
            token=token,
        )
    except (OriginPrincipalError, PermissionError, ValueError):
        return _guest_download_not_found()
    return JSONResponse(
        result,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/api/guest/download/{token}", include_in_schema=False)
def guest_download(token: str, request: Request) -> Response:
    """Consume one session-bound in-memory guest export exactly once."""

    try:
        principal = principal_from_request(request)
        principal.require_active()
    except (OriginPrincipalError, PermissionError):
        return _guest_download_not_found()
    if principal.mode is not AccessMode.GUEST or not principal.session_id:
        return _guest_download_not_found()
    try:
        payload = guest_download_registry().consume(
            token=token,
            session_id=principal.session_id,
        )
    except GuestDownloadError:
        return _guest_download_not_found()
    extension = payload.filename.rsplit(".", 1)[-1].lower()
    fallback = (
        f"SYSS_DEMO_download.{extension}"
        if re.fullmatch(r"[a-z0-9]{1,8}", extension)
        else "SYSS_DEMO_download"
    )
    return Response(
        content=payload.content,
        media_type=payload.media_type,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "Content-Disposition": (
                f'attachment; filename="{fallback}"; '
                f"filename*=UTF-8''{quote(payload.filename, safe='')}"
            ),
            "Cross-Origin-Resource-Policy": "same-origin",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/api/guest/downloads/cleanup", include_in_schema=False)
def cleanup_guest_downloads(request: Request) -> Response:
    """Clear pending one-shot exports before a guest session signs out."""

    try:
        principal = principal_from_request(request)
        principal.require_active()
    except (OriginPrincipalError, PermissionError):
        return _guest_download_not_found()
    if principal.mode is not AccessMode.GUEST or not principal.session_id:
        return _guest_download_not_found()
    guest_download_registry().cleanup_session(principal.session_id)
    cleanup_guest_session(principal.session_id)
    return Response(
        status_code=204,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


def open_browser_on_startup() -> bool:
    """Keep local first-run friendly while allowing headless verification and managed launches."""
    return os.getenv("SING_YIN_OPEN_BROWSER", "true").strip().lower() not in {"0", "false", "no", "off"}


def run() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    application_mode = current_application_mode()
    deployment = DeploymentSettings.from_environment()
    configure_local_logging()
    install_exception_hooks()
    managed_secret_path = (
        application_mode.database_path.parent / ".nicegui-storage-secret"
        if application_mode.is_practice
        else PROJECT_ROOT / "data" / "runtime" / ".nicegui-storage-secret"
    )
    storage_secret = resolve_storage_secret(deployment, managed_path=managed_secret_path)
    app.on_startup(install_asyncio_exception_handler)
    install_trusted_host_protection(app, deployment)
    install_request_tracing(app)
    logger().info(
        "event=application_starting application_mode=%s deployment_mode=%s host=%s port=%s",
        application_mode.mode,
        deployment.mode,
        deployment.host,
        deployment.port,
    )
    origin_lease = acquire_origin_process_lock(application_mode.database_path)
    try:
        get_admin_workflow()
        app.add_static_files(url_path="/assets/brand", local_directory=BRAND_ASSET_DIR)
        app.add_static_files(url_path="/assets/workflow", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "workflow")
        app.add_static_files(url_path="/assets/atmosphere", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "atmosphere")
        app.add_static_files(url_path="/assets/fonts", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "fonts")
        app.add_static_files(url_path="/assets/css", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "css")
        app.add_static_files(url_path="/assets/motion", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "motion")
        app.add_static_files(url_path="/assets/vendor", local_directory=PROJECT_ROOT / "nicegui_app" / "assets" / "vendor")
        app.add_static_files(url_path="/assets/music", local_directory=MUSIC_DIR)
        ui.run(
            title="Sing Yin Study Prefect Duty Roster",
            viewport="width=device-width, initial-scale=1, viewport-fit=cover",
            favicon=str(FAVICON_CREST_PATH),
            host=deployment.host,
            port=deployment.port,
            reload=False,
            show=open_browser_on_startup(),
            storage_secret=storage_secret,
        )
    finally:
        origin_lease.release()


if __name__ in {"__main__", "__mp_main__"}:
    run()
