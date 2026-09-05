"""Policy-driven ordinary drafts, independent of UI, SQL and public exports.

The frozen document is the read/edit seam: no operation consults current policy
behind the caller's back. Publication must revalidate live eligibility later.
The existing single-seat Assist algorithm remains the owner of its two modes.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
import json
import math

from roster_policy import AssistAssignmentMode, PrefectRole, SchoolDay, is_chinese_display_name
from roster_policy.configurable import (
    ApprovedUnavailable, BusinessId, CompiledSchedule, ScheduleExceptions,
    ScheduleMode, SeatKey, SeatState, compile_weekly,
)
from roster_policy.policy_codec import decode_weekly_policy, encode_weekly_policy
from .generator import (
    RosterGenerationError, _assist_schedule, _candidate_score,
    _normalized_history_priority_multiplier, legacy_assist_weekday_mapping,
)
from .models import Prefect
from .policy_settings import PolicyRevision


SEARCH_NODE_LIMIT = 50_000
SEARCH_WORK_LIMIT = 1_000_000
_WEIGHTS = {
    BusinessId.ASSIST_IN_CHARGE: 1.0, BusinessId.STUDY_ROOM: 1.0,
    BusinessId.HOMEWORK_COMPLETION: 1.5, BusinessId.FORM_1_STUDY_GROUP: 1.5,
}
_VACANCY_REASONS = frozenset({
    "no_eligible_person", "constraints_require_review", "search_limit",
    "assist_constraints_require_review", "operator_vacancy",
})


class DraftError(ValueError):
    """A draft request or saved snapshot violates its ordinary rules."""


@dataclass(frozen=True)
class DraftCell:
    key: SeatKey
    state: str
    prefect_id: str | None = None
    prefect_name: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DutyCommitment:
    person_id: str
    duty_date: date
    mode: ScheduleMode


@dataclass(frozen=True)
class WeeklyDraft:
    policy_ref: PolicyRevision
    schedule: CompiledSchedule
    people: tuple[Prefect, ...]
    exceptions: ScheduleExceptions
    leaves: tuple[tuple[str, date], ...]
    occupied: tuple[DutyCommitment, ...]
    assist_mode: AssistAssignmentMode
    history_multiplier: float
    previous_assist: tuple[tuple[SchoolDay, str], ...]
    cells: tuple[DraftCell, ...]


def _pairs(values, people, dates, label):
    pairs = tuple(values)
    ids = {person.id for person in people}
    if any(type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str
           or pair[0] not in ids or type(pair[1]) is not date or pair[1] not in dates for pair in pairs):
        raise DraftError(f"{label} must identify a known person and an actual schedule date.")
    if len(set(pairs)) != len(pairs):
        raise DraftError(f"{label} must not repeat.")
    return tuple(sorted(pairs))


def _people(values):
    people = tuple(values)
    if not all(isinstance(person, Prefect) for person in people):
        raise DraftError("Eligibility requires Prefect values.")
    for person in people:
        if (type(person.id) is not str or not person.id or len(person.id) > 64
                or type(person.name) is not str or not is_chinese_display_name(person.name)
                or not isinstance(person.role, PrefectRole)
                or type(person.available_days) is not frozenset
                or any(not isinstance(day, SchoolDay) for day in person.available_days)
                or type(person.history_weight) not in (int, float)
                or not math.isfinite(person.history_weight) or person.history_weight < 0
                or type(person.history_duties) is not int or person.history_duties < 0
                or type(person.needs_mentoring) is not bool
                or any(type(value) is not str for value in (person.form, person.class_name, person.remarks, person.fixed_general_duty))):
            raise DraftError("A person has invalid eligibility or authoritative name data.")
        if person.role is PrefectRole.ASSISTANT_HEAD and person.fixed_general_duty != "NONE":
            try:
                fixed = SchoolDay[person.fixed_general_duty]
            except KeyError as error:
                raise DraftError("Invalid fixed Assist weekday.") from error
            if fixed not in person.available_days:
                raise DraftError("Fixed Assist weekday must be available.")
    if len({person.id for person in people}) != len(people):
        raise DraftError("Duplicate person identity.")
    fixed = [person.fixed_general_duty for person in people
             if person.role is PrefectRole.ASSISTANT_HEAD and person.fixed_general_duty != "NONE"]
    if len(set(fixed)) != len(fixed):
        raise DraftError("Multiple people claim the same fixed Assist weekday.")
    return tuple(sorted(people, key=lambda person: person.id))


def _commitments(values, people, dates):
    commitments = tuple(values)
    ids = {person.id for person in people}
    if any(not isinstance(item, DutyCommitment) or type(item.person_id) is not str
           or item.person_id not in ids or type(item.duty_date) is not date
           or item.duty_date not in dates or not isinstance(item.mode, ScheduleMode)
           for item in commitments):
        raise DraftError("Occupancy requires a known person, actual schedule date and explicit mode.")
    if len({(item.person_id, item.duty_date) for item in commitments}) != len(commitments):
        raise DraftError("Occupancy must not repeat a person/date.")
    return tuple(sorted(commitments, key=lambda item: (item.person_id, item.duty_date, item.mode.value)))


def _excluded_dates(leaves, occupied, dates):
    # Ordinary no-consecutive duty is a hard rule, including other published
    # ordinary schedules. CP commitments only block their actual date.
    return set(leaves) | {
        (item.person_id, day) for item in occupied for day in dates
        if abs((day - item.duty_date).days) <= (1 if item.mode is ScheduleMode.WEEKLY else 0)
    }


def _eligible(person, key, excluded):
    role = PrefectRole.ASSISTANT_HEAD if key.business is BusinessId.ASSIST_IN_CHARGE else PrefectRole.STUDY_PREFECT
    return (person.role is role and SchoolDay(key.duty_date.weekday()) in person.available_days
            and (person.id, key.duty_date) not in excluded)


def validate_draft(draft: WeeklyDraft) -> None:
    if not isinstance(draft, WeeklyDraft) or not isinstance(draft.policy_ref, PolicyRevision):
        raise DraftError("An ordinary draft requires an immutable policy reference.")
    if draft.schedule != compile_weekly(draft.policy_ref.policy, draft.schedule.dates[0], exceptions=draft.exceptions):
        raise DraftError("The saved rows, dates or minutes differ from the frozen rules.")
    if draft.policy_ref.policy.businesses[0].capacity != 1:
        raise DraftError("Assist capacity greater than one is not supported by the current mode contract.")
    if _people(draft.people) != draft.people:
        raise DraftError("Eligibility snapshots require canonical person order.")
    if not isinstance(draft.assist_mode, AssistAssignmentMode):
        raise DraftError("An explicit supported Assist mode is required.")
    if type(draft.history_multiplier) not in (int, float):
        raise DraftError("History multiplier must be numeric, not boolean.")
    _normalized_history_priority_multiplier(draft.history_multiplier)
    if (_pairs(draft.leaves, draft.people, draft.schedule.dates, "Leave") != draft.leaves
            or _commitments(draft.occupied, draft.people, draft.schedule.dates) != draft.occupied):
        raise DraftError("Date constraints require canonical order.")
    if (type(draft.previous_assist) is not tuple
            or any(type(item) is not tuple or len(item) != 2 or not isinstance(item[0], SchoolDay)
                   or type(item[1]) is not str or not item[1] for item in draft.previous_assist)
            or len({item[0] for item in draft.previous_assist}) != len(draft.previous_assist)
            or tuple(sorted(draft.previous_assist)) != draft.previous_assist):
        raise DraftError("Previous Assist assignments require unique canonical weekdays.")
    expected = tuple(seat for row in draft.schedule.rows for seat in row.seats)
    if type(draft.cells) is not tuple or len(expected) != len(draft.cells):
        raise DraftError("The draft must preserve every display cell.")
    people = {person.id: person for person in draft.people}
    excluded = _excluded_dates(draft.leaves, draft.occupied, draft.schedule.dates)
    assigned = defaultdict(set)
    for cell, seat in zip(draft.cells, expected, strict=True):
        if not isinstance(cell, DraftCell) or cell.key != seat.key:
            raise DraftError("Draft cells must match the ordered actual-date seats.")
        if seat.state is not SeatState.REQUIRED:
            if cell != DraftCell(seat.key, seat.state.value):
                raise DraftError("Closed/unavailable seats cannot contain assignments or personal data.")
        elif cell.state == "vacant":
            if cell.prefect_id is not None or cell.prefect_name is not None or cell.reason not in _VACANCY_REASONS:
                raise DraftError("Vacant cells require an explicit supported reason and no person.")
        elif cell.state == "assigned":
            person = people.get(cell.prefect_id)
            if (person is None or cell.prefect_name != person.name or cell.reason is not None
                    or not _eligible(person, cell.key, excluded)):
                raise DraftError("The selected person is not eligible for this seat.")
            days = assigned[person.id]
            if any(abs((previous - cell.key.duty_date).days) <= 1 for previous in days):
                raise DraftError("A person cannot have duplicate or consecutive ordinary duties.")
            days.add(cell.key.duty_date)
        else:
            raise DraftError("An open seat must be assigned or explicitly vacant.")


def _solve_regular(keys, people, excluded, multiplier):
    """Bounded complete search first; honest best-effort vacancies on failure.

    Per-day union checks prune impossible coverage. This does not claim optimal
    partial coverage after infeasibility or budget exhaustion.
    """
    keys = sorted(keys, key=lambda key: (key.duty_date, list(_WEIGHTS).index(key.business), key.seat_index))
    # All ordinary regular posts share role/availability eligibility. Compile a
    # pool once per date, not once per capacity row.
    pools = {}
    for key in keys:
        if key.duty_date not in pools:
            pools[key.duty_date] = tuple(person for person in people if _eligible(person, key, excluded))
    base = {key: pools[key.duty_date] for key in keys}
    chosen = {}
    days = defaultdict(set)
    load = defaultdict(float)
    nodes = 0
    exhausted = False
    failed = set()
    work = 0
    bounded = True

    class SearchBudgetReached(Exception):
        pass

    def options(key):
        nonlocal work
        work += len(base[key])
        if bounded and work > SEARCH_WORK_LIMIT:
            raise SearchBudgetReached
        return sorted((person for person in base[key]
                       if all(abs((previous - key.duty_date).days) > 1 for previous in days[person.id])),
                      key=lambda person: (*_candidate_score(person, load, multiplier), person.id))

    def choose(key, person):
        chosen[key] = person
        days[person.id].add(key.duty_date)
        load[person.id] += _WEIGHTS[key.business]

    def solve(index):
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > SEARCH_NODE_LIMIT:
            exhausted = True
            return False
        if index == len(keys):
            return True
        state = (index, tuple(sorted((identity, tuple(sorted(value))) for identity, value in days.items() if value)))
        if state in failed:
            return False
        pending = defaultdict(list)
        for key in keys[index:]:
            pending[key.duty_date].append(key)
        for daily in pending.values():
            available = {person.id for person in options(daily[0])}
            if len(available) < len(daily):
                failed.add(state)
                return False
        key = keys[index]
        for person in options(key):
            choose(key, person)
            if solve(index + 1):
                return True
            del chosen[key]
            days[person.id].remove(key.duty_date)
            load[person.id] -= _WEIGHTS[key.business]
            if exhausted:
                return False
        failed.add(state)
        return False

    try:
        complete = solve(0)
    except SearchBudgetReached:
        exhausted = True
        complete = False
    if not complete:
        bounded = False  # The fallback is a single linear pass, not search.
        chosen.clear()
        days.clear()
        load.clear()
        for key in keys:
            candidates = options(key)
            if candidates:
                choose(key, candidates[0])
    reasons = {key: ("no_eligible_person" if not base[key] else "search_limit" if exhausted else "constraints_require_review")
               for key in keys if key not in chosen}
    return chosen, reasons


def generate_draft(
    policy_ref: PolicyRevision, monday: date, people: tuple[Prefect, ...], *,
    exceptions: ScheduleExceptions = ScheduleExceptions(), leaves=(), occupied=(),
    assist_mode: AssistAssignmentMode = AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
    history_multiplier: float = 1.0, previous_assist: Mapping[SchoolDay, str] | None = None,
) -> WeeklyDraft:
    if not isinstance(policy_ref, PolicyRevision):
        raise DraftError("Select an explicit school-year policy revision.")
    schedule = compile_weekly(policy_ref.policy, monday, exceptions=exceptions)
    if policy_ref.policy.businesses[0].capacity != 1:
        raise DraftError("Assist capacity greater than one is not supported by the current mode contract.")
    people = _people(people)
    leaves = _pairs(leaves, people, schedule.dates, "Leave")
    occupied = _commitments(occupied, people, schedule.dates)
    if type(history_multiplier) not in (int, float):
        raise DraftError("History multiplier must be numeric, not boolean.")
    multiplier = _normalized_history_priority_multiplier(history_multiplier)
    if not isinstance(assist_mode, AssistAssignmentMode):
        raise DraftError("Select a supported Assist mode.")
    previous = tuple(sorted((previous_assist or {}).items()))
    required = [seat.key for row in schedule.rows for seat in row.seats if seat.state is SeatState.REQUIRED]
    excluded = _excluded_dates(leaves, occupied, schedule.dates)
    assignments, reasons = _solve_regular([key for key in required if key.business is not BusinessId.ASSIST_IN_CHARGE],
                                          people, excluded, multiplier)
    assist_keys = [key for key in required if key.business is BusinessId.ASSIST_IN_CHARGE]
    leave_days = defaultdict(set)
    for identity, duty_date in excluded:
        leave_days[identity].add(SchoolDay(duty_date.weekday()))
    try:
        selected = _assist_schedule(list(people), mode=assist_mode, leave_days=leave_days,
                                   history_priority_multiplier=multiplier, rotation_key=monday.isoformat(),
                                   previous_assist_assignments=dict(previous),
                                   scheduled_days=tuple(SchoolDay(key.duty_date.weekday()) for key in assist_keys))
    except RosterGenerationError:
        # Do not invent a new fixed-weekday mapping when the authoritative mode
        # cannot cover the week. Preserve reviewable vacancies instead.
        selected = {}
    for key in assist_keys:
        person = selected.get(SchoolDay(key.duty_date.weekday()))
        if person is not None:
            assignments[key] = person
        else:
            reasons[key] = ("assist_constraints_require_review" if any(_eligible(person, key, excluded) for person in people)
                            else "no_eligible_person")
    cells = []
    for row in schedule.rows:
        for seat in row.seats:
            person = assignments.get(seat.key)
            cells.append(DraftCell(seat.key, seat.state.value) if seat.state is not SeatState.REQUIRED else
                         DraftCell(seat.key, "assigned", person.id, person.name) if person else
                         DraftCell(seat.key, "vacant", reason=reasons[seat.key]))
    result = WeeklyDraft(policy_ref, schedule, people, exceptions, leaves, occupied, assist_mode,
                         multiplier, previous, tuple(cells))
    validate_draft(result)
    return result


def edit_draft(draft: WeeklyDraft, changes: Mapping[SeatKey, str | None], *,
               people: tuple[Prefect, ...] | None = None, leaves=None, occupied=None) -> WeeklyDraft:
    validate_draft(draft)
    if not isinstance(changes, Mapping) or any(key not in {cell.key for cell in draft.cells} for key in changes):
        raise DraftError("Every edit must identify an existing actual-date seat.")
    live_people = draft.people if people is None else _people(people)
    people_by_id = {person.id: person for person in live_people}
    cells = []
    for cell in draft.cells:
        if cell.key in changes:
            identity = changes[cell.key]
            if identity is None:
                cell = DraftCell(cell.key, "vacant", reason="operator_vacancy")
            else:
                if type(identity) is not str or identity not in people_by_id:
                    raise DraftError("Select a known eligible person or explicitly choose vacancy.")
                cell = DraftCell(cell.key, "assigned", identity, people_by_id[identity].name)
        elif cell.state == "assigned" and cell.prefect_id in people_by_id:
            cell = replace(cell, prefect_name=people_by_id[cell.prefect_id].name)
        cells.append(cell)
    result = replace(draft, cells=tuple(cells), people=live_people,
                     leaves=draft.leaves if leaves is None else _pairs(leaves, live_people, draft.schedule.dates, "Leave"),
                     occupied=draft.occupied if occupied is None else _commitments(occupied, live_people, draft.schedule.dates))
    validate_draft(result)
    return result


def accepted_assist_ownership(draft: WeeklyDraft) -> tuple[WeeklyDraft, dict[str, str]]:
    """Return first accepted fixed weekdays for the caller's atomic commit.

    This reuses the existing leave-independent owner calculation. A temporary
    substitute never becomes a fixed owner. Unresolved Assist drafts cannot
    initialize ownership, and no existing explicit weekday is overwritten.
    """
    validate_draft(draft)
    active = [cell for cell in draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE
              and cell.state in {"assigned", "vacant"}]
    if draft.assist_mode is not AssistAssignmentMode.LEGACY_FIXED_WEEKDAY or not active or any(cell.state == "vacant" for cell in active):
        return draft, {}
    ownership = legacy_assist_weekday_mapping(list(draft.people))
    changes = {person.id: ownership[person.id][0].name for person in draft.people
               if person.role is PrefectRole.ASSISTANT_HEAD and person.fixed_general_duty == "NONE"
               and len(ownership.get(person.id, ())) == 1}
    people = tuple(replace(person, fixed_general_duty=changes.get(person.id, person.fixed_general_duty)) for person in draft.people)
    result = replace(draft, people=people)
    validate_draft(result)
    return result, changes


def _key(key):
    return [key.duty_date.isoformat(), key.business.value, key.seat_index]


def _payload(draft):
    return {
        "schemaVersion": 1, "mode": "weekly", "status": "draft",
        "policyRef": [draft.policy_ref.year_start, draft.policy_ref.revision],
        "policy": encode_weekly_policy(draft.policy_ref.policy),
        "dates": [day.isoformat() for day in draft.schedule.dates],
        "rows": [{"business": row.business.value, "name": row.business_name, "room": row.room,
                  "index": row.seat_index, "opening": [row.opening.start, row.opening.end],
                  "service": [row.service.start, row.service.end], "minutes": row.service_minutes}
                 for row in draft.schedule.rows],
        "people": [{"id": person.id, "name": person.name, "form": person.form, "class": person.class_name,
                    "role": person.role.value, "available": [int(day) for day in sorted(person.available_days)],
                    "weight": person.history_weight, "duties": person.history_duties,
                    "mentoring": person.needs_mentoring, "fixed": person.fixed_general_duty, "remarks": person.remarks}
                   for person in draft.people],
        "closed": [day.isoformat() for day in draft.exceptions.closed_dates],
        "unavailable": [[_key(entry.seat), entry.approval_reference] for entry in draft.exceptions.unavailable],
        "leaves": [[identity, day.isoformat()] for identity, day in draft.leaves],
        "occupied": [[item.person_id, item.duty_date.isoformat(), item.mode.value] for item in draft.occupied],
        "assistMode": draft.assist_mode.value, "historyMultiplier": draft.history_multiplier,
        "previousAssist": [[int(day), identity] for day, identity in draft.previous_assist],
        "cells": [{"key": _key(cell.key), "state": cell.state, "person": cell.prefect_id,
                   "name": cell.prefect_name, "reason": cell.reason} for cell in draft.cells],
    }


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def encode_draft(draft: WeeklyDraft) -> str:
    validate_draft(draft)
    return _json(_payload(draft))


def decode_draft(document: str) -> WeeklyDraft:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise DraftError("Duplicate snapshot JSON field.")
            value[key] = item
        return value

    def reject(_):
        raise DraftError("Non-finite snapshot JSON value.")

    def key(raw):
        if type(raw) is not list or len(raw) != 3:
            raise DraftError("Invalid actual-date seat identity.")
        return SeatKey(date.fromisoformat(raw[0]), BusinessId(raw[1]), raw[2])

    try:
        if type(document) is not str:
            raise DraftError("A saved draft must be JSON text.")
        raw = json.loads(document, object_pairs_hook=unique, parse_constant=reject)
        reference = PolicyRevision(*raw["policyRef"], decode_weekly_policy(raw["policy"]))
        exceptions = ScheduleExceptions(tuple(date.fromisoformat(value) for value in raw["closed"]),
                                        tuple(ApprovedUnavailable(key(value[0]), value[1]) for value in raw["unavailable"]))
        schedule = compile_weekly(reference.policy, date.fromisoformat(raw["dates"][0]), exceptions=exceptions)
        people = tuple(Prefect(person["id"], person["name"], person["form"], person["class"], PrefectRole(person["role"]),
                               frozenset(SchoolDay(day) for day in person["available"]), person["weight"], person["duties"],
                               person["mentoring"], person["fixed"], person["remarks"]) for person in raw["people"])
        result = WeeklyDraft(reference, schedule, people, exceptions,
                             tuple((identity, date.fromisoformat(day)) for identity, day in raw["leaves"]),
                             tuple(DutyCommitment(identity, date.fromisoformat(day), ScheduleMode(mode))
                                   for identity, day, mode in raw["occupied"]),
                             AssistAssignmentMode(raw["assistMode"]), raw["historyMultiplier"],
                             tuple((SchoolDay(day), identity) for day, identity in raw["previousAssist"]),
                             tuple(DraftCell(key(cell["key"]), cell["state"], cell["person"], cell["name"], cell["reason"])
                                   for cell in raw["cells"]))
        validate_draft(result)
        if _json(_payload(result)) != _json(raw):
            raise DraftError("Snapshot fields, rows or canonical types differ from their frozen rules.")
        return result
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError, AttributeError) as error:
        raise DraftError("The saved ordinary draft is invalid; it cannot be replaced with defaults.") from error
