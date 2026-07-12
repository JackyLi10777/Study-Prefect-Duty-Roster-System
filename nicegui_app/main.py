"""Local NiceGUI entry point for the Sing Yin Study Prefect Duty Roster System."""

from __future__ import annotations

import os

from nicegui import app, ui
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

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
from nicegui_app.runtime import get_workflow
from nicegui_app.ui import pages as _pages  # noqa: F401 - registers @ui.page routes


@app.get("/healthz", include_in_schema=False)
def healthz() -> JSONResponse:
    """Return a data-free local health result suitable for future host monitoring."""
    payload = health_snapshot()
    maintenance = get_workflow().maintenance_status()
    if maintenance.active:
        payload = {**payload, "status": "maintenance", "maintenance": True}
    return JSONResponse(payload, status_code=200 if payload["status"] == "ok" else 503)


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
    get_workflow()
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
        favicon=str(FAVICON_CREST_PATH),
        host=deployment.host,
        port=deployment.port,
        reload=False,
        show=open_browser_on_startup(),
        storage_secret=storage_secret,
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
