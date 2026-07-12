"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui_app.ui.page_shared import *  # noqa: F403

def _show_prefect_dialog(existing: dict[str, object] | None = None) -> None:
    workflow = get_workflow()
    title_key = "edit_prefect" if existing else "add_prefect"
    day_options = {day.name: day_label(day) for day in SchoolDay}
    role_options = {"study_prefect": role_label("study_prefect"), "assistant_head": role_label("assistant_head")}
    with ui.dialog() as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        ui.label(t(title_key)).classes("text-xl font-semibold")
        with ui.row().classes("w-full gap-3 flex-wrap"):
            name_zh = ui.input(label=t("name_zh"), value=existing["nameZh"] if existing else "").props(
                "name=name-zh autocomplete=off"
            ).classes("grow")
            name_en = ui.input(label=t("name_en"), value=existing["nameEn"] if existing else "").props(
                "name=name-en autocomplete=off"
            ).classes("grow")
        with ui.row().classes("w-full gap-3 flex-wrap"):
            form = ui.select(label=t("form"), options=["F.3", "F.4", "F.5", "F.6"], value=existing["form"] if existing else "F.3").classes("grow")
            class_name = ui.input(label=t("class_name"), value=existing["className"] if existing else "").props(
                "name=class-name autocomplete=off"
            ).classes("grow")
            role = ui.select(label=t("role"), options=role_options, value=existing["roleCode"] if existing else "study_prefect").classes("grow")
        availability = ui.select(
            label=t("availability"),
            options=day_options,
            value=list(existing["availableDays"]) if existing else [],
            multiple=True,
        ).classes("w-full")
        mentoring = ui.switch(t("needs_mentoring"), value=bool(existing["needsMentoring"]) if existing else False)
        remarks = ui.textarea(label=t("remarks"), value=existing["remarks"] if existing else "").props(
            "name=prefect-remarks autocomplete=off"
        ).classes("w-full")

        async def save_prefect() -> None:
            if not str(name_zh.value or "").strip():
                ui.notify(t("prefect_name_required"), type="warning")
                name_zh.run_method("focus")
                return
            if not str(class_name.value or "").strip():
                ui.notify(t("prefect_class_required"), type="warning")
                class_name.run_method("focus")
                return
            if not availability.value:
                ui.notify(t("prefect_availability_required"), type="warning")
                availability.run_method("focus")
                return
            prefect_input = PrefectInput(
                name_zh=str(name_zh.value or ""),
                name_en=str(name_en.value or "") or None,
                form=str(form.value),
                class_name=str(class_name.value or ""),
                role_code=str(role.value),
                available_days=tuple(availability.value or []),
                needs_mentoring=bool(mentoring.value),
                remarks=str(remarks.value or ""),
            )
            save_action = (
                (lambda: workflow.update_prefect(str(existing["id"]), prefect_input))
                if existing
                else (lambda: workflow.create_prefect(prefect_input))
            )
            result = await _run_with_progress(
                save_action,
                title_key="progress_prefect_save_title",
                working_key="progress_prefect_save_working",
                icon="person_check",
            )
            if result is not _OPERATION_FAILED:
                dialog.close()
                ui.notify(t("prefect_saved"), type="positive")
                ui.navigate.reload()

        with ui.row().classes("w-full justify-end gap-3 mt-4"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
            ui.button(t("save"), icon="save", on_click=save_prefect).props("color=primary")
    _delete_dialog_after_close(dialog)
    dialog.open()


def _render_fairness_panel(workflow) -> None:  # type: ignore[no-untyped-def]
    """Keep people records and their fairness context in one operator workspace."""
    _render_operation_hint("hint_fairness", icon="balance")
    with ui.card().classes("sy-surface w-full p-5"):
        ui.label(t("fairness_explained")).classes("text-lg font-semibold")
        ui.label(t("fairness_explanation")).classes("text-sm text-[var(--sy-muted)] mt-1")
    rows = workflow.fairness_rows()
    columns = [
        {"name": "nameZh", "label": t("prefect"), "field": "nameZh", "align": "left"},
        {"name": "form", "label": t("form"), "field": "form", "align": "left"},
        {"name": "className", "label": t("class_name"), "field": "className", "align": "left"},
        {"name": "historyWeight", "label": t("history_weight"), "field": "historyWeight", "align": "right"},
        {"name": "historyDuties", "label": t("history_duties"), "field": "historyDuties", "align": "right"},
    ]
    ui.table(rows=rows, columns=columns, row_key="id").classes("sy-table w-full mt-4")


@ui.page("/prefects")
def prefects_page() -> None:
    workflow = get_workflow()
    with page_shell("prefects", "/prefects"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(t("prefects")).classes("text-2xl font-semibold")
            ui.button(t("add_prefect"), icon="person_add", on_click=lambda: _show_prefect_dialog()).props("color=primary")
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            directory_tab = ui.tab("directory", label=t("directory"), icon="groups")
            import_tab = ui.tab("ai_import", label=t("ai_import"), icon="smart_toy")
            fairness_tab = ui.tab("fairness", label=t("audit"), icon="balance")
        with ui.tab_panels(tabs, value="directory", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("directory").classes("px-0"):
                prefects = workflow.prefects()
                _render_operation_hint("hint_prefect_directory", icon="groups")
                options = {item["id"]: f"{item['nameZh']} ({item['form']} {item['className']})" for item in prefects}
                with ui.row().classes("sy-directory-actions w-full items-end gap-3 flex-wrap mb-4"):
                    selected = ui.select(label=t("select_prefect"), options=options, value=next(iter(options), None)).classes("sy-directory-selector min-w-[300px]")

                    def edit_selected() -> None:
                        if selected.value:
                            _show_prefect_dialog(workflow.prefect(str(selected.value)))

                    with ui.dialog() as archive_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("confirm_archive_prefect")).classes("text-lg font-semibold")
                        ui.label(t("archive_prefect_warning")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

                        async def confirm_archive_selected() -> None:
                            if not selected.value:
                                archive_dialog.close()
                                ui.notify(t("operation_error"), type="negative")
                                return
                            prefect_id = str(selected.value)
                            archive_dialog.close()
                            result = await _run_with_progress(
                                lambda: workflow.archive_prefect(prefect_id),
                                title_key="progress_prefect_archive_title",
                                working_key="progress_prefect_archive_working",
                                icon="person_off",
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("prefect_archived"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("w-full justify-end gap-3 mt-5"):
                            ui.button(t("cancel"), icon="close", on_click=archive_dialog.close).props("flat")
                            ui.button(
                                t("confirm_archive"),
                                icon="archive",
                                on_click=confirm_archive_selected,
                            ).props("color=negative data-testid=confirm-archive-prefect")

                    def archive_selected() -> None:
                        if not selected.value:
                            ui.notify(t("operation_error"), type="negative")
                            return
                        archive_dialog.open()

                    ui.button(t("edit_prefect"), icon="edit", on_click=edit_selected).props("outline color=primary")
                    ui.button(t("archive_prefect"), icon="archive", on_click=archive_selected).props(
                        "flat color=negative data-testid=open-archive-prefect"
                    )
                rows = _prefect_directory_rows(prefects)
                columns = [
                    {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                    {"name": "form", "label": t("form"), "field": "form", "align": "left"},
                    {"name": "class", "label": t("class_name"), "field": "class", "align": "left"},
                    {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                    {"name": "availability", "label": t("availability"), "field": "availability", "align": "left"},
                    {"name": "weight", "label": t("history_weight"), "field": "weight", "align": "right"},
                    {"name": "duties", "label": t("history_duties"), "field": "duties", "align": "right"},
                ]
                ui.table(rows=rows, columns=columns, row_key="name").classes("sy-table sy-prefect-directory-desktop w-full")
                _render_mobile_prefect_cards(rows)
            with ui.tab_panel("ai_import").classes("px-0"):
                _render_operation_hint("hint_prefect_import", icon="upload_file")
                ui.label(t("ai_import_help")).classes("text-[var(--sy-muted)] max-w-3xl")
                ui.label(t("import_template_notice")).classes("text-sm text-[var(--sy-muted)] max-w-3xl mt-2")
                ui.button(
                    t("download_import_template"),
                    icon="download",
                    on_click=lambda: ui.download(prefect_import_template_csv(), "sing-yin-prefect-import-template.csv"),
                ).props("outline color=primary").classes("mt-3")
                import_text = ui.textarea(label=t("ai_import_input")).props(
                    "name=prefect-import autocomplete=off"
                ).classes("w-full max-w-3xl")
                preview_state: dict[str, ImportPreview | None] = {"value": None}
                preview_area = ui.column().classes("w-full max-w-4xl gap-3 mt-4")

                def preview_import() -> None:
                    preview = parse_prefect_import_text(str(import_text.value or ""))
                    preview_state["value"] = preview
                    preview_area.clear()
                    with preview_area:
                        if preview.issues:
                            ui.label(t("import_issues")).classes("font-semibold text-red-600")
                            for issue in preview.issues:
                                ui.label(issue).classes("text-sm text-red-600")
                        if preview.rows:
                            if not preview.issues:
                                ui.label(t("import_ready")).classes("font-semibold sy-fg-stable")
                            ui.table(
                                rows=[
                                    {
                                        "name": row.name_zh,
                                        "form": row.form,
                                        "class": row.class_name,
                                        "role": role_label(row.role_code),
                                        "availability": " / ".join(day_label(day) for day in row.available_days),
                                    }
                                    for row in preview.rows
                                ],
                                columns=[
                                    {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                                    {"name": "form", "label": t("form"), "field": "form", "align": "left"},
                                    {"name": "class", "label": t("class_name"), "field": "class", "align": "left"},
                                    {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                                    {"name": "availability", "label": t("availability"), "field": "availability", "align": "left"},
                                ],
                                row_key="name",
                            ).classes("sy-table w-full")

                async def import_preview() -> None:
                    preview = preview_state["value"]
                    if preview is None or preview.issues or not preview.rows:
                        ui.notify(t("operation_error"), type="negative")
                        return
                    result = await _run_with_progress(
                        lambda: workflow.import_prefects(preview.rows),
                        title_key="progress_import_title",
                        working_key="progress_import_working",
                        icon="upload_file",
                    )
                    if result is not _OPERATION_FAILED:
                        ui.notify(t("imported_success"), type="positive")
                        ui.navigate.reload()

                with ui.row().classes("gap-3 mt-4"):
                    ui.button(t("preview_import"), icon="fact_check", on_click=preview_import).props("outline color=primary")
                    ui.button(t("import_prefects"), icon="upload", on_click=import_preview).props("color=primary")
            with ui.tab_panel("fairness").classes("px-0"):
                _render_fairness_panel(workflow)


@ui.page("/audit")
def audit_page() -> None:
    """Keep former bookmarks valid while moving fairness beside the people directory."""
    ui.navigate.to("/prefects")
