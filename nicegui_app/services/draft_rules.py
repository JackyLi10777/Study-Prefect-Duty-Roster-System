"""Shared, side-effect-free final-state rules for formal and practice drafts.

Storage adapters translate records to stable cells. Candidate previews and
commits then use the same complete-matrix rules, including both sides of swaps.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from roster_core import Assignment, Prefect, validate_assignments
from roster_policy import DutyPost, SchoolDay, RosterPolicyError, duty_weight, is_room_open, required_posts_for_day
from nicegui_app.services.workflow_types import DraftCellEdit, DraftDayEdit, DraftSlotStateEdit, WorkflowError

_REASONS = frozenset({"school_event", "weather", "examination", "special_arrangement", "other"})


def parse_cell_key(value: str) -> tuple[SchoolDay, DutyPost, int]:
    try:
        day_code, post_code, slot_code = str(value).strip().upper().split(":")
        day, post, slot = SchoolDay[day_code], DutyPost[post_code], int(slot_code)
    except (KeyError, ValueError) as error:
        raise WorkflowError("Draft cell key contains an invalid stable code.") from error
    if slot < 1 or slot > required_posts_for_day(day).count(post):
        raise WorkflowError("Draft cell key does not identify a required roster slot.")
    return day, post, slot


def cell_key(day: SchoolDay, post: DutyPost, slot: int) -> str:
    return f"{day.name}:{post.name}:{slot}"


@dataclass(frozen=True)
class NormalizedDraftEdits:
    cells: tuple[tuple[DraftCellEdit, SchoolDay, DutyPost, int], ...]
    days: tuple[tuple[DraftDayEdit, SchoolDay, str | None, str | None], ...]
    slots: tuple[tuple[DraftSlotStateEdit, SchoolDay, DutyPost, int, str | None, str | None], ...]


def normalize_draft_edits(
    cell_edits: Iterable[DraftCellEdit] = (),
    day_edits: Iterable[DraftDayEdit] = (),
    slot_edits: Iterable[DraftSlotStateEdit] = (),
) -> NormalizedDraftEdits:
    """Normalize one final-state decision, allowing open+assignment atomically."""
    cells, days, slots = [], [], []
    seen_cells, seen_days, seen_slots = set(), set(), set()

    def metadata(edit):
        reason, note = (edit.reason_code or "").strip() or None, (edit.note or "").strip() or None
        if reason is not None and reason not in _REASONS:
            raise WorkflowError("A schedule exception must use a stable reason code.")
        if note is not None and len(note) > 1000:
            raise WorkflowError("A schedule exception note is too long.")
        return reason, note

    for edit in cell_edits:
        day, post, slot = parse_cell_key(edit.cell_key)
        key = cell_key(day, post, slot)
        if key in seen_cells:
            raise WorkflowError("A draft patch cannot change the same cell twice.")
        if edit.replacement_prefect_id is not None and not edit.replacement_prefect_id.strip():
            raise WorkflowError("An empty prefect identifier is not a vacancy decision.")
        seen_cells.add(key)
        cells.append((edit, day, post, slot))
    for edit in day_edits:
        try:
            day = edit.day if isinstance(edit.day, SchoolDay) else SchoolDay[str(edit.day).strip().upper()]
        except KeyError as error:
            raise WorkflowError("A roster day must use a stable weekday code.") from error
        if day in seen_days:
            raise WorkflowError("A draft patch cannot change the same weekday twice.")
        seen_days.add(day)
        days.append((edit, day, *metadata(edit)))
    for edit in slot_edits:
        day, post, slot = parse_cell_key(edit.cell_key)
        key = cell_key(day, post, slot)
        if not is_room_open(post, day):
            raise WorkflowError("A fixed room-policy closure cannot be overridden per slot.")
        if key in seen_slots:
            raise WorkflowError("A draft patch cannot change the same slot state twice.")
        if str(edit.state).strip().lower() not in {"open", "unavailable"}:
            raise WorkflowError("A draft slot state must be open or unavailable.")
        seen_slots.add(key)
        slots.append((edit, day, post, slot, *metadata(edit)))
    closing_days = {day for edit, day, *_ in days if edit.closed}
    if any(day in closing_days for _, day, *_ in cells):
        raise WorkflowError("A cell cannot be assigned in the same patch which closes its weekday.")
    if any(day in closing_days for _, day, *_ in slots):
        raise WorkflowError("A slot state cannot be changed in the same patch which closes its weekday.")
    unavailable = {cell_key(day, post, slot) for edit, day, post, slot, *_ in slots
                   if str(edit.state).strip().lower() == "unavailable"}
    if seen_cells & unavailable:
        raise WorkflowError("An unavailable slot cannot also contain an assignment decision.")
    return NormalizedDraftEdits(tuple(cells), tuple(days), tuple(slots))


@dataclass(frozen=True)
class DraftState:
    assignments: Mapping[str, str]
    closed_days: frozenset[SchoolDay] = frozenset()
    unavailable_slots: frozenset[str] = frozenset()


def apply_draft_overlay(state: DraftState, edits: NormalizedDraftEdits) -> DraftState:
    """Build a new complete matrix without touching its source or storage."""
    assignments = dict(state.assignments)
    closed, unavailable = set(state.closed_days), set(state.unavailable_slots)
    for edit, day, *_ in edits.days:
        if edit.closed:
            closed.add(day)
            assignments = {key: value for key, value in assignments.items() if not key.startswith(f"{day.name}:")}
            unavailable = {key for key in unavailable if not key.startswith(f"{day.name}:")}
        else:
            closed.discard(day)
    for edit, day, post, slot, *_ in edits.slots:
        key = cell_key(day, post, slot)
        if day in closed:
            raise WorkflowError("A closed weekday cannot contain a slot exception.")
        if str(edit.state).strip().lower() == "unavailable":
            unavailable.add(key)
            assignments.pop(key, None)
        else:
            unavailable.discard(key)
    for edit, day, post, slot in edits.cells:
        key = cell_key(day, post, slot)
        if day in closed or key in unavailable:
            raise WorkflowError("A closed or unavailable cell cannot contain an assignment.")
        if edit.replacement_prefect_id is None:
            assignments.pop(key, None)
        else:
            assignments[key] = edit.replacement_prefect_id
    return DraftState(assignments, frozenset(closed), frozenset(unavailable))


def validate_draft_state(
    state: DraftState, prefects: Iterable[Prefect], *,
    leave_days: Mapping[str, set[SchoolDay]], fixed_owners: Mapping[str, str] = {},
) -> None:
    people = tuple(prefects)
    by_id = {person.id: person for person in people}
    assignments = []
    for key, prefect_id in state.assignments.items():
        day, post, _ = parse_cell_key(key)
        if prefect_id not in by_id:
            raise WorkflowError("A selected prefect no longer exists or is inactive.")
        if post is DutyPost.ASSIST_IN_CHARGE and fixed_owners.get(day.name, prefect_id) != prefect_id:
            raise WorkflowError("Legacy fixed-weekday mode requires the weekday's assigned Assistant Head Study Prefect.")
        assignments.append(Assignment(day, post, prefect_id, by_id[prefect_id].name, duty_weight(post)))
    try:
        validate_assignments(assignments, people, leave_days=leave_days, closed_days=state.closed_days,
                             unavailable_slots=tuple(parse_cell_key(key) for key in state.unavailable_slots),
                             require_complete=False)
    except RosterPolicyError as error:
        raise WorkflowError(str(error)) from error


def draft_candidates(
    state: DraftState, target_key: str, prefects: Iterable[Prefect], *,
    leave_days: Mapping[str, set[SchoolDay]], fixed_owners: Mapping[str, str] = {},
    source_key: str | None = None,
) -> list[dict[str, object]]:
    """Evaluate the complete result of each choice, including a reciprocal swap.

    ``source_key`` makes a pointer/keyboard move one atomic intent: it is removed
    before adjacent-day checks, not mistakenly treated as an existing duty.
    """
    day, _, _ = parse_cell_key(target_key)
    if day in state.closed_days or target_key in state.unavailable_slots:
        return []
    people = tuple(prefects)
    original = state.assignments.get(target_key)
    outputs = []
    for person in people:
        if person.id == original:
            continue
        occupied = source_key if source_key and state.assignments.get(source_key) == person.id else next(
            (key for key, value in state.assignments.items()
             if key != target_key and key.startswith(f"{day.name}:") and value == person.id), None)
        proposed = dict(state.assignments)
        proposed[target_key] = person.id
        if occupied:
            if original:
                proposed[occupied] = original
            else:
                proposed.pop(occupied, None)
        try:
            validate_draft_state(DraftState(proposed, state.closed_days, state.unavailable_slots), people,
                                 leave_days=leave_days, fixed_owners=fixed_owners)
        except WorkflowError:
            continue
        outputs.append({"id": person.id, "nameZh": person.name, "form": person.form,
                        "className": person.class_name, "historyWeight": person.history_weight,
                        "requiresSwap": occupied is not None, "occupiedCellKey": occupied})
    rank = {person.id: (person.history_weight, int("".join(c for c in person.form if c.isdigit()) or 99),
                       person.history_duties, person.name) for person in people}
    return sorted(outputs, key=lambda item: rank[str(item["id"])])
