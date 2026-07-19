"""Shared, read-only presentation model for weekly roster surfaces.

Policy decides which slots exist and who may serve them.  This module only
normalizes those decisions so the browser preview, PDF renderer, and public
viewer cannot drift in their weekday/row/closed/vacant interpretation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from roster_policy import ROOM_OPENING_TIME_WINDOWS, DutyPost, SchoolDay, is_room_open


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
        return ROOM_OPENING_TIME_WINDOWS[self.post]


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
class RosterScheduleCell:
    day: SchoolDay
    post: DutyPost
    slot_index: int
    status: str
    prefect_name: str | None = None


@dataclass(frozen=True)
class RosterScheduleRow:
    spec: RosterRowSpec
    cells: tuple[RosterScheduleCell, ...]


def build_roster_schedule(
    assignments: Iterable[Mapping[str, object]],
) -> tuple[RosterScheduleRow, ...]:
    """Return a stable post-by-week matrix from assignment read models."""

    indexed: dict[tuple[str, str, int], Mapping[str, object]] = {}
    for item in assignments:
        try:
            key = (str(item["day"]), str(item["postCode"]), int(item["slotIndex"]))
        except (KeyError, TypeError, ValueError):
            continue
        indexed[key] = item

    rows: list[RosterScheduleRow] = []
    for spec in ROSTER_ROWS:
        cells: list[RosterScheduleCell] = []
        for day in DAY_ORDER:
            if not is_room_open(spec.post, day):
                cells.append(RosterScheduleCell(day, spec.post, spec.slot_index, "closed"))
                continue
            item = indexed.get((day.name, spec.post.name, spec.slot_index))
            if item is None or str(item.get("status")) != "active":
                cells.append(RosterScheduleCell(day, spec.post, spec.slot_index, "vacant"))
                continue
            cells.append(
                RosterScheduleCell(
                    day,
                    spec.post,
                    spec.slot_index,
                    "active",
                    str(item.get("prefectName") or "").strip() or None,
                )
            )
        rows.append(RosterScheduleRow(spec, tuple(cells)))
    return tuple(rows)


__all__ = [
    "DAY_ORDER",
    "DAY_TEXT",
    "ROSTER_ROWS",
    "RosterRowSpec",
    "RosterScheduleCell",
    "RosterScheduleRow",
    "build_roster_schedule",
    "roster_display_label",
    "roster_row_spec",
]
