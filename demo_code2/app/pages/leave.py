"""
Leave Adjustment page. Post-publication leave handling with substitute
recommendations. Integrates LeaveAdjustmentService for real operations.
"""
from nicegui import ui
from theme import apply_theme
from components.layout import page_layout
from services.leave_service import LeaveAdjustmentService
from models.enums import Weekday, Room
from utils.data import load_prefects, sample_prefects
from i18n.helpers import t as _t


def _get_prefect_names():
    """Return dict mapping Chinese display name -> English backend name."""
    rows = load_prefects() or sample_prefects()
    result = {}
    for r in rows:
        en_name = r.get("name", "")
        zh_name = r.get("name_zh", "") or en_name
        if en_name and zh_name:
            result[zh_name] = en_name
    return dict(sorted(result.items()))


@ui.page("/leave")
def leave_page():
    apply_theme()
    page_layout()

    # Try to access current roster from shared state
    try:
        from pages.roster import _current_roster
    except ImportError:
        _current_roster = None

    with ui.column().classes("w-full max-w-5xl mx-auto px-6 py-6 gap-4"):
        ui.label(_t("請假调整", "Leave Adjustment")).classes("text-xl font-bold text-teal-700 dark:text-teal-300")
        ui.label(
            _t("處理发布后的請假申请，提供公平意识替补建议。", "Handle post-publication leave requests with fairness-aware replacement recommendations.")
        ).classes("text-sm text-slate-500 dark:text-slate-400")

        if _current_roster is None:
            with ui.card().classes("w-full rounded-xl shadow-sm dark:shadow-md p-6 text-center"):
                ui.icon("event_busy", size="48px").classes("text-slate-300 dark:text-slate-600 mb-3")
                ui.label(_t("没有值班表", "No roster available")).classes("text-lg text-slate-500 dark:text-slate-400")
                ui.label(
                    _t("请先在值班表页面生成值班表，然后回到这里进行請假调整。", "Generate a roster first on the Roster page, then return here to apply leave adjustments.")
                ).classes("text-sm text-slate-400 dark:text-slate-500 mt-1")
                ui.button(_t("前往值班表", "Go to Roster"), icon="arrow_forward", on_click=lambda: ui.navigate.to("/roster")).props(
                    "color=teal-7"
                ).classes("rounded-lg mt-3")
            return

        ui.separator()

        prefects_map = _get_prefect_names()
        svc = LeaveAdjustmentService(
            prefects=[{"name": en, "history_weight": 0, "available": list(Weekday)} for en in prefects_map.values()]
        )

        # Step 1: Select prefect
        ui.label(_t("步骤1：選擇請假風紀", "Step 1: Select Prefect on Leave")).classes("text-lg font-semibold mt-2")
        with ui.row().classes("gap-4 items-end"):
            prefect_sel = ui.select(label=_t("風紀姓名", "Prefect Name"), options=prefects_map, with_input=True).classes(
                "w-64"
            ).props("outlined color=teal-7")
            find_btn = ui.button(_t("查找分配", "Find Assignments"), icon="search")

        result_area = ui.column().classes("w-full mt-4")

        def _do_find():
            result_area.clear()
            name = prefect_sel.value
            if not name:
                ui.notify("Please select a prefect first.", type="warning")
                return
            affected = svc.find_affected_assignments(_current_roster, name)
            if not affected:
                with result_area:
                    with ui.card().classes("w-full rounded-xl shadow-sm dark:shadow-md p-5"):
                        ui.label(name + " has no assignments in the current roster.").classes(
                            "text-slate-500 dark:text-slate-400"
                        )
                return
            with result_area:
                ui.label(_t("找到 ", "Found ") + str(len(affected)) + " assignment(s):").classes(
                    "text-sm font-semibold text-teal-700 dark:text-teal-300 mb-2"
                )
                for a in affected:
                    day = a["day"]
                    room = a["room"]
                    slot = a["slot_idx"]
                    with ui.card().classes("w-full rounded-xl shadow-sm dark:shadow-md p-4 mb-2"):
                        with ui.row().classes("items-center gap-4"):
                            ui.label(day.name + " - " + room.name + " (slot " + str(slot) + ")").classes(
                                "font-semibold text-slate-700 dark:text-slate-300"
                            )
                            # Get replacement candidates
                            exclude = {name}
                            candidates = svc.get_replacement_with_day_check(
                                _current_roster, day, room, exclude
                            )
                            cand_names = [c["name"] for c in candidates] if candidates else ["[ON LEAVE]"]
                            rep_sel = ui.select(
                                label="Replacement", options=cand_names, value=cand_names[0], with_input=True
                            ).classes("w-48").props("outlined color=teal-7 dense")

                            def make_apply(d=day, r=room, s=slot, rs=rep_sel, n=name):
                                def _apply():
                                    repl = rs.value
                                    if repl == "[ON LEAVE]":
                                        repl = None
                                    w = 1.0  # Room 302 weight
                                    if r in (Room.ROOM_303, Room.ROOM_202):
                                        w = 1.5
                                    msg = svc.apply_adjustment(_current_roster, n, d, r, s, repl, w)
                                    ui.notify(msg, type="positive" if "Replaced" in msg else "warning")
                                    _do_find()
                                return _apply

                            ui.button(_t("應用", "Apply"), icon="check", on_click=make_apply()).props(
                                "color=teal-7 size=sm"
                            ).classes("rounded-lg")

        find_btn.on_click(_do_find)
