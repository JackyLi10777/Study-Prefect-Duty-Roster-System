"""School-year settings through the existing identity/transaction/backup Module.

No page, scheduler or export reads these settings until its own vertical rollout
is complete. These workflow methods nevertheless execute real durable commands,
not provisional repository writes or a second receipt system.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path
from typing import TypeVar

from sqlalchemy import select

from nicegui_app.persistence.models import BackupObligationRecord, OperationCommandRecord
from nicegui_app.services.maintenance import MaintenanceModeError
from nicegui_app.services.operation_context import current_operation_actor
from nicegui_app.services.transaction_policy_repository import TransactionPolicyRepository
from nicegui_app.services.workflow_types import PolicyCommandResult, WorkflowMaintenanceError
from roster_core.command_identity import normalize_command_id
from roster_core.policy_settings import PolicyRevision, PolicySettings, PolicyStorageError, ResetPreview, policy_request_digest
from roster_policy.configurable import WeeklyPolicy
from roster_policy.policy_codec import encode_weekly_policy


_T = TypeVar("_T")
_POLICY_OPERATIONS = {"policy_initialized": "initialize", "policy_saved": "save", "policy_reset": "reset"}
_LOGGER = logging.getLogger(__name__)


class PolicyWorkflowMixin:
    @staticmethod
    def _require_policy_actor(command_id: str | None = None) -> None:
        actor = current_operation_actor()
        if actor is None or actor.mode not in {"admin", "local_maintenance"}:
            raise PermissionError("School-year settings require an administrative page identity.")
        if command_id is not None and actor.command_id != command_id:
            raise PermissionError("The settings command must match its bound operation identity.")

    def _read_policy(self, action: Callable[[PolicySettings], _T]) -> _T:
        self._require_policy_actor()
        with self._session() as session:
            self._begin_consistent_read(session)
            return action(PolicySettings(TransactionPolicyRepository(session, self)))

    def policy_current(self, year_start: int) -> PolicyRevision:
        return self._read_policy(lambda settings: settings.current(year_start))

    def policy_revision(self, year_start: int, revision: int) -> PolicyRevision:
        return self._read_policy(lambda settings: settings.revision(year_start, revision))

    def policy_reset_preview(self, year_start: int) -> ResetPreview:
        return self._read_policy(lambda settings: settings.preview_reset(year_start))

    def initialize_policy(self, year_start: int, *, command_id: str) -> PolicyCommandResult:
        return self._run_policy_command(command_id, lambda settings: settings.initialize(year_start, command_id=command_id))

    def save_policy(
        self, year_start: int, policy: WeeklyPolicy, *, expected_revision: int, command_id: str,
    ) -> PolicyCommandResult:
        return self._run_policy_command(command_id, lambda settings: settings.save(
            year_start, policy, expected_revision=expected_revision, command_id=command_id,
        ))

    def reset_policy(self, preview: ResetPreview, *, command_id: str) -> PolicyCommandResult:
        return self._run_policy_command(command_id, lambda settings: settings.reset(preview, command_id=command_id))

    def _run_policy_command(
        self, command_id: str, action: Callable[[PolicySettings], PolicyRevision],
    ) -> PolicyCommandResult:
        normalized = normalize_command_id(command_id)
        self._require_policy_actor(normalized)
        try:
            # Authorize before even acquiring the host-wide fence: rejected raw
            # callers must not create a lease/lock file beside official storage.
            with self.maintenance.serialized_operation():
                with self._session() as session:
                    self._begin_serialized_write(session)
                    replayed = session.get(OperationCommandRecord, normalized) is not None
                    # Exact retries are recovery, not new writes. The repository
                    # still checks the full original digest before replaying.
                    if not replayed:
                        self._assert_business_write_admitted("save_policy")
                    revision = action(PolicySettings(TransactionPolicyRepository(session, self)))
                    session.commit()
                try:
                    self._fulfill_backup_obligation(normalized)
                except Exception as error:
                    # Commit has happened. Retain its revision and identity;
                    # never imply rollback or invite a new save. No raw error,
                    # identity, document, filename or command ID goes to logs.
                    _LOGGER.warning("Policy command committed; recovery snapshot pending (%s)", type(error).__name__)
                    return PolicyCommandResult(normalized, revision, "pending", replayed)
                return PolicyCommandResult(normalized, revision, "verified", replayed)
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def policy_command_result(self, *, command_id: str) -> PolicyCommandResult | None:
        """Read a committed result without mutating it or attempting backup I/O writes."""
        self._require_policy_actor()
        normalized = normalize_command_id(command_id)
        with self._session() as session:
            self._begin_consistent_read(session)
            command = session.get(OperationCommandRecord, normalized)
            if command is None or command.operation_type not in _POLICY_OPERATIONS:
                return None
            if command.status != "committed":
                raise PolicyStorageError("The policy command has no committed result.")
            try:
                receipt = self._decode_operation_receipt(command.result_json)
                if type(receipt) is not dict or set(receipt) != {"year_start", "revision"}:
                    raise ValueError("Invalid policy receipt shape.")
                settings = PolicySettings(TransactionPolicyRepository(session, self))
                revision = settings.revision(receipt["year_start"], receipt["revision"])
                digest = policy_request_digest(
                    _POLICY_OPERATIONS[command.operation_type], revision.year_start, revision.revision - 1,
                    encode_weekly_policy(revision.policy),
                )
                expected = self._operation_fingerprint(command.operation_type, {"policyRequestDigest": digest})
                if command.request_fingerprint != expected:
                    raise ValueError("The policy receipt identifies a different command's revision.")
            except (ValueError, TypeError) as error:
                raise PolicyStorageError("The saved policy receipt cannot identify a valid revision.") from error
            obligation = session.scalar(select(BackupObligationRecord).where(
                BackupObligationRecord.command_id == normalized,
            ))
            if obligation is None or obligation.operation_type != command.operation_type:
                raise PolicyStorageError("The committed policy command is missing its recovery obligation.")
            backup_completed = obligation.status == "completed"
            backup_path = Path(obligation.backup_path) if obligation.backup_path is not None else None
        # The command, revision and obligation were copied from one snapshot.
        # Release its WAL read/pooled connection before checking a backup file;
        # file hashing and integrity checks must not pin the live database.
        verified = (
            backup_completed and backup_path is not None and backup_path.is_file()
            and self.verify_backup(backup_path).get("valid") is True
        )
        return PolicyCommandResult(normalized, revision, "verified" if verified else "pending", True)
