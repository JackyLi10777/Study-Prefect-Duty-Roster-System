"""Shared, read-only presentation model for weekly roster surfaces.

Policy decides which slots exist and who may serve them.  This module only
normalizes those decisions so the browser preview, PDF renderer, and public
viewer cannot drift in their weekday/row/closed/vacant interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Iterable, Literal, Mapping

from roster_policy import (
    DUTY_SERVICE_TIME_WINDOWS,
    ROOM_OPENING_TIME_WINDOWS,
    DutyPost,
    SchoolDay,
    is_chinese_display_name,
    is_room_open,
)


DAY_ORDER: tuple[SchoolDay, ...] = (
    SchoolDay.MONDAY,
    SchoolDay.TUESDAY,
    SchoolDay.WEDNESDAY,
    SchoolDay.THURSDAY,
    SchoolDay.FRIDAY,
)

DAY_TEXT: dict[SchoolDay, tuple[str, str]] = {
    SchoolDay.MONDAY: ("星期一", "MONDAY"),
    SchoolDay.TUESDAY: ("星期二", "TUESDAY"),
    SchoolDay.WEDNESDAY: ("星期三", "WEDNESDAY"),
    SchoolDay.THURSDAY: ("星期四", "THURSDAY"),
    SchoolDay.FRIDAY: ("星期五", "FRIDAY"),
}


class RosterPresentationError(ValueError):
    """A malformed roster read model cannot be presented safely."""


class RosterCellState(str, Enum):
    """Stable semantic states shared by every roster surface."""

    ASSIGNED = "assigned"
    VACANT = "vacant"
    ROOM_CLOSED = "room_closed"
    DAY_CLOSED = "day_closed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class RosterRowSpec:
    post: DutyPost
    slot_index: int
    display_label: str

    @property
    def label_zh(self) -> str:
        """Compatibility alias: duty-post names intentionally remain English."""

        return self.display_label

    @property
    def label_en(self) -> str:
        return self.display_label

    @property
    def opening_time(self) -> tuple[str, str]:
        """Room availability window retained as non-prominent metadata."""

        return ROOM_OPENING_TIME_WINDOWS[self.post]

    @property
    def service_time(self) -> tuple[str, str]:
        """Actual prefect duty window shown in matrices and exports."""

        return DUTY_SERVICE_TIME_WINDOWS[self.post]


ROSTER_ROWS: tuple[RosterRowSpec, ...] = (
    RosterRowSpec(DutyPost.ASSIST_IN_CHARGE, 1, "Assist. in charge"),
    RosterRowSpec(DutyPost.ROOM_302, 1, "Room 302 Study Room"),
    RosterRowSpec(DutyPost.ROOM_303, 1, "Homework Completion Room - 1"),
    RosterRowSpec(DutyPost.ROOM_303, 2, "Homework Completion Room - 2"),
    RosterRowSpec(DutyPost.ROOM_202, 1, "Room 202 F1 Study Group - 1"),
    RosterRowSpec(DutyPost.ROOM_202, 2, "Room 202 F1 Study Group - 2"),
)


def roster_row_spec(post: DutyPost, slot_index: int) -> RosterRowSpec:
    """Return the canonical presentation row for one policy post and slot."""

    for spec in ROSTER_ROWS:
        if spec.post == post and spec.slot_index == slot_index:
            return spec
    raise KeyError((post, slot_index))


def roster_display_label(post_code: str | DutyPost, slot_index: int = 1) -> str:
    """Resolve an assignment read model to its canonical duty-post label."""

    post = post_code if isinstance(post_code, DutyPost) else DutyPost[str(post_code)]
    return roster_row_spec(post, int(slot_index)).display_label


@dataclass(frozen=True)
class RosterScheduleDay:
    day: SchoolDay
    duty_date: date | None
    state: Literal["open", "day_closed"] = "open"

    @property
    def label_zh(self) -> str:
        return DAY_TEXT[self.day][0]

    @property
    def label_en(self) -> str:
        return DAY_TEXT[self.day][1].title()


@dataclass(frozen=True)
class RosterScheduleCell:
    day: SchoolDay
    post: DutyPost
    slot_index: int
    state: RosterCellState
    duty_date: date | None = None
    cell_key: str = ""
    assignment_id: int | None = None
    prefect_id: str | None = None
    prefect_name: str | None = None
    editable: bool = False

    @property
    def status(self) -> str:
        """Legacy browser/PDF status kept while callers migrate to ``state``."""

        if self.state is RosterCellState.ASSIGNED:
            return "active"
        if self.state is RosterCellState.VACANT:
            return "vacant"
        return "closed"


@dataclass(frozen=True)
class RosterScheduleRow:
    spec: RosterRowSpec
    cells: tuple[RosterScheduleCell, ...]


@dataclass(frozen=True)
class RosterSchedulePresentation:
    """Canonical weekly matrix with private and public-safe projections."""

    roster_week_id: int | None
    week_start: date
    version: int
    status: str
    days: tuple[RosterScheduleDay, ...]
    rows: tuple[RosterScheduleRow, ...]

    def to_dict(self) -> dict[str, object]:
        """Serialize the full local presentation contract, including stable IDs."""

        return {
            "week": {
                "id": self.roster_week_id,
                "weekStart": self.week_start.isoformat(),
                "version": self.version,
                "status": self.status,
            },
            "days": [
                {
                    "code": item.day.name,
                    "date": item.duty_date.isoformat() if item.duty_date else None,
                    "labelZh": item.label_zh,
                    "labelEn": item.label_en,
                    "state": item.state,
                }
                for item in self.days
            ],
            "rows": [
                {
                    "postCode": row.spec.post.name,
                    "slotIndex": row.spec.slot_index,
                    "labelZh": row.spec.label_zh,
                    "labelEn": row.spec.label_en,
                    "openingTime": _time_dict(row.spec.opening_time),
                    "serviceTime": _time_dict(row.spec.service_time),
                    "cells": [
                        {
                            "dayCode": cell.day.name,
                            "date": cell.duty_date.isoformat() if cell.duty_date else None,
                            "cellKey": cell.cell_key,
                            "state": cell.state.value,
                            "assignmentId": cell.assignment_id,
                            "prefectId": cell.prefect_id,
                            "prefectName": cell.prefect_name,
                            "editable": cell.editable,
                        }
                        for cell in row.cells
                    ],
                }
                for row in self.rows
            ],
        }

    def to_public_dict(self) -> dict[str, object]:
        """Return the existing minimum-data public-viewer matrix schema."""

        rows: list[dict[str, object]] = []
        for row in self.rows:
            public_cells: list[dict[str, str]] = []
            for cell in row.cells:
                if cell.state is RosterCellState.ASSIGNED:
                    name_zh = str(cell.prefect_name or "").strip()
                    if not is_chinese_display_name(name_zh):
                        raise RosterPresentationError(
                            "Every name in a public roster must be a valid Chinese display name."
                        )
                    public_cells.append(
                        {
                            "status": "assigned",
                            "state": RosterCellState.ASSIGNED.value,
                            "nameZh": name_zh,
                        }
                    )
                elif cell.state is RosterCellState.VACANT:
                    public_cells.append(
                        {"status": "vacant", "state": RosterCellState.VACANT.value}
                    )
                else:
                    # Keep the v1 ``status`` value for deployed viewers while
                    # exposing the additive semantic state required to
                    # distinguish a room-policy closure from a whole-day
                    # weekly override.
                    public_cells.append(
                        {"status": "closed", "state": cell.state.value}
                    )
            rows.append(
                {
                    "postCode": row.spec.post.name,
                    "slotIndex": row.spec.slot_index,
                    "labelZh": row.spec.label_zh,
                    "labelEn": row.spec.label_en,
                    "dutyTime": _time_dict(row.spec.service_time),
                    "cells": public_cells,
                }
            )
        return {
            "weekStart": self.week_start.isoformat(),
            "version": self.version,
            "days": [
                {
                    "code": item.day.name,
                    "date": item.duty_date.isoformat() if item.duty_date else None,
                    "labelZh": item.label_zh,
                    "labelEn": item.label_en,
                    "state": item.state,
                }
                for item in self.days
            ],
            "rows": rows,
        }


def build_roster_presentation(
    week: Mapping[str, object],
    assignments: Iterable[Mapping[str, object]],
    *,
    closed_days: Iterable[str | SchoolDay] = (),
    unavailable_slots: Iterable[object] = (),
    editable: bool | None = None,
    strict: bool = False,
) -> RosterSchedulePresentation:
    """Build the canonical dated matrix from an atomic workflow snapshot."""

    week_start = _coerce_week_start(week.get("weekStart"))
    status = str(week.get("status") or "draft")
    if editable is None:
        editable = status == "draft"
    resolved_closed_days = _closed_days(week.get("closedDays"), closed_days, strict=strict)
    resolved_unavailable_slots = _unavailable_slots(
        week.get("slotExceptions", week.get("unavailableSlots")),
        unavailable_slots,
        strict=strict,
    )
    rows = _build_rows(
        assignments,
        week_start=week_start,
        closed_days=resolved_closed_days,
        unavailable_slots=resolved_unavailable_slots,
        editable=bool(editable),
        strict=strict,
    )
    return RosterSchedulePresentation(
        roster_week_id=_optional_int(week.get("id")),
        week_start=week_start,
        version=_optional_int(week.get("version")) or 1,
        status=status,
        days=tuple(
            RosterScheduleDay(
                day,
                week_start + timedelta(days=int(day)),
                "day_closed" if day in resolved_closed_days else "open",
            )
            for day in DAY_ORDER
        ),
        rows=rows,
    )


def build_roster_schedule(
    assignments: Iterable[Mapping[str, object]],
    *,
    closed_days: Iterable[str | SchoolDay] = (),
    unavailable_slots: Iterable[object] = (),
) -> tuple[RosterScheduleRow, ...]:
    """Compatibility adapter returning the historical undated row tuple."""

    return _build_rows(
        assignments,
        week_start=None,
        closed_days=_closed_days(None, closed_days, strict=False),
        unavailable_slots=_unavailable_slots(None, unavailable_slots, strict=False),
        editable=True,
        strict=False,
    )


def _build_rows(
    assignments: Iterable[Mapping[str, object]],
    *,
    week_start: date | None,
    closed_days: frozenset[SchoolDay],
    unavailable_slots: frozenset[tuple[SchoolDay, DutyPost, int]],
    editable: bool,
    strict: bool,
) -> tuple[RosterScheduleRow, ...]:
    indexed: dict[tuple[str, str, int], Mapping[str, object]] = {}
    for item in assignments:
        try:
            key = (str(item["day"]), str(item["postCode"]), int(item["slotIndex"]))
        except (KeyError, TypeError, ValueError) as error:
            if strict:
                raise RosterPresentationError("The roster contains an invalid assignment.") from error
            continue
        existing = indexed.get(key)
        if existing is not None:
            existing_status = str(existing.get("status") or "")
            item_status = str(item.get("status") or "")
            if existing_status == "active" and item_status == "replaced":
                continue
            if existing_status == "replaced" and item_status == "active":
                indexed[key] = item
                continue
            if strict:
                raise RosterPresentationError("The roster contains a duplicate duty slot.")
        indexed[key] = item

    rows: list[RosterScheduleRow] = []
    for spec in ROSTER_ROWS:
        cells: list[RosterScheduleCell] = []
        for day in DAY_ORDER:
            duty_date = week_start + timedelta(days=int(day)) if week_start else None
            common = {
                "day": day,
                "post": spec.post,
                "slot_index": spec.slot_index,
                "duty_date": duty_date,
                "cell_key": f"{day.name}:{spec.post.name}:{spec.slot_index}",
            }
            if day in closed_days:
                cells.append(
                    RosterScheduleCell(**common, state=RosterCellState.DAY_CLOSED, editable=False)
                )
                continue
            if not is_room_open(spec.post, day):
                cells.append(
                    RosterScheduleCell(**common, state=RosterCellState.ROOM_CLOSED, editable=False)
                )
                continue
            if (day, spec.post, spec.slot_index) in unavailable_slots:
                cells.append(
                    RosterScheduleCell(**common, state=RosterCellState.UNAVAILABLE, editable=False)
                )
                continue
            item = indexed.get((day.name, spec.post.name, spec.slot_index))
            if item is None:
                if strict:
                    raise RosterPresentationError("The roster is missing a required duty slot.")
                cells.append(
                    RosterScheduleCell(**common, state=RosterCellState.VACANT, editable=editable)
                )
                continue
            assignment_status = str(item.get("status") or "")
            assignment_id = _optional_int(item.get("id"))
            prefect_id = str(item.get("prefectId") or "").strip() or None
            if assignment_status == "vacant":
                cells.append(
                    RosterScheduleCell(
                        **common,
                        state=RosterCellState.VACANT,
                        assignment_id=assignment_id,
                        editable=editable,
                    )
                )
                continue
            if assignment_status not in {"active", "replaced"}:
                if strict:
                    raise RosterPresentationError("The roster contains an invalid assignment status.")
                cells.append(
                    RosterScheduleCell(
                        **common,
                        state=RosterCellState.VACANT,
                        assignment_id=assignment_id,
                        editable=editable,
                    )
                )
                continue
            prefect_name = str(item.get("prefectName") or "").strip() or None
            if strict and not prefect_name:
                raise RosterPresentationError("The roster contains an assignment without a prefect name.")
            cells.append(
                RosterScheduleCell(
                    **common,
                    state=RosterCellState.ASSIGNED,
                    assignment_id=assignment_id,
                    prefect_id=prefect_id,
                    prefect_name=prefect_name,
                    editable=editable,
                )
            )
        rows.append(RosterScheduleRow(spec, tuple(cells)))
    return tuple(rows)


def _unavailable_slots(
    week_value: object,
    explicit: Iterable[object],
    *,
    strict: bool,
) -> frozenset[tuple[SchoolDay, DutyPost, int]]:
    values: list[object] = []
    if week_value is not None:
        if isinstance(week_value, (str, Mapping)):
            values.append(week_value)
        else:
            try:
                values.extend(iter(week_value))  # type: ignore[arg-type]
            except TypeError as error:
                if strict:
                    raise RosterPresentationError("The roster contains an invalid unavailable-slot list.") from error
    values.extend(explicit)
    result: set[tuple[SchoolDay, DutyPost, int]] = set()
    valid_keys = {
        (day, spec.post, spec.slot_index)
        for day in DAY_ORDER
        for spec in ROSTER_ROWS
        if is_room_open(spec.post, day)
    }
    for value in values:
        try:
            if isinstance(value, Mapping):
                if value.get("kind", "unavailable") != "unavailable":
                    raise ValueError
                raw_key = value.get("cellKey")
                if raw_key:
                    day_code, post_code, slot_text = str(raw_key).split(":", 2)
                    slot = (SchoolDay[day_code], DutyPost[post_code], int(slot_text))
                else:
                    slot = (
                        SchoolDay[str(value["day"])],
                        DutyPost[str(value["postCode"])],
                        int(value["slotIndex"]),
                    )
            elif isinstance(value, tuple) and len(value) == 3:
                raw_day, raw_post, raw_index = value
                slot = (
                    raw_day if isinstance(raw_day, SchoolDay) else SchoolDay[str(raw_day)],
                    raw_post if isinstance(raw_post, DutyPost) else DutyPost[str(raw_post)],
                    int(raw_index),
                )
            else:
                day_code, post_code, slot_text = str(value).split(":", 2)
                slot = (SchoolDay[day_code], DutyPost[post_code], int(slot_text))
            if slot not in valid_keys:
                raise ValueError
            result.add(slot)
        except (KeyError, TypeError, ValueError):
            if strict:
                raise RosterPresentationError("The roster contains an invalid unavailable slot.") from None
    return frozenset(result)


def _closed_days(
    week_value: object,
    explicit: Iterable[str | SchoolDay],
    *,
    strict: bool,
) -> frozenset[SchoolDay]:
    values: list[object] = []
    if week_value is not None:
        if isinstance(week_value, (str, SchoolDay)):
            values.append(week_value)
        else:
            try:
                values.extend(iter(week_value))  # type: ignore[arg-type]
            except TypeError as error:
                if strict:
                    raise RosterPresentationError("The roster contains an invalid closed-day list.") from error
    values.extend(explicit)
    result: set[SchoolDay] = set()
    for value in values:
        try:
            result.add(value if isinstance(value, SchoolDay) else SchoolDay[str(value)])
        except (KeyError, TypeError):
            if strict:
                raise RosterPresentationError("The roster contains an invalid closed day.") from None
    return frozenset(result)


def _coerce_week_start(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise RosterPresentationError("Roster week start must be an ISO calendar date.") from error
    raise RosterPresentationError("Roster week start must be a date or ISO date string.")


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _time_dict(value: tuple[str, str]) -> dict[str, str]:
    return {"start": value[0], "end": value[1]}


__all__ = [
    "DAY_ORDER",
    "DAY_TEXT",
    "ROSTER_ROWS",
    "RosterCellState",
    "RosterPresentationError",
    "RosterRowSpec",
    "RosterScheduleCell",
    "RosterScheduleDay",
    "RosterSchedulePresentation",
    "RosterScheduleRow",
    "build_roster_presentation",
    "build_roster_schedule",
    "roster_display_label",
    "roster_row_spec",
]
