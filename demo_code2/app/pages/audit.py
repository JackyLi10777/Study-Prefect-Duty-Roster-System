"""
Audit Log page. View recent system actions with timestamps.
"""
from datetime import datetime
from nicegui import ui
from theme import apply_theme
from components.layout import page_layout
from utils.audit import get_recent
from i18n.helpers import t as _t


@ui.page("/audit")
def audit_page():
    apply_theme()
    page_layout()
    with ui.column().classes("w-full max-w-5xl mx-auto px-6 py-6 gap-4"):
        ui.label(_t("審計日誌", "Audit Log")).classes("text-xl font-bold text-teal-700 dark:text-teal-300")
        ui.label(_t("追蹤系統操作：值班表生成、請假調整、數據導入。", _t("追蹤系統操作：值班表生成、請假調整、數據匯入。", "Track system actions: roster generation, leave adjustment, data imports."))).classes(
            "text-sm text-slate-500 dark:text-slate-400"
        )

        try:
            entries = get_recent(50)
        except Exception:
            entries = []

        if not entries:
            with ui.card().classes("w-full rounded-xl shadow-sm dark:shadow-md p-8 text-center"):
                ui.icon("history", size="48px").classes("text-slate-300 dark:text-slate-600 mb-3")
                ui.label(_t("暫無審計記錄", _t("暫無審計記錄", "No audit records yet"))).classes("text-lg text-slate-400 dark:text-slate-500")
                ui.label(
                    _t("值班表生成、請假調整等操作後記錄會自動出現。", _t("值班表生成、請假調整等操作後記錄會自動出現。", "Records appear automatically after roster generation, leave adjustments, etc."))
                ).classes("text-sm text-slate-400 dark:text-slate-500 mt-1")
            return

        columns = [
            {"name": "time", "label": _t("時間", "Time"), "field": "time", "align": "left", "sortable": True},
            {"name": "action", "label": _t("操作", "Action"), "field": "action", "align": "left"},
            {"name": "detail", "label": _t("詳情", "Detail"), "field": "detail", "align": "left"},
        ]
        rows = []
        for e in entries:
            ts = e.get("timestamp", "")
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            rows.append({
                "time": str(ts),
                "action": str(e.get("action", "")),
                "detail": str(e.get("detail", ""))[:100],
            })

        ui.table(
            columns=columns, rows=rows, row_key="time",
            pagination={"rowsPerPage": 20}
        ).classes("w-full rounded-lg")
