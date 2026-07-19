from __future__ import annotations

from nicegui_app.services.roster_presentation import (
    DAY_ORDER,
    ROSTER_ROWS,
    build_roster_schedule,
    roster_display_label,
)
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
