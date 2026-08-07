from __future__ import annotations

from nicegui_app.services.roster_presentation import (
    DAY_ORDER,
    ROSTER_ROWS,
    RosterCellState,
    RosterPresentationError,
    build_roster_presentation,
    build_roster_schedule,
    roster_display_label,
)
import pytest
from roster_policy import DutyPost, SchoolDay


def _cell(schedule, post: DutyPost, slot_index: int, day: SchoolDay):
    row = next(item for item in schedule if item.spec.post is post and item.spec.slot_index == slot_index)
    return next(item for item in row.cells if item.day is day)


def test_schedule_distinguishes_open_vacancies_from_closed_room_days() -> None:
    schedule = build_roster_schedule([])

    assert _cell(schedule, DutyPost.ROOM_202, 1, SchoolDay.MONDAY).status == "vacant"
    assert _cell(schedule, DutyPost.ROOM_202, 1, SchoolDay.TUESDAY).status == "closed"
    assert _cell(schedule, DutyPost.ROOM_202, 2, SchoolDay.FRIDAY).status == "closed"
    assert _cell(schedule, DutyPost.ROOM_303, 1, SchoolDay.TUESDAY).status == "vacant"


def test_schedule_keeps_stable_pdf_row_and_weekday_order_with_chinese_names() -> None:
    schedule = build_roster_schedule(
        [
            {
                "day": "MONDAY",
                "postCode": "ROOM_302",
                "slotIndex": 1,
                "status": "active",
                "prefectName": "測試風紀",
            }
        ]
    )

    assert tuple(row.spec for row in schedule) == ROSTER_ROWS
    assert tuple(cell.day for cell in schedule[0].cells) == DAY_ORDER
    cell = _cell(schedule, DutyPost.ROOM_302, 1, SchoolDay.MONDAY)
    assert cell.status == "active"
    assert cell.prefect_name == "測試風紀"


@pytest.mark.parametrize("reverse", [False, True])
def test_schedule_prefers_active_replacement_over_replaced_history(reverse: bool) -> None:
    active = {
        "id": 102,
        "day": "MONDAY",
        "postCode": "ROOM_302",
        "slotIndex": 1,
        "status": "active",
        "prefectName": "現任風紀",
    }
    replaced = {
        "id": 101,
        "day": "MONDAY",
        "postCode": "ROOM_302",
        "slotIndex": 1,
        "status": "replaced",
        "prefectName": "原任風紀",
    }
    assignments = [active, replaced]
    if reverse:
        assignments.reverse()

    cell = _cell(
        build_roster_schedule(assignments),
        DutyPost.ROOM_302,
        1,
        SchoolDay.MONDAY,
    )

    assert cell.assignment_id == 102
    assert cell.prefect_name == "現任風紀"


def test_presentation_serializes_one_dated_matrix_with_private_and_public_boundaries() -> None:
    presentation = build_roster_presentation(
        {
            "id": 42,
            "weekStart": "2026-09-07",
            "version": 3,
            "status": "draft",
            "closedDays": ["WEDNESDAY"],
        },
        [
            {
                "id": 91,
                "day": "MONDAY",
                "postCode": "ROOM_302",
                "slotIndex": 1,
                "status": "replaced",
                "prefectId": "prefect-zh",
                "prefectName": "測試風紀",
            }
        ],
    )

    assigned = _cell(presentation.rows, DutyPost.ROOM_302, 1, SchoolDay.MONDAY)
    room_closed = _cell(presentation.rows, DutyPost.ROOM_202, 1, SchoolDay.TUESDAY)
    day_closed = _cell(presentation.rows, DutyPost.ROOM_302, 1, SchoolDay.WEDNESDAY)
    assert assigned.state is RosterCellState.ASSIGNED
    assert assigned.status == "active"
    assert assigned.assignment_id == 91
    assert assigned.prefect_id == "prefect-zh"
    assert assigned.duty_date.isoformat() == "2026-09-07"
    assert assigned.cell_key == "MONDAY:ROOM_302:1"
    assert assigned.editable is True
    assert room_closed.state is RosterCellState.ROOM_CLOSED and room_closed.editable is False
    assert day_closed.state is RosterCellState.DAY_CLOSED and day_closed.editable is False
    assert all(
        _cell(presentation.rows, row.spec.post, row.spec.slot_index, SchoolDay.WEDNESDAY).state
        is RosterCellState.DAY_CLOSED
        for row in presentation.rows
    )

    serialized = presentation.to_dict()
    room_302 = next(row for row in serialized["rows"] if row["postCode"] == "ROOM_302")
    assert serialized["week"] == {
        "id": 42,
        "weekStart": "2026-09-07",
        "version": 3,
        "status": "draft",
    }
    assert room_302["openingTime"] == {"start": "15:40", "end": "18:30"}
    assert room_302["serviceTime"] == {"start": "15:40", "end": "17:00"}
    assert room_302["cells"][0]["assignmentId"] == 91

    public = presentation.to_public_dict()
    public_room_302 = next(row for row in public["rows"] if row["postCode"] == "ROOM_302")
    assert public_room_302["dutyTime"] == {"start": "15:40", "end": "17:00"}
    assert public_room_302["cells"][0] == {
        "status": "assigned",
        "state": "assigned",
        "nameZh": "測試風紀",
    }
    assert public_room_302["cells"][2] == {
        "status": "closed",
        "state": "day_closed",
    }
    assert "assignmentId" not in str(public)
    assert "prefectId" not in str(public)
    assert "cellKey" not in str(public)


def test_strict_presentation_rejects_missing_or_duplicate_open_slots() -> None:
    week = {"weekStart": "2026-09-07", "status": "published", "version": 1}

    with pytest.raises(RosterPresentationError, match="missing a required duty slot"):
        build_roster_presentation(week, [], strict=True)

    duplicate = {
        "day": "MONDAY",
        "postCode": "ROOM_302",
        "slotIndex": 1,
        "status": "vacant",
    }
    with pytest.raises(RosterPresentationError, match="duplicate duty slot"):
        build_roster_presentation(week, [duplicate, duplicate], strict=True)


def test_schedule_uses_the_same_authoritative_english_duty_post_names_in_every_locale() -> None:
    assert tuple(row.display_label for row in ROSTER_ROWS) == (
        "Assist. in charge",
        "Room 302 Study Room",
        "Homework Completion Room - 1",
        "Homework Completion Room - 2",
        "Room 202 F1 Study Group - 1",
        "Room 202 F1 Study Group - 2",
    )
    assert all(row.label_zh == row.label_en == row.display_label for row in ROSTER_ROWS)
    assert roster_display_label("ROOM_303", 2) == "Homework Completion Room - 2"
