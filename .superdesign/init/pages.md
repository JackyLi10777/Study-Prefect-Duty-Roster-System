# Key Page Dependency Trees

These trees are complete for render-facing local UI dependencies. Linked service and policy modules define available states but should remain source references rather than copied design payloads.

## Common shell dependency tree

- [`nicegui_app/ui/shell.py`](../../nicegui_app/ui/shell.py)
  - [`nicegui_app/ui/i18n.py`](../../nicegui_app/ui/i18n.py)
    - [`nicegui_app/ui/preferences.py`](../../nicegui_app/ui/preferences.py)
    - [`nicegui_app/ui/i18n_catalog/__init__.py`](../../nicegui_app/ui/i18n_catalog/__init__.py)
  - [`nicegui_app/ui/theme.py`](../../nicegui_app/ui/theme.py)
    - [`nicegui_app/ui/design_token_contract.py`](../../nicegui_app/ui/design_token_contract.py)
    - [`nicegui_app/ui/theme_markup.py`](../../nicegui_app/ui/theme_markup.py)
    - [`nicegui_app/ui/motion.py`](../../nicegui_app/ui/motion.py)
  - [`nicegui_app/ui/music.py`](../../nicegui_app/ui/music.py)
    - [`nicegui_app/ui/youtube_music.py`](../../nicegui_app/ui/youtube_music.py)
    - [`nicegui_app/ui/sound.py`](../../nicegui_app/ui/sound.py)
  - [`nicegui_app/runtime.py`](../../nicegui_app/runtime.py)
  - [`nicegui_app/access_context.py`](../../nicegui_app/access_context.py)
  - [`nicegui_app/application_mode.py`](../../nicegui_app/application_mode.py)
  - [`nicegui_app/contact.py`](../../nicegui_app/contact.py)
- [`design_system/tokens.v1.json`](../../design_system/tokens.v1.json)
- [`nicegui_app/assets/css/sing-yin-tokens-v1.css`](../../nicegui_app/assets/css/sing-yin-tokens-v1.css)
- [`nicegui_app/assets/css/sing-yin-theme-v1.css`](../../nicegui_app/assets/css/sing-yin-theme-v1.css)
- [`nicegui_app/assets/css/sing-yin-narrative-v1.css`](../../nicegui_app/assets/css/sing-yin-narrative-v1.css)
- [`nicegui_app/assets/css/sing-yin-mobile-v1.css`](../../nicegui_app/assets/css/sing-yin-mobile-v1.css)

## `/` — Dashboard

Entry: [`dashboard_page` in `home.py`](../../nicegui_app/ui/page_routes/home.py)

- Common shell dependency tree
- [`nicegui_app/ui/devotional.py`](../../nicegui_app/ui/devotional.py)
  - [`packages/roster_core/roster_core/devotional.py`](../../packages/roster_core/roster_core/devotional.py)
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_navigate_with_feedback`
  - `_render_flow_step`
  - `_tone_badge`
- [`nicegui_app/ui/preferences.py`](../../nicegui_app/ui/preferences.py)
- [`nicegui_app/runtime.py`](../../nicegui_app/runtime.py)

Primary regions: Daily Verse, mobile next action, Weekly Pulse, recent-roster history.

## `/rosters` — Weekly roster workspace

Entry: [`rosters_page` in `weekly.py`](../../nicegui_app/ui/page_routes/weekly.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_next_monday`
  - `_render_empty_state`
  - `_render_operation_hint`
  - `_run_with_progress`
  - `_safe_read_action`
- [`nicegui_app/ui/access_control.py`](../../nicegui_app/ui/access_control.py)
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)
- [`packages/roster_core/roster_core/__init__.py`](../../packages/roster_core/roster_core/__init__.py)
- [`packages/roster_policy/roster_policy/__init__.py`](../../packages/roster_policy/roster_policy/__init__.py)

Primary regions: empty-ready orientation, generation and history tabs, week and fairness controls, leave declarations, roster history.

## `/rosters/{roster_week_id}` — Roster detail

Entry: [`roster_detail_page` in `weekly.py`](../../nicegui_app/ui/page_routes/weekly.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_render_roster_table`
  - `_render_storage_lifecycle`
  - `_render_roster_route_state`
  - `_open_roster_export_dialog`
  - `_run_with_progress`
- [`nicegui_app/ui/access_control.py`](../../nicegui_app/ui/access_control.py)
  - `render_roster_share_action`
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)
- [`packages/roster_policy/roster_policy/__init__.py`](../../packages/roster_policy/roster_policy/__init__.py)

Primary regions: status and week summary, desktop table or phone cards, publication controls, draft correction, export, and route recovery.

## `/rosters/{roster_week_id}/adjustments` — Published-duty adjustment

Entry: [`adjustment_detail_page` in `weekly.py`](../../nicegui_app/ui/page_routes/weekly.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_render_roster_table`
  - `_render_operation_hint`
  - `_render_roster_route_state`
  - `_run_with_progress`
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)
- [`packages/roster_policy/roster_policy/__init__.py`](../../packages/roster_policy/roster_policy/__init__.py)

Primary regions: current roster, original assignment, eligible substitute, required reason, confirmation, and completed state.

## `/prefects` — Directory and fairness

Entry: [`prefects_page` in `people.py`](../../nicegui_app/ui/page_routes/people.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_prefect_directory_rows`
  - `_render_mobile_prefect_cards`
  - `_render_responsive_table`
  - `_render_empty_state`
  - `_run_with_progress`
- [`nicegui_app/ui/page_access.py`](../../nicegui_app/ui/page_access.py)
- [`nicegui_app/ui/downloads.py`](../../nicegui_app/ui/downloads.py)
- [`nicegui_app/services/prefect_import_assistant.py`](../../nicegui_app/services/prefect_import_assistant.py)
- [`nicegui_app/services/summary_report_export.py`](../../nicegui_app/services/summary_report_export.py)
- [`nicegui_app/utils/prefect_file_import.py`](../../nicegui_app/utils/prefect_file_import.py)
- [`nicegui_app/utils/prefect_import.py`](../../nicegui_app/utils/prefect_import.py)
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)
- [`packages/roster_policy/roster_policy/__init__.py`](../../packages/roster_policy/roster_policy/__init__.py)

Primary regions: directory and fairness tabs, desktop table or phone cards, editor dialog, reports, import preview, and restricted states.

## `/handover` — Successor handover

Entry: [`handover_page` in `stewardship.py`](../../nicegui_app/ui/page_routes/stewardship.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_run_with_progress`
  - `_tone_badge`
- [`nicegui_app/ui/reference_navigation.py`](../../nicegui_app/ui/reference_navigation.py)
- [`nicegui_app/release_evidence.py`](../../nicegui_app/release_evidence.py)
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)

Primary regions: hero, page contents, successor steps, school-year rollover, readiness cards, machine evidence, and human acceptance.

## `/settings` — Settings and recovery

Entry: [`settings_page` in `stewardship.py`](../../nicegui_app/ui/page_routes/stewardship.py)

- Common shell dependency tree
- [`nicegui_app/ui/music.py`](../../nicegui_app/ui/music.py)
- [`nicegui_app/ui/page_access.py`](../../nicegui_app/ui/page_access.py)
- [`nicegui_app/ui/downloads.py`](../../nicegui_app/ui/downloads.py)
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_render_operation_hint`
  - `_render_empty_state`
  - `_run_with_progress`
  - `_tone_badge`
- [`nicegui_app/services/roster_workflow.py`](../../nicegui_app/services/roster_workflow.py)

Primary regions: media preferences, handover summary, recovery status, integrity warning, package preparation, and restore confirmation.

## `/access-control` — Access and public links

Entry: [`access_control_page` in `access.py`](../../nicegui_app/ui/page_routes/access.py)

- Common shell dependency tree
- [`nicegui_app/ui/access_control.py`](../../nicegui_app/ui/access_control.py)
  - `render_access_control_console`
  - `_render_active_shares`
  - `_open_create_confirmation`
- [`nicegui_app/ui/page_access.py`](../../nicegui_app/ui/page_access.py)
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
- [`nicegui_app/services/public_roster_share.py`](../../nicegui_app/services/public_roster_share.py)

Primary regions: access-mode introduction, operator and viewer cards, roster selection, create confirmation, and active-link management.

## `/platform` — Platform and team

Entry: [`platform_page` in `showcase.py`](../../nicegui_app/ui/page_routes/showcase.py)

- Common shell dependency tree
- [`nicegui_app/ui/platform_summary.py`](../../nicegui_app/ui/platform_summary.py)
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_render_feedback_channel`
  - `_render_co_creation`
  - `_tone_badge`
- [`nicegui_app/ui/reference_navigation.py`](../../nicegui_app/ui/reference_navigation.py)
- [`nicegui_app/release_evidence.py`](../../nicegui_app/release_evidence.py)

Primary regions: editorial hero, live summary, team operating model, capabilities, solutions, principles, resources, and co-creation closing.

## `/system-architecture` — Architecture and trust

Entry: [`system_architecture_page` in `showcase.py`](../../nicegui_app/ui/page_routes/showcase.py)

- Common shell dependency tree
- [`nicegui_app/ui/page_shared.py`](../../nicegui_app/ui/page_shared.py)
  - `_render_feedback_channel`
  - `_tone_badge`
- [`nicegui_app/ui/reference_navigation.py`](../../nicegui_app/ui/reference_navigation.py)
- [`nicegui_app/release_evidence.py`](../../nicegui_app/release_evidence.py)
- [`nicegui_app/ui/platform_summary.py`](../../nicegui_app/ui/platform_summary.py)

Primary regions: architecture hero, service lifeline, system layers, trust evidence, FAQ, and reference pager.
