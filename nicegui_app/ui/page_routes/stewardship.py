"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from pathlib import Path

from nicegui import events, run, ui

from nicegui_app.release_evidence import load_release_evidence
from nicegui_app.runtime import get_workflow
from nicegui_app.ui.downloads import deliver_generated_download
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import t
from nicegui_app.ui.music import render_guest_music_settings, render_music_library_settings
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.page_access import (
    is_guest_mode as _is_guest_mode,
    render_restricted_capability as _render_restricted_capability,
)
from nicegui_app.ui.page_shared import (
    _OPERATION_FAILED,
    _render_empty_state,
    _render_operation_hint,
    _run_with_progress,
    _tone_badge,
)
from nicegui_app.ui.reference_navigation import render_page_toc, render_reference_pager
from nicegui_app.ui.shell import page_shell

@ui.page("/handover")
async def handover_page() -> None:
    workflow = get_workflow()
    overview = await run.io_bound(workflow.backup_overview)
    readiness = overview["readiness"]
    evidence_time = overview["evidenceGeneratedAt"].astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    release_evidence = load_release_evidence()
    with page_shell("/handover"):
        with ui.element("section").classes("sy-handover-hero w-full").props(
            f'aria-label="{attr(t("handover"))}"'
        ):
            ui.icon("handshake").classes("sy-handover-hero-icon").props("aria-hidden=true")
            ui.label(t("handover_intro")).classes("sy-handover-hero-copy")
        render_page_toc(
            (
                ("handover-steps-section", "handover_steps_title"),
                ("handover-rollover-section", "school_year_rollover_title"),
                ("handover-readiness-section", "handover_readiness_title"),
                ("handover-acceptance-section", "acceptance_title"),
            )
        )
        with ui.card().classes("sy-surface sy-operations-panel w-full p-6").props(
            f'id=handover-steps-section aria-label="{attr(t("handover_steps_title"))}"'
        ):
            for key in ("handover_step_one", "handover_step_two", "handover_step_three", "handover_step_four"):
                ui.label(t(key)).classes("text-sm leading-6")

        with ui.element("section").classes("sy-school-year-rollover sy-operations-panel w-full").props(
            f'id=handover-rollover-section aria-label="{attr(t("school_year_rollover_title"))}" '
            'data-testid=school-year-rollover'
        ):
            with ui.row().classes("w-full items-start gap-4 no-wrap"):
                ui.icon("event_repeat").classes("sy-school-year-rollover-icon").props("aria-hidden=true")
                with ui.column().classes("gap-1 grow min-w-0"):
                    ui.label(t("school_year_rollover_title")).classes("sy-school-year-rollover-title")
                    ui.label(t("school_year_rollover_intro")).classes("sy-school-year-rollover-copy")
                    ui.label(t("school_year_rollover_safety")).classes("sy-school-year-rollover-safety")

            if readiness["activePrefectCount"] > 0:
                confirmation_phrase = t("school_year_rollover_confirmation_phrase")
                with ui.dialog() as rollover_dialog, ui.card().classes("sy-surface w-full max-w-lg p-6"):
                    ui.label(t("school_year_rollover_confirm_title")).classes("text-xl font-semibold")
                    ui.label(t("school_year_rollover_confirm_body")).classes(
                        "mt-2 text-sm leading-6 text-[var(--sy-muted)]"
                    )
                    confirmation = ui.input(
                        label=t("school_year_rollover_confirmation_label", phrase=confirmation_phrase)
                    ).props("autocomplete=off data-testid=school-year-rollover-confirmation").classes("w-full mt-5")

                    async def perform_school_year_rollover() -> None:
                        if str(confirmation.value or "").strip() != confirmation_phrase:
                            return
                        rollover_dialog.close()
                        result = await _run_with_progress(
                            workflow.prepare_new_school_year,
                            title_key="progress_school_year_rollover_title",
                            working_key="progress_school_year_rollover_working",
                            icon="event_repeat",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(
                                t(
                                    "school_year_rollover_done",
                                    count=int(result["archivedPrefectCount"]),
                                ),
                                type="positive",
                                timeout=7_000,
                            )
                            navigate_to("/prefects")

                    with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                        ui.button(t("cancel"), icon="close", on_click=rollover_dialog.close).props("flat")
                        confirm_rollover = ui.button(
                            t("school_year_rollover_confirm_action"),
                            icon="event_repeat",
                            on_click=perform_school_year_rollover,
                        ).props("color=negative data-testid=confirm-school-year-rollover")
                        confirm_rollover.disable()

                    def update_rollover_confirmation(event: events.ValueChangeEventArguments) -> None:
                        if str(event.value or "").strip() == confirmation_phrase:
                            confirm_rollover.enable()
                        else:
                            confirm_rollover.disable()

                    confirmation.on_value_change(update_rollover_confirmation)

                ui.button(
                    t("school_year_rollover_action"),
                    icon="event_repeat",
                    on_click=rollover_dialog.open,
                ).props("outline color=negative data-testid=open-school-year-rollover").classes("mt-4")
            else:
                _tone_badge(t("school_year_rollover_already_empty"), "stable").classes("mt-4")
                ui.button(
                    t("school_year_rollover_empty_action"),
                    icon="upload_file",
                    on_click=lambda: navigate_to("/prefects"),
                ).props("outline color=primary data-testid=open-new-directory-import").classes("mt-4")
        checks = (
            ("handover_prefects_ready", f"{readiness['activePrefectCount']}", readiness["activePrefectCount"] > 0),
            ("handover_rosters_ready", f"{readiness['rosterCount']}", readiness["rosterCount"] > 0),
            ("handover_backup_ready", t("verified") if readiness["verifiedBackup"] else t("handover_attention"), readiness["verifiedBackup"]),
        )
        with ui.element("section").classes("sy-handover-readiness-grid w-full").props(
            f'id=handover-readiness-section aria-label="{attr(t("handover_readiness_title"))}" '
            'data-testid=handover-readiness-grid'
        ):
            for label_key, value, ready in checks:
                with ui.element("article").classes("sy-surface sy-handover-readiness-card"):
                    ui.label(t(label_key)).classes("text-sm text-[var(--sy-muted)]")
                    ui.label(value).classes("text-xl font-semibold mt-1")
                    _tone_badge(t("handover_ready") if ready else t("handover_attention"), "stable" if ready else "attention").classes("mt-3")
        with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
            ui.label(t("backup_evidence_time", time=evidence_time)).classes(
                "text-xs text-[var(--sy-muted)]"
            ).props("data-testid=handover-backup-evidence-time")
            ui.button(
                t("backup_recheck_now"),
                icon="refresh",
                on_click=ui.navigate.reload,
            ).props("flat data-testid=handover-backup-recheck")

        state_key = {
            "pass": "acceptance_status_pass",
            "running": "acceptance_status_running",
            "stale": "acceptance_status_stale",
            "fail": "acceptance_status_fail",
            "missing": "acceptance_status_missing",
            "unreadable": "acceptance_status_unreadable",
        }[release_evidence.state]
        state_body_key = f"acceptance_body_{release_evidence.state}"
        state_icon = {
            "pass": "verified_user",
            "running": "sync",
            "stale": "update",
            "fail": "error_outline",
            "missing": "pending_actions",
            "unreadable": "report_problem",
        }[release_evidence.state]
        state_tone = {
            "pass": "stable",
            "running": "action",
            "stale": "attention",
            "fail": "danger",
            "missing": "attention",
            "unreadable": "danger",
        }[release_evidence.state]
        with ui.element("section").classes("sy-acceptance-panel w-full").props(
            f'id=handover-acceptance-section role=status aria-live=polite '
            f'aria-label="{attr(t("acceptance_title"))}" data-testid=acceptance-status'
        ):
            with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
                with ui.row().classes("items-start gap-3 no-wrap"):
                    ui.icon("fact_check").classes("sy-acceptance-panel-icon").props("aria-hidden=true")
                    with ui.column().classes("gap-1"):
                        ui.label(t("acceptance_title")).classes("sy-acceptance-title")
                        ui.label(t("acceptance_intro")).classes("sy-acceptance-intro")
                _tone_badge(t(state_key), state_tone, props="data-testid=acceptance-state-badge")
            with ui.element("div").classes("sy-acceptance-grid"):
                with ui.element("article").classes("sy-acceptance-card"):
                    ui.icon(state_icon).classes(f"sy-acceptance-card-icon sy-fg-{state_tone}").props("aria-hidden=true")
                    ui.label(t("acceptance_machine_title")).classes("sy-acceptance-card-kicker")
                    ui.label(t(state_key)).classes("sy-acceptance-card-title")
                    ui.label(t(state_body_key)).classes("sy-acceptance-card-copy")
                    if release_evidence.total_checks:
                        ui.label(
                            t(
                                "acceptance_checks_summary",
                                passed=release_evidence.passed_checks,
                                total=release_evidence.total_checks,
                            )
                        ).classes("sy-acceptance-meta")
                    if release_evidence.finished_at:
                        ui.label(
                            t(
                                "acceptance_report_time",
                                time=release_evidence.finished_at.strftime("%Y-%m-%d %H:%M UTC"),
                            )
                        ).classes("sy-acceptance-meta")
                with ui.element("article").classes("sy-acceptance-card sy-acceptance-card--human"):
                    ui.icon("groups").classes("sy-acceptance-card-icon sy-fg-attention").props("aria-hidden=true")
                    ui.label(t("acceptance_human_title")).classes("sy-acceptance-card-kicker")
                    ui.label(t("acceptance_human_required")).classes("sy-acceptance-card-title")
                    ui.label(t("acceptance_human_body")).classes("sy-acceptance-card-copy")
                    ui.label(t("acceptance_role_summary")).classes("sy-acceptance-meta")
            with ui.expansion(t("acceptance_steps_title"), icon="checklist").classes(
                "sy-acceptance-steps w-full"
            ).props("data-testid=acceptance-human-steps"):
                with ui.element("ol").classes("sy-acceptance-step-list"):
                    for key in (
                        "acceptance_task_directory",
                        "acceptance_task_pdf",
                        "acceptance_task_successor",
                        "acceptance_task_advisor",
                    ):
                        with ui.element("li"):
                            ui.label(t(key))
            with ui.row().classes("sy-acceptance-actions w-full gap-3 flex-wrap"):
                ui.button(
                    t("acceptance_open_guide"),
                    icon="menu_book",
                    on_click=lambda: navigate_to("/guide"),
                ).props("outline color=primary data-testid=acceptance-open-guide")
                ui.button(
                    t("open_backup_settings"),
                    icon="settings_backup_restore",
                    on_click=lambda: navigate_to("/settings"),
                ).props(
                    "flat data-testid=acceptance-open-settings "
                    "data-sy-icon-motion-mode=rotary-navigation"
                )
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: navigate_to("/system-architecture")).props("flat").classes("self-start")
        render_reference_pager(previous=("/guide", "operator_guide"))


@ui.page("/settings")
async def settings_page() -> None:
    workflow = get_workflow()
    overview = await run.io_bound(workflow.backup_overview)
    status = overview["status"]
    backup_inventory = overview["inventory"]
    backups = list(backup_inventory["items"])
    backup_options = {
        str(item["path"]): f"{item['createdAt']:%Y-%m-%d %H:%M} | {item['path'].name}"
        for item in backups
        if item["verification"].get("valid")
    }
    readiness = overview["readiness"]
    evidence_time = overview["evidenceGeneratedAt"].astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    with page_shell("/settings"):
        _render_operation_hint("hint_settings", icon="settings_backup_restore")
        if _is_guest_mode():
            render_guest_music_settings()
            _render_restricted_capability(icon="library_music")
        else:
            render_music_library_settings()
        with ui.card().classes("sy-surface sy-operations-panel w-full p-6"):
            with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label(t("handover")).classes("text-lg font-semibold")
                ui.button(t("open_handover_guide"), icon="handshake", on_click=lambda: navigate_to("/handover")).props("outline color=primary")
            with ui.row().classes("w-full gap-3 flex-wrap mt-4"):
                for label_key, value, ready in (
                    ("handover_prefects_ready", f"{readiness['activePrefectCount']}", readiness["activePrefectCount"] > 0),
                    ("handover_rosters_ready", f"{readiness['rosterCount']}", readiness["rosterCount"] > 0),
                    ("handover_backup_ready", t("verified") if readiness["verifiedBackup"] else t("handover_attention"), readiness["verifiedBackup"]),
                ):
                    with ui.element("div").classes("sy-status-summary"):
                        ui.label(t(label_key)).classes("text-xs text-[var(--sy-muted)]")
                        ui.label(value).classes("font-semibold")
                        ui.icon("check_circle" if ready else "priority_high").classes(
                            "sy-fg-stable" if ready else "sy-fg-attention"
                        ).props("aria-hidden=true")
        with ui.card().classes("sy-surface sy-operations-panel w-full p-6"):
            ui.label(t("persistence_notice")).classes("text-lg font-semibold")
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap mt-2"):
                ui.label(t("backup_evidence_time", time=evidence_time)).classes(
                    "text-xs text-[var(--sy-muted)]"
                ).props("data-testid=settings-backup-evidence-time")
                ui.button(
                    t("backup_recheck_now"),
                    icon="refresh",
                    on_click=ui.navigate.reload,
                ).props("flat data-testid=settings-backup-recheck")
            ui.label(f"{t('database')}: {status['databasePath']}").classes("sy-path-value text-sm text-[var(--sy-muted)] mt-3")
            ui.label(f"{t('backup_directory')}: {status['backupDirectory']}").classes("sy-path-value text-sm text-[var(--sy-muted)]")
            if status["latestPath"]:
                ui.label(str(status["latestPath"])).classes("sy-path-value text-xs text-[var(--sy-muted)] mt-2")
            verification = status["latestVerification"]
            if verification and verification.get("valid"):
                _tone_badge(t("verified"), "stable").classes("mt-3")
            invalid_backup_count = int(backup_inventory["invalidCount"])
            if invalid_backup_count:
                reason_keys = {
                    "missing_file": "backup_issue_file",
                    "invalid_extension": "backup_issue_file",
                    "manifest_missing": "backup_issue_manifest",
                    "manifest_unreadable": "backup_issue_manifest",
                    "checksum_mismatch": "backup_issue_checksum",
                    "sqlite_unreadable": "backup_issue_database",
                    "integrity_failed": "backup_issue_database",
                    "schema_incomplete": "backup_issue_schema",
                    "unknown": "backup_issue_unknown",
                }
                with ui.element("section").classes("sy-backup-integrity-warning w-full mt-4").props(
                    'role=status aria-live=polite data-testid=invalid-backup-summary'
                ):
                    with ui.row().classes("items-start gap-3 no-wrap"):
                        ui.icon("gpp_maybe").classes("sy-backup-integrity-warning-icon").props("aria-hidden=true")
                        with ui.column().classes("gap-1 grow"):
                            ui.label(t("invalid_backup_summary_title", count=invalid_backup_count)).classes(
                                "font-semibold"
                            )
                            ui.label(t("invalid_backup_summary_body")).classes(
                                "text-sm leading-6 text-[var(--sy-muted)]"
                            )
                            with ui.row().classes("gap-2 flex-wrap mt-1"):
                                for reason_code, count in dict(backup_inventory["invalidReasonCounts"]).items():
                                    message_key = reason_keys.get(str(reason_code), "backup_issue_unknown")
                                    _tone_badge(f"{t(message_key)} × {count}", "attention")

        async def create_verified_backup() -> None:
            result = await _run_with_progress(
                workflow.create_verified_backup,
                title_key="progress_manual_backup_title",
                working_key="progress_manual_backup_working",
                icon="add_to_drive",
            )
            if result is not _OPERATION_FAILED:
                ui.notify(t("verified_backup_created"), type="positive")
                ui.navigate.reload()

        with ui.card().classes("sy-surface sy-operations-panel w-full p-6"):
            ui.label(t("handover_backup_package")).classes("text-lg font-semibold")
            ui.label(t("handover_backup_package_notice")).classes("text-sm text-[var(--sy-muted)] mt-1")
            if backup_options:
                with ui.dialog() as handover_package_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                    ui.label(t("handover_backup_package")).classes("text-lg font-semibold")
                    ui.label(t("handover_backup_package_warning")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-2")

                    async def download_handover_package() -> None:
                        package = await _run_with_progress(
                            workflow.build_verified_handover_package,
                            title_key="progress_handover_title",
                            working_key="progress_handover_working",
                            icon="archive",
                        )
                        if package is not _OPERATION_FAILED:
                            if not deliver_generated_download(
                                package.content,
                                package.filename,
                                media_type="application/zip",
                            ):
                                return
                            ui.notify(t("handover_backup_package_ready"), type="positive")
                            handover_package_dialog.close()

                    with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                        ui.button(t("cancel"), icon="close", on_click=handover_package_dialog.close).props("flat")
                        ui.button(t("confirm_handover_backup_package"), icon="download", on_click=download_handover_package).props("color=primary")
                ui.button(
                    t("handover_backup_package"),
                    icon="archive",
                    on_click=handover_package_dialog.open,
                ).props("outline color=primary data-testid=handover-package-ready-action").classes("mt-4")
            else:
                _render_empty_state(
                    title_key="no_verified_backup_title",
                    body_key="no_verified_backup_handover_body",
                    icon="inventory_2",
                    action_key="create_verified_backup",
                    action=create_verified_backup,
                )
                ui.button(t("handover_backup_package"), icon="archive").props(
                    "outline disable aria-disabled=true data-testid=handover-package-disabled-no-backup"
                ).classes("mt-3")

        with ui.card().classes("sy-surface sy-operations-panel w-full p-6"):
            ui.label(t("backup_restore")).classes("text-lg font-semibold")
            ui.label(t("restore_warning")).classes("text-sm text-[var(--sy-muted)] mt-1")
            ui.label(t("create_verified_backup_notice")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-3")
            if backup_options:
                ui.button(
                    t("create_verified_backup"),
                    icon="add_to_drive",
                    on_click=create_verified_backup,
                ).props("outline data-testid=create-verified-backup-action").classes("mt-3")
                selected_backup = ui.select(
                    label=t("select_backup"),
                    options=backup_options,
                    value=next(iter(backup_options)),
                ).classes("w-full mt-4")

                with ui.dialog() as restore_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                    ui.label(t("confirm_restore")).classes("text-lg font-semibold")
                    ui.label(t("restore_warning")).classes("text-sm text-[var(--sy-muted)] mt-2")

                    async def restore_selected_backup() -> None:
                        backup_path = Path(str(selected_backup.value))
                        restore_dialog.close()
                        result = await _run_with_progress(
                            lambda: workflow.restore_backup(backup_path),
                            title_key="progress_restore_title",
                            working_key="progress_restore_working",
                            icon="restore",
                        )
                        if result is not _OPERATION_FAILED:
                            ui.notify(t("backup_restored"), type="positive")
                            ui.navigate.reload()

                    with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                        ui.button(t("cancel"), icon="close", on_click=restore_dialog.close).props("flat")
                        ui.button(t("confirm_restore"), icon="restore", on_click=restore_selected_backup).props(
                            "color=negative data-testid=confirm-restore-action"
                        )
                ui.button(
                    t("restore_selected_backup"),
                    icon="restore",
                    on_click=restore_dialog.open,
                ).props("outline data-testid=restore-ready-action").classes("sy-button-attention mt-4")
            else:
                _render_empty_state(
                    title_key="no_verified_backup_title",
                    body_key="no_verified_backup_restore_body",
                    icon="settings_backup_restore",
                    action_key="create_verified_backup",
                    action=create_verified_backup,
                    action_props="outline color=primary",
                    action_test_id="create-verified-backup-action",
                )
                ui.button(t("restore_selected_backup"), icon="restore").props(
                    "outline disable aria-disabled=true data-testid=restore-disabled-no-backup"
                ).classes("mt-3")
