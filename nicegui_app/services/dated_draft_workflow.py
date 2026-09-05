"""Dated ordinary draft commands in the existing official transaction lifecycle."""
from datetime import date, timedelta
import hashlib
import logging
from pathlib import Path

from sqlalchemy import select

from roster_core.command_identity import normalize_command_id
from roster_core.dated_draft import DutyCommitment, accepted_assist_ownership, decode_draft, edit_draft, encode_draft, generate_draft
from roster_core.policy_settings import PolicySettings, PolicyVersionConflict
from roster_policy import AssistAssignmentMode, SchoolDay
from roster_policy.configurable import ScheduleExceptions, ScheduleMode, SeatKey
from nicegui_app.persistence.models import (
    BackupObligationRecord, DatedDraftCurrentRecord, DatedDraftRevisionRecord, OperationCommandRecord,
    PrefectRecord, RosterAssignmentRecord, RosterWeekRecord,
)
from nicegui_app.services.dated_draft_types import (
    DatedDraftCommandResult, DatedDraftSnapshot, draft_identity, draft_version, edit_payload, exception_payload,
)
from nicegui_app.services.maintenance import MaintenanceModeError
from nicegui_app.services.operation_context import current_operation_actor
from nicegui_app.services.transaction_policy_repository import TransactionPolicyRepository
from nicegui_app.services.workflow_types import WorkflowConflictError, WorkflowError, WorkflowMaintenanceError

_LOGGER = logging.getLogger(__name__)


class DatedDraftWorkflowMixin:
    def dated_draft_command_result(self, *, command_id: str) -> DatedDraftCommandResult | None:
        self._require_policy_actor()
        command_id = normalize_command_id(command_id)
        with self._session() as session:
            self._begin_consistent_read(session)
            command = session.get(OperationCommandRecord, command_id)
            if command is None or command.operation_type not in {
                "dated_draft_created", "dated_draft_edited", "dated_draft_regenerated", "dated_draft_policy_adopted",
            }:
                return None
            if command.status != "committed":
                raise WorkflowError("The dated draft command has no committed result.")
            snapshot = self._read_dated_receipt(session, command_id, self._decode_operation_receipt(command.result_json))
            obligation = session.scalar(select(BackupObligationRecord).where(BackupObligationRecord.command_id == command_id))
            if obligation is None or obligation.operation_type != command.operation_type:
                raise WorkflowError("The dated draft receipt is missing its recovery obligation.")
            completed = obligation.status == "completed"
            path = Path(obligation.backup_path) if obligation.backup_path is not None else None
        # Do not pin the live WAL while hashing/verifying recovery evidence.
        verified = completed and path is not None and path.is_file() and self.verify_backup(path).get("valid") is True
        return DatedDraftCommandResult(command_id, snapshot, "verified" if verified else "pending", True)

    def _read_dated_receipt(self, session, command_id, receipt):
        if set(receipt) != {"scheduleId", "version", "documentDigest"}:
            raise WorkflowError("Invalid dated draft command receipt.")
        snapshot = self._read_dated_draft(session, receipt["scheduleId"], receipt["version"])
        record = session.get(DatedDraftRevisionRecord, (snapshot.schedule_id, snapshot.version))
        if (record.command_id != command_id
                or hashlib.sha256(encode_draft(snapshot.draft).encode("utf-8")).hexdigest() != receipt["documentDigest"]):
            raise WorkflowError("Dated draft receipt does not identify its original result.")
        return snapshot

    def dated_draft_snapshot(self, schedule_id: str, *, version: int | None = None) -> DatedDraftSnapshot:
        self._require_policy_actor()
        draft_identity(schedule_id)
        if version is not None:
            draft_version(version)
        with self._session() as session:
            self._begin_consistent_read(session)
            return self._read_dated_draft(session, schedule_id, version)

    def _read_dated_draft(self, session, identity, version=None):
        draft_identity(identity)
        if version is None:
            current = session.get(DatedDraftCurrentRecord, identity)
            if current is None:
                raise WorkflowError("Dated draft was not found.")
            version = current.version
        draft_version(version)
        record = session.get(DatedDraftRevisionRecord, (identity, version))
        if record is None:
            raise WorkflowError("The immutable dated draft revision was not found.")
        draft = decode_draft(record.document)
        reference = PolicySettings(TransactionPolicyRepository(session, self)).revision(record.year_start, record.policy_revision)
        if (reference != draft.policy_ref or draft.schedule.dates[0] != record.week_start
                or encode_draft(draft) != record.document):
            raise WorkflowError("The saved draft does not match its policy reference.")
        return DatedDraftSnapshot(identity, version, draft)

    def _dated_inputs(self, session, monday):
        people = tuple(sorted(self._active_prefects(session), key=lambda person: person.id))
        ids = {person.id for person in people}
        leaves = tuple(sorted((identity, monday + timedelta(days=int(day)))
                              for identity, days in self._leave_days_for_week(session, monday).items()
                              for day in days if identity in ids))
        statement = (select(RosterAssignmentRecord).join(RosterWeekRecord)
                     .where(RosterWeekRecord.week_start == monday, RosterWeekRecord.status == "published",
                            RosterAssignmentRecord.status == "active", RosterAssignmentRecord.prefect_id.is_not(None)))
        occupied = tuple(DutyCommitment(identity, day, ScheduleMode.WEEKLY) for identity, day in sorted({
            (row.prefect_id, monday + timedelta(days=int(SchoolDay[row.day])))
            for row in session.scalars(statement) if row.prefect_id in ids}))
        return people, leaves, occupied

    def _generate_dated(self, session, reference, monday, *, exceptions, assist_mode, history_multiplier):
        from nicegui_app.services.workflow_parts.lifecycle import _previous_assist_weekday_assignments
        people, leaves, occupied = self._dated_inputs(session, monday)
        previous = _previous_assist_weekday_assignments(session, monday)
        legacy_date = session.scalar(select(RosterWeekRecord.week_start)
                                     .where(RosterWeekRecord.week_start < monday, RosterWeekRecord.status.in_(("draft", "published")))
                                     .order_by(RosterWeekRecord.week_start.desc()).limit(1))
        prior = session.scalar(select(DatedDraftCurrentRecord).where(DatedDraftCurrentRecord.week_start < monday)
                               .order_by(DatedDraftCurrentRecord.week_start.desc()).limit(1))
        # During the unactivated seam transition, chronology wins across both
        # sources. The dated source wins only an explicit same-week tie.
        if prior is not None and (legacy_date is None or prior.week_start >= legacy_date):
            from roster_policy.configurable import BusinessId
            previous = {SchoolDay(cell.key.duty_date.weekday()): cell.prefect_id
                        for cell in self._read_dated_draft(session, prior.schedule_id).draft.cells
                        if cell.key.business is BusinessId.ASSIST_IN_CHARGE and cell.state == "assigned"}
        draft = generate_draft(reference, monday, people, exceptions=exceptions, leaves=leaves, occupied=occupied,
                               assist_mode=assist_mode, history_multiplier=history_multiplier, previous_assist=previous)
        draft, ownership = accepted_assist_ownership(draft)
        for identity, weekday in ownership.items():
            person = session.get(PrefectRecord, identity)
            person.fixed_general_duty = weekday
            person.version += 1
            person.updated_at = self._now()
        return draft

    def create_dated_weekly_draft(
        self, year_start: int, policy_revision: int, week_start: date, *, command_id: str,
        exceptions: ScheduleExceptions = ScheduleExceptions(),
        assist_mode: AssistAssignmentMode = AssistAssignmentMode.LEGACY_FIXED_WEEKDAY,
        history_multiplier: float = 1.0,
    ) -> DatedDraftCommandResult:
        self._require_policy_actor()
        if type(week_start) is not date or week_start.weekday() != 0:
            raise WorkflowError("An ordinary draft requires an actual Monday.")
        if not isinstance(assist_mode, AssistAssignmentMode):
            raise WorkflowError("Select a supported Assist mode.")
        payload = {"year": year_start, "policyRevision": policy_revision, "monday": week_start.isoformat(),
                   "exceptions": exception_payload(exceptions), "assistMode": assist_mode.value, "multiplier": history_multiplier}

        def create(session):
            reference = PolicySettings(TransactionPolicyRepository(session, self)).current(year_start)
            if type(policy_revision) is not int or reference.revision != policy_revision:
                raise PolicyVersionConflict("Review the current school-year policy before generating.")
            if session.scalar(select(DatedDraftCurrentRecord).where(DatedDraftCurrentRecord.week_start == week_start)) is not None:
                raise WorkflowConflictError("This week already has a dated draft; reopen it.")
            identity = "DRAFT-" + hashlib.sha256(normalize_command_id(command_id).encode("utf-8")).hexdigest()[:32]
            draft = self._generate_dated(session, reference, week_start, exceptions=exceptions,
                                         assist_mode=assist_mode, history_multiplier=history_multiplier)
            return self._store_dated_draft(session, identity, 0, draft)

        return self._run_dated_command("dated_draft_created", command_id, payload, create, expected_version=0)

    def regenerate_dated_draft(self, schedule_id: str, *, expected_version: int, command_id: str) -> DatedDraftCommandResult:
        return self._change_dated_draft(schedule_id, expected_version, command_id, "dated_draft_regenerated")

    def adopt_dated_draft_policy(self, schedule_id: str, policy_revision: int, *, expected_version: int, command_id: str) -> DatedDraftCommandResult:
        draft_version(policy_revision)
        return self._change_dated_draft(schedule_id, expected_version, command_id, "dated_draft_policy_adopted", policy_revision=policy_revision)

    def edit_dated_draft(self, schedule_id: str, changes: dict[SeatKey, str | None], *, expected_version: int, command_id: str) -> DatedDraftCommandResult:
        edit_payload(changes)
        return self._change_dated_draft(schedule_id, expected_version, command_id, "dated_draft_edited", changes=changes)

    def _change_dated_draft(self, identity, expected, command_id, operation, *, policy_revision=None, changes=None):
        self._require_policy_actor()
        draft_identity(identity)
        draft_version(expected)
        changes = dict(changes) if changes is not None else None
        payload = {"scheduleId": identity, "expectedVersion": expected, "policyRevision": policy_revision,
                   "changes": edit_payload(changes) if changes is not None else None}

        def change(session):
            current = self._read_dated_draft(session, identity)
            if current.version != expected:
                raise WorkflowConflictError("The dated draft changed; reload before editing.")
            old = current.draft
            reference = old.policy_ref
            if policy_revision is not None:
                reference = PolicySettings(TransactionPolicyRepository(session, self)).current(reference.year_start)
                if reference.revision != policy_revision:
                    raise PolicyVersionConflict("Review the current policy before explicit adoption.")
            if changes is not None:
                people, leaves, occupied = self._dated_inputs(session, old.schedule.dates[0])
                # Verify the proposed complete result against live eligibility;
                # the previous immutable revision retains its original inputs.
                updated = edit_draft(old, changes, people=people, leaves=leaves, occupied=occupied)
            else:
                updated = self._generate_dated(session, reference, old.schedule.dates[0], exceptions=old.exceptions,
                                               assist_mode=old.assist_mode, history_multiplier=old.history_multiplier)
            return self._store_dated_draft(session, identity, expected, updated)

        return self._run_dated_command(operation, command_id, payload, change, expected_version=expected)

    def _store_dated_draft(self, session, identity, expected, draft):
        version = draft_version(expected + 1)
        document = encode_draft(draft)
        session.add(DatedDraftRevisionRecord(schedule_id=identity, version=version,
                                            year_start=draft.policy_ref.year_start, policy_revision=draft.policy_ref.revision,
                                            week_start=draft.schedule.dates[0], document=document,
                                            command_id=current_operation_actor().command_id))
        session.flush()
        current = session.get(DatedDraftCurrentRecord, identity)
        if current is None:
            if expected != 0:
                raise WorkflowConflictError("Dated draft current pointer is missing.")
            session.add(DatedDraftCurrentRecord(schedule_id=identity, version=version, week_start=draft.schedule.dates[0]))
        else:
            if current.version != expected:
                raise WorkflowConflictError("The dated draft changed in another operation.")
            current.version = version
        session.flush()
        return DatedDraftSnapshot(identity, version, draft)

    def _run_dated_command(self, operation, command_id, payload, action, *, expected_version):
        command_id = normalize_command_id(command_id)
        self._require_policy_actor(command_id)
        try:
            with self.maintenance.serialized_operation():
                with self._session() as session:
                    self._begin_serialized_write(session)
                    replayed = session.get(OperationCommandRecord, command_id) is not None
                    if not replayed:
                        self._assert_business_write_admitted(operation)
                    command, receipt = self._claim_operation_command(session, operation_type=operation, command_id=command_id, payload=payload)
                    if receipt is None:
                        snapshot = action(session)
                        receipt = {"scheduleId": snapshot.schedule_id, "version": snapshot.version,
                                   "documentDigest": hashlib.sha256(encode_draft(snapshot.draft).encode("utf-8")).hexdigest()}
                        self._audit(session, operation, None, {"version": snapshot.version, "cellCount": len(snapshot.draft.cells)})
                        self._commit_operation_command(session, record=command, result=receipt, roster_week_id=None)
                    else:
                        snapshot = self._read_dated_receipt(session, command_id, receipt)
                        expected_id = payload.get("scheduleId", "DRAFT-" + hashlib.sha256(command_id.encode("utf-8")).hexdigest()[:32])
                        if snapshot.version != expected_version + 1 or snapshot.schedule_id != expected_id:
                            raise WorkflowError("Dated draft receipt does not identify its original result.")
                    session.commit()
                try:
                    self._fulfill_backup_obligation(command_id)
                    backup_status = "verified"
                except Exception as error:
                    _LOGGER.warning("Dated draft committed; backup pending (%s)", type(error).__name__)
                    backup_status = "pending"
                return DatedDraftCommandResult(command_id, snapshot, backup_status, replayed)
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error
