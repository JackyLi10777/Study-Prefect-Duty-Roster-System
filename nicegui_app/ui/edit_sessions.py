"""Typed UI edit sessions that own buffered operator intent.

Routes render controls and translate feedback.  These sessions own the harder
state rules: what is dirty, which command can be retried, how undo/redo behaves,
and how an optimistic conflict may be retained or reapplied.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from uuid import uuid4

from nicegui_app.services.workflow_types import (
    PREFECT_PATCH_FIELDS,
    DraftCellEdit,
    DraftDayEdit,
    DraftSlotStateEdit,
    PrefectPatch,
)
from roster_policy import SchoolDay


PrefectRow = dict[str, object]


@dataclass
class PrefectDirectoryFilter:
    query: str = ""
    form: str = "all"
    role: str = "all"
    support: str = "all"
    sort: str = "name_asc"


_PREFECT_ROLE_ORDER = {"assistant_head": 0, "study_prefect": 1}


def filter_prefect_directory(
    prefects: Iterable[Mapping[str, object]],
    filters: PrefectDirectoryFilter,
) -> list[PrefectRow]:
    """Filter and stably sort one shared desktop/mobile directory model."""

    term = filters.query.strip().casefold()

    def matches(item: Mapping[str, object]) -> bool:
        if filters.form != "all" and str(item["form"]) != filters.form:
            return False
        if filters.role != "all" and str(item["roleCode"]) != filters.role:
            return False
        if filters.support == "needs_mentoring" and not bool(item["needsMentoring"]):
            return False
        if filters.support == "new" and not (
            float(item["historyWeight"]) == 0 and int(item["historyDuties"]) == 0
        ):
            return False
        if not term:
            return True
        haystack = " ".join(
            (
                str(item["nameZh"]),
                str(item.get("nameEn") or ""),
                str(item["form"]),
                str(item["className"]),
            )
        ).casefold()
        return term in haystack

    def grade_key(item: Mapping[str, object]) -> tuple[int, str]:
        digits = "".join(
            character for character in str(item["form"]) if character.isdigit()
        )
        return int(digits or 99), str(item["className"]).casefold()

    key_map: dict[str, tuple[Callable[[Mapping[str, object]], object], bool]] = {
        "name_asc": (lambda item: str(item["nameZh"]), False),
        "name_desc": (lambda item: str(item["nameZh"]), True),
        "grade_asc": (grade_key, False),
        "grade_desc": (grade_key, True),
        "role_asc": (
            lambda item: _PREFECT_ROLE_ORDER.get(str(item["roleCode"]), 99),
            False,
        ),
        "role_desc": (
            lambda item: _PREFECT_ROLE_ORDER.get(str(item["roleCode"]), 99),
            True,
        ),
        "weight_asc": (lambda item: float(item["historyWeight"]), False),
        "weight_desc": (lambda item: float(item["historyWeight"]), True),
        "duties_asc": (lambda item: int(item["historyDuties"]), False),
        "duties_desc": (lambda item: int(item["historyDuties"]), True),
        "created_asc": (lambda item: str(item.get("createdAt") or ""), False),
        "created_desc": (lambda item: str(item.get("createdAt") or ""), True),
    }
    key, reverse = key_map.get(filters.sort, key_map["name_asc"])
    filtered = [dict(item) for item in prefects if matches(item)]
    return sorted(
        filtered,
        key=lambda item: (key(item), str(item["id"])),
        reverse=reverse,
    )


@dataclass
class PrefectEditSession:
    """Own one buffered, atomic prefect-directory save intent."""

    originals: dict[str, PrefectRow]
    pending: dict[str, dict[str, object]] = field(default_factory=dict)
    conflicts: dict[str, PrefectRow] = field(default_factory=dict)
    filters: PrefectDirectoryFilter = field(default_factory=PrefectDirectoryFilter)
    command_id: str | None = None
    _command_factory: Callable[[], str] = field(
        default=lambda: f"prefect-batch-ui:{uuid4().hex}",
        repr=False,
    )

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, object]],
        *,
        command_factory: Callable[[], str] | None = None,
    ) -> PrefectEditSession:
        originals = {str(row["id"]): dict(row) for row in rows}
        if command_factory is None:
            return cls(originals=originals)
        return cls(originals=originals, _command_factory=command_factory)

    @property
    def dirty(self) -> bool:
        return bool(self.pending)

    @property
    def pending_count(self) -> int:
        return len(self.pending)

    def visible_rows(self) -> list[PrefectRow]:
        return filter_prefect_directory(
            (self.merged_row(prefect_id) for prefect_id in self.originals),
            self.filters,
        )

    def merged_row(self, prefect_id: str) -> PrefectRow:
        merged = dict(self.originals[prefect_id])
        merged.update(self.pending.get(prefect_id, {}))
        return merged

    def update_filter(self, key: str, value: object) -> None:
        if key not in {"query", "form", "role", "support", "sort"}:
            raise ValueError(f"Unknown prefect directory filter: {key}")
        setattr(self.filters, key, str(value or ""))

    def stage(self, prefect_id: str, field_name: str, value: object) -> bool:
        if prefect_id not in self.originals:
            raise KeyError(prefect_id)
        if field_name not in PREFECT_PATCH_FIELDS:
            raise ValueError(f"Field is not editable inline: {field_name}")
        normalized = (
            [day.name for day in SchoolDay if day.name in set(value or [])]
            if field_name == "availableDays"
            else value
        )
        before = dict(self.pending.get(prefect_id, {}))
        if normalized == self.originals[prefect_id].get(field_name):
            staged = self.pending.get(prefect_id)
            if staged is not None:
                staged.pop(field_name, None)
                if not staged:
                    self.pending.pop(prefect_id, None)
        else:
            self.pending.setdefault(prefect_id, {})[field_name] = normalized
        after = self.pending.get(prefect_id, {})
        if before == after:
            return False
        self.command_id = self._command_factory() if self.pending else None
        self.conflicts.pop(prefect_id, None)
        return True

    def ensure_command_id(self) -> str:
        if not self.dirty:
            raise ValueError("No prefect edits are pending.")
        if self.command_id is None:
            self.command_id = self._command_factory()
        return self.command_id

    def patches(self) -> tuple[PrefectPatch, ...]:
        return tuple(
            PrefectPatch(
                prefect_id=prefect_id,
                changes=dict(changes),
                expected_version=int(self.originals[prefect_id]["version"]),
            )
            for prefect_id, changes in sorted(self.pending.items())
        )

    def apply_save_result(self, result: Mapping[str, object]) -> None:
        updated = [dict(row) for row in result.get("updated", [])]  # type: ignore[arg-type]
        conflicts = [dict(row) for row in result.get("conflicts", [])]  # type: ignore[arg-type]
        errors = list(result.get("errors", []))  # type: ignore[arg-type]
        if updated and (conflicts or errors):
            raise ValueError("Atomic prefect save returned a partial result.")
        for row in updated:
            prefect_id = str(row["id"])
            self.originals[prefect_id] = row
            self.pending.pop(prefect_id, None)
        self.conflicts = {
            str(conflict["prefectId"]): conflict for conflict in conflicts
        }
        if updated and not self.pending:
            self.command_id = None

    def discard_conflict(self, prefect_id: str) -> bool:
        conflict = self.conflicts.pop(prefect_id, None)
        if conflict is None:
            return False
        self.originals[prefect_id] = dict(conflict["latest"])  # type: ignore[arg-type]
        self.pending.pop(prefect_id, None)
        self.command_id = self._command_factory() if self.pending else None
        return True

    def reapply_conflict(self, prefect_id: str) -> bool:
        conflict = self.conflicts.pop(prefect_id, None)
        if conflict is None:
            return False
        self.originals[prefect_id] = dict(conflict["latest"])  # type: ignore[arg-type]
        self.command_id = self._command_factory()
        return True


@dataclass(frozen=True)
class DraftEditSnapshot:
    cells: tuple[tuple[str, str | None], ...]
    days: tuple[tuple[str, bool], ...]
    slots: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class DraftMutation:
    kind: str
    source_prefect_id: str | None = None
    target_prefect_id: str | None = None
    exchanged_cell_key: str | None = None


@dataclass
class DraftConflictSnapshot:
    latest_version: int | None = None
    changes: list[str] = field(default_factory=list)


@dataclass
class DraftEditSession:
    """Own one reviewed draft patch from local manipulation through retry."""

    original_assignments: dict[str, str | None]
    original_unavailable: set[str]
    original_closed_days: set[str]
    reviewed_version: int
    pending_cells: dict[str, str | None] = field(default_factory=dict)
    pending_days: dict[str, bool] = field(default_factory=dict)
    pending_slots: dict[str, bool] = field(default_factory=dict)
    selected_cell: str | None = None
    move_source: str | None = None
    command_id: str | None = None
    conflict: DraftConflictSnapshot = field(default_factory=DraftConflictSnapshot)
    _undo: list[DraftEditSnapshot] = field(default_factory=list, repr=False)
    _redo: list[DraftEditSnapshot] = field(default_factory=list, repr=False)
    _command_factory: Callable[[], str] = field(
        default=lambda: f"draft-patch-ui:{uuid4().hex}",
        repr=False,
    )

    @property
    def dirty(self) -> bool:
        return bool(self.pending_cells or self.pending_days or self.pending_slots)

    @property
    def pending_count(self) -> int:
        return len(self.pending_cells) + len(self.pending_days) + len(self.pending_slots)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def effective_assignment(self, cell_key: str) -> str | None:
        return self.pending_cells.get(cell_key, self.original_assignments.get(cell_key))

    def day_is_closed(self, day_name: str) -> bool:
        return self.pending_days.get(day_name, day_name in self.original_closed_days)

    def slot_is_unavailable(self, cell_key: str) -> bool:
        return self.pending_slots.get(cell_key, cell_key in self.original_unavailable)

    def _snapshot(self) -> DraftEditSnapshot:
        return DraftEditSnapshot(
            cells=tuple(sorted(self.pending_cells.items())),
            days=tuple(sorted(self.pending_days.items())),
            slots=tuple(sorted(self.pending_slots.items())),
        )

    def _restore(self, snapshot: DraftEditSnapshot) -> None:
        self.pending_cells.clear()
        self.pending_cells.update(snapshot.cells)
        self.pending_days.clear()
        self.pending_days.update(snapshot.days)
        self.pending_slots.clear()
        self.pending_slots.update(snapshot.slots)
        self.command_id = None
        self.move_source = None

    def _remember(self) -> None:
        self._undo.append(self._snapshot())
        self._redo.clear()
        self.command_id = None

    def _stage_cell(self, cell_key: str, prefect_id: str | None) -> None:
        if prefect_id == self.original_assignments.get(cell_key):
            self.pending_cells.pop(cell_key, None)
        else:
            self.pending_cells[cell_key] = prefect_id

    def stage_candidate(
        self,
        cell_key: str,
        replacement_prefect_id: str | None,
    ) -> DraftMutation:
        current_id = self.effective_assignment(cell_key)
        if replacement_prefect_id == current_id:
            return DraftMutation("noop")
        day_name = cell_key.partition(":")[0]
        if self.day_is_closed(day_name) or self.slot_is_unavailable(cell_key):
            return DraftMutation("blocked")
        occupied_cell_key = (
            next(
                (
                    candidate_key
                    for candidate_key in self.original_assignments
                    if candidate_key != cell_key
                    and candidate_key.partition(":")[0] == day_name
                    and self.effective_assignment(candidate_key)
                    == replacement_prefect_id
                ),
                None,
            )
            if replacement_prefect_id is not None
            else None
        )
        self._remember()
        self._stage_cell(cell_key, replacement_prefect_id)
        if occupied_cell_key:
            self._stage_cell(occupied_cell_key, current_id)
        return DraftMutation(
            "swap" if occupied_cell_key else "assign",
            source_prefect_id=current_id,
            target_prefect_id=replacement_prefect_id,
            exchanged_cell_key=occupied_cell_key,
        )

    def stage_move(self, source_key: str, target_key: str) -> DraftMutation:
        self.move_source = None
        if source_key == target_key:
            return DraftMutation("noop")
        source_day = source_key.partition(":")[0]
        target_day = target_key.partition(":")[0]
        if (
            self.day_is_closed(source_day)
            or self.day_is_closed(target_day)
            or self.slot_is_unavailable(source_key)
            or self.slot_is_unavailable(target_key)
        ):
            return DraftMutation("blocked")
        source_id = self.effective_assignment(source_key)
        target_id = self.effective_assignment(target_key)
        if source_id is None:
            return DraftMutation("empty", target_prefect_id=target_id)
        self._remember()
        self._stage_cell(source_key, target_id)
        self._stage_cell(target_key, source_id)
        self.selected_cell = target_key
        return DraftMutation(
            "swap" if target_id else "move",
            source_prefect_id=source_id,
            target_prefect_id=target_id,
        )

    def stage_slot(self, cell_key: str, unavailable: bool) -> bool:
        if self.slot_is_unavailable(cell_key) == unavailable:
            return False
        self._remember()
        if unavailable == (cell_key in self.original_unavailable):
            self.pending_slots.pop(cell_key, None)
        else:
            self.pending_slots[cell_key] = unavailable
        if unavailable:
            self.pending_cells.pop(cell_key, None)
            if self.move_source == cell_key:
                self.move_source = None
        return True

    def stage_day(self, day_name: str, closed: bool) -> bool:
        if self.day_is_closed(day_name) == closed:
            return False
        self._remember()
        if closed == (day_name in self.original_closed_days):
            self.pending_days.pop(day_name, None)
        else:
            self.pending_days[day_name] = closed
        if closed:
            prefix = f"{day_name}:"
            for key in tuple(self.pending_cells):
                if key.startswith(prefix):
                    self.pending_cells.pop(key, None)
            for key in tuple(self.pending_slots):
                if key.startswith(prefix):
                    self.pending_slots.pop(key, None)
            if self.selected_cell and self.selected_cell.startswith(prefix):
                self.selected_cell = None
            if self.move_source and self.move_source.startswith(prefix):
                self.move_source = None
        return True

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        return True

    def discard(self) -> None:
        self.pending_cells.clear()
        self.pending_days.clear()
        self.pending_slots.clear()
        self._undo.clear()
        self._redo.clear()
        self.command_id = None
        self.move_source = None
        self.selected_cell = None
        self.conflict = DraftConflictSnapshot()

    def patch_edits(
        self,
    ) -> tuple[tuple[DraftCellEdit, ...], tuple[DraftDayEdit, ...], tuple[DraftSlotStateEdit, ...]]:
        return (
            tuple(
                DraftCellEdit(cell_key=key, replacement_prefect_id=value)
                for key, value in sorted(self.pending_cells.items())
            ),
            tuple(
                DraftDayEdit(day=day, closed=closed)
                for day, closed in sorted(self.pending_days.items())
            ),
            tuple(
                DraftSlotStateEdit(
                    cell_key=cell_key,
                    state="unavailable" if unavailable else "open",
                )
                for cell_key, unavailable in sorted(self.pending_slots.items())
            ),
        )

    def ensure_command_id(self) -> str:
        if not self.dirty:
            raise ValueError("No draft edits are pending.")
        if self.command_id is None:
            self.command_id = self._command_factory()
        return self.command_id

    def set_conflict(self, *, latest_version: int | None, changes: Iterable[str]) -> None:
        self.conflict = DraftConflictSnapshot(
            latest_version=latest_version,
            changes=list(changes),
        )

    def reapply_conflict(self) -> bool:
        if self.conflict.latest_version is None:
            return False
        self.reviewed_version = self.conflict.latest_version
        self.command_id = None
        return True


__all__ = [
    "DraftConflictSnapshot",
    "DraftEditSession",
    "DraftEditSnapshot",
    "DraftMutation",
    "PrefectDirectoryFilter",
    "PrefectEditSession",
    "filter_prefect_directory",
]
