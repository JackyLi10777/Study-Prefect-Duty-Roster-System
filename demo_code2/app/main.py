"""
Sing Yin Secondary School Study Prefect Duty Roster System
===========================================================
NiceGUI Version -- Multi-Page Architecture with Sidebar Navigation
Run with: python main.py
"""

import os
from pathlib import Path
import sys
import secrets
sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from utils.logging_config import setup_logging, get_logger
from middleware.request_id import RequestIDMiddleware
from nicegui import ui, app
from theme import apply_theme
from components.sidebar import create_sidebar
from utils.error_handler import log_exception_with_context

# Exception handler imports
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
# Register all page routes by importing them
import pages.dashboard
import pages.roster
import pages.prefects
import pages.leave
import pages.audit


# =============================================================================
# Global Exception Handlers
# =============================================================================

async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions.
    Logs full traceback with request context and returns JSON 500.
    """
    log_exception_with_context(exc, request)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "request_id": request.headers.get("X-Request-ID", "-"),
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for HTTP exceptions (4xx, 5xx).
    Logs warning with context and returns appropriate JSON response.
    """
    logger = __import__("logging").getLogger("sing_yin.http")
    rid = request.headers.get("X-Request-ID", "-")
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path} [rid={rid}]: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": rid,
        },
    )


# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


# =============================================================================
# Root redirect + Design System page
# =============================================================================

@ui.page("/design")
def design_system_page():
    """Professional Teal Design System v4.0 validation page."""
    from i18n.helpers import t as _t
    from theme import Type
    from components.kpi_card import KpiCard
    apply_theme()
    create_sidebar()

    with ui.column().classes("w-full max-w-6xl mx-auto px-6 py-8 gap-6"):
        ui.label(_t("專業青藍色設計系統 v4.0", "Professional Teal Design System v4.0")).classes(
            "text-2xl font-bold text-teal-700 dark:text-teal-300"
        )
        ui.label(
            _t("HyperOS Native - 聖言中學學習風紀值班表系統", "HyperOS Native - Sing Yin Secondary School Study Prefect Roster")
        ).classes("text-sm text-slate-500 dark:text-slate-400")

        ui.separator()

        ui.label(_t("KPI 卡片（HyperOS 漸變效果）", "KPI Cards (with HyperOS Gradient)")).classes("text-lg font-semibold mt-2")
        with ui.row().classes("gap-4 w-full flex-wrap"):
            KpiCard("28", _t("總風紀數", "Total Prefects"), gradient=True)
            KpiCard("12.5", _t("平均負荷 (分)", "Avg Load (pts)"), gradient=True)
            KpiCard("3.2", _t("公平指數", "Fairness Index"))
            KpiCard("98%", _t("覆蓋率", "Coverage Rate"))

        ui.label(_t("按鈕", "Buttons")).classes("text-lg font-semibold mt-4")
        with ui.row().classes("gap-3 items-center flex-wrap"):
            ui.button(_t("生成值班表", "Generate Roster")).props("color=teal-7").classes("rounded-lg font-semibold")
            ui.button(_t("取消", "Cancel")).props("outline color=teal-7").classes("rounded-lg font-semibold")
            ui.button(_t("刪除", "Delete")).props("color=red-6").classes("rounded-lg font-semibold")



# =============================================================================
# Entry point
# =============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    # ---- Initialize logging + request ID tracking ----
    setup_logging(level=logging.INFO)
    logger = get_logger("app")
    logger.info("Sing Yin Study Prefect Roster System starting...")
    logger.info("Logging system initialized. Writing logs to logs/app.log")
    app.add_middleware(RequestIDMiddleware)

    # Register sys.excepthook for exceptions outside request handling
    import sys
    def _global_excepthook(exc_type, exc_value, exc_tb):
        import traceback
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"Unhandled exception outside request context:\n{tb_str}")
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _global_excepthook

    secret = os.getenv("STORAGE_SECRET", "dev-secret-sing-yin-roster-2026")
    ui.run(
        title="Sing Yin Study Prefect Roster",
        favicon="\U0001F4CB",
        dark=None,
        reload=False,
        show=True,
        port=8080,
        storage_secret=secret,
    )
