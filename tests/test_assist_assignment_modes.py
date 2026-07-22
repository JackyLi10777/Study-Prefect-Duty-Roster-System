from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

import pytest

from roster_core import Prefect, RosterGenerationError, generate_weekly_roster
from roster_policy import AssistAssignmentMode, DAYS, DutyPost, PrefectRole, SchoolDay


def _prefect(
    identifier: str,
    role: PrefectRole,
    *,
    available_days: tuple[SchoolDay, ...] = DAYS,
    history_weight: float = 0.0,
    fixed_general_duty: str = "NONE",
) -> Prefect:
    return Prefect(
        id=identifier,
        name=f"測試{identifier}",
        form="F.5",
        class_name="A",
        role=role,
        available_days=frozenset(available_days),
        history_weight=history_weight,
        fixed_general_duty=fixed_general_duty,
    )


def _directory(*, assistants: int = 6) -> list[Prefect]:
    return [
        *(
            _prefect(f"ahp-{index}", PrefectRole.ASSISTANT_HEAD)
            for index in range(assistants)
        ),
        *(
            _prefect(f"sp-{index}", PrefectRole.STUDY_PREFECT)
            for index in range(12)
        ),
    ]


def _assist_by_day(assignments: list) -> dict[SchoolDay, str]:
    return {
        assignment.day: assignment.prefect_id
        for assignment in assignments
        if assignment.post is DutyPost.ASSIST_IN_CHARGE
    }


def _assert_assist_policy(assignments: list, prefects: list[Prefect]) -> None:
    prefect_by_id = {prefect.id: prefect for prefect in prefects}
    assist = [
        assignment
        for assignment in assignments
        if assignment.post is DutyPost.ASSIST_IN_CHARGE
    ]
    assert [assignment.day for assignment in assist] == list(DAYS)
    assert all(prefect_by_id[item.prefect_id].role is PrefectRole.ASSISTANT_HEAD for item in assist)
    assigned_days: dict[str, list[int]] = {}
    for item in assist:
        assigned_days.setdefault(item.prefect_id, []).append(int(item.day))
    assert all(
        all(right - left > 1 for left, right in pairwise(days))
        for days in (sorted(values) for values in assigned_days.values())
    )


def test_legacy_mode_preserves_canonical_weekdays_across_weeks_and_history_changes() -> None:
    prefects = _directory()
    first = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-07",
    )
    updated = [
        replace(prefect, history_weight=100.0 - index)
        if prefect.role is PrefectRole.ASSISTANT_HEAD
        else prefect
        for index, prefect in enumerate(prefects)
    ]
    second = generate_weekly_roster(
        updated,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-14",
    )

    assert _assist_by_day(first) == _assist_by_day(second)
    _assert_assist_policy(first, prefects)


def test_legacy_mode_uses_durable_identity_when_a_display_name_is_corrected() -> None:
    prefects = _directory()
    baseline = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
    )
    renamed = [
        replace(prefect, name="修正姓名") if prefect.id == "ahp-0" else prefect
        for prefect in prefects
    ]

    regenerated = generate_weekly_roster(
        renamed,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
    )

    assert _assist_by_day(regenerated) == _assist_by_day(baseline)


def test_legacy_mode_preserves_explicit_fixed_weekdays_from_existing_directory_data() -> None:
    prefects = _directory()
    prefects = [
        replace(prefect, fixed_general_duty="THURSDAY")
        if prefect.id == "ahp-0"
        else prefect
        for prefect in prefects
    ]

    first = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-07",
    )
    following = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-14",
    )

    assert _assist_by_day(first)[SchoolDay.THURSDAY] == "ahp-0"
    assert _assist_by_day(following)[SchoolDay.THURSDAY] == "ahp-0"


def test_legacy_mode_rejects_fixed_weekday_outside_declared_availability() -> None:
    prefects = _directory()
    prefects = [
        replace(
            prefect,
            available_days=frozenset({SchoolDay.MONDAY}),
            fixed_general_duty="TUESDAY",
        )
        if prefect.id == "ahp-0"
        else prefect
        for prefect in prefects
    ]

    with pytest.raises(RosterGenerationError, match="not an available day"):
        generate_weekly_roster(
            prefects,
            assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        )


def test_legacy_mode_rejects_conflicting_explicit_fixed_weekdays() -> None:
    prefects = _directory()
    prefects = [
        replace(prefect, fixed_general_duty="MONDAY")
        if prefect.id in {"ahp-0", "ahp-1"}
        else prefect
        for prefect in prefects
    ]

    with pytest.raises(RosterGenerationError, match="More than one"):
        generate_weekly_roster(
            prefects,
            assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        )


def test_legacy_leave_uses_one_week_substitute_then_restores_fixed_weekday() -> None:
    # Exactly five AHPs leaves no unused one-for-one substitute.  The legacy
    # policy must keep the four unaffected fixed weekdays and let one eligible
    # AHP cover an additional non-consecutive day for this week only.
    prefects = _directory(assistants=5)
    baseline = generate_weekly_roster(
        prefects,
        assist_assignment_mode="legacy_fixed_weekday",
        assist_rotation_key="2026-09-07",
    )
    baseline_by_day = _assist_by_day(baseline)
    absent_id = baseline_by_day[SchoolDay.MONDAY]

    leave_week = generate_weekly_roster(
        prefects,
        leave_days={absent_id: {SchoolDay.MONDAY}},
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-14",
    )
    leave_by_day = _assist_by_day(leave_week)
    restored = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        assist_rotation_key="2026-09-21",
    )

    assert leave_by_day[SchoolDay.MONDAY] != absent_id
    assert {
        day: prefect_id
        for day, prefect_id in leave_by_day.items()
        if day is not SchoolDay.MONDAY
    } == {
        day: prefect_id
        for day, prefect_id in baseline_by_day.items()
        if day is not SchoolDay.MONDAY
    }
    assert len(set(leave_by_day.values())) == 4
    assert _assist_by_day(restored) == baseline_by_day
    _assert_assist_policy(leave_week, prefects)


def test_flexible_mode_varies_by_week_but_retries_are_reproducible() -> None:
    prefects = _directory(assistants=5)
    first = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-07",
    )
    first_retry = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-07",
    )
    first_by_day = _assist_by_day(first)
    following_week = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-14",
        previous_assist_assignments=first_by_day,
    )
    following_retry = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-14",
        previous_assist_assignments=first_by_day,
    )

    assert first == first_retry
    assert following_week == following_retry
    following_by_day = _assist_by_day(following_week)
    assert following_by_day != first_by_day
    assert all(following_by_day[day] != first_by_day[day] for day in DAYS)
    _assert_assist_policy(first, prefects)
    _assert_assist_policy(following_week, prefects)


def test_flexible_mode_excludes_recorded_leave_and_keeps_later_rotation_valid() -> None:
    prefects = _directory(assistants=5)
    baseline = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-07",
    )
    baseline_by_day = _assist_by_day(baseline)
    absent_id = baseline_by_day[SchoolDay.MONDAY]

    leave_week = generate_weekly_roster(
        prefects,
        leave_days={absent_id: {SchoolDay.MONDAY}},
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-14",
        previous_assist_assignments=baseline_by_day,
    )
    leave_by_day = _assist_by_day(leave_week)
    following = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-21",
        previous_assist_assignments=leave_by_day,
    )
    following_retry = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-21",
        previous_assist_assignments=leave_by_day,
    )

    assert leave_by_day[SchoolDay.MONDAY] != absent_id
    assert following_retry == following
    _assert_assist_policy(leave_week, prefects)
    _assert_assist_policy(following, prefects)


def test_flexible_mode_accepts_unavoidable_same_weekday_repeats_from_availability() -> None:
    assistants = [
        _prefect(
            f"ahp-{day.name.lower()}",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(day,),
        )
        for day in DAYS
    ]
    prefects = [
        *assistants,
        *(
            _prefect(f"sp-{index}", PrefectRole.STUDY_PREFECT)
            for index in range(12)
        ),
    ]
    previous = {
        day: f"ahp-{day.name.lower()}"
        for day in DAYS
    }

    assignments = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-14",
        previous_assist_assignments=previous,
    )

    assert _assist_by_day(assignments) == previous
    _assert_assist_policy(assignments, prefects)


def test_flexible_mode_keeps_history_ahead_of_same_weekday_avoidance() -> None:
    assistants = [
        _prefect(
            f"ahp-{day.name.lower()}",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(day,),
        )
        for day in DAYS
    ]
    assistants.append(
        _prefect(
            "ahp-high-history",
            PrefectRole.ASSISTANT_HEAD,
            history_weight=100.0,
        )
    )
    prefects = [
        *assistants,
        *(
            _prefect(f"sp-{index}", PrefectRole.STUDY_PREFECT)
            for index in range(12)
        ),
    ]
    previous = {
        day: f"ahp-{day.name.lower()}"
        for day in DAYS
    }

    assignments = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-14",
        previous_assist_assignments=previous,
    )

    assert _assist_by_day(assignments) == previous
    assert "ahp-high-history" not in _assist_by_day(assignments).values()
    _assert_assist_policy(assignments, prefects)


def test_flexible_mode_keeps_history_weight_as_primary_fairness_anchor() -> None:
    prefects = _directory()
    high_load_id = "ahp-5"
    weighted = [
        replace(prefect, history_weight=100.0)
        if prefect.id == high_load_id
        else prefect
        for prefect in prefects
    ]
    assignments = generate_weekly_roster(
        weighted,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-07",
    )

    assert high_load_id not in _assist_by_day(assignments).values()
    _assert_assist_policy(assignments, weighted)


def test_flexible_mode_finds_the_global_minimum_history_cost_matching() -> None:
    assistants = [
        _prefect("ahp-0", PrefectRole.ASSISTANT_HEAD, history_weight=10.0),
        _prefect(
            "ahp-1",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(SchoolDay.MONDAY, SchoolDay.WEDNESDAY, SchoolDay.THURSDAY),
            history_weight=1.0,
        ),
        _prefect(
            "ahp-2",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(
                SchoolDay.MONDAY,
                SchoolDay.TUESDAY,
                SchoolDay.WEDNESDAY,
                SchoolDay.THURSDAY,
            ),
            history_weight=2.0,
        ),
        _prefect(
            "ahp-3",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(SchoolDay.MONDAY, SchoolDay.WEDNESDAY, SchoolDay.FRIDAY),
            history_weight=2.0,
        ),
        _prefect("ahp-4", PrefectRole.ASSISTANT_HEAD, history_weight=1.0),
        _prefect(
            "ahp-5",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(
                SchoolDay.MONDAY,
                SchoolDay.WEDNESDAY,
                SchoolDay.THURSDAY,
                SchoolDay.FRIDAY,
            ),
            history_weight=2.0,
        ),
    ]
    prefects = [
        *assistants,
        *(
            _prefect(f"sp-{index}", PrefectRole.STUDY_PREFECT)
            for index in range(12)
        ),
    ]

    assignments = generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
        assist_rotation_key="2026-09-07",
    )
    assist_ids = set(_assist_by_day(assignments).values())
    weight_by_id = {prefect.id: prefect.history_weight for prefect in assistants}

    assert "ahp-0" not in assist_ids
    assert sum(weight_by_id[prefect_id] for prefect_id in assist_ids) == 8.0
    _assert_assist_policy(assignments, prefects)


def test_both_modes_honor_declared_available_days() -> None:
    assistants = [
        _prefect(
            f"ahp-{day.name.lower()}",
            PrefectRole.ASSISTANT_HEAD,
            available_days=(day,),
        )
        for day in DAYS
    ]
    prefects = [
        *assistants,
        *(
            _prefect(f"sp-{index}", PrefectRole.STUDY_PREFECT)
            for index in range(12)
        ),
    ]

    for mode in AssistAssignmentMode:
        assignments = generate_weekly_roster(
            prefects,
            assist_assignment_mode=mode,
            assist_rotation_key="2026-09-07",
        )
        for day, prefect_id in _assist_by_day(assignments).items():
            assert day in next(prefect.available_days for prefect in assistants if prefect.id == prefect_id)
        _assert_assist_policy(assignments, prefects)


def test_nonconsecutive_fallback_scales_when_fewer_than_five_assistants_exist() -> None:
    prefects = _directory(assistants=3)

    for mode in AssistAssignmentMode:
        assignments = generate_weekly_roster(
            prefects,
            assist_assignment_mode=mode,
            assist_rotation_key="2026-09-07",
        )
        _assert_assist_policy(assignments, prefects)


def test_default_mode_is_legacy_and_does_not_require_a_rotation_key() -> None:
    prefects = _directory()

    assert generate_weekly_roster(prefects) == generate_weekly_roster(
        prefects,
        assist_assignment_mode=AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
    )


@pytest.mark.parametrize("rotation_key", [None, "", "   "])
def test_flexible_mode_requires_a_nonempty_rotation_key(rotation_key: str | None) -> None:
    with pytest.raises(RosterGenerationError, match="rotation key is required"):
        generate_weekly_roster(
            _directory(),
            assist_assignment_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY,
            assist_rotation_key=rotation_key,
        )


def test_unknown_assist_mode_is_rejected() -> None:
    with pytest.raises(RosterGenerationError, match="Unsupported Assist assignment mode"):
        generate_weekly_roster(_directory(), assist_assignment_mode="surprise-me")
