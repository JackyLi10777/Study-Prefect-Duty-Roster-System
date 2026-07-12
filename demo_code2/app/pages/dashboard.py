"""
Dashboard — The central landing page for the 首席導學風紀.

Two distinct visual zones:
1. Sacred Scripture Zone  — warm, reverent, set apart visually (~40% height)
2. Operational Dashboard   — professional Teal design system (~60% height)
"""

from datetime import date, datetime
from pathlib import Path
from nicegui import ui, app

from theme import apply_theme, TealTheme, Type, toggle_theme, get_theme
from components.header import create_header
from components.sidebar import create_sidebar
from components.kpi_card import KpiCard
from utils.i18n import is_zh
from utils.data import load_prefects, sample_prefects
from models.enums import Role, Form, Weekday

theme = TealTheme()

# =============================================================================
# Daily Scripture Verses — curated for servant leadership
# =============================================================================

# 500-verse daily scripture bank (with 31-verse fallback)
try:
    from data.daily_verses import get_daily_verse_ui
    _has_500_verses = True
except ImportError:
    _has_500_verses = False
    get_daily_verse_ui = None

# Fallback 7-verse list (used when daily_verses.py is unavailable)
FALLBACK_VERSES = [
    {"ref": "Mark 10:43-45", "ref_zh": "???? 10:43-45", "text": "Whoever wants to become great among you must be your servant...", "text_zh": "????????????????????????????????"},
    {"ref": "Philippians 2:3-4", "ref_zh": "???? 2:3-4", "text": "Do nothing out of selfish ambition or vain conceit.", "text_zh": "????????????????????????"},
    {"ref": "Colossians 3:23", "ref_zh": "???? 3:23", "text": "Whatever you do, work at it with all your heart.", "text_zh": "????????????????????"},
    {"ref": "Isaiah 40:31", "ref_zh": "???? 40:31", "text": "Those who hope in the Lord will renew their strength.", "text_zh": "??????????????"},
    {"ref": "Matthew 5:16", "ref_zh": "???? 5:16", "text": "Let your light shine before others.", "text_zh": "?????????????"},
    {"ref": "Psalm 37:5", "ref_zh": "?? 37:5", "text": "Commit your way to the Lord; trust in him.", "text_zh": "????????????????"},
    {"ref": "Joshua 1:9", "ref_zh": "???? 1:9", "text": "Be strong and courageous. Do not be afraid.", "text_zh": "????????????"},
]



def _today_verse():
    """Return verse from 500-verse bank, or fallback to embedded list."""
    if _has_500_verses and get_daily_verse_ui:
        try:
            return get_daily_verse_ui()
        except Exception:
            pass
    # Fallback
    day_of_year = datetime.now().timetuple().tm_yday
    return FALLBACK_VERSES[day_of_year % len(FALLBACK_VERSES)]


# =============================================================================
# Sacred Scripture Section CSS
# =============================================================================

SCRIPTURE_CSS = """
<style>
    .scripture-zone {
        background: linear-gradient(
            180deg,
            #FDF8F0 0%,
            #F9F2E3 40%,
            #F7F6F3 100%
        );
        border: 2px solid #D4AF37;
        border-left: 6px solid #D4AF37;
        border-radius: 16px;
        padding: 36px 32px 28px 32px;
        margin-bottom: 24px;
        position: relative;
    }
    .scripture-zone::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(
            90deg,
            transparent 0%,
            #D4AF37 20%,
            #D4AF37 80%,
            transparent 100%
        );
        border-radius: 2px;
    }
    .scripture-ref {
        font-family: "Georgia", "Noto Serif TC", "Times New Roman", serif;
        font-size: 12px;
        font-weight: 400;
        color: #A68B3D;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .scripture-text {
        font-family: "Georgia", "Noto Serif TC", "Times New Roman", serif;
        font-size: 18px;
        font-weight: 400;
        color: #4A3728;
        line-height: 1.9;
        letter-spacing: 0.3px;
        margin-bottom: 12px;
        max-width: 720px;
    }
    .scripture-divider {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 20px 0;
        color: #C4A44A;
        font-size: 10px;
    }
    .scripture-divider::before,
    .scripture-divider::after {
        content: "";
        flex: 1;
        height: 1px;
        background: linear-gradient(
            90deg,
            transparent,
            #D4AF37,
            transparent
        );
    }
    .scripture-reflection {
        font-family: "Georgia", "Noto Serif TC", serif;
        font-size: 13px;
        color: #7B6914;
        font-style: italic;
        line-height: 1.7;
        max-width: 580px;
    }

    /* Dark mode */
    body.dark .scripture-zone {
        background: linear-gradient(
            180deg,
            #1E1B15 0%,
            #1A1812 40%,
            #0F172A 100%
        );
        border-color: #8B7332;
        border-left-color: #8B7332;
    }
    body.dark .scripture-text {
        color: #E8DCC8;
    }
    body.dark .scripture-ref {
        color: #B8972E;
    }
    body.dark .scripture-reflection {
        color: #C4B078;
    }
</style>
"""


# =============================================================================
# Dashboard Page
# =============================================================================

@ui.page("/")
def dashboard_page():
    """Main dashboard — Sacred Scripture + Operational Overview."""
    apply_theme()
    create_header()
    create_sidebar()
    ui.add_head_html(SCRIPTURE_CSS)
    from i18n.helpers import t as _t
    ui.label(_t("每日金句、系統状态、KPI概覧、備份与還原", "Daily scripture, system status, KPI overview, backup & restore.")).classes("text-sm text-slate-500 dark:text-slate-400 mb-4")

    # ---- System Status Indicators ----
    with ui.row().classes("gap-3 mb-2 px-1 items-center opacity-100"):
        from utils.sheets import status_detail as sheets_status
        from services.ai_parser import status_detail as ai_status
        sheets = sheets_status()
        ai = ai_status()
        s_class = sheets["level"]
        s_text = sheets["label"]
        a_class = ai["level"]
        a_text = ai["label"]
        with ui.element("div").classes("flex items-center gap-1 text-xs"):
            ui.element("span").classes("status-dot " + s_class)
            ui.label(s_text).classes("text-slate-500 dark:text-slate-400")
            if sheets["detail"]:
                ui.tooltip(sheets["detail"] + " | " + sheets["action"])
        with ui.element("div").classes("flex items-center gap-1 text-xs"):
            ui.element("span").classes("status-dot " + a_class)
            ui.label(a_text).classes("text-slate-500 dark:text-slate-400")
            if ai["detail"]:
                ui.tooltip(ai["detail"] + " | " + ai["action"])

    # ---- Logo Settings ----
        show_logo = app.storage.user.get("show_logo", True)
        def _toggle_logo():
            app.storage.user["show_logo"] = not app.storage.user.get("show_logo", True)
        with ui.row().classes("gap-4 mb-2 px-1 items-center"):
            ui.switch("Show Logo on PDF", value=show_logo, on_change=_toggle_logo).props("color=teal-7")
            ui.label(_t("使用項目資料夾中的 logo.png", _t("使用項目資料夾中的 logo.png", "Uses logo.png from project folder"))).classes("text-xs text-slate-400")

        # ---- Load data ----
    rows = load_prefects()
    if not rows:
        rows = sample_prefects()
    # Build simple stats without importing Prefect (avoid dataclass dependency)
    total = len(rows)
    active_count = sum(1 for r in rows if r.get("active", True))
    ahp_count = sum(
        1 for r in rows
        if r.get("active", True)
        and (r.get("role") == Role.ASSISTANT_HEAD_PREFECT
             or str(r.get("role", "")) == "ASSISTANT_HEAD_PREFECT")
    )
    sp_count = sum(
        1 for r in rows
        if r.get("active", True)
        and (r.get("role") == Role.STUDY_PREFECT
             or str(r.get("role", "")) == "STUDY_PREFECT")
    )
    avg_load = sum(float(r.get("history_weight", 0)) for r in rows) / max(active_count, 1)

    # ---- Welcome Banner (first-time users, no prefect data) ----
    if len(rows) == 0:
        with ui.element("div").classes(
            "w-full bg-teal-50 dark:bg-teal-900/30 border-l-4 border-teal-500 dark:border-teal-400 p-4 mb-4 rounded-r-lg"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("waving_hand").classes("text-teal-600 text-2xl")
                with ui.column().classes("gap-1"):
                    ui.label(_t("歡迎使用風紀值班表系統！", "Welcome to the Study Prefect Duty Roster!")).classes(
                        "text-body font-semibold text-teal-800 dark:text-teal-200")
                    ui.label(_t("請前往風紀管理頁面加載示範數據以開始使用。", "To get started, go to the Prefects page and load the sample data.")).classes(
                        "text-body-sm text-teal-700 dark:text-teal-300")
                ui.button(_t("前往風紀管理", "Go to Prefects"), on_click=lambda: ui.navigate.to("/prefects"))                         .props("color=teal-7 size=sm").classes("rounded-[14px]")

    # ---- Daily Verse ----
    verse = _today_verse()
    weekday_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    today_str = f"{date.today().strftime('%Y年%m月%d日')} {weekday_zh[date.today().weekday()]}"

    with ui.column().classes("w-full max-w-7xl mx-auto px-6 py-6 gap-4"):

    # =====================================================================
    # ZONE 1: Sacred Scripture — warm, set apart, reverent
        # =====================================================================

        with ui.element("div").classes("scripture-zone"):
            ui.label(today_str).classes("scripture-ref")
            if is_zh():
                ui.label(verse.get("ref_zh", verse.get("ref", ""))).classes("scripture-ref")
                ui.label(verse.get("text_zh", verse.get("text", ""))).classes("scripture-text")
            else:
                ui.label(verse.get("ref", verse.get("ref_zh", ""))).classes("scripture-ref")
                ui.label(verse.get("text", verse.get("text_zh", ""))).classes("scripture-text")

            with ui.element("div").classes("scripture-divider"):
                ui.label(_t("✦  每日金句  ✦", "✦  Daily Scripture  ✦"))

                        # Brief reflection
            en_reflections = [
                "Today in your busy duty work, remember you are working for God, not for men.",
                "True leaders first become servants. How will you serve your team today?",
                "When you feel weary, look to God; He will give you new strength.",
                "In every small responsibility, live out your faith; your faithfulness will be seen.",
                "Whatever challenge you face today, know your labor in the Lord is not in vain.",
                "Entrust today's duties to God; He will guide your steps.",
                "In the tension between study and duty, let God''s Word be your strength.",
            ]

            reflections = [
                "今天在忙碌的值班工作中，記得你是為上帝而做，不是為人而做。",
                "真正的領袖是先成為僕人。今天你要如何服事你的團隊？",
                "當你感到疲憊時，仰望上帝，祂必賜你新的力量。",
                "在每一個微小的責任中活出信仰，你的忠心會被看見。",
                "今天不論遇到什麼挑戰，記住你的勞苦在主裡不是徒然的。",
                "將今天的值班交託給上帝，祂必引導你的腳步。",
                "在學業與職責的壓力中，讓上帝的話語成為你的力量。",
            ]
            reflection = reflections[date.today().weekday()] if is_zh() else en_reflections[date.today().weekday()]
            ui.label(f"「{reflection}」").classes("scripture-reflection")

        # =====================================================================
        # ZONE 2: Operational Dashboard — Professional Teal
        # =====================================================================

        ui.label(_t("營運概覧", "Operational Overview")).classes(Type.H2 + " text-slate-800 dark:text-slate-100 mb-2")

        # ---- KPI Cards ----
        with ui.row().classes("gap-4 w-full flex-wrap dark:text-slate-100"):
            KpiCard(str(active_count), _t("活躍風紀", "Active Prefects"), gradient=True)
            KpiCard(str(ahp_count), "AHPs", gradient=True)
            KpiCard(str(sp_count), _t("學習風紀", "Study Prefects"))
            KpiCard(f"{avg_load:.1f}", _t("平均負荷 (分)", "Avg Load (pts)"))

        # ---- Data Health: Gentle Drift Detection (Regenerative) ----
    health_issues = []
    name_zh_missing = [r for r in rows if r.get("active", True) and not r.get("name_zh", "").strip()]
    if name_zh_missing:
        health_issues.append(f"{len(name_zh_missing)} prefect(s) missing Chinese name")
    names_list = [r.get("name", "") for r in rows]
    duplicates = [n for n in names_list if names_list.count(n) > 1]
    if duplicates:
        health_issues.append(f"Duplicate name(s): {', '.join(set(duplicates))}")
    no_available = [r for r in rows if r.get("active", True) and not r.get("available", [])]
    if no_available:
        health_issues.append(f"{len(no_available)} prefect(s) with no available days")

    if health_issues:
        with ui.element("div").classes(
            "w-full bg-amber-50/70 dark:bg-amber-900/20 border-l-4 border-amber-300 dark:border-amber-500 p-3 mb-4 rounded-r-lg opacity-90"
        ):
            with ui.row().classes("items-start gap-2"):
                ui.icon("info").classes("text-amber-500 text-sm mt-0.5")
                with ui.column().classes("gap-1"):
                    ui.label(_t("數據健康提示", "Data Health Notes")).classes("text-xs font-medium text-amber-700 dark:text-amber-300")
                    for issue in health_issues:
                        ui.label(f"· {issue}").classes("text-xs text-amber-600 dark:text-amber-400")
                    ui.label(_t("這些是溫馨提示——系統仍可正常運作，但修復它們能提升值班表品質。", _t("這些是溫馨提示－－系統仍可正常運作，但修復它們能提升值班表品質。", "These are gentle reminders -- the system will work fine, but fixing them improves roster quality."))).classes("text-xs text-amber-500/70 dark:text-amber-500/50 mt-1 italic")
                    ui.label("• Fix: Go to Prefects page, edit each prefect to add Chinese names.").classes("text-xs text-amber-500/80 dark:text-amber-500/60")

    # ---- Quick Actions ----

    ui.label(_t("快速操作", "Quick Actions")).classes("text-lg font-semibold mt-4 mb-2")
    with ui.row().classes("gap-4 w-full flex-wrap dark:text-slate-100"):
        with ui.card().classes("flex-1 min-w-[200px] rounded-xl shadow-sm dark:shadow-md p-5 dark:bg-slate-800"):
            ui.icon("people", size="28px").classes("text-teal-600 dark:text-teal-400 mb-2")
            ui.label(_t("管理風紀", _t("管理風紀", "Manage Prefects"))).classes("text-base font-semibold text-slate-700 dark:text-slate-300")
            ui.label(_t("添加、匯入或編輭風紀數擾", "Add, import, or edit prefect data")).classes("text-xs text-slate-500 dark:text-slate-400 mt-1")
            ui.button(_t("前往風紀管理", "Open Prefects"), icon="arrow_forward", on_click=lambda: ui.navigate.to("/prefects")).props("flat color=teal-7 size=sm").classes("mt-2")
        with ui.card().classes("flex-1 min-w-[200px] rounded-xl shadow-sm dark:shadow-md p-5 dark:bg-slate-800"):
            ui.icon("grid_view", size="28px").classes("text-teal-600 dark:text-teal-400 mb-2")
            ui.label(_t("生成值班表", "Generate Roster")).classes("text-base font-semibold text-slate-700 dark:text-slate-300")
            ui.label(_t("建立本周值班安排", "Create this week duty assignments")).classes("text-xs text-slate-500 dark:text-slate-400 mt-1")
            ui.button(_t("前往值班表", "Open Roster"), icon="arrow_forward", on_click=lambda: ui.navigate.to("/roster")).props("flat color=teal-7 size=sm").classes("mt-2")
        with ui.card().classes("flex-1 min-w-[200px] rounded-xl shadow-sm dark:shadow-md p-5 dark:bg-slate-800"):
            ui.icon("event_busy", size="28px").classes("text-teal-600 dark:text-teal-400 mb-2")
            ui.label(_t("請假调整", _t("請假調整", "Adjust Leave"))).classes("text-base font-semibold text-slate-700 dark:text-slate-300")
            ui.label(_t("處理发布后的請假申请", "Handle post-publication leave requests")).classes("text-xs text-slate-500 dark:text-slate-400 mt-1")
            ui.button(_t("前往請假", "Open Leave"), icon="arrow_forward", on_click=lambda: ui.navigate.to("/leave")).props("flat color=teal-7 size=sm").classes("mt-2")

        # ---- Fairness Chart ----
        if active_count > 1:
            names = [r.get("name_zh", "") or r.get("name", "?") for r in rows if r.get("active", True)]
            loads = [float(r.get("history_weight", 0)) for r in rows if r.get("active", True)]
            pair = sorted(zip(loads, names))
            sorted_loads = [p[0] for p in pair]
            sorted_names = [p[1] for p in pair]
            ui.echart({
                "title": {"text": _t("負荷分佈", "Load Distribution"), "left": "center", "textStyle": {"fontSize": 14}},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "value", "name": "pts"},
                "yAxis": {"type": "category", "data": sorted_names, "inverse": True},
                "series": [{"data": sorted_loads, "type": "bar",
                    "itemStyle": {"color": "#0F766E", "borderRadius": [0, 4, 4, 0]},
                    "barWidth": "60%"}],
                "grid": {"top": 30, "right": 20, "bottom": 20, "left": 120},
            }).classes("w-full h-64 mt-2")

        # ---- Backup Reminder ----
        from utils.audit import get_log
        gen_count = sum(1 for e in get_log() if e.get("action") == "roster_generate")
        backup_count = sum(1 for e in get_log() if "backup" in e.get("action", "").lower())
        if gen_count > backup_count + 2:
            with ui.element("div").classes(
                "w-full bg-amber-50 dark:bg-amber-900/30 border-l-4 border-amber-400 dark:border-amber-500 p-4 mb-2 rounded-r-lg"
            ):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("warning").classes("text-amber-600")
                    ui.label(
                        f"Backup reminder: {gen_count} roster(s) generated since last backup. "
                        "Download a JSON backup to protect your data."
                    ).classes("text-body-sm text-amber-800 dark:text-amber-200 flex-1")
                    ui.button(_t("立即備份", "Backup Now"), on_click=_do_backup)                         .props("color=amber-7 size=sm").classes("rounded-[14px]")

        # ---- Mentoring Pairs ----
        from services.mentoring import get_pairing_stats
        mentor_prefects = []
        for r in rows:
            try:
                from models.prefect import Prefect
                mentor_prefects.append(Prefect(name=r.get("name",""), form=r.get("form","F4"),
                    class_name=r.get("class_name",""), role=r.get("role","STUDY_PREFECT"),
                    available=r.get("available",[]), history_weight=float(r.get("history_weight",0)),
                    active=r.get("active",True)))
            except Exception as e:
                try:
                    from utils.audit import log_action
                    log_action("dashboard_prefect_parse", str(e)[:200])
                except Exception: pass
        if mentor_prefects:
            try:
                svc = RosterService(prefects=mentor_prefects)
                roster = svc.generate_weekly_roster(week_start=date(2026,6,22))
                stats = get_pairing_stats(roster, mentor_prefects)
                if stats["possible"] > 0:
                    pct_val = stats["pct"]
                    pct_color = "text-emerald-600" if pct_val >= 50 else "text-amber-600" if pct_val >= 25 else "text-red-500"
                    with ui.card().classes("w-full rounded-[20px] shadow-sm dark:shadow-md p-6 dark:bg-slate-800"):
                        with ui.row().classes("items-center justify-between"):
                            ui.label(_t("師徒配對", "Mentoring Pairs")).classes("text-h3")
                            ui.label("{} / {} ({} pct)".format(stats["actual"], stats["possible"], stats["pct"]))                                 .classes("text-lg font-bold " + pct_color)
                        for pair in stats["pairs"][:6]:
                            day_name = pair["day"].name if hasattr(pair["day"], "name") else str(pair["day"])
                            room_name = pair["room"].name if hasattr(pair["room"], "name") else str(pair["room"])
                            ui.label(
                                "{} {}: {} (mentor) + {} (mentee)".format(
                                    day_name, room_name, pair["mentor"], pair["mentee"])
                            ).classes("text-body-sm text-slate-600 dark:text-slate-400")
            except Exception:
                pass

        # ---- Quick Actions ----
        ui.label(_t("快速操作", "Quick Actions")).classes(Type.H2 + " text-slate-800 dark:text-slate-100 mt-4 mb-2")

        with ui.row().classes("gap-3 flex-wrap"):
            ui.button(_t("生成值班表", "Generate Roster"), icon="calendar_month") \
                .props("color=teal-7").classes("rounded-[14px] font-semibold") \
                .on_click(lambda: ui.navigate.to("/roster"))
            ui.button(_t("管理風紀", "Manage Prefects"), icon="people") \
                .props("outline color=teal-7").classes("rounded-[14px] font-semibold") \
                .on_click(lambda: ui.navigate.to("/prefects"))
            ui.button(_t("審計日誌", "View Audit Log"), icon="history") \
                .props("outline color=teal-7").classes("rounded-[14px] font-semibold")

        # ---- Scripture Zone Quick Access ----

        # ---- System: Backup / Restore ----
        ui.label(_t("系統", "System")).classes(Type.H2 + " text-slate-800 dark:text-slate-100 mt-6 mb-2")

        with ui.row().classes("gap-3 flex-wrap"):
            def _do_backup():
                from utils.backup import export_backup
                from utils.audit import get_log
                json_str = export_backup(prefects=rows, audit_log=get_log())
                filename = f"singyin_backup_{date.today().strftime('%Y%m%d')}.json"
                ui.download(json_str.encode("utf-8"), filename)
                ui.notify("Backup downloaded.", type="positive", position="top")

            ui.button(_t("備份系統", "Backup System"), icon="backup", on_click=_do_backup) \
                .props("color=teal-7").classes("rounded-[14px] font-semibold")

            # Restore via file upload dialog
            with ui.dialog() as restore_dialog, ui.card().classes("rounded-xl p-6 max-w-lg"):
                ui.label(_t("從備份還原", "Restore from Backup")).classes(Type.H2 + " mb-3")
                ui.label("Upload a .json backup file previously exported by this system.") \
                    .classes("text-body text-secondary mb-4")
                restore_upload = ui.upload(
                    label="Choose backup file (.json)",
                    auto_upload=True,
                    on_upload=lambda e: _handle_upload(e),
                ).props("accept=.json").classes("w-full mb-4")
                ui.label("After uploading, review the backup details below before applying.") \
                    .classes("text-body-sm text-slate-400")
            ui.button(_t("從備份還原", "Restore from Backup"), icon="restore", on_click=restore_dialog.open) \
                .props("outline color=teal-7").classes("rounded-[14px] font-semibold")

        # ---- Audit Log ----
        with ui.expansion(_t("審計日誌（最近變更）", "Audit Log (Recent Changes)"), icon="history").classes("w-full mt-2"):
            from utils.audit import get_recent
            log_entries = get_recent(15)
            if log_entries:
                for entry in log_entries:
                    ts = entry["timestamp"][:19].replace("T", " ")
                    action = entry["action"]
                    details = entry["details"]
                    affected = ", ".join(entry.get("affected", []))
                    ui.label(f"[{ts}] {action} ? {details}").classes("text-body-sm text-slate-600 dark:text-slate-400")
                    if affected:
                        ui.label(f"  Affected: {affected}").classes("text-body-sm text-slate-500 ml-4")
            else:
                ui.label(_t("暫無審計記錄", "No audit entries yet.")).classes("text-body-sm text-slate-400")

        


@ui.page("/dashboard")
def dashboard_alias():
    """Alias for the dashboard."""
    ui.navigate.to("/")


def _handle_upload(e):
    """Handle backup file upload."""
    from utils.backup import import_backup, import_safe, restore_state, restore_audit_log
    from utils.data import save_prefects
    try:
        content = e.content.read().decode("utf-8")
        data = import_backup(content)
        safe = import_safe(data, rows)
        if not safe["valid"]:
            ui.notify("Invalid backup file.", type="negative", position="top")
            return
        if safe.get("warnings"):
            for w in safe["warnings"]:
                ui.notify(w, type="warning", position="top")
        # Apply restore
        result = restore_state(data, rows)
        restore_audit_log(data)
        save_prefects(rows)
        ui.notify(
            f"Restored {result["updated"]} prefect load values "
            f"from backup ({safe["prefect_count"]} prefects in backup).",
            type="positive", position="top"
        )
        ui.navigate.to("/")
    except ValueError as ve:
        ui.notify(f"Invalid backup: {ve}", type="negative", position="top")
    except Exception as ex:
        ui.notify(f"Restore failed: {ex}", type="negative", position="top")
