from __future__ import annotations

from dataclasses import replace

import pytest

import roster_core.generator as generator_module
from roster_core import Assignment, Prefect, RosterGenerationError, generate_weekly_roster
from roster_core.generator import validate_assignments
from roster_core.loaders import load_prefect_seed
from roster_policy import DAYS, DutyPost, PrefectRole, RosterPolicyError, SchoolDay, duty_weight


def _prefect(
    identifier: str,
    name: str,
    *,
    role: PrefectRole,
    days: set[SchoolDay],
    history_weight: float = 0.0,
    fixed_day: SchoolDay | None = None,
) -> Prefect:
    return Prefect(
        id=identifier,
        name=name,
        form="F.5",
        class_name="5A",
        role=role,
        available_days=frozenset(days),
        history_weight=history_weight,
        fixed_general_duty=fixed_day.name if fixed_day is not None else "NONE",
    )


def _greedy_trap_directory() -> list[Prefect]:
    prefects = [
        _prefect(
            f"ahp-{int(day)}",
            f"助理{label}",
            role=PrefectRole.ASSISTANT_HEAD,
            days={day},
            fixed_day=day,
        )
        for day, label in zip(DAYS, "甲乙丙丁戊", strict=True)
    ]
    prefects.extend(
        _prefect(
            f"mw-{index}",
            f"隔日{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.MONDAY, SchoolDay.WEDNESDAY},
        )
        for index, label in enumerate("甲乙")
    )
    prefects.extend(
        _prefect(
            f"mon-{index}",
            f"星期一{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.MONDAY},
        )
        for index, label in enumerate("甲乙丙")
    )
    # A one-pass fairness-greedy allocator selects these three low-history
    # prefects on Tuesday, then leaves only two candidates for Wednesday's five
    # seats. A complete solution instead uses the Tuesday-only alternatives.
    prefects.extend(
        _prefect(
            f"bridge-{index}",
            f"跨日{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.TUESDAY, SchoolDay.WEDNESDAY},
            history_weight=0.0,
        )
        for index, label in enumerate("甲乙丙")
    )
    prefects.extend(
        _prefect(
            f"tue-alt-{index}",
            f"星期二替代{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.TUESDAY},
            history_weight=20.0,
        )
        for index, label in enumerate("甲乙丙")
    )
    prefects.extend(
        _prefect(
            f"thu-{index}",
            f"星期四{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.THURSDAY},
        )
        for index, label in enumerate("甲乙丙丁戊")
    )
    prefects.extend(
        _prefect(
            f"fri-{index}",
            f"星期五{label}",
            role=PrefectRole.STUDY_PREFECT,
            days={SchoolDay.FRIDAY},
        )
        for index, label in enumerate("甲乙丙")
    )
    return prefects


def test_generation_backtracks_when_fairness_greedy_choice_blocks_later_day() -> None:
    prefects = _greedy_trap_directory()
    tuesday_candidates = sorted(
        (
            prefect
            for prefect in prefects
            if prefect.role is PrefectRole.STUDY_PREFECT
            and SchoolDay.TUESDAY in prefect.available_days
        ),
        key=lambda prefect: (prefect.history_weight, prefect.name),
    )
    assert {prefect.id for prefect in tuesday_candidates[:3]} == {
        "bridge-0",
        "bridge-1",
        "bridge-2",
    }

    assignments = generate_weekly_roster(prefects)

    tuesday_regular_ids = {
        assignment.prefect_id
        for assignment in assignments
        if assignment.day is SchoolDay.TUESDAY
        and assignment.post is not DutyPost.ASSIST_IN_CHARGE
    }
    wednesday_regular_ids = {
        assignment.prefect_id
        for assignment in assignments
        if assignment.day is SchoolDay.WEDNESDAY
        and assignment.post is not DutyPost.ASSIST_IN_CHARGE
    }
    assert tuesday_regular_ids == {"tue-alt-0", "tue-alt-1", "tue-alt-2"}
    assert {"bridge-0", "bridge-1", "bridge-2"} <= wednesday_regular_ids
    validate_assignments(assignments, prefects)


def test_generation_fails_cleanly_when_search_budget_is_exhausted(monkeypatch) -> None:
    monkeypatch.setattr(generator_module, "REGULAR_SCHEDULE_SEARCH_NODE_LIMIT", 0)

    with pytest.raises(RosterGenerationError, match="safe search limit"):
        generate_weekly_roster(_greedy_trap_directory())


def test_generation_uses_explicit_slot_keys_not_solver_mapping_order(monkeypatch) -> None:
    original_solver = generator_module._solve_regular_schedule

    def reverse_mapping_order(*args, **kwargs):  # type: ignore[no-untyped-def]
        solved = original_solver(*args, **kwargs)
        return dict(reversed(tuple(solved.items())))

    monkeypatch.setattr(generator_module, "_solve_regular_schedule", reverse_mapping_order)
    prefects = _greedy_trap_directory()

    assignments = generate_weekly_roster(prefects)

    validate_assignments(assignments, prefects)


@pytest.fixture
def valid_roster() -> tuple[list[Assignment], list[Prefect]]:
    prefects = load_prefect_seed()
    return generate_weekly_roster(prefects), prefects


def test_validation_rejects_empty_roster(valid_roster) -> None:
    _, prefects = valid_roster

    with pytest.raises(RosterPolicyError, match="cannot be empty"):
        validate_assignments([], prefects)


def test_validation_rejects_missing_day(valid_roster) -> None:
    assignments, prefects = valid_roster
    incomplete = [item for item in assignments if item.day is not SchoolDay.FRIDAY]

    with pytest.raises(RosterPolicyError, match="Incorrect post coverage on FRIDAY"):
        validate_assignments(incomplete, prefects)


def test_validation_rejects_missing_seat(valid_roster) -> None:
    assignments, prefects = valid_roster
    removed = next(
        item
        for item in assignments
        if item.day is SchoolDay.MONDAY and item.post is DutyPost.ROOM_303
    )
    incomplete = list(assignments)
    incomplete.remove(removed)

    with pytest.raises(RosterPolicyError, match="Incorrect post coverage on MONDAY"):
        validate_assignments(incomplete, prefects)


def test_validation_rejects_extra_seat(valid_roster) -> None:
    assignments, prefects = valid_roster
    monday_ids = {
        item.prefect_id for item in assignments if item.day is SchoolDay.MONDAY
    }
    extra_prefect = next(
        prefect
        for prefect in prefects
        if prefect.role is PrefectRole.STUDY_PREFECT
        and SchoolDay.MONDAY in prefect.available_days
        and prefect.id not in monday_ids
    )
    extra = Assignment(
        day=SchoolDay.MONDAY,
        post=DutyPost.ROOM_302,
        prefect_id=extra_prefect.id,
        prefect_name=extra_prefect.name,
        weight=duty_weight(DutyPost.ROOM_302),
    )

    with pytest.raises(RosterPolicyError, match="Incorrect post coverage on MONDAY"):
        validate_assignments([*assignments, extra], prefects)


def test_validation_rejects_noncanonical_duty_weight(valid_roster) -> None:
    assignments, prefects = valid_roster
    invalid = list(assignments)
    invalid[0] = replace(invalid[0], weight=invalid[0].weight + 0.5)

    with pytest.raises(RosterPolicyError, match="Incorrect duty weight"):
        validate_assignments(invalid, prefects)
