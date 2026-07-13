"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui_app.ui.page_shared import *  # noqa: F403


def _release_evidence_tone(state: str) -> str:
    """Map release evidence to the same operator meaning used across the app."""
    return {
        "pass": "stable",
        "running": "action",
        "stale": "attention",
        "missing": "attention",
        "unreadable": "attention",
        "fail": "danger",
    }.get(state, "attention")

@ui.page("/platform")
def platform_page() -> None:
    team_roles = (
        ("flag", "team_role_head", "team_role_head_function", "team_role_head_body", "lead"),
        ("hub", "team_role_assistant", "team_role_assistant_function", "team_role_assistant_body", "coordination"),
        ("meeting_room", "team_role_prefect", "team_role_prefect_function", "team_role_prefect_body", "service"),
        ("fact_check", "team_role_advisor", "team_role_advisor_function", "team_role_advisor_body", "assurance"),
    )
    capability_groups = (
        ("calendar_month", "capability_operations_title", "capability_operations_body", "capability_operations_output"),
        ("balance", "capability_fairness_title", "capability_fairness_body", "capability_fairness_output"),
        ("translate", "capability_experience_title", "capability_experience_body", "capability_experience_output"),
        ("shield", "capability_continuity_title", "capability_continuity_body", "capability_continuity_output"),
    )
    solutions = (
        ("event_available", "solution_weekly_title", "solution_weekly_body", "solution_weekly_outcome", "/rosters"),
        ("person_off", "solution_adjustment_title", "solution_adjustment_body", "solution_adjustment_outcome", "/adjustments"),
        ("query_stats", "solution_fairness_title", "solution_fairness_body", "solution_fairness_outcome", "/audit"),
        ("inventory_2", "solution_handover_title", "solution_handover_body", "solution_handover_outcome", "/handover"),
    )
    culture_values = (
        ("platform_value_service_title", "platform_value_service_body"),
        ("platform_value_fairness_title", "platform_value_fairness_body"),
        ("platform_value_clarity_title", "platform_value_clarity_body"),
        ("platform_value_responsibility_title", "platform_value_responsibility_body"),
        ("platform_value_continuity_title", "platform_value_continuity_body"),
    )

    summary = PlatformSummary.unavailable()
    summary_reference = ""
    started_at = perf_counter()
    try:
        summary = load_platform_summary(get_workflow())
    except Exception as error:
        summary_reference = new_operation_reference()
        record_operator_failure(
            error,
            action="load_platform_summary",
            reference=summary_reference,
            started_at=started_at,
        )

    release_labels = {
        "pass": "platform_release_pass",
        "running": "platform_release_running",
        "stale": "platform_release_stale",
        "fail": "platform_release_fail",
        "missing": "platform_release_missing",
        "unreadable": "platform_release_unreadable",
    }
    release_value = t(release_labels.get(summary.release_state, "platform_release_unreadable"))
    if summary.release_total_checks:
        release_value = t(
            "platform_release_checks",
            passed=summary.release_passed_checks,
            total=summary.release_total_checks,
        )

    with page_shell("platform", "/platform", music_context="architecture"):
        with ui.element("section").classes("sy-platform-hero w-full").props(
            f'aria-label="{t("platform")}" data-testid=platform-hero'
        ):
            with ui.column().classes("sy-platform-hero-copy gap-2"):
                ui.label(t("platform_kicker")).classes("sy-architecture-kicker")
                ui.html(t("platform"), tag="h2").classes("sy-architecture-title")
                ui.label(t("platform_intro")).classes("sy-architecture-copy")
                ui.label(t("platform_principle")).classes("sy-platform-principle")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_snapshot_kicker", "platform_snapshot_title", "platform_snapshot_copy", show_kicker=True
            )
            if summary.available:
                metrics = (
                    ("groups", str(summary.active_prefect_count), "platform_metric_prefects", "platform_metric_prefects_note"),
                    ("calendar_view_week", str(summary.roster_count), "platform_metric_rosters", "platform_metric_rosters_note"),
                    ("verified_user", t("verified") if summary.verified_backup else t("handover_attention"), "platform_metric_backup", "platform_metric_backup_note"),
                    ("fact_check", release_value, "platform_metric_release", "platform_metric_release_note"),
                )
                with ui.element("div").classes("sy-platform-snapshot").props(
                    "data-testid=platform-live-summary aria-live=polite"
                ):
                    for icon, value, label_key, note_key in metrics:
                        with ui.element("article").classes("sy-platform-metric"):
                            ui.icon(icon).classes("sy-platform-metric-icon").props("aria-hidden=true")
                            ui.label(value).classes("sy-platform-metric-value")
                            ui.label(t(label_key)).classes("sy-platform-metric-label")
                            ui.label(t(note_key)).classes("sy-platform-metric-note")
            else:
                with ui.element("div").classes("sy-platform-unavailable").props(
                    "role=status data-testid=platform-summary-unavailable"
                ):
                    ui.label(t("platform_snapshot_unavailable_title")).classes("font-semibold")
                    ui.label(t("platform_snapshot_unavailable_body")).classes("mt-2 text-sm leading-6 text-[var(--sy-muted)]")
                    if summary_reference:
                        ui.label(t("error_reference", reference=summary_reference)).classes(
                            "mt-3 text-xs text-[var(--sy-muted)]"
                        )

        with ui.element("section").classes("sy-architecture-section w-full").props(
            f'aria-label="{t("team_operating_model_title")}"'
        ):
            _render_architecture_section_heading(
                "team_operating_model_kicker", "team_operating_model_title", "team_operating_model_copy"
            )
            with ui.element("div").classes("sy-team-operating-model").props("data-testid=team-operating-model"):
                for icon, role_key, function_key, body_key, level in team_roles:
                    with ui.element("article").classes(f"sy-team-role sy-team-role--{level}"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("sy-team-role-icon").props("aria-hidden=true")
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(t(role_key)).classes("sy-team-role-title")
                                ui.label(t(function_key)).classes("sy-team-role-function")
                        ui.label(t(body_key)).classes("sy-team-role-copy")
            ui.label(t("team_operating_model_note")).classes("sy-team-operating-model-note")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading("capability_map_kicker", "capability_map_title", "capability_map_copy")
            with ui.element("div").classes("sy-capability-map").props("data-testid=capability-map"):
                for icon, title_key, body_key, output_key in capability_groups:
                    with ui.element("article").classes("sy-capability-card"):
                        ui.icon(icon).classes("sy-capability-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-capability-title")
                        ui.label(t(body_key)).classes("sy-capability-copy")
                        ui.label(t(output_key)).classes("sy-capability-output")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "solutions_portfolio_kicker", "solutions_portfolio_title", "solutions_portfolio_copy"
            )
            with ui.element("div").classes("sy-solutions-grid").props("data-testid=solutions-portfolio"):
                for icon, title_key, body_key, outcome_key, route in solutions:
                    with ui.element("article").classes("sy-solution-card"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("sy-solution-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-solution-title")
                        ui.label(t(body_key)).classes("sy-solution-copy")
                        ui.label(t(outcome_key)).classes("sy-solution-outcome")
                        ui.button(
                            t("solution_open_workspace"),
                            icon="arrow_forward",
                            on_click=lambda destination=route: ui.navigate.to(destination),
                        ).props("flat").classes("sy-solution-action self-start")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_culture_kicker", "platform_culture_title", "platform_culture_copy"
            )
            with ui.element("div").classes("sy-platform-culture").props("data-testid=platform-principles"):
                for index, (title_key, body_key) in enumerate(culture_values, start=1):
                    with ui.element("article").classes("sy-platform-value"):
                        ui.label(f"{index:02d}").classes("sy-platform-value-index").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-platform-value-title")
                        ui.label(t(body_key)).classes("sy-platform-value-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "platform_resources_kicker", "platform_resources_title", "platform_resources_copy"
            )
            with ui.element("div").classes("sy-platform-resources").props("data-testid=platform-resources"):
                for icon, label_key, route in (
                    ("menu_book", "platform_resource_guide", "/guide"),
                    ("account_tree", "platform_resource_architecture", "/system-architecture"),
                    ("handshake", "platform_resource_handover", "/handover"),
                ):
                    with ui.element("article").classes("sy-platform-resource"):
                        ui.button(
                            t(label_key), icon=icon, on_click=lambda destination=route: ui.navigate.to(destination)
                        ).props("flat")

        _render_feedback_channel()
        _render_co_creation()


@ui.page("/engineering")
def engineering_page() -> None:
    blueprint = (
        ("desktop_windows", "engineering_layer_ui", "engineering_layer_ui_body"),
        ("rule", "engineering_layer_policy", "engineering_layer_policy_body"),
        ("schema", "engineering_layer_core", "engineering_layer_core_body"),
        ("receipt_long", "engineering_layer_workflow", "engineering_layer_workflow_body"),
        ("database", "engineering_layer_evidence", "engineering_layer_evidence_body"),
    )
    gates = (
        ("policy", "engineering_gate_repository"),
        ("security", "engineering_gate_security"),
        ("science", "engineering_gate_tests"),
        ("code", "engineering_gate_compile"),
        ("inventory_2", "engineering_gate_dependencies"),
        ("web", "engineering_gate_browser"),
        ("speed", "engineering_gate_runtime"),
        ("conversion_path", "engineering_gate_workflow"),
        ("dns", "engineering_gate_deployment"),
        ("settings_backup_restore", "engineering_gate_recovery"),
    )
    pillars = (
        ("balance", "engineering_pillar_fairness", "engineering_pillar_fairness_body"),
        ("restore_page", "engineering_pillar_recovery", "engineering_pillar_recovery_body"),
        ("manage_search", "engineering_pillar_observability", "engineering_pillar_observability_body"),
        ("science", "engineering_pillar_practice", "engineering_pillar_practice_body"),
        ("accessibility_new", "engineering_pillar_experience", "engineering_pillar_experience_body"),
        ("laptop_windows", "engineering_pillar_delivery", "engineering_pillar_delivery_body"),
    )
    evolution = (
        ("engineering_evolution_domain", "engineering_evolution_domain_body"),
        ("engineering_evolution_durable", "engineering_evolution_durable_body"),
        ("engineering_evolution_experience", "engineering_evolution_experience_body"),
        ("engineering_evolution_release", "engineering_evolution_release_body"),
    )
    evidence = load_release_evidence()
    release_state_keys = {
        "pass": "platform_release_pass",
        "running": "platform_release_running",
        "stale": "platform_release_stale",
        "fail": "platform_release_fail",
        "missing": "platform_release_missing",
        "unreadable": "platform_release_unreadable",
    }
    evidence_label = (
        t("engineering_release_current", passed=evidence.passed_checks, total=evidence.total_checks)
        if evidence.state == "pass" and evidence.total_checks
        else t("engineering_release_state", state=t(release_state_keys.get(evidence.state, "platform_release_unreadable")))
    )
    evidence_tone = _release_evidence_tone(evidence.state)
    gate_value = (
        f"{evidence.passed_checks:02d}/{evidence.total_checks:02d}"
        if evidence.total_checks
        else t("engineering_fact_unavailable")
    )
    facts = (
        (t("engineering_fact_full_suite"), "science", "engineering_fact_tests", "engineering_fact_tests_body"),
        (gate_value, "verified", "engineering_fact_gates", "engineering_fact_gates_body"),
        ("05", "layers", "engineering_fact_layers", "engineering_fact_layers_body"),
        ("02", "translate", "engineering_fact_languages", "engineering_fact_languages_body"),
    )

    with page_shell("engineering", "/engineering", music_context="architecture"):
        with ui.element("section").classes("sy-engineering-hero w-full").props(
            f'aria-label="{t("engineering")}" data-testid=engineering-hero'
        ):
            with ui.column().classes("gap-2"):
                ui.label(t("engineering_kicker")).classes("sy-architecture-kicker")
                ui.html(t("engineering"), tag="h2").classes("sy-architecture-title")
                ui.label(t("engineering_intro")).classes("sy-architecture-copy")
                _tone_badge(t("engineering_badge"), "stable").classes("mt-3 self-start")

        with ui.element("section").classes("sy-architecture-section w-full"):
            ui.html(t("engineering_facts_title"), tag="h2").classes("sy-architecture-section-title")
            with ui.element("div").classes("sy-engineering-facts").props("data-testid=engineering-facts"):
                for value, icon, title_key, body_key in facts:
                    with ui.element("article").classes("sy-engineering-fact"):
                        with ui.row().classes("items-center justify-between no-wrap"):
                            ui.label(value).classes("sy-engineering-fact-value")
                            ui.icon(icon).classes("sy-engineering-fact-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-fact-title")
                        ui.label(t(body_key)).classes("sy-engineering-fact-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_blueprint_kicker", "engineering_blueprint_title", "engineering_blueprint_copy"
            )
            with ui.element("ol").classes("sy-engineering-blueprint").props("data-testid=engineering-blueprint"):
                for index, (icon, title_key, body_key) in enumerate(blueprint, start=1):
                    with ui.element("li").classes("sy-engineering-blueprint-layer"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.label(f"{index:02d}").classes("sy-engineering-blueprint-index").props("aria-hidden=true")
                            ui.icon(icon).classes("sy-engineering-blueprint-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-blueprint-title")
                        ui.label(t(body_key)).classes("sy-engineering-blueprint-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_pipeline_kicker", "engineering_pipeline_title", "engineering_pipeline_copy", show_kicker=True
            )
            _tone_badge(evidence_label, evidence_tone).classes("self-start")
            with ui.element("ol").classes("sy-engineering-gates").props("data-testid=engineering-gates"):
                for index, (icon, title_key) in enumerate(gates, start=1):
                    with ui.element("li").classes("sy-engineering-gate"):
                        ui.label(f"{index:02d}").classes("sy-engineering-gate-index")
                        ui.icon(icon).classes(f"sy-engineering-gate-icon sy-fg-{evidence_tone}").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-gate-title")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_pillars_kicker", "engineering_pillars_title", "engineering_pillars_copy"
            )
            with ui.element("div").classes("sy-engineering-pillars").props("data-testid=engineering-pillars"):
                for icon, title_key, body_key in pillars:
                    with ui.element("article").classes("sy-engineering-pillar"):
                        ui.icon(icon).classes("sy-engineering-pillar-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-engineering-pillar-title")
                        ui.label(t(body_key)).classes("sy-engineering-pillar-copy")

        with ui.element("section").classes("sy-architecture-section w-full"):
            _render_architecture_section_heading(
                "engineering_evolution_kicker", "engineering_evolution_title", "engineering_evolution_copy"
            )
            with ui.element("ol").classes("sy-engineering-evolution").props("data-testid=engineering-evolution"):
                for title_key, body_key in evolution:
                    with ui.element("li").classes("sy-engineering-evolution-item"):
                        ui.label(t(title_key)).classes("sy-engineering-evolution-title")
                        ui.label(t(body_key)).classes("sy-engineering-evolution-copy")

        with ui.element("section").classes("sy-engineering-resources w-full"):
            ui.html(t("engineering_resources_title"), tag="h2").classes("sy-architecture-section-title")
            with ui.row().classes("gap-3 flex-wrap mt-4"):
                ui.link(t("engineering_open_github"), GITHUB_REPOSITORY_URL, new_tab=True).props(
                    'rel="noopener noreferrer"'
                ).classes("sy-engineering-resource-link")
                ui.button(
                    t("engineering_open_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")
                ).props("outline")
                ui.button(
                    t("engineering_open_platform"), icon="domain", on_click=lambda: ui.navigate.to("/platform")
                ).props("flat")


@ui.page("/system-architecture")
def system_architecture_page() -> None:
    layers = (
        ("desktop_windows", "architecture_ui_title", "architecture_ui_body"),
        ("rule", "architecture_policy_title", "architecture_policy_body"),
        ("receipt_long", "architecture_workflow_title", "architecture_workflow_body"),
        ("shield", "architecture_safety_title", "architecture_safety_body"),
        ("archive", "architecture_handover_title", "architecture_handover_body"),
    )
    service_flow = (
        ("groups", "architecture_flow_prepare_title", "architecture_flow_prepare_body", "architecture_flow_prepare_result"),
        ("edit_calendar", "architecture_flow_draft_title", "architecture_flow_draft_body", "architecture_flow_draft_result"),
        ("verified", "architecture_flow_publish_title", "architecture_flow_publish_body", "architecture_flow_publish_result"),
        ("picture_as_pdf", "architecture_flow_export_title", "architecture_flow_export_body", "architecture_flow_export_result"),
        ("person_off", "architecture_flow_adjust_title", "architecture_flow_adjust_body", "architecture_flow_adjust_result"),
        ("inventory_2", "architecture_flow_handover_title", "architecture_flow_handover_body", "architecture_flow_handover_result"),
    )
    evidence = (
        ("gavel", "architecture_evidence_policy_title", "architecture_evidence_policy_body", "architecture_evidence_policy_label"),
        ("balance", "architecture_evidence_ledger_title", "architecture_evidence_ledger_body", "architecture_evidence_ledger_label"),
        ("restore_page", "architecture_evidence_recovery_title", "architecture_evidence_recovery_body", "architecture_evidence_recovery_label"),
        ("lock", "architecture_evidence_privacy_title", "architecture_evidence_privacy_body", "architecture_evidence_privacy_label"),
    )
    faq_items = (
        ("faq_draft_q", "faq_draft_a"),
        ("faq_publish_q", "faq_publish_a"),
        ("faq_leave_q", "faq_leave_a"),
        ("faq_names_q", "faq_names_a"),
        ("faq_storage_q", "faq_storage_a"),
        ("faq_restore_q", "faq_restore_a"),
        ("faq_remote_q", "faq_remote_a"),
        ("faq_support_q", "faq_support_a"),
        ("faq_music_q", "faq_music_a"),
    )
    with page_shell("system_architecture", "/system-architecture", music_context="architecture"):
        with ui.element("section").classes("sy-architecture-hero w-full").props(f'aria-label="{t("system_architecture")}"'):
            with ui.column().classes("gap-2"):
                ui.label(t("architecture_kicker")).classes("sy-architecture-kicker")
                ui.html(t("system_architecture"), tag="h2").classes("sy-architecture-title")
                ui.label(t("architecture_intro")).classes("sy-architecture-copy")
                _tone_badge(t("architecture_local_badge"), "stable").classes("mt-3 self-start")
                ui.label(t("architecture_reading_note")).classes("sy-architecture-reading-note")
                ui.label(t("architecture_platform_link_note")).classes("sy-architecture-reading-note")
                ui.button(t("open_platform"), icon="domain", on_click=lambda: ui.navigate.to("/platform")).props(
                    "outline data-testid=architecture-open-platform"
                ).classes("mt-2 self-start")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_flow_title")}"'):
            _render_architecture_section_heading(
                "architecture_flow_kicker", "architecture_flow_title", "architecture_flow_copy", show_kicker=True
            )
            ui.element("div").classes("sy-architecture-lifeline-visual w-full").props("aria-hidden=true data-testid=architecture-lifeline-visual")
            with ui.element("ol").classes("sy-service-lifeline").props("data-testid=service-lifeline"):
                for index, (icon, title_key, body_key, result_key) in enumerate(service_flow, start=1):
                    with ui.element("li").classes("sy-service-stage"):
                        with ui.row().classes("sy-service-stage-head items-center gap-3 no-wrap"):
                            ui.label(f"{index:02d}").classes("sy-service-stage-index").props("aria-hidden=true")
                            ui.icon(icon).classes("sy-service-stage-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-service-stage-title")
                        ui.label(t(body_key)).classes("sy-service-stage-copy")
                        ui.label(t(result_key)).classes("sy-service-stage-result")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_layers_title")}"'):
            _render_architecture_section_heading("architecture_layers_kicker", "architecture_layers_title", "architecture_layers_copy")
        with ui.element("section").classes("sy-architecture-grid w-full").props(f'aria-label="{t("architecture_layers_title")}"'):
            for icon, title_key, body_key in layers:
                with ui.element("article").classes("sy-architecture-layer"):
                    ui.icon(icon).classes("sy-architecture-layer-icon").props("aria-hidden=true")
                    ui.label(t(title_key)).classes("sy-architecture-layer-title")
                    ui.label(t(body_key)).classes("sy-architecture-layer-copy")

        with ui.element("section").classes("sy-architecture-section w-full").props(f'aria-label="{t("architecture_evidence_title")}"'):
            _render_architecture_section_heading("architecture_evidence_kicker", "architecture_evidence_title", "architecture_evidence_copy")
            with ui.element("div").classes("sy-trust-evidence-grid").props("data-testid=trust-evidence"):
                for icon, title_key, body_key, label_key in evidence:
                    with ui.element("article").classes("sy-trust-evidence-card"):
                        ui.icon(icon).classes("sy-trust-evidence-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-trust-evidence-title")
                        ui.label(t(body_key)).classes("sy-trust-evidence-copy")
                        ui.label(t(label_key)).classes("sy-trust-evidence-label")

        with ui.element("section").classes("sy-architecture-faq w-full").props(f'aria-label="{t("architecture_faq_title")}" data-testid=architecture-faq'):
            _render_architecture_section_heading("architecture_faq_kicker", "architecture_faq_title", "architecture_faq_copy")
            with ui.column().classes("sy-architecture-faq-list w-full gap-2"):
                for question_key, answer_key in faq_items:
                    with ui.expansion(t(question_key), icon="help_outline").classes("sy-architecture-faq-item w-full"):
                        ui.label(t(answer_key)).classes("sy-architecture-faq-answer")
        _render_feedback_channel()


def _render_architecture_section_heading(
    kicker_key: str,
    title_key: str,
    copy_key: str,
    *,
    show_kicker: bool = False,
) -> None:
    with ui.column().classes("sy-architecture-section-heading gap-1"):
        if show_kicker:
            ui.label(t(kicker_key)).classes("sy-architecture-section-kicker")
        ui.html(t(title_key), tag="h2").classes("sy-architecture-section-title").props(
            f"id={title_key}-heading"
        )
        ui.label(t(copy_key)).classes("sy-architecture-section-copy")
