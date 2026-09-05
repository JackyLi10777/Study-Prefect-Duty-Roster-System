"""Pure next-action selection for the Dashboard's selected roster week."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DashboardNextAction:
    status_key: str
    tone: str
    action_key: str
    destination: str
    icon: str


def resolve_dashboard_next_action(
    *,
    has_prefects: bool,
    week_start: date,
    selected_week: Mapping[str, object] | None,
    latest_week: Mapping[str, object] | None = None,
) -> DashboardNextAction:
    """Use the generation page's exact week, never an unrelated latest roster.

    Both workflow adapters return only active records from their exact-week
    lookup. The latest history item may supply a withdrawn status, but only for
    that same week and only when there is no active record.
    """
    if week_start.weekday() != 0:
        raise ValueError("The Dashboard roster week must start on a Monday.")
    if not has_prefects:
        return DashboardNextAction(
            "flow_directory_ready", "attention", "open_prefects", "/prefects", "groups"
        )

    record = selected_week
    if (record is None and latest_week is not None
            and str(latest_week.get("weekStart")) == week_start.isoformat()
            and latest_week.get("status") == "withdrawn"):
        record = latest_week
    if record is None or str(record.get("weekStart")) != week_start.isoformat():
        return DashboardNextAction(
            "dashboard_no_active_week", "action", "create_draft", "/rosters", "edit_calendar"
        )
    status = record.get("status")
    if status == "withdrawn":
        return DashboardNextAction(
            "withdrawn", "attention", "create_draft", "/rosters", "edit_calendar"
        )
    if status not in {"draft", "published"}:
        raise ValueError("Unknown Dashboard roster status.")
    roster_id = record.get("id")
    if type(roster_id) is not int or roster_id <= 0:
        raise ValueError("The Dashboard requires a valid roster identifier.")
    if status == "draft":
        return DashboardNextAction(
            "flow_draft_ready", "action", "flow_open_draft", f"/rosters/{roster_id}", "fact_check"
        )
    return DashboardNextAction(
        "published", "stable", "flow_open_published", f"/rosters/{roster_id}", "description"
    )
