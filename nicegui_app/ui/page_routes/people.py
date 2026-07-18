"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import hashlib
import json

from nicegui import events, ui

from nicegui_app.access_context import Capability
from nicegui_app.runtime import get_workflow
from nicegui_app.services.prefect_import_assistant import (
    ImportAssistantError,
    import_assistant_status,
    suggest_deepseek_column_mapping,
)
from nicegui_app.services.roster_workflow import PeriodSummaryReport, PrefectInput
from nicegui_app.services.summary_report_export import (
    build_duty_allocation_statement_pdf,
    build_summary_report_json,
    build_summary_report_pdf,
)
from nicegui_app.ui.downloads import deliver_generated_download
from nicegui_app.ui.i18n import day_label, role_label, t
from nicegui_app.ui.page_access import (
    allows as _allows,
    render_restricted_capability as _render_restricted_capability,
)
from nicegui_app.ui.page_shared import (
    _OPERATION_FAILED,
    _delete_dialog_after_close,
    _prefect_directory_rows,
    _render_mobile_prefect_cards,
    _render_operation_hint,
    _render_responsive_table,
    _run_with_progress,
    _tone_badge,
)
from nicegui_app.ui.shell import page_shell
from nicegui_app.ui.theme import current_theme
from nicegui_app.utils.prefect_file_import import (
    MAX_IMPORT_BYTES,
    ParsedImportFile,
    PrefectFileImportError,
    TARGET_FIELDS,
    parse_prefect_file,
    suggest_local_column_mapping,
    validate_target_mapping,
)
from nicegui_app.utils.prefect_import import (
    ImportPreview,
    parse_prefect_import_rows,
    parse_prefect_import_text,
    prefect_import_template_csv,
)
from roster_policy import SchoolDay


def _prefect_file_preview_fingerprint(
    *,
    filename: str,
    content: bytes,
    sheet_name: str | None,
    mapping: Mapping[str, str],
) -> str:
    """Bind an approved preview to the exact file, worksheet, and mapping."""
    payload = json.dumps(
        {
            "filename": filename.casefold(),
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "sheet_name": sheet_name or "",
            "mapping": sorted((str(target), str(source)) for target, source in mapping.items()),
        },
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _prefect_text_preview_fingerprint(text: str) -> str:
    """Bind a pasted-directory preview to the exact text the operator reviewed."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _show_prefect_dialog(existing: dict[str, object] | None = None) -> None:
    workflow = get_workflow()
    title_key = "edit_prefect" if existing else "add_prefect"
    day_options = {day.name: day_label(day) for day in SchoolDay}
    role_options = {"study_prefect": role_label("study_prefect"), "assistant_head": role_label("assistant_head")}
    with ui.dialog() as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        ui.label(t(title_key)).classes("text-xl font-semibold")
        with ui.row().classes("sy-mobile-field-row w-full gap-3 flex-wrap"):
            name_zh = ui.input(label=t("name_zh"), value=existing["nameZh"] if existing else "").props(
                "name=name-zh autocomplete=off"
            ).classes("grow")
            name_en = ui.input(label=t("name_en"), value=existing["nameEn"] if existing else "").props(
                "name=name-en autocomplete=off"
            ).classes("grow")
        with ui.row().classes("sy-mobile-field-row w-full gap-3 flex-wrap"):
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
                (
                    lambda: workflow.update_prefect(
                        str(existing["id"]),
                        prefect_input,
                        expected_version=int(existing["version"]),
                    )
                )
                if existing
                else (lambda: workflow.create_prefect(prefect_input))
            )
            result = await _run_with_progress(
                save_action,
                title_key="progress_prefect_save_title",
                working_key="progress_prefect_save_working",
                icon="person_check",
                on_conflict=lambda _error: ui.notify(t("prefect_write_conflict"), type="warning", timeout=8_000),
            )
            if result is not _OPERATION_FAILED:
                dialog.close()
                ui.notify(t("prefect_saved"), type="positive")
                ui.navigate.reload()

        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-4"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
            ui.button(t("save"), icon="save", on_click=save_prefect).props("color=primary")
    _delete_dialog_after_close(dialog)
    dialog.open()


def _summary_metric(label: str, value: str, detail: str) -> None:
    with ui.element("article").classes("sy-surface min-w-[150px] grow px-4 py-4"):
        ui.label(label).classes("text-xs font-semibold uppercase tracking-wide text-[var(--sy-muted)]")
        ui.label(value).classes("text-2xl font-semibold mt-1")
        ui.label(detail).classes("text-xs text-[var(--sy-muted)] mt-1")


def _report_status_text(codes: tuple[str, ...]) -> str:
    labels = {
        "new_prefect": t("status_new_prefect"),
        "needs_mentoring": t("status_needs_mentoring"),
        "assistant_head": role_label("assistant_head"),
    }
    resolved = [labels[code] for code in codes if code in labels]
    return " · ".join(resolved) if resolved else t("status_regular")


def _prefect_file_error_text(error: PrefectFileImportError) -> str:
    return t(f"prefect_file_error_{error.code}")


def _import_assistant_error_text(error: ImportAssistantError) -> str:
    return t(f"deepseek_error_{error.code}")


def _render_import_preview_content(preview_area, preview: ImportPreview) -> None:  # type: ignore[no-untyped-def]
    preview_area.clear()
    with preview_area:
        if preview.issues:
            ui.label(t("import_issues")).classes("font-semibold sy-fg-danger")
            for issue in preview.issues:
                ui.label(issue).classes("text-sm sy-fg-danger")
        if preview.rows:
            if not preview.issues:
                ui.label(t("import_ready")).classes("font-semibold sy-fg-stable")
            _render_responsive_table(
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
            )


def _render_period_report(report: PeriodSummaryReport) -> None:
    with ui.row().classes("w-full gap-3 flex-wrap mt-4").props("data-testid=summary-report-metrics"):
        _summary_metric(t("report_published_weeks"), str(report.published_week_count), t("report_published_weeks_detail"))
        coverage = f"{report.coverage_rate:.1f}%" if report.coverage_rate is not None else t("not_applicable")
        _summary_metric(t("report_coverage"), coverage, t("report_coverage_detail"))
        _summary_metric(t("report_recorded_duties"), str(report.active_assignment_count), t("report_recorded_duties_detail"))
        _summary_metric(t("report_scheduled_hours"), f"{report.scheduled_minutes / 60:.1f}", t("report_scheduled_hours_detail"))
        _summary_metric(t("report_fairness_spread"), f"{report.fairness_spread:.1f}", t("report_fairness_spread_detail"))
        _summary_metric(
            t("report_ledger_status"),
            t("report_ledger_balanced") if report.fairness_ledger_balanced else t("report_ledger_review"),
            t("report_ledger_status_detail"),
        )

    with ui.card().classes("sy-surface w-full p-5 mt-4"):
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label(t("report_executive_summary")).classes("text-lg font-semibold")
                ui.label(t("report_executive_summary_detail")).classes("text-sm text-[var(--sy-muted)]")
            _tone_badge(
                t("report_complete_coverage") if report.vacant_slot_count == 0 and report.recorded_slot_count else t("report_review_vacancies"),
                "stable" if report.vacant_slot_count == 0 and report.recorded_slot_count else "attention",
            )
        ui.label(
            t(
                "report_assist_coverage_sentence",
                filled=report.assist_filled_count,
                required=report.assist_required_count,
            )
        ).classes("text-sm leading-6 mt-3")
        ui.label(
            t(
                "report_adjustment_sentence",
                adjustments=report.leave_adjustment_count,
                replacements=report.replacement_count,
                vacancies=report.vacant_slot_count,
            )
        ).classes("text-sm leading-6")
        ui.label(t("report_service_not_performance")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

    if report.trend:
        with ui.card().classes("sy-surface w-full p-5 mt-4"):
            ui.label(t("fairness_trend")).classes("text-lg font-semibold")
            ui.label(t("fairness_trend_detail")).classes("text-sm text-[var(--sy-muted)] mt-1")
            chart_dark = current_theme() == "dark"
            chart_text = "#F5F5F7" if chart_dark else "#3A3A3C"
            chart_muted = "#AEAEB2" if chart_dark else "#6E6E73"
            chart_line = "rgba(235,235,245,.16)" if chart_dark else "rgba(60,60,67,.14)"
            chart_tooltip = "#1C1C1E" if chart_dark else "#FFFFFF"
            chart_action = "#9BC2D2" if chart_dark else "#35647C"
            chart_attention = "#F0C96A" if chart_dark else "#8A6423"
            chart_neutral = "#C5C7CA" if chart_dark else "#59686D"
            ui.echart(
                {
                    "animation": False,
                    "textStyle": {"color": chart_text},
                    "tooltip": {
                        "trigger": "axis",
                        "backgroundColor": chart_tooltip,
                        "borderColor": chart_line,
                        "textStyle": {"color": chart_text},
                    },
                    "legend": {
                        "type": "scroll",
                        "data": [t("trend_median"), t("trend_spread"), t("trend_stddev")],
                        "textStyle": {"color": chart_muted},
                    },
                    "grid": {"left": 45, "right": 24, "top": 52, "bottom": 44},
                    "xAxis": {
                        "type": "category",
                        "data": [point.week_start.isoformat() for point in report.trend],
                        "axisLabel": {"rotate": 25, "color": chart_muted, "hideOverlap": True},
                        "axisLine": {"lineStyle": {"color": chart_line}},
                    },
                    "yAxis": {
                        "type": "value",
                        "name": t("history_weight"),
                        "nameTextStyle": {"color": chart_muted},
                        "axisLabel": {"color": chart_muted},
                        "splitLine": {"lineStyle": {"color": chart_line}},
                    },
                    "series": [
                        {
                            "name": t("trend_median"),
                            "type": "line",
                            "smooth": True,
                            "symbolSize": 7,
                            "data": [point.median for point in report.trend],
                            "lineStyle": {"color": chart_action, "width": 2},
                            "itemStyle": {"color": chart_action},
                        },
                        {
                            "name": t("trend_spread"),
                            "type": "line",
                            "smooth": True,
                            "symbolSize": 7,
                            "data": [point.spread for point in report.trend],
                            "lineStyle": {"color": chart_attention, "width": 2},
                            "itemStyle": {"color": chart_attention},
                        },
                        {
                            "name": t("trend_stddev"),
                            "type": "line",
                            "smooth": True,
                            "symbolSize": 7,
                            "data": [point.population_stddev for point in report.trend],
                            "lineStyle": {"color": chart_neutral, "width": 2},
                            "itemStyle": {"color": chart_neutral},
                        },
                    ],
                }
            ).classes("sy-fairness-trend-chart w-full h-80 mt-3").props(f'aria-label="{t("fairness_trend")}" data-testid=fairness-trend-chart')
            with ui.expansion(t("trend_accessible_table"), icon="table_chart").classes("w-full"):
                _render_responsive_table(
                    rows=[
                        {
                            "week": point.week_start.isoformat(),
                            "minimum": point.minimum,
                            "median": point.median,
                            "maximum": point.maximum,
                            "spread": point.spread,
                            "stddev": point.population_stddev,
                            "source": f"#{point.roster_week_id} v{point.version}",
                        }
                        for point in report.trend
                    ],
                    columns=[
                        {"name": "week", "label": t("week"), "field": "week", "align": "left"},
                        {"name": "minimum", "label": t("trend_minimum"), "field": "minimum", "align": "right"},
                        {"name": "median", "label": t("trend_median"), "field": "median", "align": "right"},
                        {"name": "maximum", "label": t("trend_maximum"), "field": "maximum", "align": "right"},
                        {"name": "spread", "label": t("trend_spread"), "field": "spread", "align": "right"},
                        {"name": "stddev", "label": t("trend_stddev"), "field": "stddev", "align": "right"},
                        {"name": "source", "label": t("report_source_version"), "field": "source", "align": "left"},
                    ],
                    row_key="week",
                )

    with ui.card().classes("sy-surface w-full p-5 mt-4"):
        ui.label(t("recorded_service_participation")).classes("text-lg font-semibold")
        ui.label(t("recorded_service_participation_detail")).classes("text-sm text-[var(--sy-muted)] mt-1")
        _render_responsive_table(
            rows=[
                {
                    "name": row.name_zh,
                    "role": role_label(row.role_code),
                    "duties": row.duty_count,
                    "points": row.workload_points,
                    "hours": round(row.scheduled_minutes / 60, 2),
                    "assist": row.assist_in_charge_count,
                    "status": _report_status_text(row.status_codes),
                }
                for row in report.contributions
            ],
            columns=[
                {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                {"name": "duties", "label": t("report_recorded_duties"), "field": "duties", "align": "right"},
                {"name": "points", "label": t("history_weight"), "field": "points", "align": "right"},
                {"name": "hours", "label": t("report_scheduled_hours"), "field": "hours", "align": "right"},
                {"name": "assist", "label": t("report_assist_duties"), "field": "assist", "align": "right"},
                {"name": "status", "label": t("support_status"), "field": "status", "align": "left"},
            ],
            row_key="name",
            classes="mt-3",
            test_id="summary-contribution-table",
        )

    statement_options = {
        row.prefect_id: t(
            "allocation_statement_option",
            name=row.name_zh,
            duties=row.duty_count,
            hours=f"{row.scheduled_minutes / 60:.2f}",
        )
        for row in report.contributions
        if row.duty_count > 0
    }
    with ui.card().classes("sy-surface w-full p-5 mt-4"):
        ui.label(t("allocation_statement_title")).classes("text-lg font-semibold")
        ui.label(t("allocation_statement_detail")).classes(
            "text-sm leading-6 text-[var(--sy-muted)] mt-1"
        )
        if not statement_options:
            ui.label(t("allocation_statement_empty")).classes("text-sm text-[var(--sy-muted)] mt-3")
        else:
            statement_prefect = ui.select(
                label=t("select_prefect"),
                options=statement_options,
                value=next(iter(statement_options)),
            ).classes("w-full max-w-xl mt-3")

            async def download_statement(language: str) -> None:
                if not statement_prefect.value:
                    ui.notify(t("select_prefect"), type="warning")
                    return
                export = await _run_with_progress(
                    lambda: build_duty_allocation_statement_pdf(
                        report,
                        str(statement_prefect.value),
                        language="zh" if language == "zh" else "en",
                    ),
                    title_key="progress_allocation_statement_title",
                    working_key="progress_allocation_statement_working",
                    icon="workspace_premium",
                )
                if export is not _OPERATION_FAILED:
                    deliver_generated_download(
                        export.content,
                        export.filename,
                        media_type=export.media_type,
                    )
                    ui.notify(t("allocation_statement_ready"), type="positive")

            with ui.row().classes("w-full gap-3 flex-wrap mt-3"):
                ui.button(
                    t("download_allocation_statement_zh"),
                    icon="workspace_premium",
                    on_click=lambda: download_statement("zh"),
                ).props("outline color=primary data-testid=download-allocation-statement-zh")
                ui.button(
                    t("download_allocation_statement_en"),
                    icon="workspace_premium",
                    on_click=lambda: download_statement("en"),
                ).props("outline color=primary data-testid=download-allocation-statement-en")


def _render_fairness_panel(workflow) -> None:  # type: ignore[no-untyped-def]
    """Keep people records, fairness explanation, and period evidence together."""
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
    _render_responsive_table(
        rows=rows,
        columns=columns,
        row_key="id",
        classes="mt-4",
    )

    ui.separator().classes("my-7")
    with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
        with ui.column().classes("gap-1 max-w-3xl"):
            ui.label(t("summary_report_title")).classes("text-xl font-semibold")
            ui.label(t("summary_report_intro")).classes("text-sm leading-6 text-[var(--sy-muted)]")
        _tone_badge(t("summary_report_read_only"), "stable")

    published_weeks = sorted(
        (week for week in workflow.roster_weeks() if week["status"] == "published"),
        key=lambda week: week["weekStart"],
    )
    week_options = {str(week["weekStart"]): str(week["weekStart"]) for week in published_weeks}
    with ui.row().classes("w-full gap-3 items-end flex-wrap mt-4"):
        first_week = ui.select(
            label=t("report_first_week"),
            options=week_options,
            value=next(iter(week_options), None),
        ).classes("min-w-[220px] grow")
        last_week = ui.select(
            label=t("report_last_week"),
            options=week_options,
            value=next(reversed(week_options), None) if week_options else None,
        ).classes("min-w-[220px] grow")
        preview_button = ui.button(t("generate_summary_report"), icon="analytics").props(
            "color=primary data-testid=generate-summary-report"
        )
    ui.label(t("report_week_range_notice")).classes("text-xs text-[var(--sy-muted)] mt-2")

    report_state: dict[str, PeriodSummaryReport | None] = {"value": None}
    report_area = ui.column().classes("w-full gap-0")

    def selected_range() -> tuple[date | None, date | None]:
        return (
            date.fromisoformat(str(first_week.value)) if first_week.value else None,
            date.fromisoformat(str(last_week.value)) if last_week.value else None,
        )

    def display_report(report: PeriodSummaryReport) -> None:
        report_state["value"] = report
        report_area.clear()
        with report_area:
            _render_period_report(report)

    async def refresh_report() -> None:
        start, end = selected_range()
        if start is not None and end is not None and start > end:
            ui.notify(t("report_range_invalid"), type="warning")
            first_week.run_method("focus")
            return
        report = await _run_with_progress(
            lambda: workflow.build_period_report(period_start=start, period_end=end),
            title_key="progress_summary_report_title",
            working_key="progress_summary_report_working",
            icon="analytics",
        )
        if report is not _OPERATION_FAILED:
            display_report(report)
            ui.notify(t("summary_report_ready"), type="positive")

    async def download_report(kind: str) -> None:
        report = report_state["value"]
        if report is None:
            ui.notify(t("generate_preview_first"), type="warning")
            return
        export = await _run_with_progress(
            lambda: (
                build_summary_report_json(report)
                if kind == "json"
                else build_summary_report_pdf(report, language="zh" if kind == "zh" else "en")
            ),
            title_key="progress_summary_export_title",
            working_key="progress_summary_export_working",
            icon="download",
        )
        if export is not _OPERATION_FAILED:
            deliver_generated_download(
                export.content,
                export.filename,
                media_type=export.media_type,
            )
            ui.notify(t("summary_export_ready"), type="positive")

    preview_button.on_click(refresh_report)
    with ui.row().classes("sy-mobile-actions w-full gap-3 flex-wrap mt-4"):
        ui.button(t("download_summary_zh_pdf"), icon="picture_as_pdf", on_click=lambda: download_report("zh")).props(
            "outline color=primary data-testid=download-summary-zh"
        )
        ui.button(t("download_summary_en_pdf"), icon="picture_as_pdf", on_click=lambda: download_report("en")).props(
            "outline color=primary data-testid=download-summary-en"
        )
        ui.button(t("download_report_evidence_json"), icon="data_object", on_click=lambda: download_report("json")).props(
            "outline color=primary data-testid=download-summary-json"
        )
    with ui.card().classes("sy-surface sy-border-attention w-full border-l-4 p-5 mt-4"):
        ui.label(t("report_evidence_not_backup")).classes("font-semibold")
        ui.label(t("report_evidence_not_backup_detail")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-1")
        ui.button(t("open_handover_backup"), icon="verified_user", on_click=lambda: ui.navigate.to("/handover")).props(
            "flat color=primary"
        ).classes("mt-2")

    display_report(workflow.build_period_report())


@ui.page("/prefects")
def prefects_page() -> None:
    workflow = get_workflow()
    with page_shell("/prefects"):
        with ui.row().classes("sy-page-lead w-full items-center justify-between"):
            ui.label(t("prefects")).classes("text-2xl font-semibold")
            ui.button(t("add_prefect"), icon="person_add", on_click=lambda: _show_prefect_dialog()).props("color=primary")
        with ui.tabs().classes("w-full sy-fg-action") as tabs:
            directory_tab = ui.tab("directory", label=t("directory"), icon="groups")
            import_tab = ui.tab("ai_import", label=t("ai_import"), icon="upload_file")
            fairness_tab = ui.tab("fairness", label=t("audit"), icon="balance")
        with ui.tab_panels(tabs, value="directory", animated=False, keep_alive=False).classes("w-full bg-transparent"):
            with ui.tab_panel("directory").classes("px-0"):
                prefects = workflow.prefects()
                _render_operation_hint("hint_prefect_directory", icon="groups")
                if not prefects:
                    with ui.element("section").classes("sy-empty-state sy-empty-state--illustrated w-full mb-5").props(
                        "data-testid=empty-prefect-directory role=status"
                    ):
                        ui.icon("group_add").classes("sy-empty-state-icon").props("aria-hidden=true")
                        ui.label(t("empty_prefect_title")).classes("text-xl font-semibold")
                        ui.label(t("empty_prefect_detail")).classes(
                            "text-sm leading-6 text-[var(--sy-muted)] max-w-2xl text-center"
                        )
                        with ui.row().classes("sy-mobile-actions justify-center gap-3 flex-wrap mt-2"):
                            ui.button(
                                t("empty_prefect_add_action"),
                                icon="person_add",
                                on_click=lambda: _show_prefect_dialog(),
                            ).props("color=primary data-testid=empty-add-prefect")
                            ui.button(
                                t("empty_prefect_import_action"),
                                icon="upload_file",
                                on_click=lambda: tabs.set_value("ai_import"),
                            ).props("outline color=primary data-testid=empty-open-import")
                options = {item["id"]: f"{item['nameZh']} ({item['form']} {item['className']})" for item in prefects}
                prefect_versions = {str(item["id"]): int(item["version"]) for item in prefects}
                directory_actions_classes = "sy-directory-actions w-full items-end gap-3 flex-wrap mb-4"
                if not prefects:
                    directory_actions_classes += " hidden"
                with ui.row().classes(directory_actions_classes):
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
                                lambda: workflow.archive_prefect(
                                    prefect_id,
                                    expected_version=prefect_versions[prefect_id],
                                ),
                                title_key="progress_prefect_archive_title",
                                working_key="progress_prefect_archive_working",
                                icon="person_off",
                                on_conflict=lambda _error: ui.notify(
                                    t("prefect_write_conflict"), type="warning", timeout=8_000
                                ),
                            )
                            if result is not _OPERATION_FAILED:
                                ui.notify(t("prefect_archived"), type="positive")
                                ui.navigate.reload()

                        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
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

                    edit_button = ui.button(t("edit_prefect"), icon="edit", on_click=edit_selected).props("outline color=primary")
                    archive_button = ui.button(t("archive_prefect"), icon="archive", on_click=archive_selected).props(
                        "flat color=negative data-testid=open-archive-prefect"
                    )
                    if not prefects:
                        selected.disable()
                        edit_button.disable()
                        archive_button.disable()
                rows = _prefect_directory_rows(prefects)
                for row in rows:
                    row["supportStatus"] = _report_status_text(tuple(row["supportCodes"]))
                columns = [
                    {"name": "name", "label": t("prefect"), "field": "name", "align": "left"},
                    {"name": "form", "label": t("form"), "field": "form", "align": "left"},
                    {"name": "class", "label": t("class_name"), "field": "class", "align": "left"},
                    {"name": "role", "label": t("role"), "field": "role", "align": "left"},
                    {"name": "availability", "label": t("availability"), "field": "availability", "align": "left"},
                    {"name": "weight", "label": t("history_weight"), "field": "weight", "align": "right"},
                    {"name": "duties", "label": t("history_duties"), "field": "duties", "align": "right"},
                    {"name": "supportStatus", "label": t("support_status"), "field": "supportStatus", "align": "left"},
                ]
                directory_table_classes = "sy-table sy-prefect-directory-desktop w-full"
                if not prefects:
                    directory_table_classes += " hidden"
                ui.table(rows=rows, columns=columns, row_key="name").classes(directory_table_classes)
                _render_mobile_prefect_cards(rows)
            with ui.tab_panel("ai_import").classes("px-0"):
                _render_operation_hint("hint_prefect_import", icon="upload_file")
                import_allowed = _allows(Capability.DATA_IMPORT) and _allows(Capability.FILE_UPLOAD)
                ai_allowed = _allows(Capability.AI_USE)
                if not import_allowed:
                    _render_restricted_capability(icon="lock")
                ui.label(t("ai_import_help")).classes("text-[var(--sy-muted)] max-w-3xl")
                ui.label(t("import_template_notice")).classes("text-sm text-[var(--sy-muted)] max-w-3xl mt-2")
                ui.button(
                    t("download_import_template"),
                    icon="download",
                    on_click=lambda: ui.download(prefect_import_template_csv(), "sing-yin-prefect-import-template.csv"),
                ).props("outline color=primary").classes("mt-3")

                with ui.card().classes("sy-surface w-full max-w-4xl p-5 mt-5"):
                    ui.label(t("file_import_title")).classes("text-lg font-semibold")
                    ui.label(t("file_import_intro")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-1")
                    file_state: dict[str, object | None] = {
                        "filename": None,
                        "content": None,
                        "parsed": None,
                        "revision": 0,
                    }
                    file_preview_state: dict[str, object | None] = {
                        "value": None,
                        "fingerprint": None,
                    }
                    import_button_state: dict[str, object | None] = {"value": None}
                    mapping_controls: dict[str, object] = {}
                    mapping_area = ui.column().classes("w-full gap-3 mt-4").props(
                        "data-testid=prefect-file-mapping"
                    )
                    file_preview_area = ui.column().classes("w-full gap-3 mt-4").props(
                        "data-testid=prefect-file-preview"
                    )

                    def set_file_import_enabled(enabled: bool) -> None:
                        button = import_button_state["value"]
                        if button is None:
                            return
                        if enabled:
                            button.enable()
                        else:
                            button.disable()

                    def invalidate_file_preview() -> None:
                        file_preview_state["value"] = None
                        file_preview_state["fingerprint"] = None
                        file_preview_area.clear()
                        set_file_import_enabled(False)

                    def reset_file_import_state() -> int:
                        """Start a new upload generation and remove every stale write action."""
                        file_state["revision"] = int(file_state["revision"] or 0) + 1
                        invalidate_file_preview()
                        mapping_controls.clear()
                        mapping_area.clear()
                        import_button_state["value"] = None
                        file_state["filename"] = None
                        file_state["content"] = None
                        file_state["parsed"] = None
                        return int(file_state["revision"])

                    def current_mapping() -> dict[str, str]:
                        return {
                            target: str(control.value)
                            for target, control in mapping_controls.items()
                            if control.value
                        }

                    def current_file_fingerprint(
                        parsed: ParsedImportFile,
                        mapping: Mapping[str, str],
                    ) -> str | None:
                        filename = file_state["filename"]
                        content = file_state["content"]
                        if not isinstance(filename, str) or not isinstance(content, bytes):
                            return None
                        return _prefect_file_preview_fingerprint(
                            filename=filename,
                            content=content,
                            sheet_name=parsed.sheet_name,
                            mapping=mapping,
                        )

                    def safe_parse_file(filename: str, content: bytes, sheet_name: str | None = None):
                        try:
                            return parse_prefect_file(filename, content, sheet_name=sheet_name), None
                        except PrefectFileImportError as error:
                            return None, error

                    async def render_mapping(parsed: ParsedImportFile, *, revision: int) -> None:
                        if revision != file_state["revision"]:
                            return
                        invalidate_file_preview()
                        mapping_controls.clear()
                        mapping_area.clear()
                        import_button_state["value"] = None
                        file_state["parsed"] = parsed
                        local_mapping = suggest_local_column_mapping(parsed.headers)
                        with mapping_area:
                            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                                with ui.column().classes("gap-0"):
                                    ui.label(str(parsed.filename)).classes("font-semibold")
                                    ui.label(
                                        t(
                                            "file_import_detected",
                                            rows=len(parsed.rows),
                                            columns=len(parsed.headers),
                                        )
                                    ).classes("text-xs text-[var(--sy-muted)]")
                                _tone_badge(t("local_validation"), "stable")

                            if len(parsed.sheet_names) > 1:
                                sheet_select = ui.select(
                                    label=t("select_worksheet"),
                                    options=list(parsed.sheet_names),
                                    value=parsed.sheet_name,
                                ).classes("w-full max-w-md")

                                async def change_sheet() -> None:
                                    file_state["revision"] = int(file_state["revision"] or 0) + 1
                                    sheet_revision = int(file_state["revision"])
                                    invalidate_file_preview()
                                    file_state["parsed"] = None
                                    filename = str(file_state["filename"] or "")
                                    content = bytes(file_state["content"] or b"")
                                    result = await _run_with_progress(
                                        lambda: safe_parse_file(filename, content, str(sheet_select.value)),
                                        title_key="progress_import_file_title",
                                        working_key="progress_import_file_working",
                                        icon="table_view",
                                    )
                                    if sheet_revision != file_state["revision"]:
                                        return
                                    if result is _OPERATION_FAILED:
                                        return
                                    reparsed, parse_error = result
                                    if parse_error:
                                        ui.notify(_prefect_file_error_text(parse_error), type="negative", timeout=8_000)
                                        return
                                    await render_mapping(reparsed, revision=sheet_revision)

                                sheet_select.on_value_change(lambda _event: change_sheet())

                            ui.label(t("column_mapping_title")).classes("font-semibold mt-2")
                            ui.label(t("column_mapping_intro")).classes("text-sm text-[var(--sy-muted)]")
                            target_labels = {
                                "name_zh": t("name_zh"),
                                "form": t("form"),
                                "class_name": t("class_name"),
                                "role": t("role"),
                                "available_days": t("availability"),
                                "remarks": t("remarks"),
                            }
                            with ui.grid(columns=2).classes("w-full gap-3 sy-import-mapping-grid"):
                                for target in TARGET_FIELDS:
                                    control = ui.select(
                                        label=target_labels[target],
                                        options=list(parsed.headers),
                                        value=local_mapping.get(target),
                                    ).props(f"clearable data-testid=prefect-mapping-{target}").classes("w-full")
                                    control.on_value_change(lambda _event: invalidate_file_preview())
                                    mapping_controls[target] = control

                            status = import_assistant_status()
                            with ui.card().classes("sy-surface-subtle w-full p-4 mt-2"):
                                with ui.row().classes("w-full items-start justify-between gap-3 flex-wrap"):
                                    with ui.column().classes("gap-1 max-w-2xl"):
                                        ui.label(t("deepseek_mapping_title")).classes("font-semibold")
                                        ui.label(t("deepseek_mapping_privacy")).classes(
                                            "text-sm leading-6 text-[var(--sy-muted)]"
                                        )
                                    _tone_badge(
                                        t("deepseek_ready") if status.ready else t("deepseek_not_configured"),
                                        "stable" if status.ready else "neutral",
                                    )

                                async def ask_deepseek() -> None:
                                    if not ai_allowed:
                                        _render_restricted_capability(icon="lock")
                                        return
                                    if revision != file_state["revision"] or file_state["parsed"] is not parsed:
                                        invalidate_file_preview()
                                        return
                                    invalidate_file_preview()
                                    existing_mapping = current_mapping()

                                    def action():
                                        try:
                                            return (
                                                suggest_deepseek_column_mapping(
                                                    parsed,
                                                    existing_mapping=existing_mapping,
                                                ),
                                                None,
                                            )
                                        except ImportAssistantError as error:
                                            return None, error

                                    result = await _run_with_progress(
                                        action,
                                        title_key="progress_deepseek_mapping_title",
                                        working_key="progress_deepseek_mapping_working",
                                        icon="auto_fix_high",
                                    )
                                    if revision != file_state["revision"] or file_state["parsed"] is not parsed:
                                        return
                                    if result is _OPERATION_FAILED:
                                        return
                                    suggestion, assistant_error = result
                                    if assistant_error:
                                        ui.notify(_import_assistant_error_text(assistant_error), type="warning", timeout=8_000)
                                        return
                                    for target, source in suggestion.target_to_source.items():
                                        control = mapping_controls[target]
                                        control.value = source
                                        control.update()
                                    ui.notify(
                                        t("deepseek_mapping_applied", count=suggestion.suggested_target_count),
                                        type="positive",
                                    )

                                ui.button(
                                    t("ask_deepseek_mapping"),
                                    icon="auto_fix_high",
                                    on_click=ask_deepseek,
                                ).props(
                                    f"outline color=primary data-testid=deepseek-column-mapping {'disable' if not status.ready or not ai_allowed else ''}"
                                ).classes("mt-3")

                            def preview_file_mapping() -> None:
                                invalidate_file_preview()
                                if revision != file_state["revision"] or file_state["parsed"] is not parsed:
                                    ui.notify(t("operation_error"), type="negative")
                                    return
                                mapping = current_mapping()
                                try:
                                    validate_target_mapping(mapping, parsed.headers)
                                except PrefectFileImportError as error:
                                    ui.notify(_prefect_file_error_text(error), type="warning", timeout=8_000)
                                    return
                                preview = parse_prefect_import_rows(list(parsed.rows), target_to_source=mapping)
                                file_preview_state["value"] = preview
                                _render_import_preview_content(file_preview_area, preview)
                                if not preview.issues and preview.rows:
                                    file_preview_state["fingerprint"] = current_file_fingerprint(parsed, mapping)
                                    set_file_import_enabled(file_preview_state["fingerprint"] is not None)

                            async def import_file_preview() -> None:
                                preview = file_preview_state["value"]
                                if (
                                    not isinstance(preview, ImportPreview)
                                    or preview.issues
                                    or not preview.rows
                                    or revision != file_state["revision"]
                                    or file_state["parsed"] is not parsed
                                ):
                                    invalidate_file_preview()
                                    ui.notify(t("operation_error"), type="negative")
                                    return
                                mapping = current_mapping()
                                try:
                                    validate_target_mapping(mapping, parsed.headers)
                                except PrefectFileImportError as error:
                                    invalidate_file_preview()
                                    ui.notify(_prefect_file_error_text(error), type="warning", timeout=8_000)
                                    return
                                fingerprint = current_file_fingerprint(parsed, mapping)
                                if fingerprint is None or fingerprint != file_preview_state["fingerprint"]:
                                    invalidate_file_preview()
                                    ui.notify(t("operation_error"), type="negative")
                                    return
                                fresh_preview = parse_prefect_import_rows(
                                    list(parsed.rows),
                                    target_to_source=mapping,
                                )
                                if fresh_preview.issues or not fresh_preview.rows:
                                    invalidate_file_preview()
                                    ui.notify(t("operation_error"), type="negative")
                                    return
                                result = await _run_with_progress(
                                    lambda: workflow.import_prefects(fresh_preview.rows),
                                    title_key="progress_import_title",
                                    working_key="progress_import_working",
                                    icon="upload_file",
                                )
                                if result is not _OPERATION_FAILED:
                                    ui.notify(t("imported_success"), type="positive")
                                    ui.navigate.reload()

                            with ui.row().classes("w-full gap-3 flex-wrap mt-2"):
                                ui.button(
                                    t("preview_mapped_file"),
                                    icon="fact_check",
                                    on_click=preview_file_mapping,
                                ).props("outline color=primary data-testid=preview-prefect-file")
                                import_button = ui.button(
                                    t("import_prefects"),
                                    icon="upload",
                                    on_click=import_file_preview,
                                ).props("color=primary data-testid=import-prefect-file")
                                import_button.disable()
                                import_button_state["value"] = import_button

                    async def upload_prefect_file(event: events.UploadEventArguments) -> None:
                        if not import_allowed:
                            ui.notify(t("access_restricted_title"), type="warning")
                            return
                        revision = reset_file_import_state()
                        try:
                            content = await event.file.read()
                            filename = event.file.name
                            if revision != file_state["revision"]:
                                return
                            file_state["filename"] = filename
                            file_state["content"] = content
                            result = await _run_with_progress(
                                lambda: safe_parse_file(filename, content),
                                title_key="progress_import_file_title",
                                working_key="progress_import_file_working",
                                icon="table_view",
                            )
                            if revision != file_state["revision"]:
                                return
                            if result is _OPERATION_FAILED:
                                return
                            parsed, parse_error = result
                            if parse_error:
                                ui.notify(_prefect_file_error_text(parse_error), type="negative", timeout=8_000)
                                return
                            await render_mapping(parsed, revision=revision)
                        finally:
                            upload_control.reset()

                    def reject_prefect_file() -> None:
                        reset_file_import_state()
                        upload_control.reset()
                        ui.notify(t("prefect_file_rejected"), type="negative")

                    upload_control = ui.upload(
                        label=t("choose_prefect_file"),
                        max_file_size=MAX_IMPORT_BYTES,
                        max_files=1,
                        on_upload=upload_prefect_file,
                        on_rejected=reject_prefect_file,
                        auto_upload=True,
                    ).props("accept=.csv,.xlsx data-testid=prefect-file-upload").classes("w-full max-w-2xl mt-3")
                    if not import_allowed:
                        upload_control.disable()

                ui.separator().classes("my-6")
                ui.label(t("paste_import_fallback")).classes("font-semibold")
                ui.label(t("paste_import_fallback_detail")).classes("text-sm text-[var(--sy-muted)]")
                import_text = ui.textarea(label=t("ai_import_input")).props(
                    "name=prefect-import autocomplete=off data-testid=paste-prefect-import-input"
                ).classes("w-full max-w-3xl")
                if not _allows(Capability.CLIPBOARD_INGEST):
                    import_text.disable()
                preview_state: dict[str, ImportPreview | None] = {"value": None}
                preview_fingerprint: dict[str, str | None] = {"value": None}
                text_import_button_state: dict[str, object | None] = {"value": None}
                preview_area = ui.column().classes("w-full max-w-4xl gap-3 mt-4")

                def set_text_import_enabled(enabled: bool) -> None:
                    button = text_import_button_state["value"]
                    if button is None:
                        return
                    if enabled:
                        button.enable()
                    else:
                        button.disable()

                def invalidate_text_preview() -> None:
                    preview_state["value"] = None
                    preview_fingerprint["value"] = None
                    preview_area.clear()
                    set_text_import_enabled(False)

                def handle_text_change(event: object) -> None:
                    if preview_state["value"] is None:
                        return
                    text = str(getattr(event, "value", "") or "")
                    approved_fingerprint = preview_fingerprint["value"]
                    if (
                        approved_fingerprint is None
                        or _prefect_text_preview_fingerprint(text) != approved_fingerprint
                    ):
                        invalidate_text_preview()

                import_text.on_value_change(handle_text_change)

                def preview_import() -> None:
                    text = str(import_text.value or "")
                    preview = parse_prefect_import_text(text)
                    preview_state["value"] = preview
                    preview_fingerprint["value"] = None
                    preview_area.clear()
                    with preview_area:
                        if preview.issues:
                            ui.label(t("import_issues")).classes("font-semibold sy-fg-danger")
                            for issue in preview.issues:
                                ui.label(issue).classes("text-sm sy-fg-danger")
                        if preview.rows:
                            if not preview.issues:
                                ui.label(t("import_ready")).classes("font-semibold sy-fg-stable")
                            _render_responsive_table(
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
                            )
                    ready = not preview.issues and bool(preview.rows)
                    if ready:
                        preview_fingerprint["value"] = _prefect_text_preview_fingerprint(text)
                    set_text_import_enabled(ready)

                async def import_preview() -> None:
                    preview = preview_state["value"]
                    if preview is None or preview.issues or not preview.rows:
                        ui.notify(t("operation_error"), type="negative")
                        return
                    text = str(import_text.value or "")
                    fingerprint = _prefect_text_preview_fingerprint(text)
                    if fingerprint != preview_fingerprint["value"]:
                        invalidate_text_preview()
                        ui.notify(t("operation_error"), type="negative")
                        return
                    fresh_preview = parse_prefect_import_text(text)
                    if fresh_preview.issues or not fresh_preview.rows:
                        invalidate_text_preview()
                        ui.notify(t("operation_error"), type="negative")
                        return
                    result = await _run_with_progress(
                        lambda: workflow.import_prefects(fresh_preview.rows),
                        title_key="progress_import_title",
                        working_key="progress_import_working",
                        icon="upload_file",
                    )
                    if result is not _OPERATION_FAILED:
                        ui.notify(t("imported_success"), type="positive")
                        ui.navigate.reload()

                with ui.row().classes("sy-mobile-actions gap-3 mt-4"):
                    preview_import_button = ui.button(t("preview_import"), icon="fact_check", on_click=preview_import).props(
                        "outline color=primary data-testid=preview-pasted-prefects"
                    )
                    import_button = ui.button(t("import_prefects"), icon="upload", on_click=import_preview).props(
                        "color=primary data-testid=import-pasted-prefects"
                    )
                    import_button.disable()
                    text_import_button_state["value"] = import_button
                    if not _allows(Capability.CLIPBOARD_INGEST):
                        preview_import_button.disable()
            with ui.tab_panel("fairness").classes("px-0"):
                _render_fairness_panel(workflow)


@ui.page("/audit")
def audit_page() -> None:
    """Keep former bookmarks valid while moving fairness beside the people directory."""
    ui.navigate.to("/prefects")
