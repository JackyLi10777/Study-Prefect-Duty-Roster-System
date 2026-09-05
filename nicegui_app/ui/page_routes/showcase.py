"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from time import perf_counter
from collections.abc import Callable

from nicegui import ui
from roster_core import load_devotional_seed

from nicegui_app.contact import GITHUB_REPOSITORY_URL
from nicegui_app.observability import new_operation_reference, record_operator_failure
from nicegui_app.release_evidence import load_release_evidence
from nicegui_app.runtime import get_workflow
from nicegui_app.ui.components import (
    code_sample,
    editorial_heading,
    empty_state,
    motion_pattern,
    reference_pager,
    responsive_table,
    status,
)
from nicegui_app.ui.brand import render_service_weave_mark
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.lazy_sections import lazy_expansion
from nicegui_app.ui.reading_navigation import ReadingNavigation, reading_toc
from nicegui_app.ui.page_shared import _render_co_creation, _render_feedback_channel
from nicegui_app.ui.platform_summary import PlatformSummary, load_platform_summary
from nicegui_app.ui.shell import page_shell


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

def _trust_article(classes: str) -> ui.element:
    """Use separators instead of stacked card surfaces on reading pages."""
    return ui.element("article").classes(classes).style(
        "background: transparent; box-shadow: none; border-radius: 0; "
        "border-width: 0 0 1px; padding: 12px 0"
    )


def _trust_section(navigation: ReadingNavigation, anchor: str, title_key: str,
                   test_id: str, render: Callable[[], None]) -> ui.expansion:
    """Keep source-owned anchors outside retained NiceGUI expansion identities."""
    with ui.element("section").classes("w-full max-w-4xl").props(f"id={anchor}"):
        panel = lazy_expansion(t(title_key), icon="expand_more", test_id=test_id, render=render)
    navigation.register(anchor, lambda: panel.set_value(True))
    return panel


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
    operating_map = (
        ("touch_app", "platform_map_intent_title", "platform_map_intent_body"),
        ("space_dashboard", "platform_map_ui_title", "platform_map_ui_body"),
        ("rule", "platform_map_policy_title", "platform_map_policy_body"),
        ("receipt_long", "platform_map_workflow_title", "platform_map_workflow_body"),
        ("database", "platform_map_evidence_title", "platform_map_evidence_body"),
        ("picture_as_pdf", "platform_map_output_title", "platform_map_output_body"),
    )

    with page_shell("/platform"):
        navigation = ReadingNavigation()
        with ui.element("section").classes("w-full max-w-4xl").props(
            f'aria-label="{attr(t("platform"))}" data-testid=platform-hero'
        ):
            with ui.column().classes("sy-platform-hero-copy gap-2"):
                with ui.row().classes("sy-platform-brand-lockup items-center gap-3 no-wrap"):
                    render_service_weave_mark(context="display", test_id="platform-product-mark")
                    with ui.column().classes("gap-0 min-w-0"):
                        ui.label(t("service_weave_name")).classes("sy-platform-brand-name")
                        ui.label(t("app_name")).classes("sy-platform-brand-function")
                ui.label(t("platform_intro")).classes("sy-architecture-copy")

        ui.button(t("dashboard"), icon="space_dashboard", on_click=lambda: navigate_to("/")).props(
            "color=primary data-testid=platform-open-workspace"
        )
        reading_toc(
            (
                ("platform-snapshot-section", "platform_snapshot_title"),
                ("platform-team-section", "team_operating_model_title"),
                ("platform-operating-map-section", "platform_operating_map_title"),
                ("platform-capabilities-section", "capability_map_title"),
                ("platform-solutions-section", "solutions_portfolio_title"),
                ("platform-convictions-section", "platform_convictions_title"),
                ("platform-principles-section", "platform_culture_title"),
                ("platform-resources-section", "platform_resources_title"),
            )
        )

        def render_platform_snapshot_section() -> None:
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
            with ui.element("section").classes("w-full"):
                _render_architecture_section_heading(
                    "platform_snapshot_kicker", "platform_snapshot_title", "platform_snapshot_copy"
                )
                if summary.available:
                    ui.label(t(release_labels.get(summary.release_state, "platform_release_unreadable"))).props(
                        "role=status data-testid=platform-release-state"
                    ).classes(f"font-semibold sy-fg-{_release_evidence_tone(summary.release_state)}")
                    metrics = (
                        ("groups", str(summary.active_prefect_count), "platform_metric_prefects", "platform_metric_prefects_note"),
                        ("calendar_view_week", str(summary.roster_count), "platform_metric_rosters", "platform_metric_rosters_note"),
                        ("verified_user", t("verified") if summary.verified_backup else t("handover_attention"), "platform_metric_backup", "platform_metric_backup_note"),
                        ("fact_check", release_value, "platform_metric_release", "platform_metric_release_note"),
                    )
                    with ui.element("div").classes("sy-platform-snapshot").style("display: flex; flex-direction: column").props(
                        "data-testid=platform-live-summary aria-live=polite"
                    ):
                        for icon, value, label_key, note_key in metrics:
                            with _trust_article("sy-platform-metric"):
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

        _trust_section(navigation, "platform-snapshot-section", "platform_snapshot_title",
                       "platform-summary-details", render_platform_snapshot_section)

        def render_platform_team_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("team_operating_model_title"))}"'
            ):
                _render_architecture_section_heading(
                    "team_operating_model_kicker", "team_operating_model_title", "team_operating_model_copy"
                )
                with ui.element("div").classes("sy-team-operating-model").style("display: flex; flex-direction: column").props("data-testid=team-operating-model"):
                    for icon, role_key, function_key, body_key, level in team_roles:
                        with _trust_article(f"sy-team-role sy-team-role--{level}"):
                            with ui.row().classes("items-center gap-3 no-wrap"):
                                ui.icon(icon).classes("sy-team-role-icon").props("aria-hidden=true")
                                with ui.column().classes("gap-0 min-w-0"):
                                    ui.label(t(role_key)).classes("sy-team-role-title")
                                    ui.label(t(function_key)).classes("sy-team-role-function")
                            ui.label(t(body_key)).classes("sy-team-role-copy")
                ui.label(t("team_operating_model_note")).classes("sy-team-operating-model-note")

        _trust_section(navigation, "platform-team-section", "team_operating_model_title",
                       "platform-team-details", render_platform_team_section)

        def render_platform_operating_map_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("platform_operating_map_title"))}"'
            ):
                _render_architecture_section_heading(
                    "platform_operating_map_kicker",
                    "platform_operating_map_title",
                    "platform_operating_map_copy",
                )
                with motion_pattern(
                    "platform-continuity",
                    classes="sy-platform-operating-map",
                    test_id="platform-operating-map",
                    props="role=list",
                ):
                    for index, (icon, title_key, body_key) in enumerate(operating_map, start=1):
                        with _trust_article("sy-platform-map-node").props(
                            f"role=listitem data-sequence={index} data-sy-motion-item"
                        ):
                            with ui.row().classes("sy-platform-map-node-head items-center gap-3 no-wrap"):
                                ui.icon(icon).classes("sy-platform-map-node-icon").props("aria-hidden=true")
                                ui.label(t(title_key)).classes("sy-platform-map-node-title")
                            ui.label(t(body_key)).classes("sy-platform-map-node-copy")
                ui.label(t("platform_operating_map_note")).classes("sy-platform-operating-map-note")

        _trust_section(navigation, "platform-operating-map-section", "platform_operating_map_title",
                       "platform-operating-map-details", render_platform_operating_map_section)

        def render_platform_capabilities_section() -> None:
            with ui.element("section").classes("w-full"):
                _render_architecture_section_heading("capability_map_kicker", "capability_map_title", "capability_map_copy")
                with ui.element("div").classes("sy-capability-map").style("display: flex; flex-direction: column").props("data-testid=capability-map"):
                    for icon, title_key, body_key, output_key in capability_groups:
                        with _trust_article("sy-capability-card"):
                            ui.icon(icon).classes("sy-capability-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-capability-title")
                            ui.label(t(body_key)).classes("sy-capability-copy")
                            ui.label(t(output_key)).classes("sy-capability-output")

        _trust_section(navigation, "platform-capabilities-section", "capability_map_title",
                       "platform-capabilities-details", render_platform_capabilities_section)

        def render_platform_solutions_section() -> None:
            with ui.element("section").classes("w-full"):
                _render_architecture_section_heading(
                    "solutions_portfolio_kicker", "solutions_portfolio_title", "solutions_portfolio_copy"
                )
                with ui.element("div").classes("sy-solutions-grid").style("display: flex; flex-direction: column").props("data-testid=solutions-portfolio"):
                    for icon, title_key, body_key, outcome_key, route in solutions:
                        with _trust_article("sy-solution-card"):
                            with ui.row().classes("items-center gap-3 no-wrap"):
                                ui.icon(icon).classes("sy-solution-icon").props("aria-hidden=true")
                                ui.label(t(title_key)).classes("sy-solution-title")
                            ui.label(t(body_key)).classes("sy-solution-copy")
                            ui.label(t(outcome_key)).classes("sy-solution-outcome")
                            ui.button(
                                t("solution_open_workspace"),
                                icon="arrow_forward",
                                on_click=lambda destination=route: navigate_to(destination),
                            ).props("flat").classes("sy-solution-action self-start")

        _trust_section(navigation, "platform-solutions-section", "solutions_portfolio_title",
                       "platform-solutions-details", render_platform_solutions_section)

        def render_platform_convictions_section() -> None:
            acts_conviction = next(entry for entry in load_devotional_seed() if entry.id == "dv-0122")
            acts_scripture_en = acts_conviction.scripture_en.removesuffix(" (NKJV)")
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("platform_convictions_title"))}" '
                'data-testid=platform-core-convictions'
            ):
                _render_architecture_section_heading(
                    "platform_convictions_kicker", "platform_convictions_title", "platform_convictions_copy"
                )
                with ui.element("div").classes("sy-platform-convictions").style("display: flex; flex-direction: column"):
                    with _trust_article(
                        "sy-platform-conviction sy-platform-conviction--direction"
                    ).props("data-testid=platform-conviction-direction"):
                        ui.icon("volunteer_activism").classes("sy-platform-conviction-icon").props("aria-hidden=true")
                        ui.label(t("platform_conviction_why_label")).classes("sy-platform-conviction-label")
                        ui.label(t("platform_conviction_why_title")).classes("sy-platform-conviction-title")
                        ui.label(t("service_principle")).classes("sy-platform-conviction-principle")
                        ui.label(t("platform_conviction_principle_label")).classes(
                            "sy-platform-conviction-reference"
                        )
                        ui.label(t("platform_conviction_why_body")).classes("sy-platform-conviction-copy")

                    with _trust_article(
                        "sy-platform-conviction sy-platform-conviction--conscience"
                    ).props("data-testid=platform-conviction-conscience"):
                        ui.icon("verified_user").classes("sy-platform-conviction-icon").props("aria-hidden=true")
                        ui.label(t("platform_conviction_how_label")).classes("sy-platform-conviction-label")
                        ui.label(t("platform_conviction_how_title")).classes("sy-platform-conviction-title")
                        ui.label(t("platform_conviction_how_body")).classes("sy-platform-conviction-copy")
                        with ui.element("div").classes("sy-platform-scriptures"):
                            with ui.element("blockquote").classes("sy-platform-scripture").props("lang=zh-Hant"):
                                ui.label(f"「{acts_conviction.scripture_zh}」").classes("sy-platform-scripture-text")
                                ui.label(
                                    f"{acts_conviction.reference_zh} · {t('platform_conviction_zh_translation')}"
                                ).classes("sy-platform-scripture-cite")
                                ui.link(
                                    t("platform_conviction_zh_source"),
                                    "https://www.bible.com/bible/2625/ACT.24.16.%E5%92%8C%E5%90%88%E6%9C%AC2010%20-%20%E7%A5%9E%E7%89%88",
                                    new_tab=True,
                                ).props(
                                    f'target=_blank rel="noopener noreferrer" referrerpolicy=no-referrer '
                                    f'aria-label="{attr(t("platform_conviction_zh_source"))}"'
                                ).classes("sy-platform-scripture-source")
                            with ui.element("blockquote").classes("sy-platform-scripture").props("lang=en"):
                                ui.label(f'“{acts_scripture_en}”').classes("sy-platform-scripture-text")
                                ui.label(
                                    f"{acts_conviction.reference_en} · {t('platform_conviction_en_translation')}"
                                ).classes("sy-platform-scripture-cite")
                                ui.link(
                                    t("platform_conviction_en_source"),
                                    "https://www.bible.com/bible/114/ACT.24.16.NKJV",
                                    new_tab=True,
                                ).props(
                                    f'target=_blank rel="noopener noreferrer" referrerpolicy=no-referrer '
                                    f'aria-label="{attr(t("platform_conviction_en_source"))}"'
                                ).classes("sy-platform-scripture-source")

        _trust_section(navigation, "platform-convictions-section", "platform_convictions_title",
                       "platform-convictions-details", render_platform_convictions_section)

        def render_platform_principles_section() -> None:
            with ui.element("section").classes("w-full"):
                _render_architecture_section_heading(
                    "platform_culture_kicker", "platform_culture_title", "platform_culture_copy"
                )
                with ui.element("div").classes("sy-platform-culture").style("display: flex; flex-direction: column").props("data-testid=platform-principles"):
                    for index, (title_key, body_key) in enumerate(culture_values, start=1):
                        with _trust_article("sy-platform-value"):
                            ui.label(f"{index:02d}").classes("sy-platform-value-index").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-platform-value-title")
                            ui.label(t(body_key)).classes("sy-platform-value-copy")

        _trust_section(navigation, "platform-principles-section", "platform_culture_title",
                       "platform-principles-details", render_platform_principles_section)

        def render_platform_resources_section() -> None:
            with ui.element("section").classes("w-full"):
                _render_architecture_section_heading(
                    "platform_resources_kicker", "platform_resources_title", "platform_resources_copy"
                )
                with ui.element("div").classes("sy-platform-resources").style("display: flex; flex-direction: column").props("data-testid=platform-resources"):
                    for icon, label_key, route in (
                        ("menu_book", "platform_resource_guide", "/guide"),
                        ("account_tree", "platform_resource_architecture", "/system-architecture"),
                        ("handshake", "platform_resource_handover", "/handover"),
                    ):
                        with _trust_article("sy-platform-resource"):
                            ui.button(
                                t(label_key), icon=icon, on_click=lambda destination=route: navigate_to(destination)
                            ).props("flat")

        _trust_section(navigation, "platform-resources-section", "platform_resources_title",
                       "platform-resources-details", render_platform_resources_section)

        _render_feedback_channel(compact=True)
        attribution = _trust_section(navigation, "platform-attribution-section", "co_creation_title",
                                     "platform-attribution-details", _render_co_creation)
        navigation.register("co-creation-title", lambda: attribution.set_value(True))
        navigation.install()
        reference_pager(next_=("/system-architecture", "system_architecture"))


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
        ("policy", "engineering_gate_repository", "repository"),
        ("security", "engineering_gate_security", "repository"),
        ("cloud_done", "engineering_gate_cloudflare", "access"),
        ("science", "engineering_gate_tests", "quality"),
        ("code", "engineering_gate_compile", "quality"),
        ("inventory_2", "engineering_gate_dependencies", "repository"),
        ("web", "engineering_gate_browser", "quality"),
        ("speed", "engineering_gate_runtime", "runtime"),
        ("conversion_path", "engineering_gate_workflow", "quality"),
        ("smartphone", "engineering_gate_mobile", "quality"),
        ("dns", "engineering_gate_deployment", "runtime"),
        ("verified_user", "engineering_gate_guest", "access"),
        ("settings_backup_restore", "engineering_gate_recovery", "recovery"),
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
    evidence_date = evidence.finished_at.date().isoformat() if evidence.finished_at else ""
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
        ("≈10B", "memory", "engineering_fact_ai_tokens", "engineering_fact_ai_tokens_body"),
    )

    with page_shell("/engineering"):
        navigation = ReadingNavigation()
        with ui.element("section").classes("w-full max-w-4xl").props(
            f'aria-label="{attr(t("engineering"))}" data-testid=engineering-hero'
        ):
            with ui.column().classes("gap-2"):
                ui.label(t("engineering_intro")).classes("sy-architecture-copy")

        ui.label(t(release_state_keys.get(evidence.state, "platform_release_unreadable"))).props(
            "role=status data-testid=engineering-release-state"
        ).classes(f"font-semibold sy-fg-{evidence_tone}")
        ui.label(evidence_label).classes("text-sm text-[var(--sy-muted)]")
        ui.label(
            f'{t("engineering_coverage_report_date")}: '
            f'{evidence_date or t("engineering_report_date_unavailable")}'
        ).classes("text-sm text-[var(--sy-muted)]").props("data-testid=engineering-release-date")
        reading_toc(
            (
                ("engineering-facts-section", "engineering_facts_title"),
                ("engineering-evidence-index-section", "engineering_coverage_title"),
                ("engineering-blueprint-section", "engineering_blueprint_title"),
                ("engineering-release-section", "engineering_pipeline_title"),
                ("engineering-pillars-section", "engineering_pillars_title"),
                ("engineering-evolution-section", "engineering_evolution_title"),
                ("engineering-resources-section", "engineering_resources_title"),
            )
        )

        def render_engineering_facts_section() -> None:
            with ui.element("section").classes("w-full").props(""):
                ui.html(t("engineering_facts_title"), tag="h2").classes("sy-architecture-section-title")
                with ui.element("div").classes("sy-engineering-facts").style("display: flex; flex-direction: column").props("data-testid=engineering-facts"):
                    for value, icon, title_key, body_key in facts:
                        with _trust_article("sy-engineering-fact"):
                            with ui.row().classes("items-center justify-between no-wrap"):
                                ui.label(value).classes("sy-engineering-fact-value")
                                ui.icon(icon).classes("sy-engineering-fact-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-engineering-fact-title")
                            ui.label(t(body_key)).classes("sy-engineering-fact-copy")

        _trust_section(navigation, "engineering-facts-section", "engineering_facts_title",
                       "engineering-facts-details", render_engineering_facts_section)

        evidence_records = [
            {
                "id": f"gate-{index}",
                "item": t(title_key),
                "type_code": type_code,
                "type": t(f"engineering_evidence_type_{type_code}"),
                "icon": icon,
            }
            for index, (icon, title_key, type_code) in enumerate(gates, start=1)
        ]

        def render_engineering_evidence_index_section() -> None:
            with ui.element("section").classes("w-full").props(
                " data-testid=engineering-evidence-index"
            ):
                editorial_heading(
                    kicker=t("engineering_evidence_kicker"),
                    title=t("engineering_coverage_title"),
                    copy=t("engineering_coverage_copy"),
                    anchor_id="engineering-evidence-title",
                )
                type_options = {
                    "all": t("engineering_evidence_all"),
                    **{
                        code: t(f"engineering_evidence_type_{code}")
                        for code in ("repository", "access", "quality", "runtime", "recovery")
                    },
                }
                state_options = {
                    "all": t("engineering_evidence_all"),
                    **{
                        state_name: t(release_state_keys[state_name])
                        for state_name in ("pass", "running", "stale", "fail", "missing", "unreadable")
                    },
                }
                with ui.element("div").classes("sy-evidence-toolbar"):
                    type_filter = ui.select(
                        type_options,
                        value="all",
                        label=t("engineering_evidence_type"),
                    ).props("data-testid=engineering-evidence-type-filter").classes("sy-evidence-filter")
                    state_filter = ui.select(
                        state_options,
                        value="all",
                        label=t("engineering_coverage_report_status"),
                    ).props("data-testid=engineering-evidence-state-filter").classes("sy-evidence-filter")
                    date_filter = ui.input(label=t("engineering_coverage_report_date")).props(
                        "type=date clearable data-testid=engineering-evidence-date-filter"
                    ).classes("sy-evidence-filter")
                    view_filter = ui.toggle(
                        {
                            "summary": t("engineering_evidence_summary"),
                            "table": t("engineering_evidence_table"),
                        },
                        value="summary",
                    ).props(f'aria-label="{attr(t("engineering_evidence_view"))}" data-testid=engineering-evidence-view-filter').classes(
                        "sy-evidence-view-toggle"
                    )

                results = ui.element("div").classes("sy-evidence-results w-full").props(
                    "aria-live=polite data-testid=engineering-evidence-results"
                )

                def render_evidence_results() -> None:
                    results.classes(add="sy-evidence-results--filtering")
                    filtered = [
                        row
                        for row in evidence_records
                        if (type_filter.value == "all" or row["type_code"] == type_filter.value)
                        and (state_filter.value == "all" or evidence.state == state_filter.value)
                        and (not date_filter.value or evidence_date == date_filter.value)
                    ]
                    results.clear()
                    with results:
                        if not filtered:
                            empty_state(
                                title=t("engineering_evidence_no_results"),
                                body=t("engineering_evidence_no_results_body"),
                                icon="filter_alt_off",
                                test_id="engineering-evidence-empty",
                            )
                        elif view_filter.value == "table":
                            responsive_table(
                                rows=filtered,
                                columns=[
                                    {
                                        "name": "item",
                                        "label": t("engineering_evidence_col_item"),
                                        "field": "item",
                                        "align": "left",
                                    },
                                    {
                                        "name": "type",
                                        "label": t("engineering_evidence_col_type"),
                                        "field": "type",
                                        "align": "left",
                                    },
                                ],
                                row_key="id",
                                test_id="engineering-evidence-table",
                            )
                        else:
                            with ui.element("div").classes("sy-evidence-summary-grid").style("display: flex; flex-direction: column"):
                                for row in filtered:
                                    with _trust_article("sy-evidence-record").props("data-testid=engineering-coverage-item"):
                                        with ui.row().classes("items-center justify-between gap-3 no-wrap"):
                                            ui.icon(str(row["icon"])).classes(
                                                "sy-evidence-record-icon"
                                            ).props("aria-hidden=true")
                                        ui.label(str(row["item"])).classes("sy-evidence-record-title")
                                        ui.label(t("engineering_coverage_record_copy")).classes(
                                            "sy-evidence-record-copy"
                                        )
                                        ui.label(str(row["type"])).classes(
                                            "sy-evidence-record-meta"
                                        )
                    ui.run_javascript(
                        """
                        requestAnimationFrame(() => requestAnimationFrame(() => {
                          document.querySelector('[data-testid="engineering-evidence-results"]')
                            ?.classList.remove('sy-evidence-results--filtering');
                        }));
                        """
                    )

                for control in (type_filter, state_filter, date_filter, view_filter):
                    control.on_value_change(lambda _event: render_evidence_results())
                render_evidence_results()

        coverage = _trust_section(navigation, "engineering-evidence-index-section", "engineering_coverage_title",
                                  "engineering-coverage-details", render_engineering_evidence_index_section)
        navigation.register("engineering-evidence-title", lambda: coverage.set_value(True))

        def render_engineering_blueprint_section() -> None:
            with ui.element("section").classes("w-full").props(""):
                _render_architecture_section_heading(
                    "engineering_blueprint_kicker", "engineering_blueprint_title", "engineering_blueprint_copy"
                )
                with ui.element("ol").classes("sy-engineering-blueprint").style("display: flex; flex-direction: column").props("data-testid=engineering-blueprint"):
                    for index, (icon, title_key, body_key) in enumerate(blueprint, start=1):
                        with ui.element("li").classes("sy-engineering-blueprint-layer"):
                            with ui.row().classes("items-center gap-3 no-wrap"):
                                ui.label(f"{index:02d}").classes("sy-engineering-blueprint-index").props("aria-hidden=true")
                                ui.icon(icon).classes("sy-engineering-blueprint-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-engineering-blueprint-title")
                            ui.label(t(body_key)).classes("sy-engineering-blueprint-copy")

        _trust_section(navigation, "engineering-blueprint-section", "engineering_blueprint_title",
                       "engineering-blueprint-details", render_engineering_blueprint_section)

        def render_engineering_release_section() -> None:
            with ui.element("section").classes("w-full").props(""):
                _render_architecture_section_heading(
                    "engineering_pipeline_kicker", "engineering_pipeline_title", "engineering_pipeline_copy"
                )
                with ui.element("ol").classes("sy-engineering-gates").style("display: flex; flex-direction: column").props("data-testid=engineering-gates"):
                    for index, (icon, title_key, _type_code) in enumerate(gates, start=1):
                        with ui.element("li").classes("sy-engineering-gate"):
                            ui.label(f"{index:02d}").classes("sy-engineering-gate-index")
                            ui.icon(icon).classes("sy-engineering-gate-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-engineering-gate-title")

        _trust_section(navigation, "engineering-release-section", "engineering_pipeline_title",
                       "engineering-process-details", render_engineering_release_section)

        def render_engineering_pillars_section() -> None:
            with ui.element("section").classes("w-full").props(""):
                _render_architecture_section_heading(
                    "engineering_pillars_kicker", "engineering_pillars_title", "engineering_pillars_copy"
                )
                with ui.element("div").classes("sy-engineering-pillars").style("display: flex; flex-direction: column").props("data-testid=engineering-pillars"):
                    for icon, title_key, body_key in pillars:
                        with _trust_article("sy-engineering-pillar"):
                            ui.icon(icon).classes("sy-engineering-pillar-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-engineering-pillar-title")
                            ui.label(t(body_key)).classes("sy-engineering-pillar-copy")

        _trust_section(navigation, "engineering-pillars-section", "engineering_pillars_title",
                       "engineering-pillars-details", render_engineering_pillars_section)

        def render_engineering_evolution_section() -> None:
            with ui.element("section").classes("w-full").props(""):
                _render_architecture_section_heading(
                    "engineering_evolution_kicker", "engineering_evolution_title", "engineering_evolution_copy"
                )
                with ui.element("ol").classes("sy-engineering-evolution").style("display: flex; flex-direction: column").props("data-testid=engineering-evolution"):
                    for title_key, body_key in evolution:
                        with ui.element("li").classes("sy-engineering-evolution-item"):
                            ui.label(t(title_key)).classes("sy-engineering-evolution-title")
                            ui.label(t(body_key)).classes("sy-engineering-evolution-copy")

        _trust_section(navigation, "engineering-evolution-section", "engineering_evolution_title",
                       "engineering-evolution-details", render_engineering_evolution_section)

        def render_engineering_resources_section() -> None:
            with ui.element("section").classes("sy-engineering-resources w-full").props(""):
                ui.html(t("engineering_resources_title"), tag="h2").classes("sy-architecture-section-title")
                with ui.row().classes("gap-3 flex-wrap mt-4"):
                    ui.link(t("engineering_open_github"), GITHUB_REPOSITORY_URL, new_tab=True).props(
                        'rel="noopener noreferrer"'
                    ).classes("sy-engineering-resource-link")
                    ui.button(
                        t("engineering_open_architecture"), icon="account_tree", on_click=lambda: navigate_to("/system-architecture")
                    ).props("outline")
                    ui.button(
                        t("engineering_open_platform"), icon="domain", on_click=lambda: navigate_to("/platform")
                    ).props("flat")

        _trust_section(navigation, "engineering-resources-section", "engineering_resources_title",
                       "engineering-resources-details", render_engineering_resources_section)

        navigation.install()
        reference_pager(previous=("/system-architecture", "system_architecture"))


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
    with page_shell("/system-architecture"):
        navigation = ReadingNavigation()
        with ui.element("section").classes("w-full max-w-4xl").props(
            f'aria-label="{attr(t("system_architecture"))}"'
        ):
            with ui.column().classes("gap-2"):
                ui.label(t("architecture_intro")).classes("sy-architecture-copy")
                status(t("architecture_local_badge"), "stable").classes("mt-3 self-start")
                ui.button(t("open_platform"), icon="domain", on_click=lambda: navigate_to("/platform")).props(
                    "outline data-testid=architecture-open-platform"
                ).classes("mt-2 self-start")

        ui.label(t("architecture_lifecycle_summary")).classes("w-full max-w-4xl text-sm leading-7")
        reading_toc(
            (
                ("architecture-flow-section", "architecture_flow_title"),
                ("architecture-layers-section", "architecture_layers_title"),
                ("architecture-evidence-section", "architecture_evidence_title"),
                ("architecture-developer-section", "developer_reference_title"),
                ("architecture-faq-section", "architecture_faq_title"),
            )
        )

        def render_architecture_flow_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("architecture_flow_title"))}"'
            ):
                _render_architecture_section_heading(
                    "architecture_flow_kicker", "architecture_flow_title", "architecture_flow_copy"
                )
                ui.element("div").classes("sy-architecture-lifeline-visual w-full").props("aria-hidden=true data-testid=architecture-lifeline-visual")
                with ui.element("ol").classes("sy-service-lifeline").style("display: flex; flex-direction: column").props("data-testid=service-lifeline"):
                    for index, (icon, title_key, body_key, result_key) in enumerate(service_flow, start=1):
                        with ui.element("li").classes("sy-service-stage"):
                            with ui.row().classes("sy-service-stage-head items-center gap-3 no-wrap"):
                                ui.label(f"{index:02d}").classes("sy-service-stage-index").props("aria-hidden=true")
                                ui.icon(icon).classes("sy-service-stage-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-service-stage-title")
                            ui.label(t(body_key)).classes("sy-service-stage-copy")
                            ui.label(t(result_key)).classes("sy-service-stage-result")

        _trust_section(navigation, "architecture-flow-section", "architecture_flow_title",
                       "architecture-flow-details", render_architecture_flow_section)

        def render_architecture_layers_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("architecture_layers_title"))}"'
            ):
                _render_architecture_section_heading("architecture_layers_kicker", "architecture_layers_title", "architecture_layers_copy")
            with ui.element("section").classes("sy-architecture-grid w-full").style("display: flex; flex-direction: column").props(
                f'aria-label="{attr(t("architecture_layers_title"))}"'
            ):
                for icon, title_key, body_key in layers:
                    with _trust_article("sy-architecture-layer"):
                        ui.icon(icon).classes("sy-architecture-layer-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-architecture-layer-title")
                        ui.label(t(body_key)).classes("sy-architecture-layer-copy")

        _trust_section(navigation, "architecture-layers-section", "architecture_layers_title",
                       "architecture-layers-details", render_architecture_layers_section)

        def render_architecture_evidence_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("architecture_evidence_title"))}"'
            ):
                _render_architecture_section_heading("architecture_evidence_kicker", "architecture_evidence_title", "architecture_evidence_copy")
                with ui.element("div").classes("sy-trust-evidence-grid").style("display: flex; flex-direction: column").props("data-testid=trust-evidence"):
                    for icon, title_key, body_key, label_key in evidence:
                        with _trust_article("sy-trust-evidence-card"):
                            ui.icon(icon).classes("sy-trust-evidence-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-trust-evidence-title")
                            ui.label(t(body_key)).classes("sy-trust-evidence-copy")
                            ui.label(t(label_key)).classes("sy-trust-evidence-label")

        _trust_section(navigation, "architecture-evidence-section", "architecture_evidence_title",
                       "architecture-evidence-details", render_architecture_evidence_section)

        developer_references = (
            ("view_quilt", "developer_reference_modules_title", "developer_reference_modules_body"),
            ("policy", "developer_reference_context_title", "developer_reference_context_body"),
            ("swap_horiz", "developer_reference_adapters_title", "developer_reference_adapters_body"),
            ("verified_user", "developer_reference_identity_title", "developer_reference_identity_body"),
            ("cycle", "developer_reference_lifecycle_title", "developer_reference_lifecycle_body"),
            ("monitor_heart", "developer_reference_health_title", "developer_reference_health_body"),
            (
                "settings_backup_restore",
                "developer_reference_recovery_title",
                "developer_reference_recovery_body",
            ),
            ("rocket_launch", "developer_reference_release_title", "developer_reference_release_body"),
        )
        def render_architecture_developer_section() -> None:
            with ui.element("section").classes("w-full").props(
                f' aria-label="{attr(t("developer_reference_title"))}" '
                "data-testid=developer-reference"
            ):
                editorial_heading(
                    kicker=t("developer_reference_kicker"),
                    title=t("developer_reference_title"),
                    copy=t("developer_reference_copy"),
                    anchor_id="developer-reference-title",
                )
                with ui.element("div").classes("sy-developer-reference-grid").style("display: flex; flex-direction: column"):
                    for icon, title_key, body_key in developer_references:
                        with _trust_article("sy-developer-reference-card"):
                            ui.icon(icon).classes("sy-developer-reference-icon").props("aria-hidden=true")
                            ui.label(t(title_key)).classes("sy-developer-reference-title")
                            ui.label(t(body_key)).classes("sy-developer-reference-copy")
                with ui.element("div").classes("sy-developer-command-grid").style("display: flex; flex-direction: column"):
                    code_sample(
                        code=(
                            "Invoke-RestMethod http://127.0.0.1:8080/healthz\n"
                            "Invoke-RestMethod http://127.0.0.1:8080/readyz"
                        ),
                        label=t("developer_reference_health_command"),
                        language="powershell",
                        test_id="developer-health-command",
                    )
                    code_sample(
                        code=(
                            "python -X utf8 -m pytest -q\n"
                            "python -X utf8 scripts/verify_update.py --release\n"
                            "python -X utf8 scripts/verify_release_candidate.py"
                        ),
                        label=t("developer_reference_release_command"),
                        language="text",
                        test_id="developer-release-command",
                    )

        developer = _trust_section(navigation, "architecture-developer-section", "developer_reference_title",
                                   "architecture-developer-details", render_architecture_developer_section)
        navigation.register("developer-reference-title", lambda: developer.set_value(True))

        def render_architecture_faq_section() -> None:
            with ui.element("section").classes("sy-architecture-faq w-full").props(
                f' aria-label="{attr(t("architecture_faq_title"))}" '
                'data-testid=architecture-faq'
            ):
                _render_architecture_section_heading("architecture_faq_kicker", "architecture_faq_title", "architecture_faq_copy")
                with ui.column().classes("sy-architecture-faq-list w-full gap-2"):
                    for question_key, answer_key in faq_items:
                        lazy_expansion(t(question_key), icon="help_outline",
                            test_id=f"architecture-faq-{question_key.removeprefix('faq_').removesuffix('_q')}",
                            render=lambda key=answer_key: ui.label(t(key)).classes("sy-architecture-faq-answer"),
                        ).classes("sy-architecture-faq-item")

        _trust_section(navigation, "architecture-faq-section", "architecture_faq_title",
                       "architecture-faq-details", render_architecture_faq_section)

        _render_feedback_channel(compact=True)
        navigation.install()
        reference_pager(previous=("/platform", "platform"), next_=("/engineering", "engineering"))


def _render_architecture_section_heading(
    kicker_key: str,
    title_key: str,
    copy_key: str,
    *,
    show_kicker: bool = False,
) -> None:
    editorial_heading(
        title=t(title_key),
        copy=t(copy_key),
        kicker=t(kicker_key) if show_kicker else None,
        anchor_id=f"{title_key}-heading",
    )
