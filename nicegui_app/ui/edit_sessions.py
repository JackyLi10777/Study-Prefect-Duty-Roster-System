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


__all__ = [
    "PrefectDirectoryFilter",
    "PrefectEditSession",
    "filter_prefect_directory",
]
