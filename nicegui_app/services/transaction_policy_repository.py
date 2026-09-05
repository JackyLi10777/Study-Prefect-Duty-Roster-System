"""Policy storage inside one caller-owned official operation transaction.

Internal Interface only: the caller verifies the live principal, acquires the
maintenance/write fence, enables SQLite foreign keys and executes BEGIN
IMMEDIATE before constructing this Adapter. The caller commits or rolls back
the entire transaction and fulfills the resulting backup obligation afterward.

Any error requires caller rollback. An Adapter cannot be reused after an error,
commit, rollback or Session close. Returned revisions are provisional until the
caller commits; no backup success or public workflow completion is implied.
"""

from __future__ import annotations

import re

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from nicegui_app.services.operation_context import OperationActor, current_operation_actor
from nicegui_app.services.sqlite_policy_repository import _append_policy_revision, _read_policy_revision
from nicegui_app.services.workflow_parts.persistence import PersistenceWorkflowMixin
from nicegui_app.services.workflow_types import WorkflowConflictError, WorkflowError
from roster_core.command_identity import CommandIdentityError, normalize_command_id
from roster_core.policy_settings import (
    PolicyCommandConflict, PolicyOperation, PolicySettingsError, PolicyStorageError, StoredPolicyRevision,
)


_OPERATION_TYPES = {"initialize": "policy_initialized", "save": "policy_saved", "reset": "policy_reset"}


class TransactionPolicyRepository:
    def __init__(self, session: Session, workflow_helpers: PersistenceWorkflowMixin) -> None:
        self._session = session
        self._helpers = workflow_helpers
        self._transaction = session.get_transaction()
        self._failed = False
        self._connection()

    def _connection(self) -> Connection:
        transaction = self._session.get_transaction()
        if (
            self._failed or self._transaction is None or transaction is not self._transaction
            or not transaction.is_active or self._session.in_nested_transaction()
        ):
            raise PolicyStorageError("Policy storage requires its original active caller transaction; rollback after errors.")
        connection = self._session.connection()
        if connection.dialect.name != "sqlite" or not connection.connection.driver_connection.in_transaction:
            raise PolicyStorageError("The caller must begin an actual SQLite transaction before using policy storage.")
        if connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() != 1:
            raise PolicyStorageError("The caller must enable SQLite foreign keys before beginning the transaction.")
        return connection

    def read(self, year_start: int, revision: int | None = None) -> StoredPolicyRevision | None:
        try:
            return _read_policy_revision(self._connection(), year_start, revision)
        except SQLAlchemyError as error:
            self._failed = True
            raise PolicyStorageError("Transactional policy read failed; the caller must roll back.") from error
        except Exception:
            self._failed = True
            raise

    def commit(
        self, year_start: int, expected_revision: int, document: str,
        command_id: str, request_digest: str, *, operation: PolicyOperation,
    ) -> StoredPolicyRevision:
        try:
            connection = self._connection()
            if operation not in _OPERATION_TYPES or type(request_digest) is not str or re.fullmatch(r"[0-9a-f]{64}", request_digest) is None:
                raise PolicySettingsError("A policy command requires an explicit operation and canonical request digest.")
            actor = current_operation_actor()
            if not isinstance(actor, OperationActor) or actor.mode not in {"admin", "local_maintenance"}:
                raise PolicySettingsError("A policy write requires a caller-bound administrative operation actor.")
            try:
                normalized = normalize_command_id(command_id)
                actor_command = normalize_command_id(actor.command_id)
            except CommandIdentityError as error:
                raise PolicySettingsError("The operation actor and policy command require valid command IDs.") from error
            if normalized != command_id or actor_command != command_id or actor.command_id != command_id:
                raise PolicySettingsError("The policy command must match its normalized operation actor command.")
            operation_type = _OPERATION_TYPES[operation]
            record, receipt = self._helpers._claim_operation_command(
                self._session, operation_type=operation_type, command_id=command_id,
                payload={"policyRequestDigest": request_digest},
            )
            if receipt is not None:
                if (
                    set(receipt) != {"year_start", "revision"}
                    or type(receipt["year_start"]) is not int or receipt["year_start"] != year_start
                    or type(receipt["revision"]) is not int or receipt["revision"] != expected_revision + 1
                ):
                    raise PolicyStorageError("The saved policy operation receipt is invalid; the caller must roll back.")
                stored = _read_policy_revision(connection, receipt["year_start"], receipt["revision"])
                if stored is None or stored.document != document:
                    raise PolicyStorageError("The policy receipt does not identify its immutable revision.")
                return stored
            stored = _append_policy_revision(connection, year_start, expected_revision, document)
            self._helpers._audit(self._session, operation_type, None, {
                "yearStart": year_start, "policyRevision": stored.revision,
            })
            self._helpers._commit_operation_command(
                self._session, record=record,
                result={"year_start": year_start, "revision": stored.revision}, roster_week_id=None,
            )
            self._session.flush()
            return stored
        except WorkflowConflictError as error:
            self._failed = True
            raise PolicyCommandConflict("The policy operation command conflicts with existing work; the caller must roll back.") from error
        except (SQLAlchemyError, WorkflowError) as error:
            self._failed = True
            raise PolicyStorageError("Transactional policy write failed; the caller must roll back.") from error
        except Exception:
            self._failed = True
            raise
