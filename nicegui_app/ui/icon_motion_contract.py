"""Auditable semantic icon and action-motion coverage contract.

The browser runtime still owns animation.  This module records why each
release-critical control is animated (or intentionally role-only) so Admin,
Guest, mobile, documentation and tests share one reviewable denominator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


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
    motion_mode: str = "role-only"
    rotation_direction: str | None = None
    preview_degrees: int = 0
    activation_degrees: int = 0
    static_rationale: str | None = None


STANDARD_STATES = ("idle", "hover_focus", "pressed", "busy", "result", "settled")
PERSISTENT_STATES = ("idle", "pressed", "state_changed", "settled")


ICON_MOTION_CONTRACTS = (
    IconMotionContract("settings", ("/settings",), ("settings",), "page_catalog.py", ("admin", "guest"), True, "settings", None, "gear", "role", STANDARD_STATES, "Only the glyph rotates; the selected host remains still.", "rotary-only", "cw", 70, 270),
    IconMotionContract("sound", ("*",), ("enable_sound_feedback", "disable_sound_feedback"), "shell.py", ("admin", "guest"), True, "volume_off", "volume_up", "toggle", "persistent", PERSISTENT_STATES, "The truthful volume state morphs without rotation.", "persistent-morph"),
    IconMotionContract("theme", ("*",), ("theme_switch_to_light", "theme_switch_to_dark"), "shell.py", ("admin", "guest", "public"), True, "light_mode", "dark_mode", "toggle", "persistent", PERSISTENT_STATES, "A user-triggered state change combines one morph with one bounded turn.", "persistent-rotary", "cw", 0, 90),
    IconMotionContract("usage_instructions", ("/guide", "/getting-started"), ("operator_guide", "getting_started"), "page_catalog.py", ("admin", "guest", "public"), True, "help_outline", "lightbulb", "navigation", "preview", STANDARD_STATES, "Source glyph remains with visible text.", "morph-only"),
    IconMotionContract("generate_draft", ("/rosters",), ("generate_roster",), "weekly.py:edit_calendar", ("admin", "guest"), True, "edit_calendar", "calendar_month", "edit", "lifecycle", STANDARD_STATES, "Result is also stated in text.", "lifecycle-morph"),
    IconMotionContract("declare_leave", ("/rosters",), ("declare_leave",), "weekly.py:event_busy", ("admin", "guest"), True, "event_busy", "event_note", "edit", "lifecycle", STANDARD_STATES, "Busy and result states remain explicit in the progress dialog and button label.", "lifecycle-morph"),
    IconMotionContract("review_publish", ("/rosters/{id}",), ("publish",), "weekly.py:publish", ("admin", "guest"), True, "publish", "fact_check", "confirm", "lifecycle", STANDARD_STATES, "No unpublished state is implied.", "lifecycle-morph"),
    IconMotionContract("published_leave", ("/rosters/{id}/adjustments",), ("adjust_roster",), "weekly.py:fact_check", ("admin", "guest"), True, "fact_check", "task_alt", "confirm", "lifecycle", STANDARD_STATES, "Status text remains authoritative.", "lifecycle-morph"),
    IconMotionContract("withdraw_published_roster", ("/rosters/{id}",), ("withdraw_roster_action",), "weekly.py:undo", ("admin", "guest"), True, "undo", None, "danger", "role", STANDARD_STATES, "Undo makes one bounded reverse turn; confirmation owns the consequence.", "rotary-action", "ccw", 0, -180),
    IconMotionContract("roster_history_navigation", ("/rosters",), ("roster_workflow_history",), "weekly.py:history", ("admin", "guest"), True, "history", None, "navigation", "role", STANDARD_STATES, "History previews and activates counter-clockwise without changing state.", "rotary-history", "ccw", -55, -180),
    IconMotionContract("data_import", ("/prefects",), ("import_prefects",), "people.py:upload_file", ("admin",), True, "upload_file", "fact_check", "upload", "lifecycle", STANDARD_STATES, "Guest restriction remains visible and static.", "lifecycle-morph"),
    IconMotionContract("fairness", ("/prefects",), ("fairness_explained",), "people.py:balance", ("admin", "guest"), True, "balance", "fact_check", "navigation", "preview", STANDARD_STATES, "Only the clickable audit entry previews the evidence view; static fairness evidence remains still.", "morph-only"),
    IconMotionContract("add_prefect", ("/prefects",), ("add_prefect",), "people.py:person_add", ("admin", "guest"), True, "person_add", "group_add", "create", "lifecycle", STANDARD_STATES, "Name and validation messages remain visible.", "lifecycle-morph"),
    IconMotionContract("edit_prefect", ("/prefects",), ("edit_prefect",), "people.py:edit", ("admin", "guest"), True, "edit", "edit_note", "edit", "lifecycle", STANDARD_STATES, "Edit does not imply save until result feedback.", "lifecycle-morph"),
    IconMotionContract("archive_prefect", ("/prefects",), ("archive_prefect",), "people.py:archive", ("admin", "guest"), True, "archive", "inventory_2", "confirm", "lifecycle", STANDARD_STATES, "Archive confirmation remains explicit.", "lifecycle-morph"),
    IconMotionContract("new_year_directory", ("/handover",), ("school_year_rollover_action",), "stewardship.py:event_repeat", ("admin", "guest"), True, "event_repeat", "calendar_month", "refresh", "lifecycle", STANDARD_STATES, "Destructive consequences remain in the dialog.", "lifecycle-morph"),
    IconMotionContract("backup_settings_navigation", ("/settings", "/handover"), ("open_backup_settings",), "page_shared.py:settings_backup_restore", ("admin", "guest"), True, "settings_backup_restore", None, "refresh", "role", STANDARD_STATES, "The circular backup navigation glyph turns without implying a restore.", "rotary-navigation", "cw", 60, 180),
    IconMotionContract("restore_backup", ("/settings",), ("restore_selected_backup",), "stewardship.py:restore", ("admin",), True, "restore", "verified", "refresh", "lifecycle", STANDARD_STATES, "Actual restore state comes only from the operation lifecycle.", "lifecycle-morph"),
    IconMotionContract("acceptance_guide", ("/handover",), ("acceptance_title",), "page_shared.py:fact_check", ("admin", "guest"), True, "fact_check", "task_alt", "confirm", "lifecycle", STANDARD_STATES, "Human acceptance cannot be fabricated by animation.", "lifecycle-morph"),
    IconMotionContract("verified_snapshot", ("/settings", "/handover"), ("create_verified_backup",), "stewardship.py:add_to_drive", ("admin",), True, "add_to_drive", "arrow_forward", "confirm", "lifecycle", STANDARD_STATES, "Verification label and digest remain visible.", "lifecycle-morph"),
    IconMotionContract("change_verse", ("/", "/devotional"), ("refresh_verse",), "home.py:refresh", ("admin", "guest", "public"), True, "refresh", "autorenew", "refresh", "lifecycle", STANDARD_STATES, "Verse text never moves with the control.", "lifecycle-morph"),
    IconMotionContract("temporary_report", ("/support",), ("report_problem",), "page_catalog.py:support_agent", ("admin", "guest", "public"), True, "support_agent", "contact_support", "navigation", "lifecycle", STANDARD_STATES, "Incident content remains untrusted and local-only.", "lifecycle-morph"),
)


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_UI_ROOT = _PROJECT_ROOT / "nicegui_app" / "ui"


def _declared_route_templates() -> set[str]:
    """Read actual NiceGUI route decorators without importing the UI runtime."""

    routes: set[str] = set()
    for path in (_UI_ROOT / "page_routes").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for route in re.findall(r'@ui\.page\("([^"]+)"\)', source):
            routes.add(re.sub(r"\{[^}]+\}", "{id}", route))
    return routes


def _callsite_source(hint: str) -> tuple[Path | None, str | None, str]:
    filename, separator, token = hint.partition(":")
    candidates = tuple(
        path
        for path in (_UI_ROOT / filename, _UI_ROOT / "page_routes" / filename)
        if path.is_file()
    )
    if len(candidates) != 1:
        return None, None, token if separator else ""
    path = candidates[0]
    return path, path.read_text(encoding="utf-8"), token if separator else ""


def validate_icon_motion_contracts(
    contracts: tuple[IconMotionContract, ...] | None = None,
) -> list[str]:
    """Validate inventory entries against real routes, copy and UI call sites."""

    if contracts is None:
        contracts = ICON_MOTION_CONTRACTS
    from nicegui_app.ui.i18n_catalog import MESSAGES

    errors: list[str] = []
    keys = [contract.key for contract in contracts]
    if len(keys) != len(set(keys)):
        errors.append("Duplicate semantic control key")
    allowed_categories = {"persistent", "preview", "lifecycle", "role", "static"}
    allowed_motion_modes = {
        "static",
        "role-only",
        "morph-only",
        "lifecycle-morph",
        "persistent-morph",
        "rotary-only",
        "persistent-rotary",
        "rotary-navigation",
        "rotary-history",
        "rotary-action",
    }
    rotary_modes = {
        "rotary-only",
        "persistent-rotary",
        "rotary-navigation",
        "rotary-history",
        "rotary-action",
    }
    declared_routes = _declared_route_templates()
    for contract in contracts:
        if contract.category not in allowed_categories:
            errors.append(f"Unknown category for {contract.key}: {contract.category}")
        if contract.motion_mode not in allowed_motion_modes:
            errors.append(f"Unknown motion mode for {contract.key}: {contract.motion_mode}")
        if contract.motion_mode in rotary_modes:
            if contract.rotation_direction not in {"cw", "ccw"}:
                errors.append(f"Missing rotation direction for {contract.key}")
            if contract.activation_degrees == 0:
                errors.append(f"Missing activation rotation for {contract.key}")
        elif contract.rotation_direction is not None or contract.preview_degrees or contract.activation_degrees:
            errors.append(f"Non-rotary contract declares rotation for {contract.key}")
        if contract.category in {"persistent", "preview", "lifecycle"} and not contract.destination_glyph:
            errors.append(f"Missing destination glyph for {contract.key}")
        if not contract.routes or not contract.i18n_keys or not contract.callsite_hint:
            errors.append(f"Incomplete traceability for {contract.key}")
        for route in contract.routes:
            normalized_route = re.sub(r"\{[^}]+\}", "{id}", route)
            if route != "*" and normalized_route not in declared_routes:
                errors.append(f"Unknown route for {contract.key}: {route}")
        for i18n_key in contract.i18n_keys:
            if i18n_key not in MESSAGES:
                errors.append(f"Unknown i18n key for {contract.key}: {i18n_key}")
        callsite_path, callsite_source, callsite_token = _callsite_source(contract.callsite_hint)
        if callsite_path is None or callsite_source is None:
            errors.append(f"Unresolved callsite for {contract.key}: {contract.callsite_hint}")
        elif callsite_token:
            if callsite_token not in callsite_source:
                errors.append(f"Missing callsite token for {contract.key}: {callsite_token}")
        elif not any(
            trace in callsite_source
            for trace in (contract.source_glyph, *contract.i18n_keys)
        ):
            errors.append(f"Untraceable callsite for {contract.key}: {contract.callsite_hint}")
        if contract.reduced_motion == "":
            errors.append(f"Missing reduced-motion result for {contract.key}")
    return errors


__all__ = ("ICON_MOTION_CONTRACTS", "IconMotionContract", "validate_icon_motion_contracts")
