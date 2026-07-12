"""
Prefect Management Page for the Sing Yin Study Prefect Duty Roster System.

Provides full CRUD: list, add, edit, delete prefects.
Integrates with utils/data.py for CSV persistence.
"""

from datetime import date
from nicegui import ui, app

from models.enums import Role, Form, Weekday
from models.prefect import Prefect
from utils.data import load_prefects, save_prefects, sample_prefects, load_demo_data
from i18n.helpers import t as _t
from components.loading import show_skeleton

# =============================================================================
# Helpers
# =============================================================================

WEEKDAY_LABELS = {
    Weekday.MON: "Monday",
    Weekday.TUE: "Tuesday",
    Weekday.WED: "Wednesday",
    Weekday.THU: "Thursday",
    Weekday.FRI: "Friday",
}

ROLE_LABELS_ZH = {
    "Study Prefect": "學習風紀",
    "AHP (Asst. Head Prefect)": "助理首席風紀",
    "Head Study Prefect": "首席學習風紀",
}

ROLE_CHOICES = {
    "Study Prefect": Role.STUDY_PREFECT,
    "AHP (Asst. Head Prefect)": Role.ASSISTANT_HEAD_PREFECT,
    "Head Study Prefect": Role.HEAD_STUDY_PREFECT,
}

FORM_CHOICES = {
    "F.3": Form.F3,
    "F.4": Form.F4,
    "F.5": Form.F5,
}

def _prefects_from_rows(rows: list) -> list:
    """Convert CSV rows (dicts) to Prefect objects."""
    prefects = []
    for r in rows:
        try:
            p = Prefect(
                name=r["name"],
                name_zh=r.get("name_zh", ""),
                form=r["form"] if isinstance(r["form"], Form) else Form[r["form"]],
                class_name=r.get("class_name", ""),
                role=r["role"] if isinstance(r["role"], Role) else Role[r["role"]],
                available=r.get("available", []),
                history_weight=float(r.get("history_weight", 0)),
                remarks=r.get("remarks", ""),
                date_joined=r.get("date_joined", str(date.today())),
                active=r.get("active", True) if isinstance(r.get("active"), bool)
                       else str(r.get("active", "")).lower() == "true",
            )
            prefects.append(p)
        except Exception as e:
            ui.notify(f"Skipped invalid prefect: {r.get('name', '?')} — {e}", type="warning")
    return prefects

# =============================================================================
# Shared State (per-session)
# =============================================================================

@ui.page("/prefects")
def prefects_page():
    """Prefect management page with table + add/edit/delete."""
    from theme import apply_theme, TealTheme, Type
    from components.header import create_header
    from components.sidebar import create_sidebar
    from utils.i18n import is_zh
    apply_theme()
    create_header()
    create_sidebar()

    theme = TealTheme()

    # Load on first render
    rows = load_prefects()
    prefects = _prefects_from_rows(rows) if rows else _prefects_from_rows(sample_prefects())

    # Skeleton loading area for async data operations
    _skeleton_area = ui.element("div")

    with ui.column().classes("w-full max-w-7xl mx-auto px-6 py-8 gap-6"):
        # ---- Header ----
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(_t("風紀管理", "Prefect Management")).classes(Type.H1 + " text-slate-800 dark:text-slate-100")
            ui.label(_t("添加、編輭、匯入和管理所有風紀记录。", "Add, edit, import, and manage all study prefect records.")).classes("text-sm text-slate-500 dark:text-slate-400 mb-4")

            # ---- Quick Data Actions ----
            with ui.row().classes("gap-2 mb-4"):
                ui.button(_t("加載示範數據", "Load Demo Data"), icon="download", on_click=lambda: [save_prefects(load_demo_data()), _refresh_table(), ui.notify(_t("示範數據已加載（11 位風紀）。", "Demo data loaded (11 prefects)."), type="positive")]).props("color=amber-7").classes("rounded-[14px] font-semibold")
                ui.button(_t("導入CSV", "Import CSV"), icon="upload_file", on_click=lambda: ui.notify(_t("請使用下方的匯入功能。", "Use the import section below."), type="info")).props("outline color=teal-7").classes("rounded-[14px]")

            with ui.row().classes("gap-2"):
                # Add button triggers dialog
                add_btn = ui.button(_t("添加風紀", "Add Prefect"), icon="person_add") \
                    .props("color=teal-7").classes("rounded-[14px] font-semibold")

                # AI Parse Remarks button
                def _ai_parse():
                    from services.ai_parser import parse_all_remarks
                    ai_dialog.open()
                ai_btn = ui.button(_t("AI 解析備註", "AI Parse Remarks"), icon="auto_awesome",
                                    on_click=_ai_parse)                     .props("outline color=purple-7").classes("rounded-[14px] font-semibold")

                # Import CSV button
                import_btn = ui.button(_t("導入CSV", "Import CSV"), icon="upload_file",
                    on_click=lambda: import_dialog.open())                     .props("outline color=teal-7").classes("rounded-[14px] font-semibold")

        # ---- Import Two-Step Dialog ----
        STANDARD_FIELDS = {
            "name": {"en": "Name", "zh": "姓名"},
            "name_zh": {"en": _t("中文姓名", "Chinese Name"), "zh": "中文名"},
            "form": {"en": "Form", "zh": "年級"},
            "class_name": {"en": "Class", "zh": "班別"},
            "role": {"en": "Role", "zh": "職位"},
            "available": {"en": "Available Days", "zh": "可當值日"},
            "history_weight": {"en": "History Weight", "zh": "歷史權重"},
            "remarks": {"en": "Remarks", "zh": "備註"},
            "fixed_general_duty": {"en": "Fixed Duty", "zh": "固定值日"},
            "active": {"en": _t("活躍", "Active"), "zh": "活踍"},
        }
        _import_content = None
        _import_cols = None

        def _handle_upload(e):
            nonlocal _import_content, _import_cols
            try:
                content = e.content.read().decode("utf-8")
                _import_content = content
                from utils.importers import parse_csv, get_sample_rows, compute_mapping_with_confidence
                cols, rows = parse_csv(content)
                if not cols:
                    imp_status.set_text("⚠️ No columns detected in file.")
                    return
                _import_cols = cols
                sample = get_sample_rows(content, 8)
                mapping_entries = compute_mapping_with_confidence(cols, sample)

                imp_status.set_text(f"✅ Detected {len(cols)} columns. Review mapping below.")
                mapping_container.clear()
                with mapping_container:
                    ui.label("欄位對應預覽 (Column Mapping Preview):").classes("text-body font-semibold mb-2")
                    _mapping_selects = {}
                    with ui.row().classes("w-full text-caption text-slate-500 pb-1 border-b mb-1"):
                        ui.label("原始欄位").classes("w-40")
                        ui.label("對應標準欄位").classes("w-48")
                        ui.label("信心度").classes("w-20")
                    for entry in mapping_entries:
                        conf = entry["confidence"]
                        badge_color = "green" if conf == "ai" else "amber" if conf == "alias" else "slate"
                        badge_text = "AI" if conf == "ai" else "別名" if conf == "alias" else "未對應"
                        options = {"-- Skip --": None}
                        for k, v in STANDARD_FIELDS.items():
                            options[f"{v['zh']} ({v['en']})"] = k
                        default_val = f"{STANDARD_FIELDS[entry['target']]['zh']} ({STANDARD_FIELDS[entry['target']]['en']})" if entry["target"] and entry["target"] in STANDARD_FIELDS else "-- Skip --"
                        with ui.row().classes("w-full items-center mb-1"):
                            ui.label(entry["source_col"]).classes("w-40 text-body-sm")
                            sel = ui.select(options=list(options.keys()), value=default_val).classes("w-48").props("dense outlined color=teal-7")
                            sel._std_field = entry["source_col"]
                            ui.label(badge_text).classes(f"w-20 text-xs px-2 py-0.5 rounded-full text-center bg-{badge_color}-100 text-{badge_color}-700")
                        _mapping_selects[entry["source_col"]] = sel

                    ui.separator().classes("my-2")
                    ui.label("資料預覽 (前 5 筆):").classes("text-body font-semibold mb-1")
                    preview_container = ui.column().classes("w-full overflow-x-auto")

                imp_confirm_btn.set_visibility(True)
            except Exception as ex:
                imp_status.set_text(f"❌ Upload error: {str(ex)[:100]}")

        def _do_import():
            nonlocal _import_content, _import_cols
            if not _import_content or not _import_cols:
                ui.notify("No file uploaded yet.", type="warning", position="top")
                return
            from utils.importers import parse_csv, map_columns, validate_import_rows
            from utils.data import save_prefects
            mapping = {}
            for k, sel in _mapping_selects.items():
                chosen = sel.value
                if chosen and chosen != "-- Skip --":
                    for label, std_key in STANDARD_FIELDS.items():
                        if f"{std_key['zh']} ({std_key['en']})" == chosen:
                            mapping[k] = label
                            break
            if not mapping:
                ui.notify("請至少對應一個欄位。", type="warning", position="top")
                return
            _, raw_rows = parse_csv(_import_content)
            mapped_rows = map_columns(raw_rows, mapping)
            valid, errors = validate_import_rows(mapped_rows)
            if not valid:
                ui.notify("No valid rows found.", type="negative", position="top")
                return
            added = 0
            for v in valid:
                name = v.get("name", "").strip()
                if not name:
                    continue
                if any(p.name.strip() == name if hasattr(p, "name") else p.get("name", "").strip() == name for p in prefects):
                    continue
                prefects.append(v)
                added += 1
            if added > 0:
                from utils.backup import silent_backup
                silent_backup(prefects, label="pre_import")
                save_prefects(prefects)
                _refresh_table()
                import_dialog.close()
                # Show import summary with change details
                summary_parts = [f"已匯入 {added} 位領袖。"]
                if errors:
                    summary_parts.append(f"{len(errors)} 則警告。")
                form_fixes = [e for e in errors if "invalid form" in e.lower()]
                if form_fixes:
                    summary_parts.append(f"{len(form_fixes)} 位領袖的年級已設為 F4。")
                dup_detected = [e for e in errors if "duplicate" in e.lower()]
                if dup_detected:
                    summary_parts.append(f"{len(dup_detected)} 個重複名稱已跳過。")
                ui.notify(" ".join(summary_parts), type="positive", position="top", timeout=8000)
            if errors:
                for err in errors[:5]:
                    ui.notify(err, type="warning", position="top")

        with ui.dialog() as import_dialog, ui.card().classes("rounded-xl p-6 max-w-2xl max-h-[80vh] overflow-y-auto dark:bg-slate-800"):
            ui.label("匯入領袖資料 (Import Prefects)").classes(Type.H2 + " mb-2")
            ui.label("上傳 CSV 檔案，系統將自動偵測欄位對應。您可以在匯入前檢查並調整對應關係。").classes("text-body text-secondary mb-4")
            imp_upload = ui.upload(label="選擇 CSV 檔案 (.csv)", auto_upload=True,
                on_upload=lambda e: _handle_upload(e)).props("accept=.csv").classes("w-full mb-3")
            imp_status = ui.label("").classes("text-body-sm text-slate-500 mb-2")
            mapping_container = ui.column().classes("w-full")
            imp_confirm_btn = ui.button("確認匯入 (Confirm Import)", icon="check_circle",
                on_click=lambda: _do_import()).props("color=teal-7").classes("rounded-[14px] font-semibold mt-3")
            imp_confirm_btn.set_visibility(False)

        # ---- AI Parse Dialog ----
        with ui.dialog() as ai_dialog, ui.card().classes("rounded-xl p-6 max-w-2xl"):
            ui.label(_t("AI 解析備註", "AI Parse Remarks")).classes(Type.H2 + " mb-2")
            ui.label(_t("人工智能將分析備註欄位，並建議更新固定值班和可用日期。", "The AI will analyze the Remarks column and suggest updates for fixed duties and available days."))                 .classes("text-body text-secondary mb-4")

            def _run_parse():
                from services.ai_parser import parse_all_remarks
                results = parse_all_remarks(prefects)
                if not results:
                    ui.notify("No remarks to parse, or no changes detected.", type="info")
                    return
                ai_results_container.clear()
                with ai_results_container:
                    ui.label(f"Found {len(results)} prefect(s) with suggested changes:").classes("text-body font-medium mb-2")
                    ai_checks = {}
                    for r in results:
                        chg_desc = ", ".join(f"{k}: {v}" for k, v in r["changes"].items())
                        ai_checks[r["name"]] = ui.checkbox(
                            f"{r['name']} ? {r['remarks'][:40]}...  ?  {chg_desc}",
                            value=True
                        ).props("color=teal-7")
                    
                    def _apply_ai():
                        applied = 0
                        for r in results:
                            if ai_checks[r["name"]].value:
                                for p in prefects:
                                    pname = (p.name_zh) if hasattr(p, "name") else p.get("name", "")
                                    if pname == r["name"]:
                                        for field, val in r["changes"].items():
                                            if field == "available":
                                                from models.enums import Weekday
                                                setattr(p, field, [Weekday[d] for d in val if d in Weekday.__members__])
                                            else:
                                                setattr(p, field, val)
                                        applied += 1
                                        break
                        if applied > 0:
                            from utils.data import save_prefects
                            save_prefects(prefects)
                            _refresh_table()
                            ui.notify(f"Applied {applied} change(s).", type="positive", position="top")
                        ai_dialog.close()

                    ui.button(_t("應用已選變更", "Apply Selected Changes"), on_click=_apply_ai)                         .props("color=teal-7").classes("rounded-lg mt-3")

            ui.button(_t("開始分析", "Start Parsing"), on_click=_run_parse)                 .props("color=purple-7").classes("rounded-[14px]")
            ai_results_container = ui.column().classes("w-full mt-2")

        # ---- Prefect Table ----
        columns = [
            {"name": "name", "label": _t("姓名", "Name"), "field": "display_name", "align": "left"},
            {"name": "form", "label": _t("年级", "Form"), "field": "form", "align": "left"},
            {"name": "class_name", "label": _t("班别", "Class"), "field": "class_name", "align": "left"},
            {"name": "role", "label": _t("职位", "Role"), "field": "role", "align": "left"},
            {"name": "available", "label": _t("可值日", "Available Days"), "field": "available", "align": "left"},
            {"name": "load", "label": _t("负荷 (分)", "Load (pts)"), "field": "load", "align": "right"},
            {"name": "active", "label": _t("活跃", "Active"), "field": "active", "align": "center"},
            {"name": "actions", "label": "", "field": "actions", "align": "center"},
        ]

        def _refresh_table():
            """Reload prefects and refresh the table."""
            nonlocal prefects
            rows = load_prefects()
            prefects = _prefects_from_rows(rows) if rows else []
            table.rows = _build_rows(prefects)
            table.update()

        def _build_rows(plist: list) -> list:
            """Convert Prefect list to table row dicts."""
            table_rows = []
            for p in plist:
                avail_str = ", ".join(
                    d.value for d in p.available
                ) if p.available else "-"
                table_rows.append({
                    "name": p.name, "display_name": p.name_zh if p.name_zh and p.name_zh.strip() else p.name,
                    "form": p.form.display if hasattr(p.form, "display") else p.form.name,
                    "class_name": p.class_name,
                    "role": p.role.display,
                    "available": avail_str,
                    "load": f"{p.history_weight:.1f}",
                    "active": _t("是", "Yes") if p.active else _t("否", "No"),
                    "actions": "✎ Edit  ✕ Delete",
                })
            return table_rows

        table_rows = _build_rows(prefects)

        if not table_rows:
            with ui.card().classes("w-full rounded-[20px] shadow-sm p-12 text-center dark:bg-slate-800"):
                ui.icon("people_outline").classes("text-6xl text-slate-300 mb-4")
                ui.label(_t("暫無風紀", "No Prefects Yet")).classes(Type.H2 + " text-slate-400 mb-2")
                ui.label(_t("添加第一位風紀開始使用。", "Add your first prefect to get started.")).classes("text-body text-secondary mb-6")
        else:
            table = ui.table(
                columns=columns,
                rows=table_rows,
                row_key="name",
                pagination={"rowsPerPage": 15, "sortBy": "name"},
            ).classes("w-full rounded-lg dark:bg-slate-800").props("flat bordered dark")

        # ---- Add/Edit Dialog ----
        with ui.dialog() as edit_dialog, ui.card().classes("rounded-xl p-6 max-w-lg w-full dark:bg-slate-800"):
            ui.label(_t("添加 / 編輯風紀", "Add / Edit Prefect")).classes(Type.H2 + " mb-4")

            name_input = ui.input(
                label=_t("英文姓名 *", "English Name *"),
            placeholder="e.g. CHAN Tai Man",
            ).classes("w-full mb-3").props("outlined color=teal-7")

            name_zh_input = ui.input(
                label=_t("中文姓名", "Chinese Name"),
                placeholder="e.g. Chen Da Wen",
            ).classes("w-full mb-3").props("outlined color=teal-7")

            form_select = ui.select(
                label=_t("年級 *", "Form *"),
                options=list(FORM_CHOICES.keys()),
                value="F.4",
            ).classes("w-full mb-3").props("outlined color=teal-7")

            class_input = ui.input(
                label=_t("班別 *", "Class *"),
                placeholder="e.g. 4A",
            ).classes("w-full mb-3").props("outlined color=teal-7")

            role_select = ui.select(
                label=_t("職位 *", "Role *"),
                options=list(ROLE_CHOICES.keys()),
                value="Study Prefect",
            ).classes("w-full mb-3").props("outlined color=teal-7")

            # Available days as checkboxes
            ui.label(_t("可值班日:", "Available Days:")).classes("text-label mt-2 mb-1")
            day_checks = {}
            with ui.row().classes("gap-3 flex-wrap"):
                for day in Weekday:
                    day_checks[day] = ui.checkbox(
                        WEEKDAY_LABELS[day], value=True
                    ).props("color=teal-7")

            history_input = ui.number(
                label=_t("歷史權重 (分)", "History Weight (pts)"),
                value=0.0,
                min=0,
                step=0.5,
            ).classes("w-32 mb-3").props("outlined color=teal-7")

            active_check = ui.checkbox(_t("活躍", "Active"), value=True).props("color=teal-7")

            with ui.row().classes("gap-2 justify-end mt-4"):
                ui.button(_t("取消", "Cancel"), on_click=edit_dialog.close) \
                    .props("outline color=teal-7").classes("rounded-[14px]")
                ui.button(_t("保存", "Save"), on_click=lambda: _save_prefect()) \
                    .props("color=teal-7").classes("rounded-[14px]")

        def _open_add():
            """Open dialog for adding a new prefect."""
            name_input.value = ""
            name_zh_input.value = ""
            class_input.value = ""
            for d in Weekday:
                day_checks[d].value = True
            history_input.value = 0.0
            active_check.value = True
            edit_dialog.open()

        def _save_prefect():
            """Save the prefect from dialog fields."""
            if not name_input.value or not name_input.value.strip():
                ui.notify(_t("姓名為必填項。", "Name is required."), type="negative", position="top")
                return
            if not class_input.value or not class_input.value.strip():
                ui.notify(_t("班別為必填項。", "Class is required."), type="negative", position="top")
                return

            available = [
                d for d in Weekday if day_checks[d].value
            ]
            role = ROLE_CHOICES[role_select.value]
            form = FORM_CHOICES[form_select.value]

            # Check if updating existing or adding new
            existing = None
            for p in prefects:
                if p.name.strip() == name_input.value.strip():
                    existing = p
                    break

            if existing:
                # Update existing
                existing.name_zh = name_zh_input.value
                existing.form = form
                existing.class_name = class_input.value
                existing.role = role
                existing.available = available
                existing.history_weight = history_input.value
                existing.active = active_check.value
            else:
                # Add new
                new_p = Prefect(
                    name=name_input.value.strip(),
                    name_zh=name_zh_input.value,
                    form=form,
                    class_name=class_input.value.strip(),
                    role=role,
                    available=available,
                    history_weight=history_input.value,
                    active=active_check.value,
                )
                prefects.append(new_p)

            # Save to CSV
            save_prefects(prefects)
            edit_dialog.close()
            _refresh_table()
            ui.notify(
                _t(f"\u5df2\u4fdd\u5b58 {name_input.value} \u70ba {role_select.value}\u3002", f"Saved {name_input.value} as {role_select.value}."),
                type="positive", position="top",
            )

        def _delete_prefect(prefect_name: str):
            """Delete a prefect by name."""
            nonlocal prefects
            from utils.backup import silent_backup
            silent_backup(prefects, label="pre_delete")
            prefects = [p for p in prefects if p.name.strip() != prefect_name.strip()]
            save_prefects(prefects)
            _refresh_table()
            ui.notify(_t(f"\u5df2\u522a\u9664 {prefect_name}\u3002", f"Deleted {prefect_name}."), type="positive", position="top")

        # Wire Add button
        add_btn.on_click(_open_add)

        # ---- Quick Action: Load Demo Data ----
        ui.separator().classes("my-4")
        with ui.row().classes("gap-2"):
            ui.button(_t("加載示範數據", "Load Demo Data"), icon="download", on_click=lambda: [
                _skeleton_area.clear(),
                show_skeleton(5),
                save_prefects(load_demo_data()),
                _skeleton_area.clear(),
                _refresh_table(),
                ui.notify(_t("示範數據已加載（11 位風紀、值班歷史、請假記錄）。", "Demo data loaded (11 prefects, duty history, leave records)."), type="positive"),
            ]).props("outline color=teal-7").classes("rounded-[14px]")

