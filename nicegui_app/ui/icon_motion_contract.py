"""Auditable semantic icon and action-motion coverage contract.

The browser runtime still owns animation.  This module records why each
release-critical control is animated (or intentionally role-only) so Admin,
Guest, mobile, documentation and tests share one reviewable denominator.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IconMotionContract:
    key: str
    routes: tuple[str, ...]
    i18n_keys: tuple[str, ...]
    callsite_hint: str
    access_modes: tuple[str, ...]
    mobile: bool
    source_glyph: str
    destination_glyph: str | None
    role: str
    category: str
    states: tuple[str, ...]
    reduced_motion: str
    static_rationale: str | None = None


STANDARD_STATES = ("idle", "hover_focus", "pressed", "busy", "result", "settled")
PERSISTENT_STATES = ("idle", "pressed", "state_changed", "settled")


ICON_MOTION_CONTRACTS = (
    IconMotionContract("settings", ("/settings",), ("settings",), "page_catalog.py", ("admin", "guest"), True, "settings", None, "gear", "role", STANDARD_STATES, "Static tonal state; no rotation."),
    IconMotionContract("sound", ("*",), ("enable_sound_feedback", "disable_sound_feedback"), "shell.py", ("admin", "guest"), True, "volume_off", "volume_up", "toggle", "persistent", PERSISTENT_STATES, "Immediate truthful glyph; no transition."),
    IconMotionContract("theme", ("*",), ("theme_system", "theme_light", "theme_dark"), "shell.py", ("admin", "guest", "public"), True, "light_mode", "dark_mode", "toggle", "persistent", PERSISTENT_STATES, "Immediate truthful glyph; no transition."),
    IconMotionContract("usage_instructions", ("/guide", "/getting-started"), ("operator_guide", "getting_started"), "page_catalog.py", ("admin", "guest", "public"), True, "help_outline", "lightbulb", "navigation", "preview", STANDARD_STATES, "Source glyph remains with visible text."),
    IconMotionContract("generate_draft", ("/rosters",), ("generate_roster",), "weekly.py:edit_calendar", ("admin", "guest"), True, "edit_calendar", "calendar_month", "edit", "lifecycle", STANDARD_STATES, "Result is also stated in text."),
    IconMotionContract("review_publish", ("/rosters/{id}",), ("publish_roster",), "weekly.py:publish", ("admin", "guest"), True, "publish", "fact_check", "confirm", "lifecycle", STANDARD_STATES, "No unpublished state is implied."),
    IconMotionContract("published_leave", ("/rosters/{id}/adjustments",), ("absence_adjustment",), "weekly.py:fact_check", ("admin", "guest"), True, "fact_check", "task_alt", "confirm", "lifecycle", STANDARD_STATES, "Status text remains authoritative."),
    IconMotionContract("history_withdraw", ("/rosters/{id}",), ("withdraw_published_roster",), "weekly.py:undo", ("admin", "guest"), True, "undo", None, "danger", "role", STANDARD_STATES, "Withdrawal has no safe playful destination glyph."),
    IconMotionContract("data_import", ("/prefects",), ("import_prefects",), "people.py:upload_file", ("admin",), True, "upload_file", "fact_check", "upload", "lifecycle", STANDARD_STATES, "Guest restriction remains visible and static."),
    IconMotionContract("fairness", ("/prefects",), ("fairness",), "people.py:balance", ("admin", "guest"), True, "balance", None, "navigation", "role", STANDARD_STATES, "Fairness must not morph into a financial symbol."),
    IconMotionContract("add_prefect", ("/prefects",), ("add_prefect",), "people.py:person_add", ("admin", "guest"), True, "person_add", "group_add", "create", "lifecycle", STANDARD_STATES, "Name and validation messages remain visible."),
    IconMotionContract("edit_prefect", ("/prefects",), ("edit_prefect",), "people.py:edit", ("admin", "guest"), True, "edit", "edit_note", "edit", "lifecycle", STANDARD_STATES, "Edit does not imply save until result feedback."),
    IconMotionContract("archive_prefect", ("/prefects",), ("archive_prefect",), "people.py:archive", ("admin", "guest"), True, "archive", "inventory_2", "confirm", "lifecycle", STANDARD_STATES, "Archive confirmation remains explicit."),
    IconMotionContract("new_year_directory", ("/handover",), ("prepare_new_year_directory",), "stewardship.py:event_repeat", ("admin", "guest"), True, "event_repeat", "calendar_month", "refresh", "lifecycle", STANDARD_STATES, "Destructive consequences remain in the dialog."),
    IconMotionContract("backup_restore", ("/settings", "/handover"), ("restore", "backup"), "stewardship.py:settings_backup_restore", ("admin",), True, "settings_backup_restore", "restore", "refresh", "lifecycle", STANDARD_STATES, "Guest sees a restricted static state."),
    IconMotionContract("acceptance_guide", ("/handover",), ("acceptance_guide",), "page_shared.py:fact_check", ("admin", "guest"), True, "fact_check", "task_alt", "confirm", "lifecycle", STANDARD_STATES, "Human acceptance cannot be fabricated by animation."),
    IconMotionContract("verified_snapshot", ("/settings", "/handover"), ("verified_snapshot",), "page_shared.py:settings_backup_restore", ("admin",), True, "settings_backup_restore", "restore", "refresh", "lifecycle", STANDARD_STATES, "Verification label and digest remain visible."),
    IconMotionContract("change_verse", ("/", "/devotional"), ("another_verse",), "home.py:refresh", ("admin", "guest", "public"), True, "refresh", "autorenew", "refresh", "lifecycle", STANDARD_STATES, "Verse text never moves with the control."),
    IconMotionContract("temporary_report", ("/support",), ("report_problem",), "support.py:support_agent", ("admin", "guest", "public"), True, "support_agent", "contact_support", "navigation", "lifecycle", STANDARD_STATES, "Incident content remains untrusted and local-only."),
)


def validate_icon_motion_contracts() -> list[str]:
    errors: list[str] = []
    keys = [contract.key for contract in ICON_MOTION_CONTRACTS]
    if len(keys) != len(set(keys)):
        errors.append("Duplicate semantic control key")
    allowed_categories = {"persistent", "preview", "lifecycle", "role", "static"}
    for contract in ICON_MOTION_CONTRACTS:
        if contract.category not in allowed_categories:
            errors.append(f"Unknown category for {contract.key}: {contract.category}")
        if contract.category in {"persistent", "preview", "lifecycle"} and not contract.destination_glyph:
            errors.append(f"Missing destination glyph for {contract.key}")
        if not contract.routes or not contract.i18n_keys or not contract.callsite_hint:
            errors.append(f"Incomplete traceability for {contract.key}")
        if contract.reduced_motion == "":
            errors.append(f"Missing reduced-motion result for {contract.key}")
    return errors


__all__ = ("ICON_MOTION_CONTRACTS", "IconMotionContract", "validate_icon_motion_contracts")
