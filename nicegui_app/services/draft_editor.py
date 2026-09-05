"""Draft state and asynchronous coordination, independent of NiceGUI."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from nicegui_app.services.workflow_types import (
    DraftCellEdit, DraftDayEdit, DraftSlotStateEdit, DraftCellTarget,
    DraftPatchCommand, WorkflowError, WorkflowConflictError, CommittedWriteBackupError,
)
from nicegui_app.services.roster_presentation import build_roster_presentation, RosterCellState


class DraftEditingPort(Protocol):
    def roster_schedule_snapshot(self, roster_week_id: int) -> tuple[dict[str, object], list[dict[str, object]]]: ...
    def draft_cell_candidates(self, roster_week_id: int, cell_key: str, **kwargs: Any) -> list[dict[str, object]]: ...
    def apply_draft_patch(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class DraftSaveOutcome:
    receipt: Any
    snapshot: tuple[dict[str, object], list[dict[str, object]]] | None


class DraftCommittedWithoutBackup(CommittedWriteBackupError):
    """A verified committed intent whose recovery snapshot still needs repair."""

    def __init__(self, error: CommittedWriteBackupError, command: DraftPatchCommand, snapshot) -> None:
        super().__init__(error.event_type, error.error_message)
        self.command = command
        self.snapshot = snapshot


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
class DraftEditor:
    """Own one reviewed draft patch from local manipulation through retry."""

    original_assignments: dict[str, str | None]
    original_unavailable: set[str]
    original_closed_days: set[str]
    reviewed_version: int
    workflow: DraftEditingPort | None = field(default=None, repr=False)
    roster_week_id: int = 0
    candidate_cache: dict[str, list[dict[str, object]]] = field(default_factory=dict, repr=False)
    candidate_names: dict[str, str] = field(default_factory=dict, repr=False)
    local_revision: int = 0
    saving: bool = False
    recovery_required: bool = False
    roster_status: str = "draft"
    snapshot_refresh_failed: bool = False
    last_saved_version: int | None = None
    _closed: bool = False
    _candidate_tasks: dict[tuple[int, str, str | None], asyncio.Task] = field(default_factory=dict, repr=False)
    _candidate_gate: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(1), repr=False)
    _save_command: DraftPatchCommand | None = field(default=None, repr=False)
    _latest_snapshot: tuple[dict[str, object], list[dict[str, object]]] | None = field(default=None, repr=False)
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

    @classmethod
    def from_snapshot(cls, workflow: DraftEditingPort, roster_week_id: int, snapshot) -> DraftEditor:
        editor = cls({}, set(), set(), int(snapshot[0]["version"]), workflow, roster_week_id)
        editor.accept_snapshot(snapshot)
        return editor

    @property
    def latest_snapshot(self):
        return self._latest_snapshot

    @property
    def read_only(self) -> bool:
        return self._closed or self.recovery_required or self.roster_status != "draft"

    @property
    def dirty(self) -> bool:
        return bool(self.pending_cells or self.pending_days or self.pending_slots)

    @property
    def pending_count(self) -> int:
        return len(set(self.pending_cells) | set(self.pending_slots)) + len(self.pending_days)

    @property
    def can_undo(self) -> bool:
        return not self.saving and bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return not self.saving and bool(self._redo)

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
        self._invalidate()

    def _remember(self) -> None:
        self._undo.append(self._snapshot())
        del self._undo[:-100]
        self._redo.clear()
        self.command_id = None
        self._invalidate()

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
        if self.saving or self._closed:
            return DraftMutation("blocked")
        current_id = self.effective_assignment(cell_key)
        if replacement_prefect_id == current_id:
            return DraftMutation("noop")
        day_name = cell_key.partition(":")[0]
        if self.day_is_closed(day_name) or self.slot_is_unavailable(cell_key):
            return DraftMutation("blocked")
        if replacement_prefect_id is not None and self.workflow is not None:
            # Being the original assignee confers no eligibility after another
            # local decision. The cache belongs to this complete working state;
            # every mutation invalidates it before any further person is chosen.
            eligible_ids = {str(row["id"]) for row in self.candidate_cache.get(cell_key, ())}
            if replacement_prefect_id not in eligible_ids:
                return DraftMutation("invalid")
        occupied_cell_key = (
            next(
                (
                    candidate_key
                    for candidate_key in self.original_assignments
                    if candidate_key != cell_key
                    and candidate_key.partition(":")[0] == day_name
                    and not self.slot_is_unavailable(candidate_key)
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
        if self.saving or self._closed:
            return DraftMutation("blocked")
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
        if self.saving or self._closed:
            return False
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
        if self.saving or self._closed:
            return False
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
        if self.saving or self._closed or not self._undo:
            return False
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        return True

    def redo(self) -> bool:
        if self.saving or self._closed or not self._redo:
            return False
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        return True

    def discard(self) -> None:
        if self.saving:
            return
        self.pending_cells.clear()
        self.pending_days.clear()
        self.pending_slots.clear()
        self._undo.clear()
        self._redo.clear()
        self.command_id = None
        self.move_source = None
        self.selected_cell = None
        self.conflict = DraftConflictSnapshot()
        self._invalidate()

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

    def _invalidate(self) -> None:
        self.local_revision += 1
        self.candidate_cache.clear()
        self._save_command = None

    async def candidates(self, cell_key: str, *, source_key: str | None = None) -> list[dict[str, object]] | None:
        if self._closed or self.workflow is None:
            return None
        if source_key is None and cell_key in self.candidate_cache:
            return list(self.candidate_cache[cell_key])
        revision = self.local_revision
        task_key = (revision, cell_key, source_key)
        task = self._candidate_tasks.get(task_key)
        if task is None:
            cells, days, slots = self.patch_edits()
            async def read():
                async with self._candidate_gate:
                    if self._closed or revision != self.local_revision:
                        return None
                    return await asyncio.to_thread(
                        self.workflow.draft_cell_candidates, self.roster_week_id, cell_key,
                        cell_edits=cells, day_edits=days, slot_edits=slots, source_key=source_key,
                    )
            task = asyncio.create_task(read())
            self._candidate_tasks[task_key] = task
        try:
            result = await asyncio.shield(task)
        finally:
            if task.done():
                self._candidate_tasks.pop(task_key, None)
        if result is None or self._closed or revision != self.local_revision:
            return None
        rows = [dict(row) for row in result]
        self.candidate_names.update({str(row["id"]): str(row["nameZh"]) for row in rows})
        if source_key is None:
            self.candidate_cache[cell_key] = rows
        return list(rows)

    def prepare_save(self, reason: str | None = None) -> DraftPatchCommand:
        if self.saving or self._closed:
            raise WorkflowError("This editor cannot start another save.")
        normalized_reason = (reason or "").strip() or None
        if len(normalized_reason or "") > 1000:
            raise WorkflowError("Draft patch reason is too long.")
        if self._save_command is None or self._save_command.reason != normalized_reason:
            if self._save_command is not None:
                self.command_id = None
            targets = []
            for key in sorted(set(self.pending_cells) | set(self.pending_slots)):
                if self.slot_is_unavailable(key):
                    targets.append(DraftCellTarget(key, "unavailable"))
                else:
                    person = self.effective_assignment(key)
                    targets.append(DraftCellTarget(key, "assigned" if person else "vacant", person))
            self._save_command = DraftPatchCommand(
                self.roster_week_id, self.reviewed_version, self.ensure_command_id(),
                tuple(targets), tuple(DraftDayEdit(day, closed) for day, closed in sorted(self.pending_days.items())),
                normalized_reason,
            )
        self.saving = True
        return self._save_command

    def persist(self, command: DraftPatchCommand) -> DraftSaveOutcome:
        """Blocking storage seam; no editor state is touched on the IO thread."""
        if self.workflow is None:
            raise WorkflowError("The draft editor has no persistence adapter.")
        try:
            receipt = self.workflow.apply_draft_patch(**command.workflow_arguments())
        except CommittedWriteBackupError as error:
            # This typed error is raised only after the command receipt commits.
            # A read failure must not turn that known commit into a retryable edit.
            try:
                snapshot = self.workflow.roster_schedule_snapshot(self.roster_week_id)
            except Exception:
                snapshot = None
            raise DraftCommittedWithoutBackup(error, command, snapshot) from error
        try:
            snapshot = self.workflow.roster_schedule_snapshot(self.roster_week_id)
        except Exception:
            # The receipt already confirms persistence. A failed read is not a
            # failed write and must never leave that command pending for replay.
            snapshot = None
        return DraftSaveOutcome(receipt, snapshot)

    def finish_save(self, outcome: DraftSaveOutcome | None) -> None:
        self.saving = False
        if outcome is not None:
            self.last_saved_version = int(outcome.receipt.version)
            self._accept_committed_snapshot(outcome.snapshot, self.last_saved_version)

    def _accept_committed_snapshot(self, snapshot, saved_version: int) -> None:
        self.snapshot_refresh_failed = True
        try:
            if snapshot is not None and int(snapshot[0]["version"]) >= saved_version:
                self.accept_snapshot(snapshot)
                return
        except Exception:
            # Rendering malformed or concurrently changed data cannot undo the
            # verified commit. Require an explicit authoritative read instead.
            pass
        self.discard()
        self.snapshot_refresh_failed = True
        self.close()

    def finish_partial_save(self, error: DraftCommittedWithoutBackup) -> None:
        self.saving = False
        # Freeze before attempting any refresh. A committed command cannot be
        # made retryable by publication in another tab, a stale read, or even a
        # malformed snapshot obscuring the original backup-failure outcome.
        self.recovery_required = True
        self.last_saved_version = error.command.expected_week_version + 1
        self.close()
        self._accept_committed_snapshot(error.snapshot, self.last_saved_version)

    async def save(self, reason: str | None = None) -> DraftSaveOutcome:
        return await self.save_prepared(self.prepare_save(reason))

    async def save_prepared(self, command: DraftPatchCommand) -> DraftSaveOutcome:
        """Settle an already reviewed command after the UI write gate admits it."""
        if not self.saving or command is not self._save_command:
            raise WorkflowError("This command is not reserved by the draft editor.")
        task = asyncio.create_task(asyncio.to_thread(self.persist, command))
        try:
            outcome = await asyncio.shield(task)
        except DraftCommittedWithoutBackup as error:
            self.finish_partial_save(error)
            raise
        except asyncio.CancelledError:
            # A disconnected UI cannot cancel an already admitted transaction.
            # Keep the write claim until IO settles; never admit another save.
            def settled(completed):
                try:
                    self.finish_save(completed.result())
                except DraftCommittedWithoutBackup as error:
                    self.finish_partial_save(error)
                except Exception:
                    self.finish_save(None)
            task.add_done_callback(settled)
            raise
        except Exception:
            self.finish_save(None)
            raise
        self.finish_save(outcome)
        return outcome

    def accept_snapshot(self, snapshot, *, retain_intent: bool = False) -> None:
        week, rows = snapshot
        status = str(week["status"])
        if status not in {"draft", "published", "withdrawn"}:
            raise WorkflowError("The refreshed roster has an unknown status.")
        if status != "draft":
            self.close()
            self.roster_status = status
            if retain_intent:
                raise WorkflowConflictError("This roster is no longer an editable draft.")
        intent_cells, intent_days, intent_slots = self.patch_edits()
        presentation = build_roster_presentation(week, rows, closed_days=week.get("closedDays", ()), editable=status == "draft")
        cells = {cell.cell_key: cell for row in presentation.rows for cell in row.cells if cell.cell_key}
        self.original_assignments.clear()
        self.original_assignments.update({key: str(cell.prefect_id) if cell.prefect_id else None for key, cell in cells.items()})
        self.original_unavailable.clear()
        self.original_unavailable.update(key for key, cell in cells.items() if cell.state is RosterCellState.UNAVAILABLE)
        self.original_closed_days.clear()
        self.original_closed_days.update(item.day.name for item in presentation.days if item.state == "day_closed")
        self.reviewed_version = int(week["version"])
        self.roster_status = status
        self.snapshot_refresh_failed = False
        self.pending_cells.clear()
        self.pending_days.clear()
        self.pending_slots.clear()
        if retain_intent:
            for edit in intent_days:
                if edit.closed != (edit.day in self.original_closed_days):
                    self.pending_days[edit.day] = edit.closed
            for edit in intent_slots:
                unavailable = edit.state == "unavailable"
                if unavailable != (edit.cell_key in self.original_unavailable):
                    self.pending_slots[edit.cell_key] = unavailable
            for edit in intent_cells:
                self._stage_cell(edit.cell_key, edit.replacement_prefect_id)
        self._undo.clear()
        self._redo.clear()
        self.command_id = None
        self.move_source = None
        self.conflict = DraftConflictSnapshot()
        if status != "draft" or (self.selected_cell and self.day_is_closed(self.selected_cell.partition(":")[0])):
            self.selected_cell = None
        self._invalidate()

    def remember_latest(self, snapshot) -> None:
        self._latest_snapshot = snapshot

    @property
    def can_reapply_conflict(self) -> bool:
        return (
            not self.read_only and not self.saving
            and self._latest_snapshot is not None
            and self._latest_snapshot[0].get("status") == "draft"
        )

    def reapply_conflict(self) -> bool:
        if not self.can_reapply_conflict:
            return False
        self.accept_snapshot(self._latest_snapshot, retain_intent=True)
        self._latest_snapshot = None
        return True

    def close(self) -> None:
        self._closed = True
        self.candidate_cache.clear()
        for task in tuple(self._candidate_tasks.values()):
            task.cancel()
        self._candidate_tasks.clear()
