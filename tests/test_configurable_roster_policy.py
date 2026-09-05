"""The prelaunch policy compiler describes dated seats, not assigned people."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import date, datetime

import pytest

from roster_policy.configurable import (
    ApprovedUnavailable,
    BusinessId,
    ConfigurationError,
    CpPolicy,
    DutyTimes,
    ScheduleDateError,
    ScheduleExceptions,
    ScheduleMode,
    SeatKey,
    SeatState,
    TimeWindow,
    TimeWindowError,
    WeeklyPolicy,
    compile_cp,
    compile_weekly,
    default_cp_policy,
    default_weekly_policy,
)


MONDAY = date(2026, 9, 7)


def _change(policy, business, **changes):
    return replace(policy, businesses=tuple(
        replace(post, **changes) if post.business is business else post
        for post in policy.businesses
    ))


def _cp_policy():
    return default_cp_policy(f1_room="501", f2_room="502", f3_room="503")


def _compile_cp(policy=None, **changes):
    options = {
        "start": date(2026, 7, 10), "end": date(2026, 7, 20),
        "selected_dates": (date(2026, 7, 20), date(2026, 7, 11), date(2026, 7, 10)),
        "rooms_confirmed": True,
    }
    options.update(changes)
    return compile_cp(policy or _cp_policy(), **options)


def test_default_weekly_compiles_all_six_rows_including_disabled_f1():
    schedule = compile_weekly(default_weekly_policy(), MONDAY)
    assert schedule.dates == tuple(date(2026, 9, day) for day in range(7, 12))
    assert len(schedule.rows) == 6
    assert sum(len(row.seats) for row in schedule.rows) == 30
    assert {row.service_minutes for row in schedule.rows} == {80}
    assert {row.room for row in schedule.rows} == {None, "407", "406", "202"}
    assert all(
        seat.state is SeatState.BUSINESS_CLOSED
        for row in schedule.rows if row.business is BusinessId.FORM_1_STUDY_GROUP
        for seat in row.seats
    )
    assert schedule.mode is ScheduleMode.WEEKLY
    assert sum(seat.state is SeatState.REQUIRED for row in schedule.rows for seat in row.seats) == 20


def test_room_and_time_changes_preserve_business_and_date_seat_identity():
    original = default_weekly_policy()
    revised = _change(original, BusinessId.STUDY_ROOM, room=" Rm 509 ")
    before = compile_weekly(original, MONDAY)
    after = compile_weekly(revised, MONDAY)
    assert before.rows[1].room == "407"
    assert after.rows[1].room == "Rm 509"
    assert before.rows[1].business_name == after.rows[1].business_name == "Study Room"
    assert before.rows[1].seats == after.rows[1].seats
    assert after.rows[1].seats[0].key.value == "2026-09-07:study_room:1"
    assert original == default_weekly_policy()
    with pytest.raises(FrozenInstanceError):
        revised.businesses[1].room = "510"
    with pytest.raises(FrozenInstanceError):
        after.rows[1].service.minutes = 999


def test_caller_owned_collections_are_copied_to_immutable_values():
    posts = list(default_weekly_policy().businesses)
    days = [0, 2, 3]
    posts[3] = replace(posts[3], enabled=True, open_weekdays=days)
    policy = WeeklyPolicy(posts)
    days.clear()
    posts.clear()
    assert len(policy.businesses) == 4
    assert policy.businesses[3].open_weekdays == (0, 2, 3)
    assert isinstance(policy.businesses, tuple)


def test_f1_enabling_restores_configured_weekdays_not_all_five():
    policy = _change(default_weekly_policy(), BusinessId.FORM_1_STUDY_GROUP, enabled=True)
    schedule = compile_weekly(policy, MONDAY)
    for row in schedule.rows[-2:]:
        assert [seat.state for seat in row.seats] == [
            SeatState.REQUIRED, SeatState.BUSINESS_CLOSED, SeatState.REQUIRED,
            SeatState.REQUIRED, SeatState.BUSINESS_CLOSED,
        ]


@pytest.mark.parametrize("capacity", [0, -1, True, False, 2.0, float("nan"), "2", None])
def test_capacities_require_positive_integers(capacity):
    with pytest.raises(ConfigurationError, match="positive integer"):
        _change(default_weekly_policy(), BusinessId.STUDY_ROOM, capacity=capacity)


def test_twenty_rows_include_disabled_businesses_and_twenty_one_fails():
    policy = _change(default_weekly_policy(), BusinessId.FORM_1_STUDY_GROUP, capacity=16)
    result = compile_weekly(policy, MONDAY)
    assert len(result.rows) == 20
    assert sum(len(row.seats) for row in result.rows) == 100
    assert len({seat.key for row in result.rows for seat in row.seats}) == 100
    assert all(seat.state is SeatState.BUSINESS_CLOSED for row in result.rows[4:] for seat in row.seats)
    with pytest.raises(ConfigurationError, match="20 display rows"):
        _change(policy, BusinessId.FORM_1_STUDY_GROUP, capacity=17)
    cp = _change(_cp_policy(), BusinessId.CP_FORM_1, capacity=16)
    assert len(_compile_cp(cp).rows) == 20
    with pytest.raises(ConfigurationError, match="20 display rows"):
        _change(cp, BusinessId.CP_FORM_1, capacity=17)


@pytest.mark.parametrize("start,end,minutes", [
    ("15:40", "17:00", 80), ("08:55", "12:00", 185),
    ("09:00", "10:07", 67), ("00:00", "23:59", 1439),
])
def test_time_windows_are_exact_integer_minutes(start, end, minutes):
    window = TimeWindow(start, end)
    assert window.minutes == minutes
    assert type(window.minutes) is int


@pytest.mark.parametrize("start,end", [
    ("8:55", "12:00"), ("08:55:00", "12:00"), ("08:55", "12:00:01"),
    ("08:55 ", "12:00"), ("08:55Z", "12:00"), ("０８:５５", "12:00"),
    ("08:60", "12:00"), ("24:00", "12:00"), ("12:00", "12:00"),
    ("23:00", "01:00"), (None, "12:00"), (float("nan"), "12:00"),
])
def test_invalid_or_imprecise_time_fails_explicitly(start, end):
    with pytest.raises(TimeWindowError):
        TimeWindow(start, end)


def test_opening_and_service_are_separate_and_unlinking_is_explicit():
    opening = TimeWindow("08:30", "12:00")
    service = TimeWindow("09:00", "10:07")
    with pytest.raises(TimeWindowError, match="explicitly unlink"):
        DutyTimes(opening, service)
    independent = DutyTimes(opening, service, linked=False)
    policy = _change(default_weekly_policy(), BusinessId.STUDY_ROOM, times=independent)
    row = compile_weekly(policy, MONDAY).rows[1]
    assert row.opening == opening
    assert row.service == service
    assert row.service_minutes == 67
    assert default_weekly_policy().businesses[1].times.service.minutes == 80
    linked = TimeWindow("15:00", "16:30")
    cp = _change(_cp_policy(), BusinessId.CP_FORM_1, times=DutyTimes(linked, linked))
    assert _compile_cp(cp).rows[0].service_minutes == 90


@pytest.mark.parametrize("value", [1, 0, "false", None])
def test_linkage_and_enabling_reject_truthy_non_booleans(value):
    window = TimeWindow("15:40", "17:00")
    with pytest.raises(TimeWindowError):
        DutyTimes(window, window, linked=value)
    with pytest.raises(ConfigurationError):
        _change(default_weekly_policy(), BusinessId.STUDY_ROOM, enabled=value)


def test_schedule_exceptions_keep_closure_states_distinct_without_mutating_policy():
    policy = default_weekly_policy()
    approval = ApprovedUnavailable(SeatKey(MONDAY, BusinessId.STUDY_ROOM, 1), "approval-fixture")
    closed_dates = [date(2026, 9, 8)]
    approvals = [approval]
    exceptions = ScheduleExceptions(closed_dates, approvals)
    closed_dates.clear()
    approvals.clear()
    schedule = compile_weekly(policy, MONDAY, exceptions=exceptions)
    assert schedule.rows[1].seats[0].state is SeatState.UNAVAILABLE
    assert all(row.seats[1].state is SeatState.DAY_CLOSED for row in schedule.rows)
    assert schedule.rows[-1].seats[0].state is SeatState.BUSINESS_CLOSED
    assert schedule.rows[0].seats[0].state is SeatState.REQUIRED
    assert policy == default_weekly_policy()
    assert compile_weekly(policy, MONDAY).rows[1].seats[0].state is SeatState.REQUIRED
    assert "approval-fixture" not in repr(schedule)


@pytest.mark.parametrize("reference", ["", " ", None, True])
def test_unavailability_requires_explicit_approval_reference(reference):
    with pytest.raises(ConfigurationError, match="approval reference"):
        ApprovedUnavailable(SeatKey(MONDAY, BusinessId.STUDY_ROOM, 1), reference)


@pytest.mark.parametrize("business,index,day", [
    (BusinessId.STUDY_ROOM, 2, MONDAY), (BusinessId.CP_FORM_1, 1, MONDAY),
    (BusinessId.STUDY_ROOM, 1, date(2026, 9, 14)),
    (BusinessId.FORM_1_STUDY_GROUP, 1, MONDAY),
])
def test_unknown_and_already_closed_unavailable_seats_fail(business, index, day):
    exceptions = ScheduleExceptions(unavailable=(
        ApprovedUnavailable(SeatKey(day, business, index), "approved-fixture"),
    ))
    with pytest.raises(ConfigurationError):
        compile_weekly(default_weekly_policy(), MONDAY, exceptions=exceptions)


def test_overlapping_or_duplicate_exceptions_are_not_silently_discarded():
    approval = ApprovedUnavailable(SeatKey(MONDAY, BusinessId.STUDY_ROOM, 1), "approved-fixture")
    with pytest.raises(ConfigurationError, match="must not repeat"):
        ScheduleExceptions(unavailable=(approval, approval))
    with pytest.raises(ScheduleDateError, match="must not repeat"):
        ScheduleExceptions(closed_dates=(MONDAY, MONDAY))
    with pytest.raises(ConfigurationError, match="already closed"):
        compile_weekly(default_weekly_policy(), MONDAY, exceptions=ScheduleExceptions((MONDAY,), (approval,)))
    with pytest.raises(ScheduleDateError, match="selected actual dates"):
        compile_weekly(default_weekly_policy(), MONDAY, exceptions=ScheduleExceptions((date(2026, 9, 14),)))


def test_cp_uses_all_explicit_dates_across_weeks_including_weekends():
    schedule = _compile_cp()
    assert schedule.mode is ScheduleMode.CP
    assert schedule.dates == (date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 20))
    assert len(schedule.rows) == 6
    assert {row.service_minutes for row in schedule.rows} == {185}
    assert {row.room for row in schedule.rows} == {"501", "502", "503"}
    assert all(seat.state is SeatState.REQUIRED for row in schedule.rows for seat in row.seats)
    assert len({seat.key.value for row in schedule.rows for seat in row.seats}) == 18
    with pytest.raises(ConfigurationError, match="never ordinary weekday restrictions"):
        _change(_cp_policy(), BusinessId.CP_FORM_1, open_weekdays=(0, 1))


def test_cp_does_not_expand_unselected_years_or_impose_a_ten_day_export_limit():
    sparse = _compile_cp(start=date.min, end=date.max, selected_dates=(date.min, date.max))
    assert sparse.dates == (date.min, date.max)
    dates = tuple(date(2026, 7, day) for day in range(1, 16))
    result = _compile_cp(start=dates[0], end=dates[-1], selected_dates=dates)
    assert result.dates == dates
    assert all(len(row.seats) == 15 for row in result.rows)


@pytest.mark.parametrize("value", [False, 1, "true", None])
def test_cp_rooms_need_explicit_boolean_confirmation_each_compilation(value):
    with pytest.raises(ConfigurationError, match="confirm"):
        _compile_cp(rooms_confirmed=value)


@pytest.mark.parametrize("room", [
    None, "", "  ", 402, True, "402\n403", "402\u0085503",
    "402\u2028503", "402\u2029503",
])
def test_cp_never_supplies_last_years_rooms(room):
    with pytest.raises(ConfigurationError, match="[Rr]oom"):
        default_cp_policy(f1_room=room, f2_room="502", f3_room="503")
    with pytest.raises(ConfigurationError, match="room"):
        default_cp_policy()


@pytest.mark.parametrize("options", [
    {"selected_dates": ()},
    {"selected_dates": (date(2026, 7, 11), date(2026, 7, 11))},
    {"selected_dates": (date(2026, 7, 9),)},
    {"selected_dates": (date(2026, 7, 21),)},
    {"start": date(2026, 7, 21)},
    {"start": "2026-07-10"},
    {"selected_dates": (datetime(2026, 7, 11),)},
])
def test_cp_invalid_date_selections_fail(options):
    with pytest.raises(ScheduleDateError):
        _compile_cp(**options)


@pytest.mark.parametrize("value", [date(2026, 9, 8), "2026-09-07", datetime(2026, 9, 7), None])
def test_weekly_requires_an_actual_monday(value):
    with pytest.raises(ScheduleDateError):
        compile_weekly(default_weekly_policy(), value)


def test_mode_businesses_are_complete_unique_and_cannot_cross_modes():
    weekly = default_weekly_policy()
    with pytest.raises(ConfigurationError, match="exactly once"):
        WeeklyPolicy(weekly.businesses[:-1])
    with pytest.raises(ConfigurationError, match="exactly once"):
        WeeklyPolicy(weekly.businesses[:-1] + (weekly.businesses[0],))
    with pytest.raises(ConfigurationError, match="exactly once"):
        CpPolicy(weekly.businesses)
    with pytest.raises(ConfigurationError, match="WeeklyPolicy"):
        compile_weekly(_cp_policy(), MONDAY)
    with pytest.raises(ConfigurationError, match="CpPolicy"):
        _compile_cp(weekly)


def test_compiled_rows_have_no_person_or_approval_fields_and_are_deterministic():
    first = _compile_cp()
    second = _compile_cp()
    assert first == second
    for row in first.rows:
        assert set(asdict(row)) == {
            "business", "business_name", "room", "seat_index", "opening",
            "service", "service_minutes", "seats",
        }
        assert all(set(asdict(seat)) == {"key", "state"} for seat in row.seats)


def test_weekly_formal_names_and_custom_open_days_are_not_room_identities():
    policy = _change(default_weekly_policy(), BusinessId.HOMEWORK_COMPLETION,
                     room="Rm 410", open_weekdays=(4, 1))
    result = compile_weekly(policy, MONDAY)
    assert [row.business_name for row in result.rows] == [
        "Assist. in charge", "Study Room", "Homework Completion",
        "Homework Completion", "Form 1 Study Group", "Form 1 Study Group",
    ]
    for row in result.rows[2:4]:
        assert row.room == "Rm 410"
        assert [seat.state for seat in row.seats] == [
            SeatState.BUSINESS_CLOSED, SeatState.REQUIRED,
            SeatState.BUSINESS_CLOSED, SeatState.BUSINESS_CLOSED, SeatState.REQUIRED,
        ]


def test_cp_closure_and_approved_unavailability_use_actual_dates():
    closed = date(2026, 7, 11)
    unavailable = ApprovedUnavailable(
        SeatKey(date(2026, 7, 20), BusinessId.CP_FORM_2, 2), "teacher-fixture",
    )
    schedule = _compile_cp(exceptions=ScheduleExceptions((closed,), (unavailable,)))
    assert all(row.seats[1].state is SeatState.DAY_CLOSED for row in schedule.rows)
    assert schedule.rows[3].seats[2].state is SeatState.UNAVAILABLE
    assert schedule.rows[2].seats[2].state is SeatState.REQUIRED
    assert "teacher-fixture" not in repr(schedule)
    assert {row.service_minutes for row in schedule.rows} == {185}
