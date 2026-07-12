from __future__ import annotations

from inspect import signature

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from nicegui_app.ui import page_shared as pages
from tests.ui_source import combined_page_source, combined_theme_source


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
    assert ".sy-skip-link:focus-visible" in theme
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
    assert 'ui.colors(primary="#47758B" if is_dark else "#35647C")' in theme
    assert "color=teal-8" not in pages_source
    assert "bg-teal-" not in theme
    assert "color=primary" in pages_source
    assert "min-height: 44px" in theme
    assert "applySystemBlue" not in theme
    assert "#0A84FF" not in theme
    assert "prefers-reduced-motion: reduce" in theme


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
    assert '"stable" if week["status"] == "published" else "action"' in pages_source
    for ad_hoc_status_colour in ("color=amber-8", "color=amber-9", "color=blue-7", "color=teal-8"):
        assert ad_hoc_status_colour not in pages_source


def test_local_and_remote_images_declare_size_and_accessible_alternative() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    youtube = (PROJECT_ROOT / "nicegui_app" / "ui" / "youtube_music.py").read_text(encoding="utf-8")

    assert "width=545 height=524" in shell
    assert 'alt="{t("school_crest_alt")}"' in shell
    assert "width=640 height=615 loading=lazy decoding=async" in pages
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
        'with ui.row().classes("w-full justify-end gap-3 mt-4"):', 1
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
        'with ui.row().classes("gap-3 mt-4"):', 1
    )[0]

    for key in ("leave_prefect_required", "leave_day_required", "leave_reason_required"):
        assert leave_handler.index(key) < leave_handler.index("_run_with_progress")
    for key in ("draft_assignment_required", "draft_candidate_required", "draft_change_reason_required"):
        assert draft_handler.index(key) < draft_handler.index("_run_with_progress")
    assert "workflow.validate_week_start(selected)" in pages
    assert leave_handler.count('run_method("focus")') == 3
    assert draft_handler.count('run_method("focus")') == 3


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

    assert music_source.count("sy-settings-section ") == 2
    assert "sy-settings-section sy-online-music-settings" in youtube_source
    assert music_source.count("sy-settings-section-icon") == 2
    assert "sy-settings-section-icon" in youtube_source
    assert "text-[var(--sy-teal)]" not in music_source
    assert "text-[var(--sy-teal)]" not in youtube_source
    assert ".sy-inline-empty" in theme
    assert "music_no_custom_tracks_title" in music_source
    assert "youtube_library_empty_title" in youtube_source
    assert "sy-empty-state--illustrated" in theme
    assert page_source.count("illustrated=True") == 2
    assert "sy-button-attention" in page_source
    assert "color=negative data-testid=confirm-restore-action" in page_source
    assert 'classes(f"sy-acceptance-card-icon sy-fg-{state_tone}")' in page_source


def test_dashboard_devotional_direction_is_theme_aware_but_operator_overridable() -> None:
    page_source = combined_page_source()
    theme = combined_theme_source()

    assert 'app.storage.user.get("devotional_tone", "auto")' in page_source
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
