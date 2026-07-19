from __future__ import annotations

import re

from nicegui_app.ui import page_shared as pages
from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, OFFICIAL_ROLE_TERMS, POST_LABELS, ROLE_LABELS, ZH_HK
from roster_policy import DutyPost
from tests.ui_source import combined_theme_source


def test_domain_catalog_merge_has_no_duplicate_message_keys() -> None:
    from nicegui_app.ui.i18n_catalog import foundation, importing, media, people, platform, reporting, sharing, stewardship, weekly

    domains = (
        foundation.MESSAGES,
        weekly.MESSAGES,
        people.MESSAGES,
        stewardship.MESSAGES,
        platform.MESSAGES,
        media.MESSAGES,
        reporting.MESSAGES,
        importing.MESSAGES,
        sharing.MESSAGES,
    )
    assert len(MESSAGES) == sum(len(domain) for domain in domains)


def test_every_interface_message_has_nonempty_traditional_chinese_and_english_text() -> None:
    missing = {
        key: [locale for locale in (ZH_HK, EN) if not messages.get(locale, "").strip()]
        for key, messages in MESSAGES.items()
        if any(not messages.get(locale, "").strip() for locale in (ZH_HK, EN))
    }

    assert missing == {}


def test_public_roster_sharing_copy_explains_scope_and_link_authority() -> None:
    required = {
        "public_share_title",
        "public_share_intro",
        "public_share_confirm_body",
        "public_share_created_body",
        "public_share_revoke_confirm_body",
    }

    assert required <= MESSAGES.keys()
    assert "中文姓名" in MESSAGES["public_share_confirm_body"][ZH_HK]
    assert "公平點數" in MESSAGES["public_share_confirm_body"][ZH_HK]
    assert "Anyone with the complete link" in MESSAGES["public_share_confirm_body"][EN]
    assert "not stored" in MESSAGES["public_share_created_body"][EN]


def test_every_literal_ui_translation_lookup_exists_in_the_catalogue() -> None:
    ui_root = PROJECT_ROOT / "nicegui_app" / "ui"
    referenced: set[str] = set()
    pattern = re.compile(r"\bt\(\s*['\"]([^'\"]+)['\"]")
    for source_path in ui_root.rglob("*.py"):
        referenced.update(pattern.findall(source_path.read_text(encoding="utf-8")))

    assert referenced - MESSAGES.keys() == set()


def test_official_hong_kong_role_terms_are_consistent_in_the_interface() -> None:
    assert OFFICIAL_ROLE_TERMS["head_study_prefect"] == {ZH_HK: "首席導學風紀", EN: "Head Study Prefect"}
    assert ROLE_LABELS["assistant_head"] == {ZH_HK: "助理首席導學風紀", EN: "Assistant Head Study Prefect"}
    assert ROLE_LABELS["study_prefect"] == {ZH_HK: "導學風紀", EN: "Study Prefect"}
    assert POST_LABELS[DutyPost.ASSIST_IN_CHARGE] == {ZH_HK: "Assist. in charge", EN: "Assist. in charge"}
    assert POST_LABELS[DutyPost.ROOM_302] == {ZH_HK: "Room 302 Study Room", EN: "Room 302 Study Room"}
    assert POST_LABELS[DutyPost.ROOM_303] == {
        ZH_HK: "Homework Completion Room",
        EN: "Homework Completion Room",
    }
    assert POST_LABELS[DutyPost.ROOM_202] == {
        ZH_HK: "Room 202 F1 Study Group",
        EN: "Room 202 F1 Study Group",
    }


def test_each_core_operator_moment_has_a_bilingual_usage_hint() -> None:
    hint_keys = {
        "hint_generate_roster",
        "hint_adjust_roster",
        "hint_draft_change",
        "hint_leave_adjustment",
        "hint_prefect_directory",
        "hint_prefect_import",
        "hint_fairness",
        "hint_settings",
    }

    assert hint_keys <= MESSAGES.keys()
    assert all(MESSAGES[key][ZH_HK].startswith("用途：") for key in hint_keys)
    assert all(MESSAGES[key][EN].startswith("Purpose:") for key in hint_keys)


def test_detailed_operator_guidance_and_architecture_copy_remain_bilingual() -> None:
    required_keys = {
        "guide_open_title",
        "guide_open_body",
        "guide_support_title",
        "guide_support_body",
        "system_architecture",
        "platform",
        "platform_intro",
        "platform_snapshot_title",
        "platform_snapshot_unavailable_body",
        "platform_metric_release",
        "platform_culture_title",
        "platform_resources_title",
        "engineering",
        "engineering_intro",
        "engineering_facts_title",
        "engineering_blueprint_title",
        "engineering_pipeline_title",
        "engineering_pillars_title",
        "engineering_evolution_title",
        "engineering_resources_title",
        "architecture_intro",
        "architecture_ui_body",
        "architecture_policy_body",
        "architecture_workflow_body",
        "architecture_safety_body",
        "architecture_handover_body",
        "architecture_flow_title",
        "architecture_flow_publish_body",
        "architecture_layers_title",
        "architecture_evidence_title",
        "architecture_evidence_recovery_body",
        "architecture_faq_title",
        "faq_draft_q",
        "faq_draft_a",
        "faq_publish_q",
        "faq_publish_a",
        "faq_leave_q",
        "faq_leave_a",
        "faq_restore_q",
        "faq_restore_a",
        "co_creation_body",
        "co_creation_creator_name",
        "co_creation_creator_role",
        "co_creation_instagram_action",
        "co_creation_instagram_accessible",
        "co_creation_avatar_alt",
        "co_creation_banner_alt",
        "co_creation_quote",
        "co_creation_signature",
        "co_creation_codex_title",
        "co_creation_codex_body",
    }

    assert required_keys <= MESSAGES.keys()
    assert "START_SING_YIN_ROSTER.cmd" in MESSAGES["guide_open_body"][ZH_HK]
    assert "OP" in MESSAGES["guide_support_body"][EN]
    assert "李創杰" in MESSAGES["co_creation_body"][ZH_HK]
    assert "Codex" in MESSAGES["co_creation_body"][EN]
    assert "我是李創杰" in MESSAGES["co_creation_body"][ZH_HK]
    assert "只由我與 Codex 兩位共創者" in MESSAGES["co_creation_body"][ZH_HK]
    assert "I am LI Chuangjie Jacky" in MESSAGES["co_creation_body"][EN]
    assert "only two co-creators" in MESSAGES["co_creation_body"][EN]
    assert "我想像" in MESSAGES["co_creation_quote"][ZH_HK]
    assert MESSAGES["co_creation_signature"][ZH_HK].startswith("— 李創杰，")
    assert "公平" in MESSAGES["co_creation_codex_body"][ZH_HK]
    assert "fairness" in MESSAGES["co_creation_codex_body"][EN]
    assert MESSAGES["co_creation_creator_name"][ZH_HK] == "李創杰 · LI Chuangjie, Jacky"
    assert MESSAGES["co_creation_creator_name"][EN] == "李創杰 · LI Chuangjie, Jacky"
    assert "首席導學風紀" in MESSAGES["co_creation_creator_role"][ZH_HK]
    assert "@5662jacky" in MESSAGES["co_creation_instagram_action"][EN]
    assert "新分頁" in MESSAGES["co_creation_instagram_accessible"][ZH_HK]
    assert "new tab" in MESSAGES["co_creation_instagram_accessible"][EN]
    assert MESSAGES["co_creation_avatar_alt"][ZH_HK]
    assert MESSAGES["co_creation_banner_alt"][EN]


def test_enterprise_operating_model_keeps_official_roles_and_capabilities_bilingual() -> None:
    required_keys = {
        "platform_facts_title",
        "team_operating_model_title",
        "team_operating_model_note",
        "team_role_head",
        "team_role_head_function",
        "team_role_assistant",
        "team_role_assistant_function",
        "team_role_prefect",
        "team_role_prefect_function",
        "team_role_advisor",
        "team_role_advisor_function",
        "capability_map_title",
        "capability_operations_title",
        "capability_fairness_title",
        "capability_experience_title",
        "capability_continuity_title",
        "solutions_portfolio_title",
        "solution_weekly_title",
        "solution_adjustment_title",
        "solution_fairness_title",
        "solution_handover_title",
        "solution_open_workspace",
    }

    assert required_keys <= MESSAGES.keys()
    assert all(MESSAGES[key][ZH_HK].strip() and MESSAGES[key][EN].strip() for key in required_keys)
    assert MESSAGES["team_role_head"][ZH_HK] == "首席導學風紀"
    assert MESSAGES["team_role_assistant"][ZH_HK] == "助理首席導學風紀"
    assert MESSAGES["team_role_prefect"][ZH_HK] == "導學風紀"
    assert "不會取代" in MESSAGES["team_operating_model_note"][ZH_HK]
    assert "do not replace" in MESSAGES["team_operating_model_note"][EN]


def test_release_acceptance_states_and_human_responsibilities_remain_bilingual() -> None:
    keys = {
        "acceptance_title",
        "acceptance_intro",
        "acceptance_status_pass",
        "acceptance_status_running",
        "acceptance_status_stale",
        "acceptance_status_fail",
        "acceptance_status_missing",
        "acceptance_status_unreadable",
        "acceptance_human_required",
        "acceptance_task_directory",
        "acceptance_task_pdf",
        "acceptance_task_successor",
        "acceptance_task_advisor",
    }

    assert keys <= MESSAGES.keys()
    assert all(MESSAGES[key][ZH_HK].strip() and MESSAGES[key][EN].strip() for key in keys)
    assert "仍需" in MESSAGES["acceptance_human_required"][ZH_HK]
    assert "still required" in MESSAGES["acceptance_human_required"][EN]
    assert "七項" not in MESSAGES["acceptance_human_body"][ZH_HK]
    assert "seven" not in MESSAGES["acceptance_human_body"][EN].lower()


def test_practice_mode_identity_is_complete_and_not_colour_only() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    theme = combined_theme_source()

    for key in ("practice_mode_title", "practice_mode_body"):
        assert MESSAGES[key][ZH_HK].strip() and MESSAGES[key][EN].strip()
    assert "data-testid=practice-mode-banner" in shell
    assert "role=status" in shell
    assert "sy-practice-banner-title" in theme
    assert ".body--dark .sy-practice-banner" in theme


def test_long_running_operator_actions_have_bilingual_progress_copy() -> None:
    progress_keys = {
        "progress_preparing",
        "progress_finalising",
        "progress_keep_open",
        "progress_generate_title",
        "progress_generate_working",
        "progress_publish_title",
        "progress_publish_working",
        "progress_draft_change_title",
        "progress_draft_change_working",
        "progress_adjustment_title",
        "progress_adjustment_working",
        "progress_import_title",
        "progress_import_working",
        "progress_leave_title",
        "progress_leave_working",
        "progress_leave_cancel_title",
        "progress_leave_cancel_working",
        "progress_prefect_save_title",
        "progress_prefect_save_working",
        "progress_prefect_archive_title",
        "progress_prefect_archive_working",
        "progress_export_title",
        "progress_export_working",
        "progress_handover_title",
        "progress_handover_working",
        "progress_restore_title",
        "progress_restore_working",
        "progress_manual_backup_title",
        "progress_manual_backup_working",
        "operation_already_running",
    }

    assert progress_keys <= MESSAGES.keys()
    assert all(MESSAGES[key][ZH_HK].strip() and MESSAGES[key][EN].strip() for key in progress_keys)


def test_prefect_archive_confirmation_explains_history_and_no_immediate_undo() -> None:
    for key in ("confirm_archive_prefect", "archive_prefect_warning", "confirm_archive"):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()
    assert "歷史" in MESSAGES["archive_prefect_warning"][ZH_HK]
    assert "沒有即時復原" in MESSAGES["archive_prefect_warning"][ZH_HK]
    assert "no immediate undo" in MESSAGES["archive_prefect_warning"][EN]


def test_failure_reference_guidance_is_bilingual_and_accepts_a_safe_reference() -> None:
    for locale in (ZH_HK, EN):
        rendered = MESSAGES["error_reference"][locale].format(reference="OP-1234ABCD")
        assert "OP-1234ABCD" in rendered


def test_prefect_form_repairs_are_complete_in_both_languages() -> None:
    for key in (
        "prefect_name_required",
        "prefect_class_required",
        "prefect_availability_required",
    ):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()


def test_roster_preflight_repairs_are_complete_in_both_languages() -> None:
    for key in (
        "week_start_invalid",
        "week_start_monday_required",
        "leave_prefect_required",
        "leave_day_required",
        "leave_reason_not_provided",
        "draft_assignment_required",
        "draft_candidate_required",
    ):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()


def test_verified_backup_dependency_has_complete_empty_state_copy() -> None:
    for key in (
        "no_verified_backup_title",
        "no_verified_backup_restore_body",
        "no_verified_backup_handover_body",
    ):
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()
    assert "已驗證快照" in MESSAGES["no_verified_backup_restore_body"][ZH_HK]
    assert "verified snapshot" in MESSAGES["no_verified_backup_handover_body"][EN]


def test_stale_and_premature_roster_routes_have_complete_recovery_copy() -> None:
    keys = {
        "roster_unavailable_title",
        "roster_unavailable_body",
        "review_current_rosters",
        "review_restore_settings",
        "adjustment_unavailable_title",
        "adjustment_unavailable_body",
        "return_to_roster",
    }

    assert keys <= MESSAGES.keys()
    assert all(MESSAGES[key][ZH_HK].strip() and MESSAGES[key][EN].strip() for key in keys)
    assert "還原" in MESSAGES["roster_unavailable_body"][ZH_HK]
    assert "restore" in MESSAGES["roster_unavailable_body"][EN].lower()


def test_invalid_backup_summary_uses_safe_bilingual_categories() -> None:
    keys = (
        "invalid_backup_summary_title",
        "invalid_backup_summary_body",
        "backup_issue_file",
        "backup_issue_manifest",
        "backup_issue_checksum",
        "backup_issue_database",
        "backup_issue_schema",
        "backup_issue_unknown",
    )
    for key in keys:
        assert MESSAGES[key][ZH_HK].strip()
        assert MESSAGES[key][EN].strip()
    assert "2" in MESSAGES["invalid_backup_summary_title"][ZH_HK].format(count=2)
    assert "Do not rename" in MESSAGES["invalid_backup_summary_body"][EN]


def test_committed_without_backup_recovery_copy_is_bilingual_and_forbids_repeating_the_write() -> None:
    keys = {
        "committed_without_backup_title",
        "committed_without_backup_body",
        "support_reference_only",
        "reload_and_review",
        "open_backup_settings",
        "create_verified_backup",
        "create_verified_backup_notice",
        "verified_backup_created",
    }

    assert keys <= MESSAGES.keys()
    for locale in (ZH_HK, EN):
        assert MESSAGES["committed_without_backup_body"][locale].strip()
        assert "OP-1234ABCD" in MESSAGES["support_reference_only"][locale].format(reference="OP-1234ABCD")
    assert "請勿重複" in MESSAGES["committed_without_backup_body"][ZH_HK]
    assert "Do not repeat" in MESSAGES["committed_without_backup_body"][EN]


def test_operation_failure_message_formats_its_reference_once(monkeypatch) -> None:
    def translated(key: str, **values: object) -> str:
        return MESSAGES[key][ZH_HK].format(**values)

    monkeypatch.setattr(pages, "t", translated)
    rendered = pages._operation_error_message("OP-1234ABCD")

    assert "OP-1234ABCD" in rendered


def test_roster_display_rows_keep_chinese_prefect_names_for_both_responsive_presentations(monkeypatch, tmp_path) -> None:
    """The phone cards and desktop table must share names from one display model."""
    from datetime import date

    from nicegui_app.services.roster_workflow import RosterWorkflow

    workflow = RosterWorkflow(
        database_path=tmp_path / "roster.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(date(2026, 9, 7))
    assignments = workflow.assignments(draft.id)

    monkeypatch.setattr(pages, "t", lambda key, **_values: MESSAGES[key][ZH_HK])
    monkeypatch.setattr(pages, "day_label", lambda code: str(code))
    rows = pages._roster_display_rows(assignments)

    assert len(rows) == len(assignments) == 26
    assert [row["prefect"] for row in rows] == [assignment["prefectName"] for assignment in assignments]
    assert all(str(row["prefect"]).strip() for row in rows)
    assert {row["dayCode"] for row in rows} == {assignment["day"] for assignment in assignments}
    assert {str(row["post"]) for row in rows} >= {
        "Assist. in charge",
        "Room 302 Study Room",
        "Homework Completion Room - 1",
        "Room 202 F1 Study Group - 1",
    }


def test_prefect_directory_rows_keep_chinese_names_for_table_and_phone_cards(monkeypatch, tmp_path) -> None:
    from nicegui_app.services.roster_workflow import RosterWorkflow

    workflow = RosterWorkflow(
        database_path=tmp_path / "directory.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    prefects = workflow.prefects()

    monkeypatch.setattr(pages, "role_label", lambda code: f"role:{code}")
    monkeypatch.setattr(pages, "day_label", lambda code: f"day:{code}")
    rows = pages._prefect_directory_rows(prefects)

    assert len(rows) == len(prefects)
    assert [row["name"] for row in rows] == [prefect["nameZh"] for prefect in prefects]
    assert all(str(row["name"]).strip() for row in rows)
    assert all(str(row["availability"]).startswith("day:") for row in rows)
