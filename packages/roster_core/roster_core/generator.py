from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping

from roster_policy import (
    DAYS,
    AssistAssignmentMode,
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


def _normalize_assist_assignment_mode(
    value: AssistAssignmentMode | str,
) -> AssistAssignmentMode:
    if isinstance(value, AssistAssignmentMode):
        return value
    try:
        return AssistAssignmentMode(str(value))
    except ValueError as error:
        allowed = ", ".join(mode.value for mode in AssistAssignmentMode)
        raise RosterGenerationError(f"Unsupported Assist assignment mode; expected one of: {allowed}.") from error


def _rotation_rank(rotation_key: str, day: SchoolDay, prefect_id: str) -> int:
    """Return a stable pseudo-random rank without using process RNG state."""

    payload = f"{rotation_key}\0{day.name}\0{prefect_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _eligible_assist_candidates(
    prefects: list[Prefect],
    *,
    day: SchoolDay,
    leave_days: Mapping[str, set[SchoolDay]],
) -> list[Prefect]:
    return [
        prefect
        for prefect in prefects
        if can_assign_role(prefect.role, DutyPost.ASSIST_IN_CHARGE)
        and day in prefect.available_days
        and day not in leave_days.get(prefect.id, set())
    ]


def _find_unique_weekday_matching(
    candidate_lists: Mapping[SchoolDay, list[Prefect]],
) -> dict[SchoolDay, Prefect] | None:
    """Find a deterministic one-person-per-day matching in O(days * edges).

    Candidate ordering expresses policy preference. The augmenting-path
    matcher avoids factorial schedule enumeration and remains efficient when
    the prefect directory grows substantially.
    """

    prefect_to_day: dict[str, SchoolDay] = {}
    day_to_prefect: dict[SchoolDay, Prefect] = {}

    def claim(day: SchoolDay, seen_prefect_ids: set[str]) -> bool:
        for prefect in candidate_lists.get(day, []):
            if prefect.id in seen_prefect_ids:
                continue
            seen_prefect_ids.add(prefect.id)
            occupied_day = prefect_to_day.get(prefect.id)
            if occupied_day is None or claim(occupied_day, seen_prefect_ids):
                prefect_to_day[prefect.id] = day
                day_to_prefect[day] = prefect
                return True
        return False

    for day in DAYS:
        if day not in candidate_lists:
            continue
        if not claim(day, set()):
            return None
    return day_to_prefect


_AssistFlowCost = tuple[float, int, int, int, int, int]
_ZERO_ASSIST_FLOW_COST: _AssistFlowCost = (0.0, 0, 0, 0, 0, 0)


class _AssistFlowEdge:
    __slots__ = ("capacity", "cost", "reverse", "to")

    def __init__(
        self,
        *,
        to: int,
        reverse: int,
        capacity: int,
        cost: _AssistFlowCost,
    ) -> None:
        self.to = to
        self.reverse = reverse
        self.capacity = capacity
        self.cost = cost


def _add_assist_flow_cost(left: _AssistFlowCost, right: _AssistFlowCost) -> _AssistFlowCost:
    return tuple(
        left_component + right_component
        for left_component, right_component in zip(left, right, strict=True)
    )


def _negate_assist_flow_cost(cost: _AssistFlowCost) -> _AssistFlowCost:
    return tuple(-component for component in cost)


def _add_assist_flow_edge(
    graph: list[list[_AssistFlowEdge]],
    *,
    start: int,
    end: int,
    cost: _AssistFlowCost,
) -> _AssistFlowEdge:
    forward = _AssistFlowEdge(
        to=end,
        reverse=len(graph[end]),
        capacity=1,
        cost=cost,
    )
    backward = _AssistFlowEdge(
        to=start,
        reverse=len(graph[start]),
        capacity=0,
        cost=_negate_assist_flow_cost(cost),
    )
    graph[start].append(forward)
    graph[end].append(backward)
    return forward


def _find_min_cost_unique_weekday_matching(
    candidate_lists: Mapping[SchoolDay, list[Prefect]],
    *,
    history_priority_multiplier: float,
    rotation_key: str,
    previous_assist_assignments: Mapping[SchoolDay, str],
) -> dict[SchoolDay, Prefect] | None:
    """Return a globally minimum-cost distinct-prefect weekday matching.

    Successive shortest augmenting paths solve the bipartite min-cost flow in
    polynomial time.  Tuple costs preserve the policy's lexicographic order:
    total persistent history weight is primary. Avoiding the same weekday as
    the immediately preceding week is secondary, while the deterministic
    weekly rotation rank, form, duty count and stable identity break later
    ties. Availability remains a hard constraint because only eligible edges
    are present in the graph.
    """

    days = [day for day in DAYS if day in candidate_lists]
    prefect_by_id = {
        prefect.id: prefect
        for day in days
        for prefect in candidate_lists.get(day, [])
    }
    prefects = sorted(prefect_by_id.values(), key=lambda prefect: (prefect.id, prefect.name))
    if len(prefects) < len(days):
        return None

    source = 0
    day_offset = 1
    prefect_offset = day_offset + len(days)
    sink = prefect_offset + len(prefects)
    graph: list[list[_AssistFlowEdge]] = [[] for _ in range(sink + 1)]
    prefect_node_by_id = {
        prefect.id: prefect_offset + index
        for index, prefect in enumerate(prefects)
    }
    prefect_rank_by_id = {
        prefect.id: index
        for index, prefect in enumerate(prefects)
    }
    assignment_edges: dict[tuple[SchoolDay, str], _AssistFlowEdge] = {}

    for day_index, day in enumerate(days):
        day_node = day_offset + day_index
        _add_assist_flow_edge(
            graph,
            start=source,
            end=day_node,
            cost=_ZERO_ASSIST_FLOW_COST,
        )
        unique_candidates = {
            prefect.id: prefect
            for prefect in candidate_lists.get(day, [])
        }
        for prefect in sorted(unique_candidates.values(), key=lambda item: (item.id, item.name)):
            edge = _add_assist_flow_edge(
                graph,
                start=day_node,
                end=prefect_node_by_id[prefect.id],
                cost=(
                    history_priority_multiplier * prefect.history_weight,
                    int(previous_assist_assignments.get(day) == prefect.id),
                    _rotation_rank(rotation_key, day, prefect.id),
                    _form_rank(prefect.form),
                    prefect.history_duties,
                    prefect_rank_by_id[prefect.id],
                ),
            )
            assignment_edges[(day, prefect.id)] = edge

    for prefect in prefects:
        _add_assist_flow_edge(
            graph,
            start=prefect_node_by_id[prefect.id],
            end=sink,
            cost=_ZERO_ASSIST_FLOW_COST,
        )

    flow = 0
    while flow < len(days):
        distance: list[_AssistFlowCost | None] = [None] * len(graph)
        previous_node = [-1] * len(graph)
        previous_edge = [-1] * len(graph)
        distance[source] = _ZERO_ASSIST_FLOW_COST

        # Residual reverse edges carry negative tuple costs, so Bellman-Ford
        # is used instead of assuming non-negative scalar weights.
        for _ in range(len(graph) - 1):
            changed = False
            for node, edges in enumerate(graph):
                if distance[node] is None:
                    continue
                for edge_index, edge in enumerate(edges):
                    if edge.capacity == 0:
                        continue
                    candidate_distance = _add_assist_flow_cost(distance[node], edge.cost)
                    if distance[edge.to] is None or candidate_distance < distance[edge.to]:
                        distance[edge.to] = candidate_distance
                        previous_node[edge.to] = node
                        previous_edge[edge.to] = edge_index
                        changed = True
            if not changed:
                break

        if distance[sink] is None:
            return None

        node = sink
        while node != source:
            parent = previous_node[node]
            edge_index = previous_edge[node]
            if parent < 0 or edge_index < 0:
                return None
            edge = graph[parent][edge_index]
            edge.capacity -= 1
            graph[node][edge.reverse].capacity += 1
            node = parent
        flow += 1

    result: dict[SchoolDay, Prefect] = {}
    for day in days:
        for prefect in candidate_lists.get(day, []):
            edge = assignment_edges.get((day, prefect.id))
            if edge is not None and edge.capacity == 0:
                result[day] = prefect_by_id[prefect.id]
                break
        if day not in result:
            return None
    return result


def _find_nonconsecutive_weekday_schedule(
    candidate_lists: Mapping[SchoolDay, list[Prefect]],
    *,
    canonical: Mapping[SchoolDay, Prefect] | None,
    history_priority_multiplier: float,
    rotation_key: str,
    previous_assist_assignments: Mapping[SchoolDay, str],
) -> dict[SchoolDay, Prefect] | None:
    """Fallback scheduler when five distinct Assist prefects are unavailable.

    Only the previous prefect affects future feasibility, so dynamic
    programming keeps one best path per last prefect. This is O(days * P^2),
    honours the no-consecutive-duty rule, and avoids factorial search.
    """

    # last prefect id -> (additive score, path ids, scheduled prefects)
    states: dict[str, tuple[tuple[int, float, int, int], tuple[str, ...], tuple[Prefect, ...]]] = {}
    for day_index, day in enumerate(DAYS):
        next_states: dict[str, tuple[tuple[int, float, int, int], tuple[str, ...], tuple[Prefect, ...]]] = {}
        for prefect in candidate_lists.get(day, []):
            canonical_prefect = canonical.get(day) if canonical is not None else None
            mismatch = int(canonical_prefect is not None and canonical_prefect.id != prefect.id)
            step_score = (
                mismatch,
                history_priority_multiplier * prefect.history_weight,
                int(previous_assist_assignments.get(day) == prefect.id),
                _rotation_rank(rotation_key, day, prefect.id),
            )
            if day_index == 0:
                candidate_state = (step_score, (prefect.id,), (prefect,))
                next_states[prefect.id] = candidate_state
                continue
            for previous_id, (score, path_ids, path) in states.items():
                if previous_id == prefect.id:
                    continue
                total_score = tuple(left + right for left, right in zip(score, step_score, strict=True))
                candidate_state = (total_score, (*path_ids, prefect.id), (*path, prefect))
                current = next_states.get(prefect.id)
                if current is None or candidate_state[:2] < current[:2]:
                    next_states[prefect.id] = candidate_state
        states = next_states
        if not states:
            return None

    _, _, best_path = min(states.values(), key=lambda state: state[:2])
    return dict(zip(DAYS, best_path, strict=True))


def _canonical_assist_schedule(prefects: list[Prefect]) -> dict[SchoolDay, Prefect]:
    """Derive the legacy weekday map from stable identity and availability.

    History totals and weekly leave are intentionally excluded: otherwise the
    supposedly fixed weekday would drift after every published roster.
    """

    explicit_by_day: dict[SchoolDay, Prefect] = {}
    for prefect in prefects:
        if not can_assign_role(prefect.role, DutyPost.ASSIST_IN_CHARGE):
            continue
        fixed_code = str(prefect.fixed_general_duty or "NONE").strip().upper()
        if fixed_code == "NONE":
            continue
        try:
            fixed_day = SchoolDay[fixed_code]
        except KeyError as error:
            raise RosterGenerationError(
                f"Invalid fixed Assist. in charge weekday for {prefect.name}."
            ) from error
        if fixed_day not in prefect.available_days:
            raise RosterGenerationError(
                f"The fixed Assist. in charge weekday for {prefect.name} is not an available day."
            )
        existing = explicit_by_day.get(fixed_day)
        if existing is not None:
            raise RosterGenerationError(
                f"More than one Assistant Head Study Prefect is fixed to {fixed_day.name}."
            )
        explicit_by_day[fixed_day] = prefect

    explicit_ids = {prefect.id for prefect in explicit_by_day.values()}
    candidate_lists = {
        day: (
            [explicit_by_day[day]]
            if day in explicit_by_day
            else sorted(
                _eligible_assist_candidates(prefects, day=day, leave_days={}),
                # Persisted fixed weekdays take precedence. For remaining
                # days, database identity is the durable anchor: a corrected
                # display name must not silently move an AHP.
                key=lambda prefect: (
                    prefect.id in explicit_ids,
                    prefect.id,
                    prefect.name,
                ),
            )
        )
        for day in DAYS
    }
    for day, candidates in candidate_lists.items():
        if not candidates:
            raise RosterGenerationError(f"No eligible Assist. in charge candidate on {day.name}.")

    unique = _find_unique_weekday_matching(candidate_lists)
    if unique is not None:
        return unique
    fallback = _find_nonconsecutive_weekday_schedule(
        candidate_lists,
        canonical=None,
        history_priority_multiplier=0.0,
        rotation_key="legacy-canonical",
        previous_assist_assignments={},
    )
    if fallback is None:
        raise RosterGenerationError("No non-consecutive weekly Assist. in charge schedule is available.")
    return fallback


def legacy_assist_weekday_mapping(
    prefects: list[Prefect],
) -> dict[str, tuple[SchoolDay, ...]]:
    """Return the leave-independent canonical weekday ownership by prefect.

    Persistence uses this projection when an operator first accepts automatic
    legacy assignment.  It deliberately excludes the current week's leave so
    a temporary substitute can never become a long-term weekday owner.
    """

    days_by_prefect: dict[str, list[SchoolDay]] = defaultdict(list)
    for day, prefect in _canonical_assist_schedule(prefects).items():
        days_by_prefect[prefect.id].append(day)
    return {
        prefect_id: tuple(sorted(days, key=int))
        for prefect_id, days in days_by_prefect.items()
    }


def _legacy_assist_schedule(
    prefects: list[Prefect],
    *,
    leave_days: Mapping[str, set[SchoolDay]],
    history_priority_multiplier: float,
) -> dict[SchoolDay, Prefect]:
    canonical = _canonical_assist_schedule(prefects)
    eligible_by_day = {
        day: _eligible_assist_candidates(prefects, day=day, leave_days=leave_days)
        for day in DAYS
    }
    for day, candidates in eligible_by_day.items():
        if not candidates:
            raise RosterGenerationError(f"No eligible Assist. in charge candidate on {day.name}.")

    # Keep every available canonical occupant locked, then fill only the leave
    # vacancies. This makes a leave substitution local to that week and day.
    locked = {
        day: prefect
        for day, prefect in canonical.items()
        if day not in leave_days.get(prefect.id, set())
    }
    used_ids = {prefect.id for prefect in locked.values()}
    missing_lists = {
        day: sorted(
            (prefect for prefect in eligible_by_day[day] if prefect.id not in used_ids),
            key=lambda prefect: (
                history_priority_multiplier * prefect.history_weight,
                _form_rank(prefect.form),
                prefect.history_duties,
                prefect.name,
                prefect.id,
            ),
        )
        for day in DAYS
        if day not in locked
    }
    replacements = _find_unique_weekday_matching(missing_lists)
    if replacements is not None:
        return locked | replacements

    # If one-for-one substitution cannot cover the week, allow an eligible AHP
    # to cover an additional non-consecutive day.  Mismatch count is the first
    # dynamic-programming cost, so unaffected canonical weekdays stay fixed.
    candidate_lists = {
        day: sorted(
            eligible_by_day[day],
            key=lambda prefect: (
                prefect.id != canonical[day].id,
                history_priority_multiplier * prefect.history_weight,
                _form_rank(prefect.form),
                prefect.history_duties,
                prefect.name,
                prefect.id,
            ),
        )
        for day in DAYS
    }
    fallback = _find_nonconsecutive_weekday_schedule(
        candidate_lists,
        canonical=canonical,
        history_priority_multiplier=history_priority_multiplier,
        rotation_key="legacy-substitute",
        previous_assist_assignments={},
    )
    if fallback is None:
        raise RosterGenerationError("No non-consecutive weekly Assist. in charge schedule is available.")
    return fallback


def _flexible_assist_schedule(
    prefects: list[Prefect],
    *,
    leave_days: Mapping[str, set[SchoolDay]],
    history_priority_multiplier: float,
    rotation_key: str,
    previous_assist_assignments: Mapping[SchoolDay, str],
) -> dict[SchoolDay, Prefect]:
    candidate_lists = {
        day: sorted(
            _eligible_assist_candidates(prefects, day=day, leave_days=leave_days),
            key=lambda prefect: (
                history_priority_multiplier * prefect.history_weight,
                _rotation_rank(rotation_key, day, prefect.id),
                _form_rank(prefect.form),
                prefect.history_duties,
                prefect.name,
                prefect.id,
            ),
        )
        for day in DAYS
    }
    for day, candidates in candidate_lists.items():
        if not candidates:
            raise RosterGenerationError(f"No eligible Assist. in charge candidate on {day.name}.")

    unique = _find_min_cost_unique_weekday_matching(
        candidate_lists,
        history_priority_multiplier=history_priority_multiplier,
        rotation_key=rotation_key,
        previous_assist_assignments=previous_assist_assignments,
    )
    if unique is not None:
        return unique
    fallback = _find_nonconsecutive_weekday_schedule(
        candidate_lists,
        canonical=None,
        history_priority_multiplier=history_priority_multiplier,
        rotation_key=rotation_key,
        previous_assist_assignments=previous_assist_assignments,
    )
    if fallback is None:
        raise RosterGenerationError("No non-consecutive weekly Assist. in charge schedule is available.")
    return fallback


def _assist_schedule(
    prefects: list[Prefect],
    *,
    mode: AssistAssignmentMode,
    leave_days: Mapping[str, set[SchoolDay]],
    history_priority_multiplier: float,
    rotation_key: str,
    previous_assist_assignments: Mapping[SchoolDay, str],
) -> dict[SchoolDay, Prefect]:
    if mode is AssistAssignmentMode.LEGACY_FIXED_WEEKDAY:
        return _legacy_assist_schedule(
            prefects,
            leave_days=leave_days,
            history_priority_multiplier=history_priority_multiplier,
        )
    return _flexible_assist_schedule(
        prefects,
        leave_days=leave_days,
        history_priority_multiplier=history_priority_multiplier,
        rotation_key=rotation_key,
        previous_assist_assignments=previous_assist_assignments,
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
    assist_assignment_mode: AssistAssignmentMode | str = AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
    assist_rotation_key: str | None = None,
    previous_assist_assignments: Mapping[SchoolDay, str] | None = None,
) -> list[Assignment]:
    if not prefects:
        raise RosterGenerationError("Cannot generate roster without prefects.")

    normalized_multiplier = _normalized_history_priority_multiplier(history_priority_multiplier)
    normalized_assist_mode = _normalize_assist_assignment_mode(assist_assignment_mode)
    normalized_rotation_key = str(assist_rotation_key or "").strip()
    if (
        normalized_assist_mode is AssistAssignmentMode.FLEXIBLE_WEEKLY
        and not normalized_rotation_key
    ):
        raise RosterGenerationError(
            "Assist rotation key is required for flexible weekly assignment mode."
        )

    assignments: list[Assignment] = []
    generated_load: dict[str, float] = defaultdict(float)
    assigned_days: dict[str, set[SchoolDay]] = defaultdict(set)
    excluded_days = leave_days or {}
    assist_by_day = _assist_schedule(
        prefects,
        mode=normalized_assist_mode,
        leave_days=excluded_days,
        history_priority_multiplier=normalized_multiplier,
        rotation_key=normalized_rotation_key or "legacy-fixed-weekday",
        previous_assist_assignments=previous_assist_assignments or {},
    )

    for day in DAYS:
        assigned_today: set[str] = set()
        for post in required_posts_for_day(day):
            if post is DutyPost.ASSIST_IN_CHARGE:
                prefect = assist_by_day[day]
            else:
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
