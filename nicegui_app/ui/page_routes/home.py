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
from nicegui_app.ui.lazy_sections import lazy_expansion
from nicegui_app.ui.reference_navigation import render_reference_pager
from nicegui_app.ui.reading_navigation import ReadingNavigation, reading_toc
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
    workflow = get_workflow()
    week_start = _next_monday()
    has_prefects = bool(workflow.prefects())
    selected_week = workflow.roster_week_for_start(week_start)
    recent = workflow.roster_week_history(page=1, page_size=1)
    next_action = resolve_dashboard_next_action(
        has_prefects=has_prefects, week_start=week_start,
        selected_week=selected_week, latest_week=recent[0] if recent else None,
    )
    with page_shell("/getting-started"):
        navigation = ReadingNavigation()
        with ui.element("section").classes("w-full max-w-4xl").props("id=start-intro"):
            with ui.column().classes("gap-2"):
                ui.label(t("new_user_intro")).classes("text-[var(--sy-muted)] max-w-2xl")
            ui.label(t(next_action.status_key)).classes("font-semibold mt-3")
            with ui.row().classes("gap-3 flex-wrap mt-3"):
                action(t(next_action.action_key), icon=next_action.icon,
                       on_click=lambda: navigate_to(next_action.destination), test_id="start-next-action")
                action(t("operator_guide"), icon="help", on_click=lambda: navigate_to("/guide"), variant="quiet")
        with ui.element("section").classes("flex flex-col gap-4 w-full max-w-4xl").props(
            f'id=start-first-steps aria-label="{attr(t("start_toc_first_steps"))}"'
        ):
            steps = (
                ("new_user_step_start", "new_user_step_start_detail"),
                ("new_user_step_prepare", "new_user_step_prepare_detail"),
                ("new_user_step_week", "new_user_step_week_detail"),
            )
            step_states = (
                "start_step_opened",
                "start_step_directory_available" if has_prefects else "start_step_directory_missing",
                next_action.status_key,
            )
            for (title_key, detail_key), state_key in zip(steps, step_states, strict=True):
                with ui.element("article").classes("w-full max-w-3xl py-4 border-b border-[var(--sy-line)]"):
                    ui.label(t(title_key)).classes("text-lg font-semibold")
                    ui.label(t(state_key)).classes("text-sm font-semibold text-[var(--sy-muted)]")
                    ui.label(t(detail_key)).classes("text-sm text-[var(--sy-muted)] mt-1")
                    if title_key == "new_user_step_start":
                        ui.label(f"{t('public_address_label')}: {CANONICAL_PUBLIC_URL}").classes(
                            "font-mono text-sm font-semibold mt-3 break-all"
                        )

        reading_toc((("start-first-steps", "start_toc_first_steps"),
                     ("start-reference-map", "start_toc_reference_map")))

        reference_cards = (
            ("calendar_month", "start_reference_weekly_title", "start_reference_weekly_body", "open_rosters", "/rosters"),
            ("support", "start_reference_recovery_title", "start_reference_recovery_body", "operator_guide", "/guide"),
            ("verified_user", "start_reference_trust_title", "start_reference_trust_body", "platform", "/platform"),
        )
        def render_reference() -> None:
            with ui.column().classes("w-full").props("data-testid=reference-index"):
                ui.label(t("start_reference_copy")).classes("sy-reference-index-copy")
                for icon, title_key, body_key, action_key, route in reference_cards:
                    with ui.element("article").classes("w-full py-4 border-b border-[var(--sy-line)]"):
                        ui.label(t(title_key)).classes("font-semibold")
                        ui.label(t(body_key)).classes("text-sm leading-6 text-[var(--sy-muted)]")
                        action(t(action_key), icon=icon, on_click=lambda destination=route: navigate_to(destination),
                               variant="quiet")
        with ui.element("section").classes("w-full max-w-4xl").props("id=start-reference-map"):
            reference_panel = lazy_expansion(t("start_reference_title"), icon="map", test_id="start-reference-details",
                                             render=render_reference)
        navigation.register("start-first-steps", lambda: None)
        navigation.register("start-reference-map", lambda: reference_panel.set_value(True))
        navigation.install()
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
        navigation = ReadingNavigation()
        with ui.element("section").classes("w-full max-w-4xl").props(
            f'aria-label="{attr(t("operator_guide"))}"'
        ):
            with ui.column().classes("gap-2 max-w-3xl"):
                ui.label(t("guide_intro")).classes("text-[var(--sy-muted)] leading-7")
        # Search includes unmounted answers; only this small translated index is
        # eager, not hidden answer controls or a second full table.
        entries = [
            (anchor, anchor, t(title_key), (t(body_key),))
            for anchor, _group_key, sections in groups for title_key, body_key in sections
        ]
        entries.extend(
            (f"guide-issue-{seen.removeprefix('guide_issue_').removesuffix('_seen')}",
             "guide-troubleshooting", t(seen), (t(meaning), t(next_step)))
            for seen, meaning, next_step in issues
        )
        with ui.column().classes("w-full max-w-4xl gap-2"):
            search = ui.input(label=t("guide_search"), placeholder=t("guide_search_hint")).props(
                "clearable maxlength=400 debounce=150 data-testid=guide-search"
            ).classes("w-full")
            category = ui.select(
                {"all": t("guide_all_categories"), **{anchor: t(key) for anchor, key, _ in groups},
                 "guide-troubleshooting": t("guide_troubleshooting_title")},
                value="all", label=t("guide_category"),
            ).props("data-testid=guide-category").classes("w-full")
            reading_toc(tuple((anchor, key) for anchor, key, _ in groups) +
                        (("guide-troubleshooting", "guide_troubleshooting_title"),))
            no_results = ui.label(t("guide_no_results")).props(
                "role=status aria-live=polite data-testid=guide-no-results"
            ).classes("text-sm text-[var(--sy-muted)]")
            no_results.set_visibility(False)
            panels = {}
            for anchor, group, title, paragraphs in entries:
                if anchor == "guide-issue-vacancy":
                    ui.element("div").props("id=guide-troubleshooting data-testid=guide-troubleshooting")

                def render_answer(values=paragraphs) -> None:
                    for paragraph in values:
                        ui.label(paragraph).classes("text-sm leading-6 whitespace-pre-line text-[var(--sy-muted)]")

                with ui.element("section").classes("w-full").props(f"id={anchor}"):
                    panels[anchor] = lazy_expansion(title, icon="help_outline",
                        test_id=f"guide-answer-{anchor}", render=render_answer)

            def filter_answers() -> None:
                query = str(search.value or "").strip().casefold()[:400]
                visible_count = 0
                for anchor, group, title, paragraphs in entries:
                    visible = (category.value == "all" or category.value == group) and (
                        not query or query in " ".join((title, *paragraphs)).casefold()
                    )
                    panels[anchor].set_visibility(visible)
                    visible_count += int(visible)
                no_results.set_visibility(visible_count == 0)

            search.on_value_change(lambda _: filter_answers())
            category.on_value_change(lambda _: filter_answers())

            def reveal_answer(anchor: str) -> None:
                # A linked answer can be revealed without destroying a search.
                # The next deliberate filter change restores ordinary results.
                panels[anchor].set_visibility(True)
                panels[anchor].set_value(True)
                no_results.set_visibility(False)

            for anchor in panels:
                navigation.register(anchor, lambda target=anchor: reveal_answer(target))
            navigation.register("guide-troubleshooting", lambda: reveal_answer("guide-issue-vacancy"))
            navigation.install()
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
    with page_shell("/devotional"):
        navigation = ReadingNavigation()
        with ui.element("section").classes("sy-chapel sy-devotional-page w-full").props(
            f'aria-label="{attr(t("daily_verse"))}"'
        ):
            with ui.row().classes("sy-devotional-page-head w-full items-start justify-between gap-5 flex-wrap"):
                ui.label(t("daily_verse")).classes("text-lg font-semibold")
                with ui.row().classes("sy-devotional-page-controls items-end gap-3 flex-wrap"):
                    ui.button(
                        t("refresh_verse"),
                        icon="refresh",
                        on_click=_refresh_dashboard_verse,
                    ).props("outline").classes("sy-devotional-page-refresh")
                    ui.button(t("devotional_return_work"), icon="calendar_month",
                              on_click=lambda: _navigate_with_feedback("/")).props(
                        "color=primary data-testid=devotional-return-work"
                    )
            with ui.element("article").classes("sy-devotional-reading mt-8"):
                ui.label(scripture).classes("sy-verse")
                ui.label(reference).classes("sy-devotional-reference")
                ui.label(t("verse_translation_label")).classes("sy-verse-translation sy-verse-translation--chapel")

        def render_details() -> None:
            tone_preference = str(preference_get("devotional_tone", "auto"))
            if tone_preference not in {"auto", "guidance", "comfort"}:
                tone_preference = "auto"
            ui.label(t("devotional_tone_label")).classes("font-semibold")
            # Initialize before attaching the deliberate user-change callback.
            tone_select = ui.radio({
                "auto": t("devotional_tone_auto"), "guidance": t("devotional_tone_guidance"),
                "comfort": t("devotional_tone_comfort"),
            }, value=tone_preference).props("inline data-testid=devotional-tone")
            tone_select.on_value_change(lambda event: _set_devotional_tone(str(event.value)))
            with ui.element("article").classes("w-full py-4 border-t border-[var(--sy-line)]"):
                ui.label(t("devotional_reflection_title")).classes("font-semibold")
                ui.label(reflection.get("title", "")).classes("text-lg font-semibold")
                ui.label(reflection.get("body", "")).classes("text-sm leading-7 whitespace-pre-line")
            with ui.element("article").classes("w-full py-4 border-t border-[var(--sy-line)]"):
                ui.label(t("devotional_prayer_title")).classes("font-semibold")
                ui.label(reflection.get("prayer", t("why_we_serve"))).classes("text-sm leading-7 whitespace-pre-line")
                ui.label(t("devotional_prepare_body")).classes("text-sm leading-7 text-[var(--sy-muted)]")
        with ui.element("section").classes("w-full max-w-4xl").props("id=devotional-reflection"):
            details_panel = lazy_expansion(t("devotional_more"), icon="menu_book", test_id="devotional-details",
                                          render=render_details)
        navigation.register("devotional-reflection", lambda: details_panel.set_value(True))
        navigation.install()
