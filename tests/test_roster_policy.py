from __future__ import annotations

from collections import Counter, defaultdict

from roster_core.generator import generate_weekly_roster
from roster_core.loaders import load_prefect_seed
from roster_policy import (
    DUTY_SERVICE_TIME_WINDOWS,
    DUTY_TIME_WINDOWS,
    ROOM_CAPACITY,
    ROOM_OPENING_TIME_WINDOWS,
    DutyPost,
    PrefectRole,
    SchoolDay,
    can_assign_role,
    duty_weight,
    is_chinese_display_name,
    required_posts_for_day,
)


def test_policy_role_gates_are_strict() -> None:
    ahp = PrefectRole.ASSISTANT_HEAD
    regular = PrefectRole.STUDY_PREFECT

    assert can_assign_role(ahp, DutyPost.ASSIST_IN_CHARGE)
    assert not can_assign_role(ahp, DutyPost.ROOM_302)
    assert not can_assign_role(regular, DutyPost.ASSIST_IN_CHARGE)
    assert can_assign_role(regular, DutyPost.ROOM_303)


def test_authoritative_prefect_names_remain_chinese() -> None:
    assert is_chinese_display_name("歐陽子晴")
    assert is_chinese_display_name("陳·嘉言")
    assert not is_chinese_display_name("Test Prefect")
    assert not is_chinese_display_name("陳 Test")


def test_room_202_is_closed_on_tuesday_and_friday() -> None:
    assert DutyPost.ROOM_202 not in required_posts_for_day(SchoolDay.TUESDAY)
    assert DutyPost.ROOM_202 not in required_posts_for_day(SchoolDay.FRIDAY)
    assert required_posts_for_day(SchoolDay.MONDAY).count(DutyPost.ROOM_202) == 2


def test_room_capacity_is_part_of_the_public_policy_contract() -> None:
    assert ROOM_CAPACITY == {
        DutyPost.ASSIST_IN_CHARGE: 1,
        DutyPost.ROOM_302: 1,
        DutyPost.ROOM_303: 2,
        DutyPost.ROOM_202: 2,
    }


def test_duty_weights_match_school_policy() -> None:
    assert duty_weight(DutyPost.ASSIST_IN_CHARGE) == 1.0
    assert duty_weight(DutyPost.ROOM_302) == 1.0
    assert duty_weight(DutyPost.ROOM_303) == 1.5
    assert duty_weight(DutyPost.ROOM_202) == 1.5


def test_room_time_windows_match_school_policy() -> None:
    assert set(ROOM_OPENING_TIME_WINDOWS) == set(DutyPost)
    assert set(ROOM_OPENING_TIME_WINDOWS.values()) == {("15:40", "17:00")}
    assert DUTY_TIME_WINDOWS is ROOM_OPENING_TIME_WINDOWS


def test_service_time_is_distinct_from_room_opening_time() -> None:
    assert set(DUTY_SERVICE_TIME_WINDOWS) == set(DutyPost)
    assert set(DUTY_SERVICE_TIME_WINDOWS.values()) == {("15:40", "17:00")}
    assert DUTY_SERVICE_TIME_WINDOWS is not ROOM_OPENING_TIME_WINDOWS


def test_generated_roster_preserves_non_negotiable_rules() -> None:
    prefects = load_prefect_seed()
    prefect_by_id = {prefect.id: prefect for prefect in prefects}
    assignments = generate_weekly_roster(prefects)

    by_day = defaultdict(list)
    by_prefect = defaultdict(list)
    for assignment in assignments:
        by_day[assignment.day].append(assignment)
        by_prefect[assignment.prefect_id].append(assignment.day)
        role = prefect_by_id[assignment.prefect_id].role
        assert can_assign_role(role, assignment.post)

    for day in SchoolDay:
        expected = Counter(required_posts_for_day(day))
        actual = Counter(assignment.post for assignment in by_day[day])
        assert actual == expected
        assigned_ids = [assignment.prefect_id for assignment in by_day[day]]
        assert len(assigned_ids) == len(set(assigned_ids))

    for days in by_prefect.values():
        sorted_days = sorted(days)
        for previous, current in zip(sorted_days, sorted_days[1:]):
            assert int(current) - int(previous) > 1


def test_lower_history_weight_gets_first_regular_room_priority() -> None:
    prefects = load_prefect_seed()
    assignments = generate_weekly_roster(prefects)
    monday_room_302 = next(
        assignment
        for assignment in assignments
        if assignment.day is SchoolDay.MONDAY and assignment.post is DutyPost.ROOM_302
    )
    regular_prefects = [
        prefect
        for prefect in prefects
        if can_assign_role(prefect.role, DutyPost.ROOM_302)
        and SchoolDay.MONDAY in prefect.available_days
    ]
    expected = min(regular_prefects, key=lambda prefect: (prefect.history_weight, int(prefect.form[-1]), prefect.history_duties, prefect.name))
    assert monday_room_302.prefect_id == expected.id
