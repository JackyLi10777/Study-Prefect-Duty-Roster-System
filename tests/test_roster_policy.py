from __future__ import annotations

from collections import Counter, defaultdict

from roster_core.generator import generate_weekly_roster
from roster_core.loaders import load_prefect_seed
from roster_policy import DUTY_TIME_WINDOWS, DutyPost, SchoolDay, can_assign_role, duty_weight, required_posts_for_day


def test_policy_role_gates_are_strict() -> None:
    ahp = "Assistant Head Study Prefect (助理首席導學風紀)"
    regular = "Study Prefect (導學風紀)"

    assert can_assign_role(ahp, DutyPost.ASSIST_IN_CHARGE)
    assert not can_assign_role(ahp, DutyPost.ROOM_302)
    assert not can_assign_role(regular, DutyPost.ASSIST_IN_CHARGE)
    assert can_assign_role(regular, DutyPost.ROOM_303)


def test_room_202_is_closed_on_tuesday_and_friday() -> None:
    assert DutyPost.ROOM_202 not in required_posts_for_day(SchoolDay.TUESDAY)
    assert DutyPost.ROOM_202 not in required_posts_for_day(SchoolDay.FRIDAY)
    assert required_posts_for_day(SchoolDay.MONDAY).count(DutyPost.ROOM_202) == 2


def test_duty_weights_match_school_policy() -> None:
    assert duty_weight(DutyPost.ASSIST_IN_CHARGE) == 1.0
    assert duty_weight(DutyPost.ROOM_302) == 1.0
    assert duty_weight(DutyPost.ROOM_303) == 1.5
    assert duty_weight(DutyPost.ROOM_202) == 1.5


def test_room_time_windows_match_school_policy() -> None:
    assert DUTY_TIME_WINDOWS[DutyPost.ROOM_302] == ("15:45", "18:00")
    assert DUTY_TIME_WINDOWS[DutyPost.ROOM_303] == ("15:45", "17:00")
    assert DUTY_TIME_WINDOWS[DutyPost.ROOM_202] == ("15:45", "17:00")


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
