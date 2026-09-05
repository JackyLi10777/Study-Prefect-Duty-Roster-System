"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui import ui

from nicegui_app.config import CANONICAL_PUBLIC_URL
from nicegui_app.ui.components import action
from nicegui_app.ui.dashboard_flow import resolve_dashboard_next_action

from nicegui_app.runtime import get_workflow
from nicegui_app.ui.devotional import (
    dashboard_verse as _dashboard_verse,
    refresh_dashboard_verse as _refresh_dashboard_verse,
    set_devotional_tone as _set_devotional_tone,
)
from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import ZH_HK, current_locale, t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.page_shared import (
    _navigate_with_feedback,
    _next_monday,
    _render_feedback_channel,
    _tone_badge,
)
from nicegui_app.ui.preferences import preference_get
from nicegui_app.ui.reference_navigation import render_page_toc, render_reference_pager
from nicegui_app.ui.shell import page_shell

@ui.page("/")
def dashboard_page() -> None:
    workflow = get_workflow()
    week_start = _next_monday()
    has_prefects = bool(workflow.prefects())
    selected_week = workflow.roster_week_for_start(week_start)
    recent_weeks = workflow.roster_week_history(page=1, page_size=1)
    latest = recent_weeks[0] if recent_weeks else None
    next_action = resolve_dashboard_next_action(
        has_prefects=has_prefects,
        week_start=week_start,
        selected_week=selected_week,
        latest_week=latest,
    )
    with page_shell("/"):
        with ui.row().classes("sy-dashboard-grid w-full items-stretch"):
            with ui.element("section").classes("sy-workbench grow min-w-0").props(
                "aria-labelledby=dashboard-workbench-title data-testid=dashboard-current-week"
            ):
                with ui.column().classes("gap-3 min-w-0"):
                    ui.html(t("workbench_title"), tag="h2").classes("sy-workbench-title").props(
                        "id=dashboard-workbench-title"
                    )
                    ui.label(f"{t('week_start')}: {week_start.isoformat()}").classes(
                        "text-sm text-[var(--sy-muted)]"
                    ).props("data-testid=dashboard-week-start")
                    _tone_badge(t(next_action.status_key), next_action.tone)
                action(
                    t(next_action.action_key),
                    icon=next_action.icon,
                    on_click=lambda: _navigate_with_feedback(next_action.destination),
                    test_id="dashboard-next-action",
                    classes="mt-4 w-full",
                )
            with ui.element("aside").classes("sy-dashboard-history").props(
                "aria-labelledby=dashboard-history-title data-testid=dashboard-history"
            ):
                with ui.row().classes("sy-dashboard-history-header w-full items-start justify-between gap-3"):
                    with ui.column().classes("gap-1 min-w-0"):
                        ui.html(t("roster_workflow_history"), tag="h2").classes("sy-dashboard-history-title").props(
                            "id=dashboard-history-title"
                        )
                if not recent_weeks:
                    with ui.element("div").classes("sy-dashboard-history-empty").props("role=status"):
                        ui.icon("event_note").classes("sy-dashboard-history-empty-icon").props("aria-hidden=true")
                        with ui.column().classes("gap-1 min-w-0"):
                            ui.label(t("no_rosters")).classes("sy-dashboard-history-empty-title")
                else:
                    with ui.element("ul").classes("sy-dashboard-history-list"):
                        for week in recent_weeks:
                            with ui.element("li").classes("sy-dashboard-history-item"):
                                with ui.row().classes("w-full items-start justify-between gap-3 no-wrap"):
                                    with ui.column().classes("gap-1 min-w-0"):
                                        ui.label(str(week["weekStart"])).classes("sy-dashboard-history-week")
                                    status = str(week["status"])
                                    _tone_badge(
                                        t("published") if status == "published" else t("withdrawn") if status == "withdrawn" else t("draft"),
                                        "stable" if status == "published" else "attention" if status == "withdrawn" else "action",
                                    )
                                action(
                                    t("view"),
                                    icon="arrow_forward",
                                    on_click=lambda item=week: navigate_to(f"/rosters/{item['id']}"),
                                    variant="quiet",
                                    test_id="dashboard-history-action",
                                    classes="sy-dashboard-history-action",
                                )


@ui.page("/dashboard")
def dashboard_alias() -> None:
    navigate_to("/")


@ui.page("/getting-started")
def getting_started_page() -> None:
    with page_shell("/getting-started"):
        with ui.element("section").classes("sy-onboarding-intro w-full max-w-4xl").props("id=start-intro"):
            with ui.column().classes("gap-2"):
                ui.label(t("new_user_intro")).classes("text-[var(--sy-muted)] max-w-2xl")
            ui.icon("calendar_month").classes("sy-onboarding-symbol").props("aria-hidden=true")
        render_page_toc(
            (
                ("start-first-steps", "start_toc_first_steps"),
                ("start-reference-map", "start_toc_reference_map"),
            )
        )
        with ui.element("section").classes("sy-onboarding-steps grid gap-4 w-full").props(
            f'id=start-first-steps aria-label="{attr(t("start_toc_first_steps"))}"'
        ):
            steps = (
                ("new_user_step_start", "new_user_step_start_detail"),
                ("new_user_step_prepare", "new_user_step_prepare_detail"),
                ("new_user_step_week", "new_user_step_week_detail"),
            )
            for title_key, detail_key in steps:
                with ui.card().classes("sy-surface w-full max-w-3xl p-5"):
                    ui.label(t(title_key)).classes("text-lg font-semibold")
                    ui.label(t(detail_key)).classes("text-sm text-[var(--sy-muted)] mt-1")
                    if title_key == "new_user_step_start":
                        ui.label(f"{t('public_address_label')}: {CANONICAL_PUBLIC_URL}").classes(
                            "font-mono text-sm font-semibold mt-3 break-all"
                        )
            with ui.row().classes("gap-3 flex-wrap"):
                action(t("open_prefects"), icon="groups", on_click=lambda: navigate_to("/prefects"), variant="secondary")
                action(t("open_rosters"), icon="calendar_month", on_click=lambda: navigate_to("/rosters"))
                action(t("operator_guide"), icon="help", on_click=lambda: navigate_to("/guide"), variant="quiet")
                action(t("open_handover_guide"), icon="handshake", on_click=lambda: navigate_to("/handover"), variant="quiet")

        reference_cards = (
            ("calendar_month", "start_reference_weekly_title", "start_reference_weekly_body", "open_rosters", "/rosters"),
            ("support", "start_reference_recovery_title", "start_reference_recovery_body", "operator_guide", "/guide"),
            ("verified_user", "start_reference_trust_title", "start_reference_trust_body", "platform", "/platform"),
        )
        with ui.element("section").classes("sy-reference-index w-full max-w-5xl").props(
            f'id=start-reference-map aria-label="{attr(t("start_reference_title"))}" data-testid=reference-index'
        ):
            ui.label(t("start_reference_title")).classes("sy-reference-index-title")
            ui.label(t("start_reference_copy")).classes("sy-reference-index-copy")
            with ui.element("div").classes("sy-reference-index-grid"):
                for icon, title_key, body_key, action_key, route in reference_cards:
                    with ui.element("article").classes("sy-reference-index-card"):
                        ui.icon(icon).classes("sy-reference-index-icon").props("aria-hidden=true")
                        ui.label(t(title_key)).classes("sy-reference-index-card-title")
                        ui.label(t(body_key)).classes("sy-reference-index-card-copy")
                        action(
                            t(action_key),
                            icon="arrow_forward",
                            on_click=lambda destination=route: navigate_to(destination),
                            variant="secondary",
                            classes="sy-reference-index-action",
                        )
        render_reference_pager(next_=("/guide", "operator_guide"))


@ui.page("/guide")
def operator_guide_page() -> None:
    groups = (
        (
            "guide-week-start",
            "guide_group_week_start_title",
            (("guide_week_start_title", "guide_week_start_body"),),
        ),
        (
            "guide-before-publish",
            "guide_group_before_publish_title",
            (("guide_before_publish_title", "guide_before_publish_body"),),
        ),
        (
            "guide-after-publish",
            "guide_group_after_publish_title",
            (("guide_after_publish_title", "guide_after_publish_body"),),
        ),
        (
            "guide-fairness-review",
            "guide_group_fairness_review_title",
            (("guide_fairness_review_title", "guide_fairness_review_body"),),
        ),
        (
            "guide-annual-handover",
            "guide_group_annual_handover_title",
            (("guide_annual_handover_title", "guide_annual_handover_body"),),
        ),
    )
    issues = (
        ("guide_issue_vacancy_seen", "guide_issue_vacancy_meaning", "guide_issue_vacancy_next"),
        ("guide_issue_stale_seen", "guide_issue_stale_meaning", "guide_issue_stale_next"),
        ("guide_issue_publish_seen", "guide_issue_publish_meaning", "guide_issue_publish_next"),
        ("guide_issue_backup_seen", "guide_issue_backup_meaning", "guide_issue_backup_next"),
        ("guide_issue_restore_seen", "guide_issue_restore_meaning", "guide_issue_restore_next"),
        ("guide_issue_session_seen", "guide_issue_session_meaning", "guide_issue_session_next"),
        ("guide_issue_pdf_seen", "guide_issue_pdf_meaning", "guide_issue_pdf_next"),
        ("guide_issue_upload_seen", "guide_issue_upload_meaning", "guide_issue_upload_next"),
        ("guide_issue_network_seen", "guide_issue_network_meaning", "guide_issue_network_next"),
        ("guide_issue_withdraw_seen", "guide_issue_withdraw_meaning", "guide_issue_withdraw_next"),
        ("guide_issue_support_seen", "guide_issue_support_meaning", "guide_issue_support_next"),
    )
    with page_shell("/guide"):
        with ui.element("section").classes("sy-guide-hero w-full").props(
            f'aria-label="{attr(t("operator_guide"))}"'
        ):
            with ui.column().classes("gap-2 max-w-3xl"):
                ui.label(t("guide_intro")).classes("text-[var(--sy-muted)] leading-7")
        render_page_toc(
            (
                ("guide-week-start", "guide_group_week_start_title"),
                ("guide-before-publish", "guide_group_before_publish_title"),
                ("guide-after-publish", "guide_group_after_publish_title"),
                ("guide-fairness-review", "guide_group_fairness_review_title"),
                ("guide-annual-handover", "guide_group_annual_handover_title"),
                ("guide-troubleshooting", "guide_troubleshooting_title"),
            )
        )
        for anchor, group_title_key, sections in groups:
            with ui.element("section").classes("sy-guide-group w-full max-w-4xl").props(f"id={anchor}"):
                ui.label(t(group_title_key)).classes("sy-guide-group-title")
                with ui.column().classes("w-full gap-2"):
                    for title_key, body_key in sections:
                        with ui.expansion(t(title_key), icon="help").classes("sy-surface w-full"):
                            ui.label(t(body_key)).classes("p-4 text-sm leading-6 text-[var(--sy-muted)]")
        with ui.element("section").classes("sy-guide-troubleshooting w-full max-w-5xl").props(
            f'id=guide-troubleshooting aria-label="{attr(t("guide_troubleshooting_title"))}" '
            'data-testid=guide-troubleshooting'
        ):
            ui.label(t("guide_troubleshooting_title")).classes("sy-guide-group-title")
            ui.label(t("guide_troubleshooting_copy")).classes("sy-reference-index-copy")
            with ui.element("div").classes("sy-troubleshooting-table").props(
                f'role=table aria-label="{attr(t("guide_troubleshooting_title"))}"'
            ):
                with ui.element("div").classes("sy-troubleshooting-row sy-troubleshooting-head").props("role=row"):
                    for heading_key in ("guide_issue_seen", "guide_issue_meaning", "guide_issue_next"):
                        ui.label(t(heading_key)).classes("sy-troubleshooting-cell").props("role=columnheader")
                for seen_key, meaning_key, next_key in issues:
                    with ui.element("div").classes("sy-troubleshooting-row").props("role=row"):
                        ui.label(t(seen_key)).classes("sy-troubleshooting-cell sy-troubleshooting-symptom").props(
                            f'role=cell data-label="{t("guide_issue_seen")}"'
                        )
                        ui.label(t(meaning_key)).classes("sy-troubleshooting-cell").props(
                            f'role=cell data-label="{t("guide_issue_meaning")}"'
                        )
                        ui.label(t(next_key)).classes("sy-troubleshooting-cell").props(
                            f'role=cell data-label="{t("guide_issue_next")}"'
                        )
        _render_feedback_channel(compact=True)
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: navigate_to("/system-architecture")).props("flat").classes("self-start")
        render_reference_pager(previous=("/getting-started", "getting_started"), next_=("/handover", "handover"))



@ui.page("/devotional")
def devotional_page() -> None:
    verse = _dashboard_verse()
    locale_is_zh = current_locale() == ZH_HK
    reference = verse.reference_zh if locale_is_zh else verse.reference_en
    scripture = verse.scripture_zh if locale_is_zh else verse.scripture_en
    reflection = verse.reflection_zh if locale_is_zh else verse.reflection_en
    tone_preference = str(preference_get("devotional_tone", "auto"))
    if tone_preference not in {"auto", "guidance", "comfort"}:
        tone_preference = "auto"
    with page_shell("/devotional"):
        with ui.element("section").classes("sy-chapel sy-devotional-page w-full").props(
            f'aria-label="{attr(t("daily_verse"))}"'
        ):
            with ui.row().classes("sy-devotional-page-head w-full items-start justify-between gap-5 flex-wrap"):
                with ui.column().classes("gap-1 max-w-2xl"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("auto_stories").classes("sy-devotional-page-icon").props("aria-hidden=true")
                        ui.label(t("daily_verse")).classes("sy-kicker")
                    ui.label(t("devotional_page_intro")).classes("sy-devotional-page-intro")
                with ui.row().classes("sy-devotional-page-controls items-end gap-3 flex-wrap"):
                    tone_select = ui.select(
                        label=t("devotional_tone_label"),
                        options={
                            "auto": t("devotional_tone_auto"),
                            "guidance": t("devotional_tone_guidance"),
                            "comfort": t("devotional_tone_comfort"),
                        },
                        value=tone_preference,
                    ).props("dense outlined options-dense").classes("sy-devotional-tone-select")
                    tone_select.on_value_change(lambda event: _set_devotional_tone(str(event.value)))
                    ui.button(
                        t("refresh_verse"),
                        icon="refresh",
                        on_click=_refresh_dashboard_verse,
                    ).props("outline").classes("sy-devotional-page-refresh")
            with ui.element("article").classes("sy-devotional-reading mt-8"):
                ui.label(scripture).classes("sy-verse")
                ui.label(reference).classes("sy-devotional-reference")
                ui.label(t("verse_translation_label")).classes("sy-verse-translation sy-verse-translation--chapel")

        with ui.element("section").classes("sy-devotional-reading-grid w-full").props(
            f'aria-label="{attr(t("reflection"))}"'
        ):
            with ui.element("article").classes("sy-devotional-companion sy-devotional-companion--reflection"):
                ui.icon("menu_book").classes("sy-devotional-companion-icon").props("aria-hidden=true")
                ui.label(t("devotional_reflection_title")).classes("sy-devotional-companion-kicker")
                ui.label(reflection.get("title", "")).classes("sy-devotional-companion-title")
                ui.label(reflection.get("body", "")).classes("sy-devotional-companion-copy")
            with ui.element("article").classes("sy-devotional-companion sy-devotional-companion--prayer"):
                ui.icon("spa").classes("sy-devotional-companion-icon").props("aria-hidden=true")
                ui.label(t("devotional_prayer_title")).classes("sy-devotional-companion-kicker")
                ui.label(reflection.get("prayer", t("why_we_serve"))).classes("sy-devotional-prayer")
            with ui.element("article").classes("sy-devotional-companion sy-devotional-companion--action"):
                ui.icon("east").classes("sy-devotional-companion-icon").props("aria-hidden=true")
                ui.label(t("devotional_prepare_title")).classes("sy-devotional-companion-title")
                ui.label(t("devotional_prepare_body")).classes("sy-devotional-companion-copy")
                ui.button(
                    t("devotional_return_work"),
                    icon="calendar_month",
                    on_click=lambda: _navigate_with_feedback("/"),
                ).props("outline").classes("mt-3 self-start")
