"""Transactional roster workflow: generate, save, publish, adjust, and audit."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from typing import Iterable
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from nicegui_app.config import DEFAULT_BACKUP_DIR, DEFAULT_DATABASE_PATH, POLICY_VERSION, PREFECT_SEED_PATH
from nicegui_app.persistence.database import create_session_factory
from nicegui_app.persistence.models import (
    AuditEventRecord,
    BackupRunRecord,
    FairnessLedgerRecord,
    LeaveAdjustmentRecord,
    LeaveDeclarationRecord,
    PrefectAvailabilityRecord,
    PrefectRecord,
    RosterAssignmentRecord,
    RosterWeekRecord,
)
from roster_core.generator import RosterGenerationError, generate_weekly_roster, validate_assignments
from roster_core.models import Assignment, Prefect
from roster_policy import DutyPost, SchoolDay, can_assign_role, required_posts_for_day


class WorkflowError(ValueError):
    """Raised when an operator action conflicts with roster workflow policy."""


class CommittedWriteBackupError(WorkflowError):
    """Raised when a durable write committed but its required snapshot failed.

    Callers must not present this as a rolled-back action or invite the
    operator to repeat it. The event code is controlled application metadata;
    raw filesystem details remain local to backup evidence and support logs.
    """

    def __init__(self, event_type: str, error_message: str | None = None) -> None:
        self.event_type = event_type
        self.error_message = error_message
        super().__init__(f"{event_type} committed, but automatic backup failed")


@dataclass(frozen=True)
class BackupResult:
    success: bool
    path: Path | None
    error_message: str | None = None


@dataclass(frozen=True)
class HandoverBackupPackage:
    """An in-memory, operator-downloadable copy of one verified snapshot."""

    filename: str
    content: bytes
    source_backup_path: Path


@dataclass(frozen=True)
class RosterWeekResult:
    id: int
    week_start: date
    status: str
    version: int
    assignment_count: int
    backup_path: Path


@dataclass(frozen=True)
class LeaveAdjustmentResult:
    roster_week_id: int
    assignment_id: int
    status: str
    backup_path: Path


@dataclass(frozen=True)
class DraftAssignmentUpdateResult:
    roster_week_id: int
    assignment_id: int
    version: int
    backup_path: Path


@dataclass(frozen=True)
class PrefectInput:
    """Validated identity and availability fields accepted from management pages."""

    name_zh: str
    form: str
    class_name: str
    role_code: str
    available_days: tuple[str, ...]
    name_en: str | None = None
    needs_mentoring: bool = False
    fixed_general_duty: str = "NONE"
    remarks: str = ""
    history_weight: float = 0.0
    history_duties: int = 0


ROLE_LABELS_FOR_CORE = {
    "assistant_head": "Assistant Head Study Prefect",
    "study_prefect": "Study Prefect",
}


class RosterWorkflow:
    """The only write path for persistent roster and fairness operations."""

    def __init__(
        self,
        *,
        database_path: Path = DEFAULT_DATABASE_PATH,
        backup_dir: Path = DEFAULT_BACKUP_DIR,
        seed_path: Path = PREFECT_SEED_PATH,
    ) -> None:
        self.database_path = database_path
        self.backup_dir = backup_dir
        self.seed_path = seed_path
        self.sessions: sessionmaker[Session] | None = None

    def bootstrap(self) -> None:
        self.sessions = create_session_factory(self.database_path)
        with self._session() as session:
            if session.scalar(select(func.count()).select_from(PrefectRecord)) == 0:
                self._seed_prefects(session)
                self._audit(session, "prefects_seeded", None, {"source": str(self.seed_path)})
                session.commit()

    def validate_week_start(self, week_start: date) -> None:
        """Expose the Monday-based workflow boundary without duplicating it in the UI."""
        self._require_monday(week_start)

    def generate_and_save_draft(self, week_start: date) -> RosterWeekResult:
        self._require_monday(week_start)
        with self._session() as session:
            prefects = self._active_prefects(session)
            leave_days = self._leave_days_for_week(session, week_start)
            try:
                assignments = generate_weekly_roster(prefects, leave_days=leave_days)
            except RosterGenerationError as error:
                raise WorkflowError(f"Draft generation needs attention: {error}") from error
            week = session.scalar(select(RosterWeekRecord).where(RosterWeekRecord.week_start == week_start))
            now = self._now()
            if week is None:
                week = RosterWeekRecord(
                    week_start=week_start,
                    status="draft",
                    version=1,
                    policy_version=POLICY_VERSION,
                    generated_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(week)
                session.flush()
            elif week.status == "published":
                raise WorkflowError("This roster is already published; use a post-publication adjustment instead.")
            else:
                week.version += 1
                week.generated_at = now
                week.updated_at = now
                session.execute(delete(RosterAssignmentRecord).where(RosterAssignmentRecord.roster_week_id == week.id))
                session.flush()

            self._store_assignments(session, week.id, assignments, prefects)
            self._audit(
                session,
                "draft_generated",
                week.id,
                {
                    "assignmentCount": len(assignments),
                    "leaveDeclarationCount": sum(len(days) for days in leave_days.values()),
                    "version": week.version,
                },
            )
            session.commit()
            result = RosterWeekResult(
                id=week.id,
                week_start=week.week_start,
                status=week.status,
                version=week.version,
                assignment_count=len(assignments),
                backup_path=Path(),
            )
        backup = self._create_and_record_backup("draft_generated", result.id)
        return RosterWeekResult(
            **{**result.__dict__, "backup_path": self._require_backup(backup, committed_event="draft_generated")}
        )

    def publish(self, roster_week_id: int) -> RosterWeekResult:
        with self._session() as session:
            now = self._now()
            claim = session.execute(
                update(RosterWeekRecord)
                .where(
                    RosterWeekRecord.id == roster_week_id,
                    RosterWeekRecord.status == "draft",
                )
                .values(status="published", published_at=now, updated_at=now)
            )
            if claim.rowcount != 1:
                if session.get(RosterWeekRecord, roster_week_id) is None:
                    raise WorkflowError("Roster week was not found.")
                raise WorkflowError("This roster is already published.")

            # Claiming the draft before reading assignments makes publication a
            # database-level single-winner operation. Any later validation
            # error rolls this transaction back to the draft state.
            week = self._week_or_error(session, roster_week_id)
            assignment_rows = self._assignment_rows(session, week.id)
            self._validate_persisted_assignments(session, assignment_rows, week_start=week.week_start)
            for row in assignment_rows:
                if row.prefect_id is None or row.status != "active":
                    raise WorkflowError("A roster with a vacancy cannot be published.")
                prefect = session.get(PrefectRecord, row.prefect_id)
                if prefect is None:
                    raise WorkflowError("An assigned prefect no longer exists.")
                prefect.history_weight = round(prefect.history_weight + row.weight, 4)
                prefect.history_duties += 1
                prefect.updated_at = now
                session.add(
                    FairnessLedgerRecord(
                        prefect_id=prefect.id,
                        roster_week_id=week.id,
                        assignment_id=row.id,
                        delta=row.weight,
                        event_type="roster_published",
                        reason="Weekly roster published",
                        created_at=now,
                    )
                )
            self._audit(session, "roster_published", week.id, {"assignmentCount": len(assignment_rows), "version": week.version})
            session.commit()
            result = RosterWeekResult(
                id=week.id,
                week_start=week.week_start,
                status=week.status,
                version=week.version,
                assignment_count=len(assignment_rows),
                backup_path=Path(),
            )
        backup = self._create_and_record_backup("roster_published", result.id)
        return RosterWeekResult(
            **{**result.__dict__, "backup_path": self._require_backup(backup, committed_event="roster_published")}
        )

    def recommend_substitutes(self, roster_week_id: int, assignment_id: int) -> list[dict[str, object]]:
        """Return only currently eligible substitutes for a published-duty absence.

        This deliberately shares the same leave, availability, duplicate-day,
        consecutive-duty, and role gates as a manual draft change.  A recorded
        pre-generation absence remains a real absence after publication; it
        cannot be bypassed by the later adjustment screen.
        """
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "published":
                raise WorkflowError("Substitute recommendations are available only for a published roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            return self._eligible_assignment_candidates(session, week, assignment)

    def draft_assignment_candidates(self, roster_week_id: int, assignment_id: int) -> list[dict[str, object]]:
        """Offer only rule-compliant replacements while a roster is still a draft."""
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "draft":
                raise WorkflowError("Manual assignment changes are available only for a draft roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            return self._eligible_assignment_candidates(session, week, assignment)

    def update_draft_assignment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str,
        reason: str,
    ) -> DraftAssignmentUpdateResult:
        """Apply an auditable, policy-validated manual draft change without posting fairness weight."""
        if not reason.strip():
            raise WorkflowError("A manual draft change requires a reason.")
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "draft":
                raise WorkflowError("Only a draft roster can be changed manually.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            candidates = {candidate["id"] for candidate in self._eligible_assignment_candidates(session, week, assignment)}
            if replacement_prefect_id not in candidates:
                raise WorkflowError("The selected prefect does not meet the current roster rules for this post.")
            if assignment.prefect_id == replacement_prefect_id:
                raise WorkflowError("Choose a different prefect or cancel this manual change.")
            replacement = session.get(PrefectRecord, replacement_prefect_id)
            if replacement is None:
                raise WorkflowError("The selected prefect no longer exists.")
            original_prefect_id = assignment.prefect_id
            original_name = assignment.prefect_name_snapshot
            assignment.prefect_id = replacement.id
            assignment.prefect_name_snapshot = replacement.name_zh
            assignment.prefect_role_snapshot = replacement.role_code
            assignment.status = "active"
            self._validate_persisted_assignments(session, self._assignment_rows(session, week.id), week_start=week.week_start)
            week.version += 1
            week.updated_at = self._now()
            self._audit(
                session,
                "draft_assignment_changed",
                week.id,
                {
                    "assignmentId": assignment.id,
                    "fromPrefectId": original_prefect_id,
                    "fromPrefectName": original_name,
                    "toPrefectId": replacement.id,
                    "toPrefectName": replacement.name_zh,
                    "reason": reason.strip(),
                    "version": week.version,
                },
            )
            session.commit()
            result = DraftAssignmentUpdateResult(week.id, assignment.id, week.version, Path())
        backup = self._create_and_record_backup("draft_assignment_changed", roster_week_id)
        return DraftAssignmentUpdateResult(
            **{
                **result.__dict__,
                "backup_path": self._require_backup(backup, committed_event="draft_assignment_changed"),
            }
        )

    def apply_leave_adjustment(
        self,
        *,
        roster_week_id: int,
        assignment_id: int,
        replacement_prefect_id: str | None,
        reason: str,
    ) -> LeaveAdjustmentResult:
        if not reason.strip():
            raise WorkflowError("A leave adjustment requires a reason.")
        with self._session() as session:
            week = self._week_or_error(session, roster_week_id)
            if week.status != "published":
                raise WorkflowError("Post-publication adjustments require a published roster.")
            assignment = self._assignment_or_error(session, roster_week_id, assignment_id)
            if assignment.status != "active" or assignment.prefect_id is None:
                raise WorkflowError("This assignment is no longer active.")
            original = session.get(PrefectRecord, assignment.prefect_id)
            if original is None:
                raise WorkflowError("The original prefect no longer exists.")
            candidates = {candidate["id"] for candidate in self._eligible_assignment_candidates(session, week, assignment)}
            replacement = None
            if replacement_prefect_id:
                if replacement_prefect_id not in candidates:
                    raise WorkflowError("The selected substitute no longer meets roster rules.")
                replacement = session.get(PrefectRecord, replacement_prefect_id)
                if replacement is None:
                    raise WorkflowError("The selected substitute no longer exists.")

            now = self._now()
            original_name = assignment.prefect_name_snapshot
            original_id = assignment.prefect_id
            original.history_weight = round(original.history_weight - assignment.weight, 4)
            original.history_duties = max(0, original.history_duties - 1)
            original.updated_at = now
            session.add(
                FairnessLedgerRecord(
                    prefect_id=original.id,
                    roster_week_id=week.id,
                    assignment_id=assignment.id,
                    delta=-assignment.weight,
                    event_type="leave_adjustment_debit",
                    reason=reason,
                    created_at=now,
                )
            )

            status = "vacant"
            replacement_name = None
            if replacement is not None:
                replacement.history_weight = round(replacement.history_weight + assignment.weight, 4)
                replacement.history_duties += 1
                replacement.updated_at = now
                assignment.prefect_id = replacement.id
                assignment.prefect_name_snapshot = replacement.name_zh
                assignment.prefect_role_snapshot = replacement.role_code
                replacement_name = replacement.name_zh
                status = "replaced"
                session.add(
                    FairnessLedgerRecord(
                        prefect_id=replacement.id,
                        roster_week_id=week.id,
                        assignment_id=assignment.id,
                        delta=assignment.weight,
                        event_type="leave_adjustment_credit",
                        reason=reason,
                        created_at=now,
                    )
                )
            else:
                assignment.prefect_id = None
                assignment.prefect_name_snapshot = "VACANT"
                assignment.prefect_role_snapshot = None
                assignment.status = "vacant"

            session.add(
                LeaveAdjustmentRecord(
                    roster_week_id=week.id,
                    assignment_id=assignment.id,
                    original_prefect_id=original_id,
                    original_prefect_name=original_name,
                    replacement_prefect_id=replacement.id if replacement else None,
                    replacement_prefect_name=replacement_name,
                    reason=reason.strip(),
                    status=status,
                    created_at=now,
                )
            )
            week.version += 1
            week.updated_at = now
            self._audit(session, "leave_adjusted", week.id, {"assignmentId": assignment.id, "status": status})
            session.commit()
        backup = self._create_and_record_backup("leave_adjusted", roster_week_id)
        return LeaveAdjustmentResult(
            roster_week_id,
            assignment_id,
            status,
            self._require_backup(backup, committed_event="leave_adjusted"),
        )

    def roster_weeks(self) -> list[dict[str, object]]:
        with self._session() as session:
            rows = session.scalars(select(RosterWeekRecord).order_by(RosterWeekRecord.week_start.desc())).all()
            return [
                {
                    "id": row.id,
                    "weekStart": row.week_start,
                    "status": row.status,
                    "version": row.version,
                    "generatedAt": row.generated_at,
                    "publishedAt": row.published_at,
                }
                for row in rows
            ]

    def roster_week(self, roster_week_id: int) -> dict[str, object]:
        with self._session() as session:
            row = self._week_or_error(session, roster_week_id)
            return {
                "id": row.id,
                "weekStart": row.week_start,
                "status": row.status,
                "version": row.version,
                "generatedAt": row.generated_at,
                "publishedAt": row.published_at,
            }

    def assignments(self, roster_week_id: int) -> list[dict[str, object]]:
        with self._session() as session:
            # Keep "not found" distinct from a real roster with no assignments.
            # Route recovery, exports, and operator diagnostics all depend on this
            # read boundary reporting a stale roster identifier consistently.
            self._week_or_error(session, roster_week_id)
            rows = self._assignment_rows(session, roster_week_id)
            return [
                {
                    "id": row.id,
                    "day": row.day,
                    "postCode": row.post_code,
                    "slotIndex": row.slot_index,
                    "prefectId": row.prefect_id,
                    "prefectName": row.prefect_name_snapshot,
                    "weight": row.weight,
                    "status": row.status,
                }
                for row in rows
            ]

    def prefect_loads(self) -> dict[str, float]:
        with self._session() as session:
            rows = self._active_prefect_records(session)
            return {row.id: row.history_weight for row in rows}

    def prefects(self) -> list[dict[str, object]]:
        with self._session() as session:
            availability = self._availability_by_prefect(session)
            return [
                {
                    "id": row.id,
                    "nameZh": row.name_zh,
                    "nameEn": row.name_en,
                    "form": row.form,
                    "className": row.class_name,
                    "roleCode": row.role_code,
                    "historyWeight": row.history_weight,
                    "historyDuties": row.history_duties,
                    "availableDays": [day.name for day in sorted(availability.get(row.id, set()))],
                    "needsMentoring": row.needs_mentoring,
                }
                for row in self._active_prefect_records(session)
            ]

    def prefect(self, prefect_id: str) -> dict[str, object]:
        with self._session() as session:
            record = session.get(PrefectRecord, prefect_id)
            if record is None:
                raise WorkflowError("Prefect was not found.")
            return self._prefect_output(session, record)

    def create_prefect(self, prefect_input: PrefectInput) -> dict[str, object]:
        self._validate_prefect_input(prefect_input)
        with self._session() as session:
            self._assert_name_available(session, prefect_input.name_zh)
            record = self._new_prefect_record(prefect_input)
            session.add(record)
            session.flush()
            self._replace_availability(session, record.id, prefect_input.available_days)
            self._audit(session, "prefect_created", None, {"prefectId": record.id})
            output = self._prefect_output(session, record)
            session.commit()
        backup = self._create_and_record_backup("prefect_created", None)
        self._require_backup(backup, committed_event="prefect_created")
        return output

    def update_prefect(self, prefect_id: str, prefect_input: PrefectInput) -> dict[str, object]:
        self._validate_prefect_input(prefect_input)
        with self._session() as session:
            record = session.get(PrefectRecord, prefect_id)
            if record is None:
                raise WorkflowError("Prefect was not found.")
            self._assert_name_available(session, prefect_input.name_zh, exclude_prefect_id=prefect_id)
            record.name_zh = prefect_input.name_zh.strip()
            record.name_en = prefect_input.name_en.strip() if prefect_input.name_en else None
            record.form = prefect_input.form
            record.class_name = prefect_input.class_name.strip()
            record.role_code = prefect_input.role_code
            record.needs_mentoring = prefect_input.needs_mentoring
            record.fixed_general_duty = prefect_input.fixed_general_duty
            record.remarks = prefect_input.remarks.strip()
            record.updated_at = self._now()
            self._replace_availability(session, record.id, prefect_input.available_days)
            self._audit(session, "prefect_updated", None, {"prefectId": record.id})
            output = self._prefect_output(session, record)
            session.commit()
        backup = self._create_and_record_backup("prefect_updated", None)
        self._require_backup(backup, committed_event="prefect_updated")
        return output

    def archive_prefect(self, prefect_id: str) -> None:
        with self._session() as session:
            record = session.get(PrefectRecord, prefect_id)
            if record is None:
                raise WorkflowError("Prefect was not found.")
            if not record.active:
                raise WorkflowError("Prefect is already archived.")
            record.active = False
            record.updated_at = self._now()
            self._audit(session, "prefect_archived", None, {"prefectId": record.id})
            session.commit()
        backup = self._create_and_record_backup("prefect_archived", None)
        self._require_backup(backup, committed_event="prefect_archived")

    def import_prefects(self, prefect_inputs: Iterable[PrefectInput]) -> list[dict[str, object]]:
        inputs = list(prefect_inputs)
        if not inputs:
            raise WorkflowError("Import contains no prefects.")
        for prefect_input in inputs:
            self._validate_prefect_input(prefect_input)
        normalized_names = [prefect_input.name_zh.strip() for prefect_input in inputs]
        if len(normalized_names) != len(set(normalized_names)):
            raise WorkflowError("Import contains duplicate Chinese names.")
        with self._session() as session:
            for name in normalized_names:
                self._assert_name_available(session, name)
            records: list[PrefectRecord] = []
            for prefect_input in inputs:
                record = self._new_prefect_record(prefect_input)
                session.add(record)
                session.flush()
                self._replace_availability(session, record.id, prefect_input.available_days)
                records.append(record)
            self._audit(session, "prefects_imported", None, {"count": len(records)})
            outputs = [self._prefect_output(session, record) for record in records]
            session.commit()
        backup = self._create_and_record_backup("prefects_imported", None)
        self._require_backup(backup, committed_event="prefects_imported")
        return outputs

    def leave_adjustment_count(self, roster_week_id: int) -> int:
        with self._session() as session:
            return int(
                session.scalar(
                    select(func.count()).select_from(LeaveAdjustmentRecord).where(LeaveAdjustmentRecord.roster_week_id == roster_week_id)
                )
                or 0
            )

    def declare_leave(
        self,
        *,
        week_start: date,
        prefect_id: str,
        day: str,
        reason: str,
    ) -> dict[str, object]:
        """Record a pre-generation absence without changing published fairness history."""
        self._require_monday(week_start)
        if not reason.strip():
            raise WorkflowError("A leave declaration requires a reason.")
        try:
            school_day = SchoolDay[day]
        except KeyError as error:
            raise WorkflowError("Leave declaration contains an invalid weekday.") from error

        with self._session() as session:
            prefect = session.get(PrefectRecord, prefect_id)
            if prefect is None or not prefect.active:
                raise WorkflowError("The selected prefect is not active.")
            existing_week = session.scalar(select(RosterWeekRecord).where(RosterWeekRecord.week_start == week_start))
            if existing_week is not None and existing_week.status == "published":
                raise WorkflowError("A published roster must use a post-publication leave adjustment.")

            declaration = session.scalar(
                select(LeaveDeclarationRecord).where(
                    LeaveDeclarationRecord.week_start == week_start,
                    LeaveDeclarationRecord.prefect_id == prefect_id,
                    LeaveDeclarationRecord.day == school_day.name,
                )
            )
            now = self._now()
            if declaration is None:
                declaration = LeaveDeclarationRecord(
                    week_start=week_start,
                    prefect_id=prefect_id,
                    day=school_day.name,
                    reason=reason.strip(),
                    active=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(declaration)
            else:
                declaration.reason = reason.strip()
                declaration.active = True
                declaration.updated_at = now
            session.flush()
            self._audit(
                session,
                "pre_generation_leave_declared",
                existing_week.id if existing_week else None,
                {"prefectId": prefect_id, "weekStart": week_start.isoformat(), "day": school_day.name},
            )
            output = self._leave_declaration_output(declaration, prefect)
            session.commit()
        backup = self._create_and_record_backup("pre_generation_leave_declared", existing_week.id if existing_week else None)
        self._require_backup(backup, committed_event="pre_generation_leave_declared")
        return output

    def cancel_pre_generation_leave(self, leave_declaration_id: int) -> None:
        with self._session() as session:
            declaration = session.get(LeaveDeclarationRecord, leave_declaration_id)
            if declaration is None or not declaration.active:
                raise WorkflowError("The leave declaration was not found.")
            week = session.scalar(select(RosterWeekRecord).where(RosterWeekRecord.week_start == declaration.week_start))
            if week is not None and week.status == "published":
                raise WorkflowError("A published roster must use a post-publication leave adjustment.")
            declaration.active = False
            declaration.updated_at = self._now()
            self._audit(
                session,
                "pre_generation_leave_cancelled",
                week.id if week else None,
                {"leaveDeclarationId": declaration.id},
            )
            session.commit()
        backup = self._create_and_record_backup("pre_generation_leave_cancelled", week.id if week else None)
        self._require_backup(backup, committed_event="pre_generation_leave_cancelled")

    def pre_generation_leaves(self, week_start: date) -> list[dict[str, object]]:
        self._require_monday(week_start)
        with self._session() as session:
            records = session.execute(
                select(LeaveDeclarationRecord, PrefectRecord)
                .join(PrefectRecord, PrefectRecord.id == LeaveDeclarationRecord.prefect_id)
                .where(
                    LeaveDeclarationRecord.week_start == week_start,
                    LeaveDeclarationRecord.active.is_(True),
                )
                .order_by(LeaveDeclarationRecord.day, PrefectRecord.name_zh)
            ).all()
            return [self._leave_declaration_output(declaration, prefect) for declaration, prefect in records]

    def fairness_rows(self) -> list[dict[str, object]]:
        with self._session() as session:
            rows = sorted(self._active_prefect_records(session), key=lambda row: (row.history_weight, row.name_zh))
            return [
                {
                    "id": row.id,
                    "nameZh": row.name_zh,
                    "form": row.form,
                    "className": row.class_name,
                    "historyWeight": row.history_weight,
                    "historyDuties": row.history_duties,
                }
                for row in rows
            ]

    def generation_requirements(self, week_start: date) -> list[dict[str, object]]:
        """Expose every required weekly slot and its currently eligible pool before generation."""
        self._require_monday(week_start)
        with self._session() as session:
            availability = self._availability_by_prefect(session)
            leave_days = self._leave_days_for_week(session, week_start)
            prefects = self._active_prefect_records(session)
            requirements: list[dict[str, object]] = []
            for day in SchoolDay:
                slot_counts: dict[DutyPost, int] = defaultdict(int)
                for post in required_posts_for_day(day):
                    slot_counts[post] += 1
                    candidates = [
                        prefect
                        for prefect in prefects
                        if day in availability.get(prefect.id, set())
                        and day not in leave_days.get(prefect.id, set())
                        and can_assign_role(self._core_role(prefect.role_code), post)
                    ]
                    requirements.append(
                        {
                            "day": day.name,
                            "postCode": post.name,
                            "slotIndex": slot_counts[post],
                            "eligibleCount": len(candidates),
                            "hasVacancyRisk": not candidates,
                        }
                    )
            return requirements

    def handover_readiness(self) -> dict[str, object]:
        """Return non-sensitive, practical checks for a successor's local handover."""
        with self._session() as session:
            prefect_count = session.scalar(
                select(func.count()).select_from(PrefectRecord).where(PrefectRecord.active.is_(True))
            ) or 0
            roster_count = session.scalar(select(func.count()).select_from(RosterWeekRecord)) or 0
        backup = self.backup_status()
        latest_verification = backup["latestVerification"] or {}
        return {
            "activePrefectCount": prefect_count,
            "rosterCount": roster_count,
            "verifiedBackup": bool(latest_verification.get("valid")),
            "backupPath": backup["latestPath"],
        }

    def backup_status(self) -> dict[str, object]:
        with self._session() as session:
            latest = session.scalar(select(BackupRunRecord).order_by(BackupRunRecord.created_at.desc()))
            latest_path = Path(latest.backup_path) if latest and latest.backup_path else None
            return {
                "databasePath": self.database_path,
                "backupDirectory": self.backup_dir,
                "latestSuccess": latest.success if latest else None,
                "latestPath": latest_path,
                "latestCreatedAt": latest.created_at if latest else None,
                "latestVerification": self.verify_backup(latest_path) if latest_path else None,
            }

    def verify_backup(self, backup_path: Path) -> dict[str, object]:
        """Validate a snapshot without mutating the live database."""
        required_tables = {
            "alembic_version",
            "prefects",
            "roster_weeks",
            "roster_assignments",
            "fairness_ledger",
            "backup_runs",
        }
        if not backup_path.exists() or not backup_path.is_file():
            return {"valid": False, "reasonCode": "missing_file", "error": "Backup file was not found."}
        if backup_path.suffix != ".sqlite3":
            return {"valid": False, "reasonCode": "invalid_extension", "error": "Backup file must use the .sqlite3 extension."}

        try:
            connection = sqlite3.connect(f"file:{backup_path.resolve().as_posix()}?mode=ro", uri=True)
            try:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                table_rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            finally:
                connection.close()
        except sqlite3.Error as error:
            return {"valid": False, "reasonCode": "sqlite_unreadable", "error": f"SQLite could not open the backup: {error}"}

        table_names = {row[0] for row in table_rows}
        missing_tables = sorted(required_tables - table_names)
        try:
            checksum = self._sha256(backup_path)
        except OSError as error:
            return {
                "valid": False,
                "reasonCode": "missing_file",
                "integrity": integrity,
                "error": f"Backup file could not be read for checksum verification: {error}",
            }
        manifest_path = backup_path.with_suffix(".manifest.json")
        if not manifest_path.exists() or not manifest_path.is_file():
            return {
                "valid": False,
                "reasonCode": "manifest_missing",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup is missing its checksum manifest.",
            }
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return {
                "valid": False,
                "reasonCode": "manifest_unreadable",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup manifest could not be read: {error}",
            }
        manifest_checksum = manifest.get("sha256")
        if not isinstance(manifest_checksum, str) or manifest_checksum != checksum:
            return {
                "valid": False,
                "reasonCode": "checksum_mismatch",
                "integrity": integrity,
                "sha256": checksum,
                "error": "Backup checksum does not match its manifest.",
            }
        if integrity != "ok":
            return {
                "valid": False,
                "reasonCode": "integrity_failed",
                "integrity": integrity,
                "sha256": checksum,
                "error": "SQLite integrity check failed.",
            }
        if missing_tables:
            return {
                "valid": False,
                "reasonCode": "schema_incomplete",
                "integrity": integrity,
                "sha256": checksum,
                "error": f"Backup is missing required tables: {', '.join(missing_tables)}.",
            }
        return {
            "valid": True,
            "reasonCode": "verified",
            "integrity": integrity,
            "sha256": checksum,
            "tableCount": len(table_names),
        }

    def restore_backup(self, backup_path: Path) -> dict[str, object]:
        """Restore a managed, verified snapshot with a safety snapshot of live data first."""
        managed_directory = self.backup_dir.resolve()
        requested_path = backup_path.resolve()
        try:
            requested_path.relative_to(managed_directory)
        except ValueError as error:
            raise WorkflowError("Only snapshots in the managed backup directory can be restored.") from error

        verification = self.verify_backup(requested_path)
        if not verification.get("valid"):
            raise WorkflowError(f"Backup verification failed: {verification.get('error', 'unknown error')}")

        pre_restore = self._create_and_record_backup("pre_restore", None)
        pre_restore_path = self._require_backup(pre_restore)
        temporary_path = self.database_path.with_name(f"{self.database_path.name}.restore.tmp")
        try:
            self._dispose_database_connections()
            if temporary_path.exists():
                temporary_path.unlink()
            source = sqlite3.connect(str(requested_path))
            destination = sqlite3.connect(str(temporary_path))
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            for stale_sidecar in (Path(f"{self.database_path}-wal"), Path(f"{self.database_path}-shm")):
                stale_sidecar.unlink(missing_ok=True)
            temporary_path.replace(self.database_path)
            self.sessions = create_session_factory(self.database_path)
        except Exception as error:
            temporary_path.unlink(missing_ok=True)
            self.sessions = create_session_factory(self.database_path)
            raise WorkflowError(f"Backup restore could not be completed: {error}") from error

        with self._session() as session:
            self._audit(
                session,
                "backup_restored",
                None,
                {
                    "restoredFrom": str(requested_path),
                    "preRestoreBackup": str(pre_restore_path),
                    "sha256": verification["sha256"],
                },
            )
            session.commit()
        restored_backup = self._create_and_record_backup("backup_restored", None)
        return {
            "restoredFrom": backup_path,
            "preRestoreBackup": pre_restore_path,
            "restoredBackup": self._require_backup(restored_backup, committed_event="backup_restored"),
        }

    def backups(self, limit: int = 12) -> list[dict[str, object]]:
        """List recent managed snapshots with current verification evidence."""
        if limit < 1:
            return []
        candidates: list[tuple[Path, float]] = []
        for path in self.backup_dir.glob("*.sqlite3"):
            try:
                modified_at = path.stat().st_mtime
            except OSError:
                continue
            candidates.append((path, modified_at))
        candidates.sort(key=lambda item: item[1], reverse=True)
        selected = candidates[:limit]
        if not selected:
            return []
        with ThreadPoolExecutor(max_workers=min(4, len(selected)), thread_name_prefix="backup-verify") as executor:
            verifications = list(executor.map(self.verify_backup, (path for path, _modified_at in selected)))
        return [
            {
                "path": path,
                "createdAt": datetime.fromtimestamp(modified_at),
                "verification": verification,
            }
            for (path, modified_at), verification in zip(selected, verifications, strict=True)
        ]

    def backup_inventory(self, limit: int = 12) -> dict[str, object]:
        """Summarize recent snapshot trust without exposing raw verification errors."""
        items = self.backups(limit=limit)
        reason_counts: dict[str, int] = defaultdict(int)
        verified_count = 0
        for item in items:
            verification = item["verification"]
            if not isinstance(verification, dict):
                reason_counts["unknown"] += 1
                continue
            if verification.get("valid"):
                verified_count += 1
                continue
            reason_code = str(verification.get("reasonCode") or "unknown")
            reason_counts[reason_code] += 1
        return {
            "items": items,
            "checkedCount": len(items),
            "verifiedCount": verified_count,
            "invalidCount": len(items) - verified_count,
            "invalidReasonCounts": dict(sorted(reason_counts.items())),
        }

    def create_verified_backup(self) -> Path:
        """Create an operator-requested recovery snapshot without changing roster data."""
        backup = self._create_and_record_backup("manual_verified_backup", None)
        return self._require_backup(backup)

    def build_verified_handover_package(self) -> HandoverBackupPackage:
        """Package the latest verified managed snapshot for an operator-controlled handover copy."""
        latest = next((item for item in self.backups(limit=10_000) if item["verification"].get("valid")), None)
        if latest is None:
            raise WorkflowError("No verified backup is available for a handover package.")
        source_backup_path = Path(latest["path"])
        verification = self.verify_backup(source_backup_path)
        if not verification.get("valid"):
            raise WorkflowError(f"Backup verification failed: {verification.get('error', 'unknown error')}")
        manifest_path = source_backup_path.with_suffix(".manifest.json")
        package = BytesIO()
        with ZipFile(package, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.write(source_backup_path, arcname=source_backup_path.name)
            archive.write(manifest_path, arcname=manifest_path.name)
            archive.writestr("README.txt", self._handover_package_readme(source_backup_path.name))
        stamp = self._now().strftime("%Y%m%d-%H%M")
        return HandoverBackupPackage(
            filename=f"SYSS_Handover_Backup_{stamp}.zip",
            content=package.getvalue(),
            source_backup_path=source_backup_path,
        )

    def _seed_prefects(self, session: Session) -> None:
        raw_data = json.loads(self.seed_path.read_text(encoding="utf-8"))
        now = self._now()
        for raw in raw_data["prefects"]:
            role_code = "assistant_head" if "Assistant Head Study Prefect" in raw["role"] else "study_prefect"
            record = PrefectRecord(
                id=raw["id"],
                name_zh=raw["name"],
                form=raw["form"],
                class_name=raw["class"],
                role_code=role_code,
                history_weight=float(raw.get("historyWeight", 0)),
                history_duties=int(raw.get("historyDuties", 0)),
                needs_mentoring=bool(raw.get("needsMentoring", False)),
                fixed_general_duty=raw.get("fixedGeneralDuty", "NONE"),
                remarks=raw.get("remarks", ""),
                active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            session.flush()
            for day in raw.get("availableDays", []):
                session.add(PrefectAvailabilityRecord(prefect_id=record.id, day=day))

    def _new_prefect_record(self, prefect_input: PrefectInput) -> PrefectRecord:
        now = self._now()
        return PrefectRecord(
            id=f"prefect-{uuid4().hex[:12]}",
            name_zh=prefect_input.name_zh.strip(),
            name_en=prefect_input.name_en.strip() if prefect_input.name_en else None,
            form=prefect_input.form,
            class_name=prefect_input.class_name.strip(),
            role_code=prefect_input.role_code,
            history_weight=prefect_input.history_weight,
            history_duties=prefect_input.history_duties,
            needs_mentoring=prefect_input.needs_mentoring,
            fixed_general_duty=prefect_input.fixed_general_duty,
            remarks=prefect_input.remarks.strip(),
            active=True,
            created_at=now,
            updated_at=now,
        )

    def _replace_availability(self, session: Session, prefect_id: str, available_days: Iterable[str]) -> None:
        session.execute(delete(PrefectAvailabilityRecord).where(PrefectAvailabilityRecord.prefect_id == prefect_id))
        session.flush()
        for day in available_days:
            session.add(PrefectAvailabilityRecord(prefect_id=prefect_id, day=day))
        session.flush()

    def _assert_name_available(self, session: Session, name_zh: str, *, exclude_prefect_id: str | None = None) -> None:
        statement = select(PrefectRecord).where(PrefectRecord.name_zh == name_zh.strip())
        existing = session.scalar(statement)
        if existing is not None and existing.id != exclude_prefect_id:
            raise WorkflowError("A prefect with this Chinese name already exists.")

    def _prefect_output(self, session: Session, record: PrefectRecord) -> dict[str, object]:
        days = session.scalars(
            select(PrefectAvailabilityRecord.day).where(PrefectAvailabilityRecord.prefect_id == record.id)
        ).all()
        return {
            "id": record.id,
            "nameZh": record.name_zh,
            "nameEn": record.name_en,
            "form": record.form,
            "className": record.class_name,
            "roleCode": record.role_code,
            "historyWeight": record.history_weight,
            "historyDuties": record.history_duties,
            "availableDays": sorted(days, key=lambda day: int(SchoolDay[day])),
            "needsMentoring": record.needs_mentoring,
            "fixedGeneralDuty": record.fixed_general_duty,
            "remarks": record.remarks,
            "active": record.active,
        }

    @staticmethod
    def _validate_prefect_input(prefect_input: PrefectInput) -> None:
        if not prefect_input.name_zh.strip():
            raise WorkflowError("Chinese name is required.")
        if prefect_input.form not in {"F.3", "F.4", "F.5", "F.6"}:
            raise WorkflowError("Form must be F.3, F.4, F.5, or F.6.")
        if not prefect_input.class_name.strip():
            raise WorkflowError("Class is required.")
        if prefect_input.role_code not in ROLE_LABELS_FOR_CORE:
            raise WorkflowError("Role is not recognized.")
        if not prefect_input.available_days:
            raise WorkflowError("At least one available day is required.")
        if any(day not in SchoolDay.__members__ for day in prefect_input.available_days):
            raise WorkflowError("Availability contains an invalid weekday.")
        if len(set(prefect_input.available_days)) != len(prefect_input.available_days):
            raise WorkflowError("Availability contains duplicate weekdays.")
        if prefect_input.fixed_general_duty != "NONE" and prefect_input.fixed_general_duty not in SchoolDay.__members__:
            raise WorkflowError("Fixed duty contains an invalid weekday.")
        if prefect_input.history_weight < 0 or prefect_input.history_duties < 0:
            raise WorkflowError("History values cannot be negative.")

    def _store_assignments(self, session: Session, roster_week_id: int, assignments: Iterable[Assignment], prefects: list[Prefect]) -> None:
        role_by_id = {prefect.id: prefect.role for prefect in prefects}
        slot_counts: dict[tuple[str, str], int] = defaultdict(int)
        for assignment in assignments:
            key = (assignment.day.name, assignment.post.name)
            slot_counts[key] += 1
            session.add(
                RosterAssignmentRecord(
                    roster_week_id=roster_week_id,
                    day=assignment.day.name,
                    post_code=assignment.post.name,
                    slot_index=slot_counts[key],
                    prefect_id=assignment.prefect_id,
                    prefect_name_snapshot=assignment.prefect_name,
                    prefect_role_snapshot=self._role_code_from_core(role_by_id[assignment.prefect_id]),
                    weight=assignment.weight,
                    status="active",
                )
            )

    def _active_prefects(self, session: Session) -> list[Prefect]:
        availability = self._availability_by_prefect(session)
        return [
            Prefect(
                id=record.id,
                name=record.name_zh,
                form=record.form,
                class_name=record.class_name,
                role=self._core_role(record.role_code),
                available_days=frozenset(availability.get(record.id, set())),
                history_weight=record.history_weight,
                history_duties=record.history_duties,
                needs_mentoring=record.needs_mentoring,
                fixed_general_duty=record.fixed_general_duty,
                remarks=record.remarks,
            )
            for record in self._active_prefect_records(session)
        ]

    def _active_prefect_records(self, session: Session) -> list[PrefectRecord]:
        return session.scalars(select(PrefectRecord).where(PrefectRecord.active.is_(True))).all()

    def _availability_by_prefect(self, session: Session) -> dict[str, set[SchoolDay]]:
        availability: dict[str, set[SchoolDay]] = defaultdict(set)
        for record in session.scalars(select(PrefectAvailabilityRecord)).all():
            availability[record.prefect_id].add(SchoolDay[record.day])
        return availability

    def _leave_days_for_week(self, session: Session, week_start: date) -> dict[str, set[SchoolDay]]:
        leave_days: dict[str, set[SchoolDay]] = defaultdict(set)
        rows = session.scalars(
            select(LeaveDeclarationRecord).where(
                LeaveDeclarationRecord.week_start == week_start,
                LeaveDeclarationRecord.active.is_(True),
            )
        ).all()
        for row in rows:
            leave_days[row.prefect_id].add(SchoolDay[row.day])
        return leave_days

    @staticmethod
    def _leave_declaration_output(declaration: LeaveDeclarationRecord, prefect: PrefectRecord) -> dict[str, object]:
        return {
            "id": declaration.id,
            "weekStart": declaration.week_start,
            "prefectId": declaration.prefect_id,
            "prefectName": prefect.name_zh,
            "day": declaration.day,
            "reason": declaration.reason,
            "createdAt": declaration.created_at,
            "updatedAt": declaration.updated_at,
        }

    def _validate_persisted_assignments(
        self,
        session: Session,
        rows: list[RosterAssignmentRecord],
        *,
        week_start: date,
    ) -> None:
        prefects = self._active_prefects(session)
        domain_rows: list[Assignment] = []
        for row in rows:
            if row.prefect_id is None or row.status != "active":
                raise WorkflowError("A draft with missing assignments cannot be published.")
            domain_rows.append(
                Assignment(
                    day=SchoolDay[row.day],
                    post=DutyPost[row.post_code],
                    prefect_id=row.prefect_id,
                    prefect_name=row.prefect_name_snapshot,
                    weight=row.weight,
                )
            )
        validate_assignments(domain_rows, prefects, leave_days=self._leave_days_for_week(session, week_start))

    def _assignment_rows(self, session: Session, roster_week_id: int) -> list[RosterAssignmentRecord]:
        rows = session.scalars(
            select(RosterAssignmentRecord)
            .where(RosterAssignmentRecord.roster_week_id == roster_week_id)
        ).all()
        post_rank = {
            "ASSIST_IN_CHARGE": 0,
            "ROOM_302": 1,
            "ROOM_303": 2,
            "ROOM_202": 3,
        }
        return sorted(
            rows,
            key=lambda row: (int(SchoolDay[row.day]), post_rank[row.post_code], row.slot_index),
        )

    def _eligible_assignment_candidates(
        self,
        session: Session,
        week: RosterWeekRecord,
        assignment: RosterAssignmentRecord,
    ) -> list[dict[str, object]]:
        if assignment.status != "active" or assignment.prefect_id is None:
            raise WorkflowError("Only an active assignment can be changed manually.")
        day = SchoolDay[assignment.day]
        post = DutyPost[assignment.post_code]
        assigned_rows = self._assignment_rows(session, week.id)
        assigned_today = {
            row.prefect_id
            for row in assigned_rows
            if row.id != assignment.id and row.status == "active" and row.day == assignment.day and row.prefect_id
        }
        other_days: dict[str, set[SchoolDay]] = defaultdict(set)
        for row in assigned_rows:
            if row.id != assignment.id and row.status == "active" and row.prefect_id:
                other_days[row.prefect_id].add(SchoolDay[row.day])
        availability = self._availability_by_prefect(session)
        leave_days = self._leave_days_for_week(session, week.week_start)
        candidates = []
        for prefect in self._active_prefect_records(session):
            if prefect.id == assignment.prefect_id:
                continue
            if prefect.id in assigned_today:
                continue
            if day not in availability.get(prefect.id, set()):
                continue
            if day in leave_days.get(prefect.id, set()):
                continue
            if not can_assign_role(self._core_role(prefect.role_code), post):
                continue
            if any(abs(int(existing_day) - int(day)) == 1 for existing_day in other_days[prefect.id]):
                continue
            candidates.append(prefect)
        candidates.sort(key=lambda candidate: (candidate.history_weight, self._form_rank(candidate.form), candidate.history_duties, candidate.name_zh))
        return [
            {
                "id": candidate.id,
                "nameZh": candidate.name_zh,
                "form": candidate.form,
                "className": candidate.class_name,
                "historyWeight": candidate.history_weight,
            }
            for candidate in candidates
        ]

    def _week_or_error(self, session: Session, roster_week_id: int) -> RosterWeekRecord:
        week = session.get(RosterWeekRecord, roster_week_id)
        if week is None:
            raise WorkflowError("Roster week was not found.")
        return week

    def _assignment_or_error(self, session: Session, roster_week_id: int, assignment_id: int) -> RosterAssignmentRecord:
        assignment = session.get(RosterAssignmentRecord, assignment_id)
        if assignment is None or assignment.roster_week_id != roster_week_id:
            raise WorkflowError("Roster assignment was not found.")
        return assignment

    def _create_and_record_backup(self, event_type: str, roster_week_id: int | None) -> BackupResult:
        backup_path: Path | None = None
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = self._now().strftime("%Y%m%d-%H%M%S-%f")
            backup_path = self.backup_dir / f"{stamp}-{event_type}.sqlite3"
            temporary_path = backup_path.with_suffix(".sqlite3.tmp")
            source = sqlite3.connect(str(self.database_path))
            destination = sqlite3.connect(str(temporary_path))
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            temporary_path.replace(backup_path)
            manifest_path = backup_path.with_suffix(".manifest.json")
            manifest_path.write_text(
                json.dumps(
                    {
                        "eventType": event_type,
                        "rosterWeekId": roster_week_id,
                        "createdAt": self._now().isoformat(),
                        "database": self.database_path.name,
                        "sha256": self._sha256(backup_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            verification = self.verify_backup(backup_path)
            if not verification.get("valid"):
                result = BackupResult(
                    False,
                    backup_path,
                    f"Snapshot verification failed: {verification.get('error', 'unknown error')}",
                )
            else:
                result = BackupResult(True, backup_path)
        except Exception as error:  # pragma: no cover - exercised by filesystem failures
            result = BackupResult(False, backup_path if backup_path and backup_path.exists() else None, str(error))
        try:
            self._record_backup_result(event_type, roster_week_id, result)
        except Exception as error:  # pragma: no cover - forced through a deterministic test seam
            return BackupResult(
                False,
                result.path,
                f"Backup evidence recording failed: {type(error).__name__}",
            )
        return result

    def _record_backup_result(self, event_type: str, roster_week_id: int | None, result: BackupResult) -> None:
        """Persist snapshot evidence without allowing this secondary write to hide committed roster state."""
        with self._session() as session:
            session.add(
                BackupRunRecord(
                    event_type=event_type,
                    roster_week_id=roster_week_id,
                    backup_path=str(result.path) if result.path else None,
                    success=result.success,
                    error_message=result.error_message,
                    created_at=self._now(),
                )
            )
            session.commit()

    def _audit(self, session: Session, event_type: str, roster_week_id: int | None, metadata: dict[str, object]) -> None:
        session.add(
            AuditEventRecord(
                event_type=event_type,
                roster_week_id=roster_week_id,
                metadata_json=json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                occurred_at=self._now(),
            )
        )

    def _session(self):
        if self.sessions is None:
            raise RuntimeError("Call bootstrap() before using the roster workflow.")
        return self.sessions()

    def _dispose_database_connections(self) -> None:
        if self.sessions is None:
            return
        engine = self.sessions.kw.get("bind")
        if engine is not None:
            engine.dispose()

    @staticmethod
    def _handover_package_readme(snapshot_name: str) -> str:
        return (
            "Sing Yin Study Prefect Duty Roster System — verified handover backup\n"
            "\n"
            "此封包只供學校批准的加密離機保存及交接使用，內含一份已驗證 SQLite 快照及其 SHA-256 manifest。"
            "請勿電郵、公開上載或傳送至未經批准的平台。\n"
            "\n"
            "還原方法：把此封包解壓至受控位置，將 SQLite 檔案及同名 manifest 放回系統的 data/backups/ 目錄，"
            "然後在「系統設定」選擇顯示為「已驗證」的快照。還原前系統會先建立安全快照。\n"
            "\n"
            "This package is for school-approved encrypted offline storage and handover only. It contains one verified SQLite snapshot and its SHA-256 manifest. Do not email, publicly upload, or share it through an unapproved service.\n"
            "\n"
            "Restore: extract both files to a controlled location, return the SQLite file and its matching manifest to data/backups/, then select a Verified snapshot in Settings. The system creates a safety snapshot before restore.\n"
            f"\nSnapshot included: {snapshot_name}\n"
        )

    @staticmethod
    def _core_role(role_code: str) -> str:
        return ROLE_LABELS_FOR_CORE[role_code]

    @staticmethod
    def _role_code_from_core(role: str) -> str:
        return "assistant_head" if "Assistant Head Study Prefect" in role else "study_prefect"

    @staticmethod
    def _form_rank(form: str) -> int:
        return int(form.removeprefix("F."))

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _require_monday(week_start: date) -> None:
        if week_start.weekday() != 0:
            raise WorkflowError("A roster week must start on Monday.")

    @staticmethod
    def _require_backup(backup: BackupResult, *, committed_event: str | None = None) -> Path:
        if not backup.success or backup.path is None:
            if committed_event is not None:
                raise CommittedWriteBackupError(committed_event, backup.error_message)
            raise WorkflowError(f"Data was saved, but automatic backup failed: {backup.error_message or 'unknown error'}")
        return backup.path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
