"""NiceGUI route registrations grouped by operator domain."""

from __future__ import annotations

from nicegui_app.ui.page_shared import *  # noqa: F403

@ui.page("/")
def dashboard_page() -> None:
    workflow = get_workflow()
    verse = _dashboard_verse()
    locale_is_zh = current_locale() == ZH_HK
    reference = verse.reference_zh if locale_is_zh else verse.reference_en
    scripture = verse.scripture_zh if locale_is_zh else verse.scripture_en
    reflection = verse.reflection_zh if locale_is_zh else verse.reflection_en
    weeks = workflow.roster_weeks()
    latest = weeks[0] if weeks else None
    if latest is None:
        next_title_key = "flow_generate"
        next_action_key = "create_draft"
        next_action = lambda: _navigate_with_feedback("/rosters")
    elif latest["status"] == "draft":
        next_title_key = "flow_review"
        next_action_key = "flow_open_draft"
        next_action = lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}")
    else:
        next_title_key = "flow_leave"
        next_action_key = "flow_open_adjustment"
        next_action = lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}/adjustments")
    with page_shell("dashboard", "/", music_context="dashboard"):
        with ui.element("section").classes("sy-daily-start w-full").props(f'aria-label="{t("daily_verse")}"'):
            with ui.row().classes("w-full items-start gap-4 flex-wrap"):
                ui.icon("menu_book").classes("sy-daily-start-icon").props("aria-hidden=true")
                with ui.column().classes("grow min-w-[240px] gap-1"):
                    ui.label(t("daily_verse")).classes("sy-daily-start-kicker")
                    ui.label(scripture).classes("sy-daily-start-verse")
                    ui.label(reference).classes("sy-daily-start-reference")
                with ui.column().classes("sy-devotional-controls gap-2 items-end"):
                    tone_preference = str(app.storage.user.get("devotional_tone", "auto"))
                    ui.button(t("refresh_verse"), icon="refresh", on_click=_refresh_dashboard_verse).props("flat").classes("sy-daily-start-refresh")
            with ui.expansion(reflection.get("title", ""), icon="auto_stories").classes("sy-daily-start-reflection mt-3"):
                tone_select = ui.select(
                    label=t("devotional_tone_label"),
                    options={
                        "auto": t("devotional_tone_auto"),
                        "guidance": t("devotional_tone_guidance"),
                        "comfort": t("devotional_tone_comfort"),
                    },
                    value=tone_preference if tone_preference in {"auto", "guidance", "comfort"} else "auto",
                ).props("dense outlined options-dense").classes("sy-devotional-tone-select mb-3")
                tone_select.on_value_change(lambda event: _set_devotional_tone(str(event.value)))
                ui.label(reflection.get("body", "")).classes("text-sm leading-6 text-[var(--sy-muted)] p-1")
                if reflection.get("prayer"):
                    ui.label(f"{t('prayer')}: {reflection['prayer']}").classes("mt-3 text-sm italic text-[var(--sy-muted)]")
        with ui.element("section").classes("sy-mobile-next-action w-full").props(
            f'aria-label="{t("mobile_next_action_label")}"'
        ):
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(t("mobile_next_action_label")).classes("sy-mobile-next-action-kicker")
                ui.label(t(next_title_key)).classes("sy-mobile-next-action-title")
            ui.button(t(next_action_key), icon="arrow_forward", on_click=next_action).props("color=primary")
        with ui.row().classes("sy-dashboard-grid sy-dashboard-grid--single w-full items-stretch"):
            with ui.element("section").classes("sy-workbench grow min-w-[620px]"):
                with ui.row().classes("w-full items-start justify-between gap-5 flex-wrap"):
                    with ui.column().classes("gap-1"):
                        ui.html(t("workbench_title"), tag="h2").classes("sy-workbench-title")
                        ui.label(t("workbench_intro")).classes("sy-workbench-intro")
                    if latest is None:
                        _tone_badge(t("flow_no_roster"), "action")
                    elif latest["status"] == "draft":
                        _tone_badge(t("flow_draft_ready"), "action")
                    else:
                        _tone_badge(t("flow_published_ready"), "stable")
                with ui.element("ol").classes("sy-flow mt-7").props(f'aria-label="{t("workbench_title")}"'):
                    if latest is None:
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="active", state_key="flow_current", icon="edit_calendar", action_key="create_draft", action=lambda: _navigate_with_feedback("/rosters"))
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="pending", state_key="flow_waiting", icon="fact_check")
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="pending", state_key="flow_waiting", icon="event_busy")
                    elif latest["status"] == "draft":
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="done", state_key="flow_done", icon="edit_calendar")
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="active", state_key="flow_current", icon="fact_check", action_key="flow_open_draft", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}"))
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="pending", state_key="flow_waiting", icon="event_busy")
                    else:
                        _render_flow_step(number=1, title_key="flow_generate", detail_key="flow_generate_detail", state="done", state_key="flow_done", icon="edit_calendar")
                        _render_flow_step(number=2, title_key="flow_review", detail_key="flow_review_detail", state="done", state_key="flow_done", icon="fact_check", action_key="flow_open_published", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}"))
                        _render_flow_step(number=3, title_key="flow_leave", detail_key="flow_leave_detail", state="active", state_key="flow_current", icon="event_busy", action_key="flow_open_adjustment", action=lambda item=latest: _navigate_with_feedback(f"/rosters/{item['id']}/adjustments"))
                ui.button(t("first_time_link"), icon="play_circle", on_click=lambda: ui.navigate.to("/getting-started")).props("flat").classes("mt-5")
        ui.html(t("current_rosters"), tag="h2").classes("text-xl font-semibold mt-3")
        weeks = weeks[:3]
        if not weeks:
            _render_empty_state(
                title_key="empty_roster_title",
                body_key="empty_roster_detail",
                icon="event_note",
                illustrated=True,
            )
        else:
            for week in weeks:
                with ui.row().classes("sy-surface w-full items-center justify-between px-5 py-4"):
                    with ui.column().classes("gap-0"):
                        ui.label(str(week["weekStart"])).classes("font-semibold")
                        ui.label(f"{t('version')} {week['version']}").classes("text-sm text-[var(--sy-muted)]")
                    _tone_badge(t("published") if week["status"] == "published" else t("draft"), "stable" if week["status"] == "published" else "action")
                    ui.button(t("view"), icon="arrow_forward", on_click=lambda item=week: ui.navigate.to(f"/rosters/{item['id']}")).props("flat")


@ui.page("/dashboard")
def dashboard_alias() -> None:
    ui.navigate.to("/")


@ui.page("/getting-started")
def getting_started_page() -> None:
    with page_shell("getting_started", "/getting-started", music_context="getting_started"):
        with ui.element("section").classes("sy-onboarding-intro w-full max-w-4xl"):
            with ui.column().classes("gap-2"):
                ui.label(t("getting_started")).classes("sy-page-title")
                ui.label(t("new_user_intro")).classes("text-[var(--sy-muted)] max-w-2xl")
            ui.icon("calendar_month").classes("sy-onboarding-symbol").props("aria-hidden=true")
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
                    ui.label(f"{t('local_address_label')}: http://127.0.0.1:8080").classes("font-mono text-sm font-semibold mt-3")
        with ui.row().classes("gap-3 flex-wrap"):
            ui.button(t("open_prefects"), icon="groups", on_click=lambda: ui.navigate.to("/prefects")).props("outline color=primary")
            ui.button(t("open_rosters"), icon="calendar_month", on_click=lambda: ui.navigate.to("/rosters")).props("color=primary")
            ui.button(t("operator_guide"), icon="help", on_click=lambda: ui.navigate.to("/guide")).props("flat")
            ui.button(t("open_handover_guide"), icon="handshake", on_click=lambda: ui.navigate.to("/handover")).props("flat")


@ui.page("/guide")
def operator_guide_page() -> None:
    sections = (
        ("guide_open_title", "guide_open_body"),
        ("guide_directory_title", "guide_directory_body"),
        ("guide_draft_title", "guide_draft_body"),
        ("guide_manual_title", "guide_manual_body"),
        ("guide_publish_title", "guide_publish_body"),
        ("guide_recovery_title", "guide_recovery_body"),
        ("guide_support_title", "guide_support_body"),
    )
    with page_shell("operator_guide", "/guide", music_context="guide"):
        with ui.element("section").classes("sy-guide-hero w-full").props(f'aria-label="{t("operator_guide")}"'):
            with ui.column().classes("gap-2 max-w-3xl"):
                ui.label(t("operator_guide")).classes("sy-page-title")
                ui.label(t("guide_intro")).classes("text-[var(--sy-muted)] leading-7")
        for title_key, body_key in sections:
            with ui.expansion(t(title_key), icon="help").classes("sy-surface w-full max-w-4xl"):
                ui.label(t(body_key)).classes("p-4 text-sm leading-6 text-[var(--sy-muted)]")
        _render_feedback_channel(compact=True)
        ui.button(t("open_system_architecture"), icon="account_tree", on_click=lambda: ui.navigate.to("/system-architecture")).props("flat").classes("self-start")



@ui.page("/devotional")
def devotional_page() -> None:
    verse = select_daily_verse()
    locale_is_zh = current_locale() == ZH_HK
    reference = verse.reference_zh if locale_is_zh else verse.reference_en
    scripture = verse.scripture_zh if locale_is_zh else verse.scripture_en
    reflection = verse.reflection_zh if locale_is_zh else verse.reflection_en
    with page_shell("devotional", "/devotional", music_context="devotional"):
        with ui.element("section").classes("sy-chapel w-full"):
            ui.label(t("daily_verse")).classes("sy-kicker")
            ui.label(scripture).classes("sy-verse")
            ui.label(reference).classes("text-base font-medium text-[#F2D393]")
            ui.separator().classes("my-7 bg-[#F2D393]/50")
            ui.label(reflection.get("title", "")).classes("text-xl font-semibold")
            ui.label(reflection.get("body", "")).classes("sy-reflection")
            if reflection.get("prayer"):
                ui.label(f"{t('prayer')}: {reflection['prayer']}").classes("mt-3 text-sm italic text-[#F2D393]")
