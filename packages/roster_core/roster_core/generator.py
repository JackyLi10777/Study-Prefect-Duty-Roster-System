from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from roster_policy import (
    DAYS,
    DutyPost,
    RosterPolicyError,
    SchoolDay,
    can_assign_role,
    duty_weight,
    is_room_open,
    required_posts_for_day,
)

from .models import Assignment, Prefect


class RosterGenerationError(RuntimeError):
    """Raised when no valid roster can be generated under school policy."""


HISTORY_PRIORITY_MULTIPLIER_MIN = 0.8
HISTORY_PRIORITY_MULTIPLIER_MAX = 2.0


def _normalized_history_priority_multiplier(value: float) -> float:
    try:
        multiplier = float(value)
    except (TypeError, ValueError) as error:
        raise RosterGenerationError("History priority multiplier must be a number from 0.8 to 2.0.") from error
    if not HISTORY_PRIORITY_MULTIPLIER_MIN <= multiplier <= HISTORY_PRIORITY_MULTIPLIER_MAX:
        raise RosterGenerationError("History priority multiplier must be from 0.8 to 2.0.")
    return multiplier


def _form_rank(form: str) -> int:
    try:
        return int(form.replace("F.", "").replace("F", ""))
    except ValueError:
        return 99


def _has_consecutive_assignment(assigned_days: set[SchoolDay], day: SchoolDay) -> bool:
    return any(abs(int(previous_day) - int(day)) == 1 for previous_day in assigned_days)


def _candidate_score(
    prefect: Prefect,
    generated_load: dict[str, float],
    history_priority_multiplier: float,
) -> tuple[float, int, int, str]:
    cumulative_load = history_priority_multiplier * prefect.history_weight + generated_load[prefect.id]
    return (
        cumulative_load,
        _form_rank(prefect.form),
        prefect.history_duties,
        prefect.name,
    )


def _choose_candidate(
    prefects: list[Prefect],
    *,
    day: SchoolDay,
    post: DutyPost,
    assigned_today: set[str],
    assigned_days: dict[str, set[SchoolDay]],
    generated_load: dict[str, float],
    leave_days: Mapping[str, set[SchoolDay]],
    history_priority_multiplier: float,
) -> Prefect:
    candidates = [
        prefect
        for prefect in prefects
        if day in prefect.available_days
        and day not in leave_days.get(prefect.id, set())
        and prefect.id not in assigned_today
        and can_assign_role(prefect.role, post)
        and not _has_consecutive_assignment(assigned_days[prefect.id], day)
    ]
    if not candidates:
        raise RosterGenerationError(f"No eligible candidate for {post.value} on {day.name}.")
    return min(
        candidates,
        key=lambda prefect: _candidate_score(prefect, generated_load, history_priority_multiplier),
    )


def generate_weekly_roster(
    prefects: list[Prefect],
    *,
    leave_days: Mapping[str, set[SchoolDay]] | None = None,
    history_priority_multiplier: float = 1.0,
) -> list[Assignment]:
    if not prefects:
        raise RosterGenerationError("Cannot generate roster without prefects.")

    normalized_multiplier = _normalized_history_priority_multiplier(history_priority_multiplier)

    assignments: list[Assignment] = []
    generated_load: dict[str, float] = defaultdict(float)
    assigned_days: dict[str, set[SchoolDay]] = defaultdict(set)
    excluded_days = leave_days or {}

    for day in DAYS:
        assigned_today: set[str] = set()
        for post in required_posts_for_day(day):
            prefect = _choose_candidate(
                prefects,
                day=day,
                post=post,
                assigned_today=assigned_today,
                assigned_days=assigned_days,
                generated_load=generated_load,
                leave_days=excluded_days,
                history_priority_multiplier=normalized_multiplier,
            )
            weight = duty_weight(post)
            assignments.append(
                Assignment(
                    day=day,
                    post=post,
                    prefect_id=prefect.id,
                    prefect_name=prefect.name,
                    weight=weight,
                )
            )
            assigned_today.add(prefect.id)
            assigned_days[prefect.id].add(day)
            generated_load[prefect.id] += weight

    validate_assignments(assignments, prefects, leave_days=excluded_days)
    return assignments


def validate_assignments(
    assignments: list[Assignment],
    prefects: list[Prefect],
    *,
    leave_days: Mapping[str, set[SchoolDay]] | None = None,
) -> None:
    prefect_by_id = {prefect.id: prefect for prefect in prefects}
    by_day: dict[SchoolDay, list[Assignment]] = defaultdict(list)
    by_prefect: dict[str, set[SchoolDay]] = defaultdict(set)
    excluded_days = leave_days or {}

    for assignment in assignments:
        if assignment.prefect_id not in prefect_by_id:
            raise RosterPolicyError(f"Unknown prefect ID: {assignment.prefect_id}")
        prefect = prefect_by_id[assignment.prefect_id]
        if not is_room_open(assignment.post, assignment.day):
            raise RosterPolicyError(f"{assignment.post.value} is closed on {assignment.day.name}.")
        if not can_assign_role(prefect.role, assignment.post):
            raise RosterPolicyError(f"{prefect.name} cannot be assigned to {assignment.post.value}.")
        if assignment.day not in prefect.available_days:
            raise RosterPolicyError(f"{prefect.name} is not available on {assignment.day.name}.")
        if assignment.day in excluded_days.get(assignment.prefect_id, set()):
            raise RosterPolicyError(f"{prefect.name} is on leave on {assignment.day.name}.")
        by_day[assignment.day].append(assignment)
        by_prefect[assignment.prefect_id].add(assignment.day)

    for day, day_assignments in by_day.items():
        assigned_ids = [assignment.prefect_id for assignment in day_assignments]
        if len(assigned_ids) != len(set(assigned_ids)):
            raise RosterPolicyError(f"Duplicate prefect assignment on {day.name}.")
        actual_posts = [assignment.post for assignment in day_assignments]
        expected_posts = required_posts_for_day(day)
        if sorted(post.value for post in actual_posts) != sorted(post.value for post in expected_posts):
            raise RosterPolicyError(f"Incorrect post coverage on {day.name}.")

    for prefect_id, days in by_prefect.items():
        for day in days:
            if _has_consecutive_assignment(days - {day}, day):
                raise RosterPolicyError(f"{prefect_id} has consecutive-day assignments.")
