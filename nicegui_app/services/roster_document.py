"""Immutable, strictly validated input shared by every roster output.

Only capture_roster_document reads the workflow. Renderers receive the returned
document and cannot silently advance to a different roster revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping, Protocol

from nicegui_app.config import POLICY_VERSION
from nicegui_app.services.roster_presentation import (
    RosterPresentationError,
    RosterSchedulePresentation,
    build_roster_presentation,
)


class ScheduleSource(Protocol):
    def roster_schedule_snapshot(self, roster_week_id: int) -> tuple[dict[str, object], list[dict[str, object]]]: ...


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class RosterScheduleSnapshot:
    roster_week_id: int
    week_start: date
    status: str
    version: int
    source_policy_version: str | None
    assignments: tuple[Mapping[str, object], ...]
    week: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class RosterDocument:
    snapshot: RosterScheduleSnapshot
    presentation: RosterSchedulePresentation
    render_policy_version: str = POLICY_VERSION

    def matches_revision(self, week: Mapping[str, object]) -> bool:
        """Compare a fresh authorized read before issuing a download ticket."""
        return (
            week.get("id") == self.snapshot.roster_week_id
            and week.get("version") == self.snapshot.version
            and week.get("status") == self.snapshot.status
        )


def capture_roster_document(source: ScheduleSource, roster_week_id: int) -> RosterDocument:
    week, assignments = source.roster_schedule_snapshot(roster_week_id)
    try:
        if type(week["id"]) is not int or type(week["version"]) is not int:
            raise ValueError
        source_id = int(week["id"])
        version = int(week["version"])
        status = str(week["status"])
        start = week["weekStart"]
        if isinstance(start, datetime):
            start = start.date()
        elif isinstance(start, str):
            start = date.fromisoformat(start)
        if (
            source_id != roster_week_id or version < 1
            or status not in {"draft", "published", "withdrawn"}
            or not isinstance(start, date) or start.weekday() != 0
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise RosterPresentationError("The roster snapshot has invalid identity, revision, or week metadata.") from error
    frozen_week = _freeze({**week, "id": source_id, "version": version, "status": status, "weekStart": start})
    frozen_assignments = _freeze(assignments)
    snapshot = RosterScheduleSnapshot(
        roster_week_id=source_id,
        week_start=start,
        status=status,
        version=version,
        source_policy_version=str(week["policyVersion"]) if week.get("policyVersion") else None,
        assignments=frozen_assignments,  # type: ignore[arg-type]
        week=frozen_week,  # type: ignore[arg-type]
    )
    return RosterDocument(
        snapshot,
        build_roster_presentation(snapshot.week, snapshot.assignments, strict=True),
    )
