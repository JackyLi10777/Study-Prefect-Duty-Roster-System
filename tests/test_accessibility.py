from __future__ import annotations

from inspect import signature
import re

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from nicegui_app.ui import page_shared as pages
from tests.ui_source import combined_page_source, combined_theme_source


def _css_rules(source: str, selector_fragment: str) -> list[tuple[str, str]]:
    """Collect selector/declaration pairs containing a stable fragment."""

    matches = [
        (match.group("selectors"), match.group("body"))
        for match in re.finditer(
            r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}",
            source,
            re.DOTALL,
        )
        if selector_fragment in match.group("selectors")
    ]
    assert matches, f"Missing CSS contract for {selector_fragment}"
    return matches


def _css_declarations(source: str, selector_fragment: str) -> str:
    """Collect declarations for every rule containing a stable selector fragment."""

    return " ".join(body for _selectors, body in _css_rules(source, selector_fragment))


def test_shared_shell_provides_landmarks_skip_link_and_accessible_icon_controls() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    theme = combined_theme_source()

    for key in ("skip_to_content", "main_navigation", "open_navigation"):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()

    assert 'ui.link(t("skip_to_content"), "#main-content")' in shell
    assert 'ui.element("main").props("id=main-content tabindex=-1")' in shell
    assert "role=navigation" in shell
    assert "aria-current=page" in shell
    assert "aria-level=1" in shell
    assert 'aria-label="{t("open_navigation")}"' in shell
    assert 'aria-label="{sound_tooltip}"' in shell
    assert 'aria-label="{tooltip}"' in shell
    assert "document.documentElement.lang" in shell
    assert '"zh-Hant-HK"' in shell
    assert ".sy-skip-link:focus-visible" in theme
    assert "#main-content:focus-visible" in theme
    assert "overscroll-behavior: contain" in theme
    assert "touch-action: manipulation" in theme
    assert "user-scalable=no" not in theme
    assert "maximum-scale=1" not in theme


def test_quiet_precision_shell_uses_semantic_action_and_motion_tokens() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    theme = combined_theme_source()
    pages_source = combined_page_source()

    for class_name in ("sy-app-header", "sy-header-bar", "sy-header-title", "sy-header-tools"):
        assert class_name in shell
        assert f".{class_name}" in theme
    for token in ("--sy-motion-press: 90ms", "--sy-motion-state: 180ms", "--sy-motion-layer: 260ms"):
        assert token in theme
    assert ".sy-nav-active:before" in theme
    assert "--sy-button-primary-bg:" in theme
    assert ".sy-sidebar .q-btn .q-icon" in theme
    assert "apply_quasar_palette(is_dark)" in theme
    assert 'QUASAR_LIGHT_PALETTE = quasar_palette(mode="light")' in theme
    assert 'QUASAR_DARK_PALETTE = quasar_palette(mode="dark")' in theme
    assert "color=teal-8" not in pages_source
    assert "bg-teal-" not in theme
    assert "color=primary" in pages_source
    assert "min-height: 44px" in theme
    assert "applySystemBlue" not in theme
    assert "#0A84FF" not in theme
    assert "prefers-reduced-motion: reduce" in theme
    assert "--sy-on-accent:" in theme
    assert "--sy-on-danger:" in theme
    assert "var(--sy-on-accent)" in theme
    assert "var(--sy-on-danger)" in theme
    assert "text-transform: none !important" in theme
    assert ".q-notification.bg-negative" in theme
    assert ".q-uploader__header" in theme
    assert "100dvh" in theme
    assert "(pointer: coarse)" in theme
    assert "sidebar-stewardship-dark-v1.webp" in theme
    assert "rgba(13,17,23,.66)" in theme
    assert ".sy-brand-mark { width: 60px; height: 58px; padding: 0;" in theme
    assert "border: 0; border-radius: 0; background: transparent;" in theme
    assert ".body--dark .sy-brand-mark { border-color: transparent; background: transparent;" in theme
    assert ".sy-co-creation-crest {" in theme
    assert ".body--dark .sy-co-creation-crest { border-color: transparent; background: transparent;" in theme
    assert "drop-shadow(0 1px 0 rgba(255,255,255" not in theme
    assert "border-radius: 0" in _css_declarations(theme, ".sy-co-creation-crest")
    assert ".sy-brand-mark .q-img__image--with-transition" in theme
    assert "transition-duration: 0s !important" in theme


def test_global_control_skin_keeps_semantic_button_roles_distinct() -> None:
    """Depth may be shared globally, but meaning must still come from the action role."""

    theme = combined_theme_source()

    for token in (
        "--sy-control-edge:",
        "--sy-control-highlight:",
        "--sy-control-shadow:",
        "--sy-control-shadow-hover:",
    ):
        assert token in theme

    primary = _css_declarations(theme, ".q-btn.q-btn--standard.bg-primary")
    outline = _css_declarations(theme, ".q-btn.q-btn--outline")
    flat = _css_declarations(theme, ".q-btn.q-btn--flat")
    danger = " ".join(
        (
            _css_declarations(theme, ".q-btn.text-negative"),
            _css_declarations(theme, ".q-btn.bg-negative"),
        )
    )
    attention = _css_declarations(theme, ".q-btn.sy-button-attention")

    assert "--sy-button-primary-bg" in primary
    assert "--sy-control-highlight" in primary and "--sy-control-shadow" in primary
    assert "--sy-role-action" in outline and "--sy-control-outline-shadow" in outline
    assert "--sy-action-soft" in flat or "--sy-role-action-soft" in flat
    assert "--sy-role-danger" in danger and "--sy-on-danger" in danger
    assert "--sy-button-danger-bg" in danger
    assert ".q-btn.bg-negative .q-btn__content" in theme
    assert "--sy-role-attention" in attention and "--sy-control-outline-shadow" in attention

    action_outline_rules = [
        selectors
        for selectors, declarations in _css_rules(theme, ".q-btn.q-btn--outline")
        if "--sy-role-action" in declarations
    ]
    assert action_outline_rules
    assert all(":not(.text-negative)" in selectors for selectors in action_outline_rules)
    assert all(":not(.sy-button-attention)" in selectors for selectors in action_outline_rules)


def test_global_control_skin_excludes_quiet_navigation_and_round_controls() -> None:
    """Global depth must not make compact chrome look like competing primary actions."""

    theme = combined_theme_source()
    raised_primary_rules = [
        selectors
        for selectors, declarations in _css_rules(theme, ".q-btn.q-btn--standard.bg-primary")
        if "--sy-button-primary-bg" in declarations
    ]
    assert raised_primary_rules
    assert all(":not(.q-btn--round)" in selectors for selectors in raised_primary_rules)

    for selector_fragment in (
        ".sy-header-tools .q-btn",
        ".sy-sidebar .q-btn",
        ".sy-mobile-tab",
    ):
        declarations = _css_declarations(theme, selector_fragment)
        assert "box-shadow: none" in declarations, selector_fragment

    round_control = " ".join(
        declarations
        for selectors, declarations in _css_rules(theme, ".q-btn--round")
        if ":not(.q-btn--round)" not in selectors
    )
    assert round_control
    assert "box-shadow:" in round_control
    assert "--sy-control-shadow" not in round_control


def test_global_control_skin_preserves_touch_focus_disabled_and_busy_states() -> None:
    theme = combined_theme_source()

    button = _css_declarations(theme, ".q-btn")
    flat = _css_declarations(theme, ".q-btn.q-btn--flat")
    focus = _css_declarations(theme, ".q-btn:focus-visible")
    disabled = " ".join(
        (
            _css_declarations(theme, ".q-btn.disabled"),
            _css_declarations(theme, '.q-btn[aria-disabled="true"]'),
        )
    )
    busy = _css_declarations(theme, '.q-btn[aria-busy="true"]')

    assert "min-height: 44px" in button
    assert "min-height: 44px" in flat
    assert "outline:" in focus and "var(--sy-focus)" in focus
    assert "outline-offset:" in focus
    assert "cursor: not-allowed" in disabled
    assert "transform: none" in disabled
    assert "opacity:" in disabled or "filter:" in disabled
    assert "cursor: progress" in busy or "cursor: wait" in busy
    pointer_selector = '.q-btn:not(.disabled):not([aria-disabled="true"]):not([aria-busy="true"])'
    assert pointer_selector in theme
    assert theme.index(pointer_selector) < theme.rindex('.q-btn[aria-busy="true"] { cursor: wait; }')


def test_global_form_and_progress_skin_has_complete_semantic_states() -> None:
    theme = combined_theme_source()

    checkbox = _css_declarations(theme, ".q-checkbox__bg")
    checkbox_checked = _css_declarations(theme, ".q-checkbox__inner--truthy")
    toggle = _css_declarations(theme, ".q-toggle__track")
    toggle_checked = _css_declarations(theme, ".q-toggle__inner--truthy")
    radio_checked = _css_declarations(theme, ".q-radio__inner--truthy")
    active_tab = _css_declarations(theme, ".q-tab--active")
    progress = _css_declarations(theme, ".q-linear-progress__model")
    disabled = " ".join(
        _css_declarations(theme, selector)
        for selector in (".q-field--disabled", ".q-checkbox.disabled", ".q-toggle.disabled", ".q-radio.disabled")
    )

    assert "border-color:" in checkbox and "box-shadow:" in checkbox
    assert "--sy-role-action" in checkbox_checked
    assert "box-shadow:" in toggle and "--sy-role-stable" in toggle_checked
    assert "--sy-role-action" in radio_checked
    assert "--sy-action-soft" in active_tab
    assert "--sy-button-primary-bg" in progress
    assert "opacity:" in disabled and "cursor: not-allowed" in disabled

    for focus_selector in (
        ".q-checkbox:focus-within",
        ".q-toggle:focus-within",
        ".q-radio:focus-within",
    ):
        focus = _css_declarations(theme, focus_selector)
        assert "outline:" in focus and "var(--sy-focus)" in focus
        assert "outline-offset:" in focus


def test_component_colour_roles_are_semantic_and_consistent() -> None:
    theme = combined_theme_source()
    pages_source = combined_page_source()

    for role in ("action", "stable", "attention", "danger", "neutral"):
        assert f"--sy-role-{role}:" in theme
        assert f".sy-tone-{role}" in theme
    assert "--sy-status-action-bg:" in theme
    assert "--sy-status-stable-bg:" in theme
    assert "--sy-status-attention-bg:" in theme
    assert "--sy-image-empty-ready:" in theme
    assert "var(--sy-empty-ready-veil), var(--sy-image-empty-ready)" in theme
    assert "def _tone_badge" in pages_source
    assert '"stable" if status == "published" else "attention" if status == "withdrawn" else "action"' in pages_source
    for ad_hoc_status_colour in ("color=amber-8", "color=amber-9", "color=blue-7", "color=teal-8"):
        assert ad_hoc_status_colour not in pages_source


def test_local_and_remote_images_declare_size_and_accessible_alternative() -> None:
    brand = (PROJECT_ROOT / "nicegui_app" / "ui" / "brand.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    youtube = (PROJECT_ROOT / "nicegui_app" / "ui" / "youtube_music.py").read_text(encoding="utf-8")

    assert "width=256 height=256" in brand
    assert 'role=img aria-label="{accessible_name}"' in brand
    assert 'alt="" aria-hidden=true' in brand
    assert "width=640 height=615 loading=lazy decoding=async" in pages
    assert 'alt="{t("school_crest_alt")}"' in pages
    assert "width=320 height=180" in youtube
    assert 'alt="" loading=lazy' in youtube


def test_core_operator_fields_declare_names_and_disable_credential_autofill() -> None:
    pages = combined_page_source()
    music = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")
    youtube = (PROJECT_ROOT / "nicegui_app" / "ui" / "youtube_music.py").read_text(encoding="utf-8")

    for field_name in (
        "week-start",
        "pre-generation-leave-reason",
        "draft-change-reason",
        "leave-adjustment-reason",
        "name-zh",
        "name-en",
        "class-name",
        "prefect-remarks",
        "prefect-import",
    ):
        assert f"name={field_name}" in pages
    assert "autocomplete=off" in pages
    assert "name=music-track" in music
    assert "name=music-profile" in music
    assert "name=settings-music-profile" in music
    assert "name=youtube-local-import-url type=url autocomplete=off inputmode=url" in music
    assert "name=youtube-local-import-context autocomplete=off" in music
    assert "name=youtube-playlist-url type=url autocomplete=off inputmode=url" in youtube


def test_every_backup_sensitive_ui_write_uses_the_nonblocking_progress_boundary() -> None:
    pages = combined_page_source()

    assert "def _safe_action" not in pages
    assert pages.count("_safe_read_action(") == 3  # helper plus two candidate-list reads
    for working_key in (
        "progress_leave_working",
        "progress_leave_cancel_working",
        "progress_prefect_save_working",
        "progress_prefect_archive_working",
    ):
        assert f'working_key="{working_key}"' in pages
    assert "data-testid=confirm-archive-prefect" in pages
    assert "data-testid=open-archive-prefect" in pages


def test_prefect_form_repairs_expected_omissions_before_starting_a_durable_write() -> None:
    pages = combined_page_source()
    save_handler = pages.split("async def save_prefect() -> None:", 1)[1].split(
        'with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-4"):', 1
    )[0]

    for key in (
        "prefect_name_required",
        "prefect_class_required",
        "prefect_availability_required",
    ):
        assert save_handler.index(key) < save_handler.index("_run_with_progress")
    assert save_handler.count('run_method("focus")') == 3


def test_roster_forms_repair_predictable_input_before_background_work() -> None:
    pages = combined_page_source()
    leave_handler = pages.split("async def declare_leave() -> None:", 1)[1].split(
        'ui.button(t("declare_leave")', 1
    )[0]
    draft_handler = pages.split("async def save_draft_change() -> None:", 1)[1].split(
        'with ui.row().classes("sy-mobile-actions gap-3 mt-4"):', 1
    )[0]

    for key in ("leave_prefect_required", "leave_day_required"):
        assert leave_handler.index(key) < leave_handler.index("_run_with_progress")
    for key in ("draft_assignment_required", "draft_candidate_required"):
        assert draft_handler.index(key) < draft_handler.index("_run_with_progress")
    assert "workflow.validate_week_start(selected)" in pages
    assert leave_handler.count('run_method("focus")') == 2
    assert draft_handler.count('run_method("focus")') == 2


def test_history_priority_slider_marks_match_the_nonlinear_numeric_range() -> None:
    pages = combined_page_source()
    theme = combined_theme_source()
    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")

    # 1.0 sits one sixth of the way through the 0.8-2.0 range, not at the centre.
    assert '("1.0", "16.6667%")' in pages
    assert 'classes("sy-history-scale-mark")' in pages
    assert 'props(f"data-value={value}")' in pages
    assert ".sy-history-scale-mark" in theme
    assert ".sy-history-scale-mark:first-child" not in theme
    assert ".sy-history-scale-mark:nth-child(3)" not in theme
    assert "sy-history-scale-help" in pages
    assert 'tick_box["x"] + tick_box["width"] / 2' in verifier
    assert 'abs(actual_x - expected_x) <= 1.0' in verifier


def test_history_priority_has_a_live_accessible_explanation_chart() -> None:
    pages = combined_page_source()
    theme = combined_theme_source()

    assert 'data-testid=history-priority-chart' in pages
    assert '"aria": {' in pages
    assert 'history_priority_chart_aria' in pages
    assert 'history_priority_chart.update()' in pages
    assert 'multiplier_by_week.get(selected.isoformat(), 1.0)' in pages
    assert '.sy-history-priority-chart' in theme


def test_semantic_status_badges_do_not_inherit_quasar_primary_background() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    components = (PROJECT_ROOT / "nicegui_app" / "ui" / "components.py").read_text(encoding="utf-8")
    theme = combined_theme_source()
    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")

    assert "ui.badge(color=None)" in components
    assert "return render_status_component(text, tone, props=props)" in shared
    for tone in ("action", "stable", "attention", "danger", "neutral"):
        selector = f"body .q-badge.sy-status-badge.sy-tone-{tone}"
        assert selector in theme
        assert f"var(--sy-status-{tone}-bg) !important" in theme
    assert "assert_status_tone_contrast(page)" in verifier
    assert 'ratio >= 4.5' in verifier


def test_durable_handlers_snapshot_visible_form_values_before_the_first_await() -> None:
    pages = combined_page_source()

    for snapshot in (
        "prefect_id = str(leave_prefect.value)",
        "leave_day_value = str(leave_day.value)",
        "assignment_id = int(assignment_select.value)",
        "replacement_prefect_id = str(candidate_select.value)",
        'reason = str(reason_input.value or "").strip()',
    ):
        assert snapshot in pages


def test_backup_dependent_actions_have_guided_disabled_empty_states() -> None:
    pages = combined_page_source()

    assert 'if backup_options:' in pages
    assert "no_verified_backup_handover_body" in pages
    assert "no_verified_backup_restore_body" in pages
    assert "data-testid=handover-package-disabled-no-backup" in pages
    assert "data-testid=restore-disabled-no-backup" in pages
    assert "disable aria-disabled=true" in pages
    assert "data-testid=handover-package-ready-action" in pages
    assert "data-testid=restore-ready-action" in pages


def test_empty_state_accepts_context_specific_action_properties() -> None:
    assert "action_props" in signature(pages._render_empty_state).parameters
    assert "illustrated" in signature(pages._render_empty_state).parameters
    assert "action_props" not in signature(pages._render_flow_step).parameters


def test_secondary_pages_share_semantic_colour_and_empty_state_grammar() -> None:
    page_source = combined_page_source()
    music_source = (PROJECT_ROOT / "nicegui_app" / "ui" / "music.py").read_text(encoding="utf-8")
    youtube_source = (PROJECT_ROOT / "nicegui_app" / "ui" / "youtube_music.py").read_text(encoding="utf-8")
    theme = combined_theme_source()

    assert music_source.count("sy-settings-section ") == 3
    assert "sy-settings-section sy-online-music-settings" in youtube_source
    assert music_source.count("sy-settings-section-icon") == 3
    assert "sy-settings-section-icon" in youtube_source
    assert "text-[var(--sy-teal)]" not in music_source
    assert "text-[var(--sy-teal)]" not in youtube_source
    assert ".sy-inline-empty" in theme
    assert "music_no_custom_tracks_title" in music_source
    assert "youtube_library_empty_title" in youtube_source
    assert "sy-empty-state--illustrated" in theme
    assert page_source.count("illustrated=True") == 1
    assert 'classes("sy-dashboard-history-empty")' in page_source
    assert "sy-button-attention" in page_source
    assert "color=negative data-testid=confirm-restore-action" in page_source
    assert 'classes(f"sy-acceptance-card-icon sy-fg-{state_tone}")' in page_source


def test_decorative_icons_and_core_sections_have_explicit_semantics() -> None:
    page_source = combined_page_source()

    assert 'ui.icon("picture_as_pdf").classes("sy-export-symbol").props("aria-hidden=true")' in page_source
    assert 'ui.icon("calendar_month").classes("sy-onboarding-symbol").props("aria-hidden=true")' in page_source
    assert 'tag="h2"' in page_source
    assert 'icon="auto_awesome"' not in page_source
    assert 'icon="smart_toy"' not in page_source


def test_dashboard_devotional_direction_is_theme_aware_but_operator_overridable() -> None:
    page_source = combined_page_source()
    theme = combined_theme_source()

    assert 'preference_get("devotional_tone", "auto")' in page_source
    assert 'return "comfort" if current_theme() == "dark" else "guidance"' in page_source
    assert "_DEVOTIONAL_GUIDANCE_THEMES" in page_source
    assert "_DEVOTIONAL_COMFORT_THEMES" in page_source
    assert '"auto": t("devotional_tone_auto")' in page_source
    assert '"guidance": t("devotional_tone_guidance")' in page_source
    assert '"comfort": t("devotional_tone_comfort")' in page_source
    assert "sy-devotional-tone-select" in theme


def test_invalid_roster_routes_offer_a_live_bilingual_recovery_state() -> None:
    page_source = combined_page_source()

    assert "def _render_roster_route_state(" in page_source
    assert "role=status aria-live=polite" in page_source
    assert 'test_id="roster-unavailable-state"' in page_source
    assert 'test_id="adjustment-roster-unavailable-state"' in page_source
    assert 'test_id="adjustment-unavailable-state"' in page_source
    assert 'week["status"] != "published"' in page_source
    assert "review_restore_settings" in page_source


def test_handover_readiness_and_acceptance_use_semantic_responsive_containers() -> None:
    page_source = combined_page_source()
    theme = combined_theme_source()

    assert 'data-testid=handover-readiness-grid' in page_source
    assert 'data-testid=acceptance-status' in page_source
    assert "role=status aria-live=polite" in page_source
    assert 'data-testid=acceptance-human-steps' in page_source
    assert 'data-testid=acceptance-open-guide' in page_source
    assert 'data-testid=acceptance-open-settings' in page_source
    assert ".sy-handover-readiness-grid { display: grid; grid-template-columns: repeat(3" in theme
    assert ".sy-handover-readiness-grid, .sy-acceptance-grid { grid-template-columns: 1fr; }" in theme
    assert ".sy-acceptance-actions .q-btn { flex: 1 1 100%; min-height: 44px; }" in theme


def test_invalid_backup_summary_is_safe_status_copy_not_raw_diagnostics() -> None:
    page_source = combined_page_source()
    summary = page_source.split('data-testid=invalid-backup-summary', 1)[1].split(
        "async def create_verified_backup", 1
    )[0]

    assert "role=status aria-live=polite" in page_source
    assert "invalid_backup_summary_body" in summary
    assert '["error"]' not in summary
    assert "verification.get(\"error\")" not in summary


def test_reference_navigation_keeps_touch_targets_and_mobile_table_semantics() -> None:
    theme = combined_theme_source()
    navigation = (
        PROJECT_ROOT / "nicegui_app" / "ui" / "reference_navigation.py"
    ).read_text(encoding="utf-8")
    verifier = (PROJECT_ROOT / "scripts" / "verify_nicegui_ui.py").read_text(encoding="utf-8")
    engineering_verification = verifier.split(
        'page.goto(f"{BASE_URL}/engineering"', 1
    )[1].split('page.goto(f"{BASE_URL}/system-architecture"', 1)[0]
    architecture_verification = verifier.split(
        'page.goto(f"{BASE_URL}/system-architecture"', 1
    )[1].split('page.goto(f"{BASE_URL}/guide"', 1)[0]
    toc_rule = theme.split(".sy-reference-toc-link {", 1)[1].split("}", 1)[0]
    mobile_header_rule = theme.split(".sy-troubleshooting-head { position: absolute;", 1)[1].split("}", 1)[0]

    assert "min-height: 44px" in toc_rule
    assert 'f"data-sy-toc-target={anchor}"' in navigation
    assert "display: none" not in mobile_header_rule
    assert "clip-path: inset(50%)" in mobile_header_rule
    assert "def assert_reference_toc(" in verifier
    assert "len(targets) == len(set(targets))" in verifier
    assert "architecture-developer-section" in verifier
    assert '.locator(".sy-reference-toc-link").count()' not in engineering_verification
    assert '.locator(".sy-reference-toc-link").count()' not in architecture_verification


def test_co_creation_identity_media_keeps_link_focus_touch_and_mobile_reflow() -> None:
    theme = combined_theme_source()
    page_source = combined_page_source()
    social_rule = _css_declarations(theme, ".sy-co-creation-social")
    focus_rule = _css_declarations(theme, ".sy-co-creation-social:focus-visible")
    mobile_start = theme.index("@media (max-width: 900px) {", theme.index(".sy-co-creation-profile"))
    mobile_scope = theme[mobile_start:]

    assert "data-testid=co-creation-profile" in page_source
    assert "aria-labelledby=co-creation-title" in page_source
    assert "id=co-creation-title role=heading aria-level=2" in page_source
    assert "co_creation_instagram_accessible" in page_source
    assert "min-height: 44px" in social_rule
    assert "outline: 3px solid var(--sy-focus)" in focus_rule
    assert ".sy-co-creation-profile { grid-template-columns: 70px minmax(0, 1fr);" in mobile_scope
    assert ".sy-co-creation-social { width: 100%; justify-content: center;" in mobile_scope
    assert ".sy-co-creation-crest { display: none;" in mobile_scope
    banner_rule = _css_declarations(theme, ".sy-co-creation-banner .q-img__image")
    assert "object-fit: contain !important" in banner_rule
    assert "object-position: center !important" in banner_rule
