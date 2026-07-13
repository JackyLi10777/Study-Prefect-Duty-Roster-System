"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui_app.ui.page_shared import *  # noqa: F403

@ui.page("/handover")
def handover_page() -> None:
    workflow = get_workflow()
    readiness = workflow.handover_readiness()
    release_evidence = load_release_evidence()
    with page_shell("handover", "/handover", music_context="handover"):
        with ui.element("section").classes("sy-handover-hero w-full").props(f'aria-label="{t("handover")}"'):
            ui.icon("handshake").classes("sy-handover-hero-icon").props("aria-hidden=true")
            ui.label(t("handover")).classes("sy-handover-hero-title")
            ui.label(t("handover_intro")).classes("sy-handover-hero-copy")
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            for key in ("handover_step_one", "handover_step_two", "handover_step_three", "handover_step_four"):
                ui.label(t(key)).classes("text-sm leading-6")
        checks = (
            ("handover_prefects_ready", f"{readiness['activePrefectCount']}", readiness["activePrefectCount"] > 0),
            ("handover_rosters_ready", f"{readiness['rosterCount']}", readiness["rosterCount"] > 0),
            ("handover_backup_ready", t("verified") if readiness["verifiedBackup"] else t("handover_attention"), readiness["verifiedBackup"]),
        )
        with ui.element("section").classes("sy-handover-readiness-grid w-full").props(
            f'aria-label="{t("handover")}" data-testid=handover-readiness-grid'
        ):
            for label_key, value, ready in checks:
                with ui.element("article").classes("sy-surface sy-handover-readiness-card"):
                    ui.label(t(label_key)).classes("text-sm text-[var(--sy-muted)]")
                    ui.label(value).classes("text-xl font-semibold mt-1")
                    _tone_badge(t("handover_ready") if ready else t("handover_attention"), "stable" if ready else "attention").classes("mt-3")

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
            f'role=status aria-live=polite aria-label="{t("acceptance_title")}" data-testid=acceptance-status'
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
                    on_click=lambda: ui.navigate.to("/guide"),
                ).props("outline color=primary data-testid=acceptance-open-guide")
                ui.button(
                    t("open_backup_settings"),
                    icon="settings_backup_restore",
                    on_click=lambda: ui.navigate.to("/settings"),
                ).props("flat data-testid=acceptance-open-settings")
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")).props("flat").classes("self-start")


@ui.page("/settings")
def settings_page() -> None:
    workflow = get_workflow()
    status = workflow.backup_status()
    backup_inventory = workflow.backup_inventory()
    backups = list(backup_inventory["items"])
    backup_options = {
        str(item["path"]): f"{item['createdAt']:%Y-%m-%d %H:%M} | {item['path'].name}"
        for item in backups
        if item["verification"].get("valid")
    }
    readiness = workflow.handover_readiness()
    with page_shell("settings", "/settings"):
        ui.label(t("settings")).classes("text-2xl font-semibold")
        _render_operation_hint("hint_settings", icon="settings_backup_restore")
        render_music_library_settings()
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label(t("handover")).classes("text-lg font-semibold")
                    ui.label(t("handover_intro")).classes("text-sm text-[var(--sy-muted)]")
                ui.button(t("open_handover_guide"), icon="handshake", on_click=lambda: ui.navigate.to("/handover")).props("outline color=primary")
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
        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
            ui.label(t("persistence_notice")).classes("text-lg font-semibold")
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

        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
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
                            ui.download(package.content, package.filename)
                            ui.notify(t("handover_backup_package_ready"), type="positive")
                            handover_package_dialog.close()

                    with ui.row().classes("w-full justify-end gap-3 mt-5"):
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

        with ui.card().classes("sy-surface w-full max-w-3xl p-6"):
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

                    with ui.row().classes("w-full justify-end gap-3 mt-5"):
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
                    action_props="outline color=primary data-testid=create-verified-backup-action",
                )
                ui.button(t("restore_selected_backup"), icon="restore").props(
                    "outline disable aria-disabled=true data-testid=restore-disabled-no-backup"
                ).classes("mt-3")
