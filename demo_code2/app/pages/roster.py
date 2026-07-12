"""
Main Roster Page for the Sing Yin Study Prefect Duty Roster System.
Displays weekly roster, KPI cards, generation, leave adjustment, export.
"""
from datetime import date, timedelta
import asyncio
from nicegui import ui

from theme import TealTheme, Type, apply_theme
from components.kpi_card import KpiCard
from components.header import create_header
from components.sidebar import create_sidebar
from i18n.helpers import t as _t
from components.kpi_card import KpiCard
from services.roster_service import RosterService
from components.loading import notify_success, notify_error
from services.fairness import FairnessService
from models.enums import Role, Form, Weekday, AHPAssignmentMode, Room
from models.prefect import Prefect
from models.roster import WeeklyRoster, DailyRoster, SchoolRules

_roster_filter = ""
theme = TealTheme()
_service = None
_prefects = None
_current_roster = None
_generating = False

@ui.page("/roster")
def roster_page():
    """Main roster management page."""
    global _current_roster
    _current_roster = None  # Reset stale state
    apply_theme()
    create_header()
    create_sidebar()
    # KPI cards
    from utils.data import load_prefects, sample_prefects
    rows = load_prefects() or sample_prefects()
    total = len(rows)
    active = sum(1 for r in rows if r.get("active", True))
    active_pcts = sum(1 for r in rows if r.get("active", True) and str(r.get("role","")).startswith("STUDY"))
    active_ahp = sum(1 for r in rows if r.get("active", True) and "ASSISTANT" in str(r.get("role","")))
    avg_load = sum(float(r.get("history_weight",0)) for r in rows) / max(active, 1)
    with ui.row().classes("gap-4 w-full flex-wrap"):
        KpiCard(str(active), _t("活躍風紀", "Active Prefects"), gradient=True)
        KpiCard(str(active_ahp), "助理首席風紀", gradient=True)
        KpiCard(str(active_pcts), _t("學習風紀", "Study Prefects"))
        KpiCard(f"{avg_load:.1f}", _t("平均負荷 (分)", "Avg Load (pts)"))

    # Loading area (shown during generation)
    _loading_area = ui.element("div").classes("w-full flex items-center justify-center py-8")

    # Tab structure
    with ui.tabs().classes("w-full") as roster_tabs:
        tab_gen = ui.tab(_t("生成與檢視", "Generate and View"), icon="grid_view")
        tab_adj = ui.tab(_t("調整與編輯", "Adjust and Edit"), icon="edit")

    with ui.tab_panels(roster_tabs, value=tab_gen).classes("w-full"):
        with ui.tab_panel(tab_gen):

            # Generate controls
            with ui.card().classes("w-full rounded-[20px] shadow-sm p-6 dark:bg-slate-800"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(_t("值班表生成", "Roster Generation")).classes(Type.H3)
                    with ui.row().classes("gap-2"):
                        ui.button(_t("生成值班表", "Generate Roster"), on_click=lambda: _generate_handler()).props("color=teal-7").classes("rounded-[14px] font-semibold")
                        ui.button(_t("重置负荷", "Reset Loads"), on_click=_reset_loads).props("outline color=teal-7").classes("rounded-[14px] font-semibold")
                        ui.button(_t("匯出 PDF/HTML", "Export PDF/HTML"), icon="picture_as_pdf", on_click=lambda: _export_pdf()).props("outline color=teal-7").classes("rounded-[14px] font-semibold")

            # Workload multiplier
            with ui.row().classes("items-center gap-2 mt-2"):
                mult = _service.workload_multiplier if _service else 1.0
                ui.label(_t(f"工作量倍率: {mult:.1f}x — 較高值讓工作量較低的同學優先被分配", f"Workload Multiplier: {mult:.1f}x — higher values prioritize prefects with lower loads")).classes("text-body-sm text-slate-500")
                ui.slider(min=0.5, max=2.0, step=0.1, value=mult, on_change=lambda e: (setattr(_service, "workload_multiplier", e.value) if _service else None)).props("color=teal-7 label-always").classes("w-48")

            # Search filter
            global _roster_filter
            filter_input = ui.input(placeholder="搜尋風紀姓名 Search prefect by name...", on_change=lambda e: _rerender_roster()).classes("w-full max-w-md mt-2").props("outlined color=teal-7 clearable")

            # Vacancy counter
            vacancy_count = 0
            for day in Weekday:
                d = _current_roster.days.get(day) if _current_roster else None
                if d:
                    for room, names in d.room_assignments.items():
                        closed_days = getattr(room, "closed_days", [])
                        if day in closed_days:
                            continue
                        expected = 2 if room.name in ("ROOM_303", "ROOM_202") else 1
                        actual = sum(1 for n in names if n and n.strip() and n.strip() != "[ON LEAVE]")
                        if actual < expected:
                            vacancy_count += expected - actual
            if vacancy_count > 0:
                with ui.element("div").classes("w-full bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-400 p-2 rounded-r-lg mt-2"):
                    ui.label(str(vacancy_count) + " slot(s) unfilled").classes("text-body-sm text-amber-800 dark:text-amber-200")

            # Roster table (empty state when no roster)
            global _roster_container
            _roster_container = ui.element("div").classes("w-full mt-4")
            if _current_roster is None:
                with _roster_container:
                    with ui.element("div").classes("w-full text-center py-8"):
                        ui.icon("grid_view", size="64px").classes("text-slate-300 dark:text-slate-600 mb-4")
                        ui.label(_t("尚未生成值班表", "No Roster Generated Yet")).classes("text-lg font-semibold text-slate-500 dark:text-slate-400")
                        ui.label(_t("點擊上方「生成值班表」按鈕生成本週值班安排。", "Click Generate Roster above to create this week duty assignments.")).classes("text-sm text-slate-400 dark:text-slate-500 mt-1")
            else:
                with _roster_container:
                    _render_roster()
            with ui.tab_panel(tab_adj):
                # Leave Adjustment
                with ui.expansion(_t("請假调整", "Leave Adjustment"), icon="event_busy").classes("w-full"):
                    ui.label(_t("發布後如有風紀請假，可在此撤銷其分數並安排替補。", "Adjust leave after roster publication.")).classes("text-body text-secondary mb-3")
                    from services.leave_service import LeaveAdjustmentService
                    p_dicts = [{"name": p.name, "history_weight": p.history_weight, "available": [d.name for d in p.available]} for p in (_prefects_cache or [])]
                    leave_svc = LeaveAdjustmentService(prefects=p_dicts)
                    leave_prefect = ui.select(label=_t("選擇請假風紀", "Select Prefect on Leave"), options=leave_svc.get_available_prefects()).classes("w-full max-w-md mb-2").props("outlined color=teal-7")
                    day_options = {"Monday": "Monday", "Tuesday": "Tuesday", "Wednesday": "Wednesday", "Thursday": "Thursday", "Friday": "Friday"}
                    adj_day = ui.select(label=_t("日期", "Day"), options=day_options, value="Monday").classes("w-32 mb-2").props("outlined color=teal-7")
                    room_options = {"Room 302": "ROOM_302", "Room 303": "ROOM_303", "Room 202": "ROOM_202"}
                    adj_room = ui.select(label=_t("房間", "Room"), options=room_options, value="ROOM_302").classes("w-48 mb-2").props("outlined color=teal-7")
                    adj_slot = ui.number(_t("時段", "Slot"), value=1, min=1, max=2).classes("w-20 mb-2").props("outlined color=teal-7")
                    adj_replace = ui.select(label="Replacement (optional)", options=[""] + leave_svc.get_available_prefects(), value="").classes("w-full max-w-md mb-3").props("outlined color=teal-7")
                    def _apply_leave():
                        if not leave_prefect.value:
                            ui.notify("Select a prefect on leave, then choose a Day, Room, and Slot.", type="warning", position="top"); return
                        day_map = {"Monday":Weekday.MON,"Tuesday":Weekday.TUE,"Wednesday":Weekday.WED,"Thursday":Weekday.THU,"Friday":Weekday.FRI}
                        room_map = {"ROOM_302":Room.ROOM_302,"ROOM_303":Room.ROOM_303,"ROOM_202":Room.ROOM_202}
                        room_weights = {Room.ROOM_302:1.0,Room.ROOM_303:1.5,Room.ROOM_202:1.0}
                        from utils.backup import silent_backup
                        silent_backup(_prefects_cache if _prefects_cache else [], label="pre_leave_adj")
                        msg = leave_svc.apply_adjustment(_current_roster, leave_prefect.value, day_map[adj_day.value], room_map[adj_room.value], int(adj_slot.value)-1, adj_replace.value if adj_replace.value else None, room_weights[room_map[adj_room.value]])
                        ui.notify(msg, type="positive", position="top")
                        _rerender_roster()
                        try:
                            daily = _current_roster.days.get(day_map[adj_day.value])
                            if daily:
                                assigned = daily.room_assignments.get(room_map[adj_room.value], [])
                                if adj_replace.value and adj_replace.value not in assigned:
                                    ui.notify("Adjustment applied but slot may need review.", type="info", position="top", timeout=3000)
                        except Exception:
                            pass
                ui.button(_t("\u78ba\u8a8d\u4e26\u61c9\u7528\u8abf\u6574", "Confirm & Apply Adjustment"), on_click=_apply_leave).props("color=amber-7").classes("rounded-[14px] font-semibold mt-2")

            # Manual Edit / Substitute
            with ui.expansion(_t("手动編輭 / 替补", "Manual Edit / Substitute"), icon="swap_horiz").classes("w-full mt-2"):
                ui.label("選擇日期、房間、時段，查看現在值班人並找尋替換。系統會按公平性插少替補建議。Select Day/Room/Slot to swap prefects.").classes("text-body text-secondary mb-3")
                e_dicts = [{"name": p.name, "history_weight": p.history_weight, "available": [d.name for d in p.available]} for p in (_prefects_cache or [])]
                edit_svc = LeaveAdjustmentService(prefects=e_dicts)
                ed_day = ui.select(label="Day", options=day_options, value="Monday").classes("w-32 mb-2").props("outlined color=teal-7")
                ed_room = ui.select(label="Room", options=room_options, value="ROOM_302").classes("w-48 mb-2").props("outlined color=teal-7")
                ed_slot = ui.number("Slot", value=1, min=1, max=2).classes("w-20 mb-2").props("outlined color=teal-7")
                def _show_current():
                    day = {"Monday":Weekday.MON,"Tuesday":Weekday.TUE,"Wednesday":Weekday.WED,"Thursday":Weekday.THU,"Friday":Weekday.FRI}[ed_day.value]
                    room = {"ROOM_302":Room.ROOM_302,"ROOM_303":Room.ROOM_303,"ROOM_202":Room.ROOM_202}[ed_room.value]
                    slot = int(ed_slot.value) - 1
                    daily = _current_roster.days.get(day)
                    if not daily: ui.notify("No roster data for this day. Go to the Generate and View tab and click Generate Roster.", type="warning", position="top"); return
                    assigned = daily.room_assignments.get(room, [])
                    if slot >= len(assigned) or not assigned[slot].strip():
                        ui.notify("No prefect assigned to this slot. Try a different Day, Room, or Slot.", type="info", position="top"); return
                    current_name = assigned[slot]
                    ui.label(_t("當前: ", "Current: ") + current_name).classes("text-body text-teal-700 font-medium mt-1")
                ui.button(_t("檢查當前安排", _t("檢查當前安排", "Check Current Assignment")), on_click=_show_current).props("outline color=teal-7").classes("rounded-[14px] font-semibold")



    # ========== SERVICE SETUP ==========
_prefects_cache = None
_service_cache = None
_fairness_cache = None

def _get_service():
    global _service_cache, _prefects_cache, _service, _prefects
    if _service_cache is None:
        from utils.data import load_prefects, sample_prefects
        rows = load_prefects() or sample_prefects()
        prefects = []
        for r in rows:
            try: prefects.append(Prefect(name=r["name"], form=r["form"], class_name=r.get("class_name",""), role=r["role"], available=r.get("available",[]), history_weight=float(r.get("history_weight",0)), active=r.get("active",True)))
            except Exception: pass
        _prefects_cache = prefects
    _service_cache = RosterService(prefects=_prefects_cache if _prefects_cache else prefects)
    _service = _service_cache
    _prefects = _prefects_cache
    _load_demo_history(_service_cache)
    return _service_cache, _prefects_cache


def _load_demo_history(svc):
    import json
    from pathlib import Path
    from models.enums import Weekday, Room
    from models.roster import DailyRoster, WeeklyRoster
    from datetime import date
    demo_path = Path(__file__).resolve().parent.parent.parent / "data" / "demo_roster_history.json"
    if not demo_path.exists():
        return
    with open(demo_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        return
    room_map = {"room_302": Room.ROOM_302, "room_303": Room.ROOM_303, "room_202": Room.ROOM_202}
    weekday_map = {d.value.upper(): d for d in Weekday}
    weeks = {}
    for e in entries:
        ws = e["week_start"]
        if ws not in weeks:
            weeks[ws] = {}
        day_enum = weekday_map.get(e["day"].upper())
        if not day_enum:
            continue
        room_assignments = {}
        for json_key, room_enum in room_map.items():
            names = e.get(json_key, [])
            if names == ["closed"]:
                continue
            if names:
                room_assignments[room_enum] = names
        if room_assignments:
            weeks[ws][day_enum] = room_assignments
    for ws, days_dict in weeks.items():
        try:
            wr = WeeklyRoster(week_start=date.fromisoformat(ws))
        except ValueError:
            continue
        for day_enum, ra in days_dict.items():
            dr = wr.days.get(day_enum, DailyRoster(weekday=day_enum))
            dr.room_assignments = ra
            wr.days[day_enum] = dr
        svc._history.append(wr)


async def _generate_handler():
    """Generate roster with pre-validation, state checks, and debounce lock."""
    global _generating, _current_roster
    if _generating:
        ui.notify("Generation already in progress. Please wait.", type="warning", position="top")
        return
    svc, _ = _get_service()
    active = [p for p in svc.prefects if getattr(p, "active", True)]
    if len(active) < 3:
        ui.notify(f"Only {len(active)} active prefect(s). Go to the Prefects page to add more prefects, then return here.", type="warning", position="top")
        return
    monday = _next_monday()
    _generating = True
    _loading_area.clear()
    with _loading_area:
        ui.spinner(size="lg", type="bars").props("color=teal-7")
        ui.label(_t("正在生成值班表，請稍候...", "Generating roster, please wait...")).classes("text-sm text-slate-500 dark:text-slate-400 h-loading-text mt-2")
    await asyncio.sleep(0.05)
    try:
        roster = svc.generate_weekly_roster(week_start=monday)
        notify_success(f"Roster generated for week of {monday}")
        from services.versioning import save_version
        save_version(roster)
        try:
            from utils.backup import export_backup; from utils.audit import get_recent
            bu = export_backup(prefects=_prefects_cache, audit_log=get_recent(100))
            import os; os.makedirs("data/auto_backups", exist_ok=True)
            with open("data/auto_backups/roster_"+str(monday)+".json","w",encoding="utf-8") as bf: bf.write(bu)
            ui.notify("Auto-backup saved.", type="positive", position="top", timeout=2000)
        except Exception: pass
        _rerender_roster()
    except ValueError as e:
        _generating = False
        _loading_area.clear()
        if "No prefects" in str(e):
            ui.notify("Cannot generate: " + str(e), type="warning", position="top", timeout=8000)
        elif "less than 3" in str(e) or "Need at least" in str(e):
            ui.notify("Cannot generate: " + str(e), type="warning", position="top", timeout=8000)
        else:
            ui.notify(f"Generation failed: {{e}}", type="negative", position="top", timeout=8000)
        _generating = False


def _verify_state() -> bool:
    """Verify that all critical state variables are consistent. Returns True if healthy."""
    if _service is None:
        ui.notify("System not ready. Go to the Generate and View tab and click Generate Roster.", type="warning", position="top")
        return False
    if _current_roster is None:
        ui.notify("No roster generated. Click Generate Roster first.", type="warning", position="top")
        return False
    active = sum(1 for p in _service.prefects if getattr(p, "active", True))
    if active < 3:
        ui.notify(f"Only {active} active prefect(s). Go to the Prefects page to add more prefects.", type="warning", position="top")
        return False
    return True

def _reset_loads():
    svc, _ = _get_service()
    for p in svc.prefects: p.history_weight = 0.0
    ui.notify("All load points reset.", type="info", position="top")

def _next_monday():
    today = date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7)

def _display_roster_table():
    """Render the roster table with Chinese names."""
    global _current_roster, _prefects_cache
    roster = _current_roster
    if roster is None:
        return
    if not hasattr(roster, 'days'):
        _current_roster = None
        return
    from i18n.rules import prefect_display_name
    name_map = {}
    if _prefects_cache:
        for p in _prefects_cache:
            name_map[p.name] = getattr(p, 'name_zh', '') or p.name
    days = [Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI]
    rooms = [Room.ROOM_302, Room.ROOM_303, Room.ROOM_202]
    columns = [{'name': 'room', 'label': 'Room', 'field': 'room', 'align': 'left'}]
    for day in days:
        columns.append({'name': day.name, 'label': day.value, 'field': day.name, 'align': 'left'})
    rows_list = []
    for room in rooms:
        row = {'room': room.value}
        for day in days:
            daily = roster.days.get(day)
            # Check if room is closed on this day
            if day in room.closed_days:
                row[day.name] = '—'  # em dash for closed
                continue
            if daily and room in daily.room_assignments:
                names = daily.room_assignments[room]
                display = []
                for n in names:
                    if n and n.strip() and n.strip() != '[ON LEAVE]':
                        display.append(name_map.get(n, n))
                    elif n and '[ON LEAVE]' in n:
                        display.append('[ON LEAVE]')
                row[day.name] = ', '.join(display) if display else ''
            else:
                row[day.name] = ''
        rows_list.append(row)
    ui.table(columns=columns, rows=rows_list, row_key='room').classes('w-full rounded-lg overflow-hidden')
    return


def _rerender_roster():
    """Clear and re-render the roster table."""
    global _roster_container
    if _roster_container is not None:
        _roster_container.clear()
        with _roster_container:
            _display_roster_table()

def _export_pdf():
    """Export roster with state verification."""
    if not _verify_state():
        return
    svc, prefects = _get_service()
    try:
        roster = _current_roster  # Use current roster, not a fresh generation
        if roster is None:
            ui.notify("No roster to export. Go to the Generate and View tab and click Generate Roster first.", type="warning", position="top")
            return
    except: ui.notify("Generate a roster first.", type="warning"); return
    from utils.pdf import generate_roster_html
    html_bytes = generate_roster_html(roster, prefects)
    fn = "roster_" + str(roster.week_start) + ".html"
    ui.download(html_bytes, fn)
    ui.notify("Roster exported.", type="positive", position="top")