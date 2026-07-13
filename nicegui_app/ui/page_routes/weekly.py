"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui_app.ui.page_shared import *  # noqa: F403

@ui.page("/rosters")
def rosters_page() -> None:
    workflow = get_workflow()
    weeks = workflow.roster_weeks()
    with page_shell("rosters", "/rosters"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.html(t("rosters"), tag="h2").classes("text-2xl font-semibold")
            ui.label(t("persistence_notice")).classes("text-sm text-[var(--sy-muted)]")
        _render_storage_lifecycle(workflow)
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            generate_tab = ui.tab("generate_view", label=t("generate_view"), icon="calendar_month")
            adjust_tab = ui.tab("adjust_edit", label=t("adjust_edit"), icon="edit_calendar")
        with ui.tab_panels(tabs, value="generate_view", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("generate_view").classes("px-0"):
                with ui.card().classes("sy-surface w-full max-w-2xl p-6"):
                    ui.html(t("generate_roster"), tag="h2").classes("text-lg font-semibold")
                    _render_operation_hint("hint_generate_roster", icon="calendar_month")
                    week_input = ui.input(label=t("week_start"), value=_next_monday().isoformat()).props(
                        "type=date name=week-start autocomplete=off"
                    )
                    multiplier_by_week = {
                        week["weekStart"]: float(week.get("historyPriorityMultiplier", 1.0))
                        for week in weeks
                    }
                    try:
                        initial_week = date.fromisoformat(str(week_input.value))
                    except ValueError:
                        initial_week = _next_monday()
                    with ui.element("section").classes("sy-surface-subtle w-full p-4 mt-4"):
                        ui.label(t("history_priority_title")).classes("font-semibold")
                        ui.label(t("history_priority_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
                        )
                        history_priority = ui.slider(
                            min=HISTORY_PRIORITY_MULTIPLIER_MIN,
                            max=HISTORY_PRIORITY_MULTIPLIER_MAX,
                            step=0.1,
                            value=multiplier_by_week.get(initial_week, 1.0),
                        ).props(
                            f'label label-always snap data-testid=history-priority-multiplier '
                            f'aria-label="{t("history_priority_label")}"'
                        ).classes("w-full mt-3")
                        with ui.row().classes("w-full justify-between gap-2 text-xs text-[var(--sy-muted)]"):
                            ui.label(t("history_priority_lower"))
                            ui.label(t("history_priority_standard"))
                            ui.label(t("history_priority_higher"))

                    def refresh_history_priority() -> None:
                        selected = selected_week_start()
                        history_priority.value = multiplier_by_week.get(selected, 1.0) if selected else 1.0
                        history_priority.update()

                    def selected_week_start(*, announce_error: bool = False) -> date | None:
                        try:
                            selected = date.fromisoformat(str(week_input.value or ""))
                        except ValueError:
                            if announce_error:
                                ui.notify(t("week_start_invalid"), type="warning")
                                week_input.run_method("focus")
                            return None
                        try:
                            workflow.validate_week_start(selected)
                        except WorkflowError:
                            if announce_error:
                                ui.notify(t("week_start_monday_required"), type="warning")
                                week_input.run_method("focus")
                            return None
                        return selected

                    requirements_area = ui.column().classes("w-full gap-2 mt-4")

                    def refresh_requirements() -> None:
                        requirements_area.clear()
                        week_start = selected_week_start()
                        if week_start is None:
                            return
                        try:
                            requirements = workflow.generation_requirements(week_start)
                        except WorkflowError:
                            return
                        with requirements_area:
                            with ui.expansion(t("generation_requirements"), icon="assignment_late").classes("w-full"):
                                ui.label(t("generation_requirements_notice")).classes("p-4 pb-1 text-sm text-[var(--sy-muted)]")
                                rows = [
                                    {
                                        "id": index,
                                        "day": day_label(item["day"]),
                                        "post": post_label(item["postCode"]),
                                        "slot": item["slotIndex"],
                                        "eligible": item["eligibleCount"],
                                        "status": t("vacancy_risk") if item["hasVacancyRisk"] else t("awaiting_generation"),
                                    }
                                    for index, item in enumerate(requirements, start=1)
                                ]
                                ui.table(
                                    rows=rows,
                                    columns=[
                                        {"name": "day", "label": t("day"), "field": "day", "align": "left"},
                                        {"name": "post", "label": t("post"), "field": "post", "align": "left"},
                                        {"name": "slot", "label": "#", "field": "slot", "align": "right"},
                                        {"name": "eligible", "label": t("eligible_count"), "field": "eligible", "align": "right"},
                                        {"name": "status", "label": t("status"), "field": "status", "align": "left"},
                                    ],
                                    row_key="id",
                                ).classes("sy-table w-full p-4")
                    refresh_requirements()

                    ui.separator().classes("my-5")
                    ui.label(t("pre_generation_leave")).classes("text-base font-semibold")
                    ui.label(t("leave_generation_notice")).classes("text-sm text-[var(--sy-muted)]")
                    prefect_options = {
                        str(prefect["id"]): f"{prefect['nameZh']} ({prefect['form']} {prefect['className']})"
                        for prefect in workflow.prefects()
                    }
                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        leave_prefect = ui.select(
                            label=t("select_prefect"),
                            options=prefect_options,
                            value=next(iter(prefect_options), None),
                        ).classes("grow min-w-[220px]")
                        leave_day = ui.select(
                            label=t("leave_day"),
                            options={day.name: day_label(day) for day in SchoolDay},
                            value=SchoolDay.MONDAY.name,
                        ).classes("grow min-w-[180px]")
                    leave_reason = ui.input(label=t("leave_reason")).props(
                        "name=pre-generation-leave-reason autocomplete=off"
                    ).classes("w-full")
                    leave_list = ui.column().classes("w-full gap-2 mt-3")

                    def refresh_leave_list() -> None:
                        leave_list.clear()
                        week_start = selected_week_start()
                        if week_start is None:
                            return
                        try:
                            declarations = workflow.pre_generation_leaves(week_start)
                        except WorkflowError:
                            return
                        with leave_list:
                            if declarations:
                                ui.label(t("declared_leaves")).classes("text-sm font-semibold")
                            for declaration in declarations:
                                with ui.row().classes("w-full items-center justify-between gap-3 py-1"):
                                    ui.label(
                                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {declaration['reason']}"
                                    ).classes("text-sm text-[var(--sy-muted)]")

                                    async def cancel_leave(leave_id: int = int(declaration["id"])) -> None:
                                        result = await _run_with_progress(
                                            lambda: workflow.cancel_pre_generation_leave(leave_id),
                                            title_key="progress_leave_cancel_title",
                                            working_key="progress_leave_cancel_working",
                                            icon="event_available",
                                        )
                                        if result is not _OPERATION_FAILED:
                                            ui.notify(t("leave_cancelled"), type="positive")
                                            refresh_leave_list()

                                    ui.button(t("cancel_leave"), icon="close", on_click=cancel_leave).props("flat dense color=negative")

                    async def declare_leave() -> None:
                        week_start = selected_week_start(announce_error=True)
                        if week_start is None:
                            return
                        if not leave_prefect.value:
                            ui.notify(t("leave_prefect_required"), type="warning")
                            leave_prefect.run_method("focus")
                            return
                        if not leave_day.value:
                            ui.notify(t("leave_day_required"), type="warning")
                            leave_day.run_method("focus")
                            return
                        reason = str(leave_reason.value or "").strip()
                        if not reason:
                            ui.notify(t("leave_reason_required"), type="warning")
                            leave_reason.run_method("focus")
                            return
                        prefect_id = str(leave_prefect.value)
                        leave_day_value = str(leave_day.value)
                        result = await _run_with_progress(
                            lambda: workflow.declare_leave(
                                week_start=week_start,
                                prefect_id=prefect_id,
                                day=leave_day_value,
                                reason=reason,
                            ),
                            title_key="progress_leave_title",
                            working_key="progress_leave_working",
                            icon="event_busy",
                        )
                        if result is not _OPERATION_FAILED:
                            leave_reason.value = ""
                            leave_reason.update()
                            refresh_leave_list()
                            ui.notify(t("leave_declared"), type="positive")

                    ui.button(t("declare_leave"), icon="event_busy", on_click=declare_leave).props("outline color=primary").classes("mt-3")
                    week_input.on(
                        "change",
                        lambda _event: (
                            refresh_leave_list(),
                            refresh_requirements(),
                            refresh_history_priority(),
                        ),
                    )
                    refresh_leave_list()

                    async def generate() -> None:
                        week_start = selected_week_start(announce_error=True)
                        if week_start is None:
                            return
                        result = await _run_with_progress(
                            lambda: workflow.generate_and_save_draft(
                                week_start,
                                history_priority_multiplier=float(history_priority.value or 1.0),
                            ),
                            title_key="progress_generate_title",
                            working_key="progress_generate_working",
                            icon="edit_calendar",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(t("draft_saved"), type="positive")
                            ui.navigate.to(f"/rosters/{result.id}")

                    ui.button(t("create_draft"), icon="edit_calendar", on_click=generate).props("color=primary").classes("mt-4")
                ui.html(t("current_rosters"), tag="h2").classes("text-xl font-semibold mt-6")
                if not weeks:
                    _render_empty_state(
                        title_key="empty_roster_title",
                        body_key="empty_roster_detail",
                        icon="event_note",
                        illustrated=True,
                    )
                for week in weeks:
                    history_priority_value = f"{float(week.get('historyPriorityMultiplier', 1.0)):.1f}"
                    with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4"):
                        with ui.column().classes("gap-0"):
                            ui.label(str(week["weekStart"])).classes("text-lg font-semibold")
                            ui.label(
                                f"{t('version')} {week['version']}  |  {t('generated_at')}: {week['generatedAt']:%Y-%m-%d %H:%M}  |  "
                                f"{t('history_priority_used', value=history_priority_value)}"
                            ).classes("text-sm text-[var(--sy-muted)]")
                        _tone_badge(t("published") if week["status"] == "published" else t("draft"), "stable" if week["status"] == "published" else "action")
                        ui.button(t("view"), icon="arrow_forward", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}")).props("flat")
            with ui.tab_panel("adjust_edit").classes("px-0"):
                ui.label(t("adjustments")).classes("text-lg font-semibold")
                _render_operation_hint("hint_adjust_roster", icon="event_busy")
                published_weeks = [week for week in workflow.roster_weeks() if week["status"] == "published"]
                if not published_weeks:
                    _render_empty_state(
                        title_key="empty_published_title",
                        body_key="empty_published_detail",
                        icon="fact_check",
                    )
                for week in published_weeks:
                    with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4 mt-4"):
                        with ui.column().classes("gap-0"):
                            ui.label(str(week["weekStart"])).classes("text-lg font-semibold")
                            ui.label(f"{t('version')} {week['version']}").classes("text-sm text-[var(--sy-muted)]")
                        ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}/adjustments")).props("outline color=primary")


@ui.page("/rosters/new")
def generate_roster_page() -> None:
    ui.navigate.to("/rosters")


@ui.page("/rosters/{roster_week_id}")
def roster_detail_page(roster_week_id: int) -> None:
    workflow = get_workflow()
    with page_shell("rosters", "/rosters"):
        try:
            week = workflow.roster_week(roster_week_id)
        except WorkflowError:
            _render_roster_route_state(
                title_key="roster_unavailable_title",
                body_key="roster_unavailable_body",
                icon="link_off",
                test_id="roster-unavailable-state",
                primary_key="review_current_rosters",
                primary_path="/rosters",
                secondary_key="review_restore_settings",
                secondary_path="/settings",
            )
            return
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(str(week["weekStart"])).classes("text-2xl font-semibold")
                ui.label(f"{t('version')} {week['version']}").classes("text-[var(--sy-muted)]")
                ui.label(
                    t(
                        "history_priority_used",
                        value=f"{float(week.get('historyPriorityMultiplier', 1.0)):.1f}",
                    )
                ).classes("text-sm text-[var(--sy-muted)]")
            with ui.row().classes("gap-2"):
                if week["status"] == "draft":
                    reviewed_version = int(week["version"])
                    with ui.dialog() as publish_conflict_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("publish_conflict_title")).classes("text-lg font-semibold")
                        ui.label(t("publish_conflict_body", version=reviewed_version)).classes(
                            "text-sm text-[var(--sy-muted)] mt-2"
                        )

                        def reload_after_publish_conflict() -> None:
                            publish_conflict_dialog.close()
                            ui.navigate.reload()

                        with ui.row().classes("w-full justify-end mt-5"):
                            ui.button(
                                t("publish_conflict_review_action"),
                                icon="refresh",
                                on_click=reload_after_publish_conflict,
                            ).props("color=primary")

                    with ui.dialog() as publish_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                        ui.label(t("confirm_publish")).classes("text-lg font-semibold")
                        ui.label(t("publish_warning")).classes("text-sm text-[var(--sy-muted)] mt-2")
                        ui.label(t("publish_reviewed_version", version=reviewed_version)).classes(
                            "text-sm font-medium mt-3"
                        )

                        async def publish() -> None:
                            publish_dialog.close()
                            result = await _run_with_progress(
                                lambda: workflow.publish(
                                    roster_week_id,
                                    expected_week_version=reviewed_version,
                                ),
                                title_key="progress_publish_title",
                                working_key="progress_publish_working",
                                icon="publish",
                                on_conflict=lambda _error: publish_conflict_dialog.open(),
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("published_success"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("w-full justify-end gap-3 mt-5"):
                            ui.button(t("cancel"), icon="close", on_click=publish_dialog.close).props("flat")
                            ui.button(t("confirm_publish_action"), icon="publish", on_click=publish).props("color=primary")
                    ui.button(t("publish"), icon="publish", on_click=publish_dialog.open).props("color=primary")
                else:
                    ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: ui.navigate.to(f"/rosters/{roster_week_id}/adjustments")).props("outline color=primary")
                ui.button(t("export_pdf"), icon="picture_as_pdf", on_click=lambda: _open_roster_export_dialog(roster_week_id)).props("outline color=primary")
        if week["status"] == "draft":
            ui.label(t("draft_export_warning")).classes("sy-fg-attention font-medium")
        ui.label(t("export_pdf_notice")).classes("text-sm text-[var(--sy-muted)]")
        if week["status"] == "draft":
            ui.label(t("draft_preview")).classes("text-xl font-semibold mt-2")
            ui.label(t("draft_preview_notice")).classes("text-sm text-[var(--sy-muted)]")
            draft_assignments = workflow.assignments(roster_week_id)
            assignment_options = {
                str(item["id"]): f"{day_label(item['day'])} | {post_label(item['postCode'])} | {item['prefectName']}"
                for item in draft_assignments
                if item["status"] == "active"
            }
            with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
                ui.label(t("manual_draft_change")).classes("text-lg font-semibold")
                _render_operation_hint("hint_draft_change", icon="edit_note")
                ui.label(t("manual_draft_change_notice")).classes("text-sm text-[var(--sy-muted)] mt-3")
                assignment_select = ui.select(
                    label=t("select_draft_assignment"),
                    options=assignment_options,
                    value=next(iter(assignment_options), None),
                ).classes("w-full mt-4")
                candidate_select = ui.select(label=t("replacement"), options={}).classes("w-full")
                reason_input = ui.textarea(label=t("draft_change_reason")).props(
                    "name=draft-change-reason autocomplete=off"
                ).classes("w-full")

                def load_draft_candidates() -> None:
                    def action() -> None:
                        if not assignment_select.value:
                            raise WorkflowError("No draft assignment was selected.")
                        candidates = workflow.draft_assignment_candidates(roster_week_id, int(assignment_select.value))
                        candidate_select.options = {
                            str(candidate["id"]): f"{candidate['nameZh']} ({candidate['form']} {candidate['className']}; {candidate['historyWeight']:.1f})"
                            for candidate in candidates
                        }
                        candidate_select.value = next(iter(candidate_select.options), None)
                        candidate_select.update()
                        ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                    _safe_read_action(action, action_name="load_draft_candidates")

                async def save_draft_change() -> None:
                    if not assignment_select.value:
                        ui.notify(t("draft_assignment_required"), type="warning")
                        assignment_select.run_method("focus")
                        return
                    if not candidate_select.value:
                        ui.notify(t("draft_candidate_required"), type="warning")
                        candidate_select.run_method("focus")
                        return
                    reason = str(reason_input.value or "").strip()
                    if not reason:
                        ui.notify(t("draft_change_reason_required"), type="warning")
                        reason_input.run_method("focus")
                        return
                    assignment_id = int(assignment_select.value)
                    replacement_prefect_id = str(candidate_select.value)
                    result = await _run_with_progress(
                        lambda: workflow.update_draft_assignment(
                            roster_week_id=roster_week_id,
                            assignment_id=assignment_id,
                            replacement_prefect_id=replacement_prefect_id,
                            reason=reason,
                        ),
                        title_key="progress_draft_change_title",
                        working_key="progress_draft_change_working",
                        icon="edit_note",
                    )
                    if result is not _OPERATION_FAILED:
                        ui.notify(t("draft_changed"), type="positive")
                        ui.navigate.reload()

                with ui.row().classes("gap-3 mt-4"):
                    ui.button(t("load_draft_candidates"), icon="group_add", on_click=load_draft_candidates).props("outline color=primary")
                    ui.button(t("save_draft_change"), icon="save", on_click=save_draft_change).props("color=primary")
        else:
            with ui.card().classes("sy-surface sy-border-attention w-full max-w-3xl border-l-4 p-6"):
                ui.label(t("post_publication_leave")).classes("text-lg font-semibold")
                ui.label(t("post_publication_leave_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
                ui.button(t("adjust_roster"), icon="swap_horiz", on_click=lambda: ui.navigate.to(f"/rosters/{roster_week_id}/adjustments")).props("color=primary").classes("mt-4")
        declarations = workflow.pre_generation_leaves(week["weekStart"])
        if declarations:
            with ui.element("section").classes("sy-surface w-full px-5 py-4"):
                ui.label(t("declared_leaves")).classes("font-semibold")
                for declaration in declarations:
                    ui.label(
                        f"{day_label(str(declaration['day']))} | {declaration['prefectName']} | {declaration['reason']}"
                    ).classes("text-sm text-[var(--sy-muted)] mt-1")
        _render_roster_table(roster_week_id)


@ui.page("/adjustments")
def adjustments_page() -> None:
    ui.navigate.to("/rosters")


@ui.page("/rosters/{roster_week_id}/adjustments")
def adjustment_detail_page(roster_week_id: int) -> None:
    workflow = get_workflow()
    with page_shell("adjustments", "/rosters"):
        ui.label(t("adjustments")).classes("text-2xl font-semibold")
        _render_operation_hint("hint_leave_adjustment", icon="swap_horiz")
        try:
            week = workflow.roster_week(roster_week_id)
        except WorkflowError:
            _render_roster_route_state(
                title_key="roster_unavailable_title",
                body_key="roster_unavailable_body",
                icon="link_off",
                test_id="adjustment-roster-unavailable-state",
                primary_key="review_current_rosters",
                primary_path="/rosters",
                secondary_key="review_restore_settings",
                secondary_path="/settings",
            )
            return
        if week["status"] != "published":
            _render_roster_route_state(
                title_key="adjustment_unavailable_title",
                body_key="adjustment_unavailable_body",
                icon="pending_actions",
                test_id="adjustment-unavailable-state",
                primary_key="return_to_roster",
                primary_path=f"/rosters/{roster_week_id}",
                secondary_key="review_current_rosters",
                secondary_path="/rosters",
                secondary_icon="format_list_bulleted",
            )
            return
        adjustment_command_id = f"leave-ui:{uuid4().hex}"
        active_assignments = [item for item in workflow.assignments(roster_week_id) if item["status"] == "active"]
        options = {
            str(item["id"]): f"{day_label(item['day'])} | {post_label(item['postCode'])} | {item['prefectName']}"
            for item in active_assignments
        }
        if not options:
            _render_empty_state(
                title_key="empty_published_title",
                body_key="empty_published_detail",
                icon="fact_check",
                action_key="empty_review_action",
                action=lambda: ui.navigate.to("/rosters"),
            )
            return
        with ui.card().classes("sy-surface sy-adjustment-form w-full max-w-2xl p-6"):
            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_assignment")).classes("sy-adjustment-step-title")
                assignment_select = ui.select(
                    label=t("select_assignment"), options=options, value=next(iter(options))
                ).classes("w-full")

            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_replacement")).classes("sy-adjustment-step-title")
                replacement_select = ui.select(
                    label=t("replacement"), options={"__vacant__": t("leave_vacant")}, value="__vacant__"
                ).classes("w-full")

            def load_substitutes() -> None:
                def action() -> None:
                    candidates = workflow.recommend_substitutes(roster_week_id, int(assignment_select.value))
                    replacement_select.options = {"__vacant__": t("leave_vacant")}
                    replacement_select.options.update({str(item["id"]): f"{item['nameZh']} ({item['form']} {item['className']}; {item['historyWeight']:.1f})" for item in candidates})
                    replacement_select.value = "__vacant__"
                    replacement_select.update()
                    ui.notify(t("eligible_substitutes") if candidates else t("no_substitutes"), type="info")

                _safe_read_action(action, action_name="load_adjustment_candidates")

            async def apply_adjustment() -> None:
                reason = str(reason_input.value or "").strip()
                if not reason:
                    ui.notify(t("reason_required"), type="negative")
                    reason_input.run_method("focus")
                    return
                assignment_id = int(assignment_select.value)
                replacement_id = None if replacement_select.value == "__vacant__" else str(replacement_select.value)
                result = await _run_with_progress(
                    lambda: workflow.apply_leave_adjustment(
                        roster_week_id=roster_week_id,
                        assignment_id=assignment_id,
                        replacement_prefect_id=replacement_id,
                        reason=reason,
                        command_id=adjustment_command_id,
                        expected_week_version=int(week["version"]),
                    ),
                    title_key="progress_adjustment_title",
                    working_key="progress_adjustment_working",
                    icon="swap_horiz",
                )
                if result is not _OPERATION_FAILED:
                    ui.notify(t("adjustment_saved"), type="positive")
                    ui.navigate.to(f"/rosters/{roster_week_id}")

            with ui.element("section").classes("sy-adjustment-step"):
                ui.label(t("adjustment_step_reason")).classes("sy-adjustment-step-title")
                reason_input = ui.textarea(label=t("reason")).props(
                    "name=leave-adjustment-reason autocomplete=off"
                ).classes("w-full")
            with ui.row().classes("sy-adjustment-actions w-full gap-3"):
                ui.button(t("load_substitutes"), icon="group_add", on_click=load_substitutes).props("outline color=primary")
                ui.button(t("apply_adjustment"), icon="save", on_click=apply_adjustment).props("color=primary")
