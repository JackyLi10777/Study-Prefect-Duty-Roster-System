"""Durable external-share outbox operations.

The public viewer is an external system, so its response can be lost after it
has already accepted a share.  These operations persist the exact encrypted
delivery envelope before network I/O and bind it to the published roster
version and a canonical content digest.  A retry therefore replays the same
share rather than creating a second one.
"""

from __future__ import annotations

import re

from nicegui_app.services.workflow_dependencies import (
    ExternalShareOutboxRecord,
    MaintenanceModeError,
    OperationCommandRecord,
    RosterWeekRecord,
    WorkflowConflictError,
    WorkflowError,
    WorkflowMaintenanceError,
    json,
    select,
)


_CONTENT_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_SHARE_ID = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_OUTBOX_OPERATION = "external_share_create"


class ExternalShareOutboxMixin:
    """Persistence boundary for replay-safe public roster deliveries."""

    def queue_external_share(
        self,
        *,
        command_id: str,
        roster_week_id: int,
        roster_version: int,
        content_digest: str,
        share_id: str,
        delivery_payload: dict[str, object],
        share_key: str,
        receipt_metadata: dict[str, object],
    ) -> dict[str, object]:
        """Persist an exact delivery envelope before contacting the gateway."""

        operation_id = self._operation_command_id(_OUTBOX_OPERATION, command_id)
        if roster_week_id <= 0 or roster_version <= 0:
            raise WorkflowError("The public share roster reference is invalid.")
        if not _CONTENT_DIGEST.fullmatch(content_digest):
            raise WorkflowError("The public share content digest is invalid.")
        if not _SHARE_ID.fullmatch(share_id):
            raise WorkflowError("The public share identifier is invalid.")
        if not share_key or len(share_key) > 128:
            raise WorkflowError("The public share key is invalid.")
        if str(delivery_payload.get("shareId") or "") != share_id:
            raise WorkflowError("The public share delivery envelope is invalid.")

        fingerprint_payload = {
            "rosterWeekId": roster_week_id,
            "rosterVersion": roster_version,
            "contentDigest": content_digest,
            "expiresAt": receipt_metadata.get("expiresAt"),
        }
        request_fingerprint = self._operation_fingerprint(
            _OUTBOX_OPERATION,
            fingerprint_payload,
        )
        now = self._now()
        queued_receipt = {
            "status": "pending",
            "deliveryPayload": delivery_payload,
            "shareKey": share_key,
            "receipt": receipt_metadata,
        }

        try:
            with self.maintenance.serialized_operation():
                self._assert_business_write_admitted("queue_external_share")
                with self._session() as session:
                    self._begin_serialized_write(session)
                    existing_command = session.get(OperationCommandRecord, operation_id)
                    if existing_command is not None:
                        if (
                            existing_command.operation_type != _OUTBOX_OPERATION
                            or existing_command.request_fingerprint != request_fingerprint
                        ):
                            raise WorkflowConflictError(
                                "This public-share command was already used for different content."
                            )
                        outbox = session.scalar(
                            select(ExternalShareOutboxRecord).where(
                                ExternalShareOutboxRecord.command_id == operation_id
                            )
                        )
                        if outbox is None:
                            raise WorkflowError("The saved public-share outbox receipt is missing.")
                        saved = self._decode_share_command(existing_command.result_json)
                        return {
                            **saved,
                            "commandId": operation_id,
                            "outboxStatus": outbox.status,
                            "attempts": outbox.attempts,
                        }

                    week = session.get(RosterWeekRecord, roster_week_id)
                    if week is None or week.status != "published":
                        raise WorkflowError("Only a published roster can be shared externally.")
                    if int(week.version) != roster_version:
                        raise WorkflowConflictError(
                            "The published roster changed before sharing. Reload it and create a new link."
                        )

                    command = OperationCommandRecord(
                        command_id=operation_id,
                        operation_type=_OUTBOX_OPERATION,
                        request_fingerprint=request_fingerprint,
                        status="pending",
                        result_json=json.dumps(
                            queued_receipt,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                        created_at=now,
                        completed_at=None,
                    )
                    session.add(command)
                    session.flush()
                    session.add(
                        ExternalShareOutboxRecord(
                            command_id=operation_id,
                            share_id=share_id,
                            roster_week_id=roster_week_id,
                            roster_version=roster_version,
                            content_digest=content_digest,
                            status="pending",
                            attempts=0,
                            error=None,
                            created_at=now,
                            updated_at=now,
                            delivered_at=None,
                        )
                    )
                    self._audit(
                        session,
                        "external_share_queued",
                        roster_week_id,
                        {
                            "shareIdSuffix": share_id[-8:],
                            "rosterVersion": roster_version,
                            "contentDigest": content_digest,
                        },
                    )
                    session.commit()
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

        return {
            **queued_receipt,
            "commandId": operation_id,
            "outboxStatus": "pending",
            "attempts": 0,
        }

    def retryable_external_share_command(
        self,
        *,
        roster_week_id: int,
        roster_version: int,
        content_digest: str,
        expires_at: str,
    ) -> str | None:
        """Find the newest undelivered envelope for the same immutable share."""

        if not _CONTENT_DIGEST.fullmatch(content_digest):
            raise WorkflowError("The public share content digest is invalid.")
        with self._session() as session:
            candidates = session.scalars(
                select(ExternalShareOutboxRecord)
                .where(
                    ExternalShareOutboxRecord.roster_week_id == roster_week_id,
                    ExternalShareOutboxRecord.roster_version == roster_version,
                    ExternalShareOutboxRecord.content_digest == content_digest,
                    ExternalShareOutboxRecord.status.in_(("pending", "delivering")),
                )
                .order_by(ExternalShareOutboxRecord.id.desc())
            ).all()
            for outbox in candidates:
                command = session.get(OperationCommandRecord, outbox.command_id)
                if command is None or command.status != "pending":
                    continue
                saved = self._decode_share_command(command.result_json)
                receipt = saved.get("receipt")
                if isinstance(receipt, dict) and str(receipt.get("expiresAt") or "") == expires_at:
                    return outbox.command_id
        return None

    def begin_external_share_delivery(self, command_id: str) -> dict[str, object]:
        """Claim one attempt and return the exact previously queued envelope."""

        operation_id = self._operation_command_id(_OUTBOX_OPERATION, command_id)
        try:
            with self.maintenance.serialized_operation():
                self._assert_business_write_admitted("begin_external_share_delivery")
                with self._session() as session:
                    self._begin_serialized_write(session)
                    command = session.get(OperationCommandRecord, operation_id)
                    outbox = session.scalar(
                        select(ExternalShareOutboxRecord).where(
                            ExternalShareOutboxRecord.command_id == operation_id
                        )
                    )
                    if command is None or outbox is None:
                        raise WorkflowError("The public-share outbox receipt was not found.")
                    week = session.get(RosterWeekRecord, outbox.roster_week_id)
                    if (
                        week is None
                        or week.status != "published"
                        or week.version != outbox.roster_version
                        or outbox.status in ("cancelled", "revocation_pending", "revoked")
                    ):
                        raise WorkflowConflictError(
                            "This roster share is no longer current and cannot be delivered."
                        )
                    saved = self._decode_share_command(command.result_json)
                    if command.status == "committed" or outbox.status == "delivered":
                        return {
                            **saved,
                            "commandId": operation_id,
                            "outboxStatus": "delivered",
                            "attempts": outbox.attempts,
                        }
                    if saved.get("status") != "pending":
                        raise WorkflowError("The saved public-share delivery envelope is invalid.")
                    outbox.status = "delivering"
                    outbox.attempts += 1
                    outbox.error = None
                    outbox.updated_at = self._now()
                    session.commit()
                    return {
                        **saved,
                        "commandId": operation_id,
                        "outboxStatus": "delivering",
                        "attempts": outbox.attempts,
                    }
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def complete_external_share_delivery(
        self,
        command_id: str,
        *,
        delivered_receipt: dict[str, object],
    ) -> dict[str, object]:
        """Mark delivery once and erase the locally queued decryption key."""

        operation_id = self._operation_command_id(_OUTBOX_OPERATION, command_id)
        now = self._now()
        try:
            with self.maintenance.serialized_operation():
                with self._session() as session:
                    self._begin_serialized_write(session)
                    command = session.get(OperationCommandRecord, operation_id)
                    outbox = session.scalar(
                        select(ExternalShareOutboxRecord).where(
                            ExternalShareOutboxRecord.command_id == operation_id
                        )
                    )
                    if command is None or outbox is None:
                        raise WorkflowError("The public-share outbox receipt was not found.")
                    if str(delivered_receipt.get("shareId") or "") != outbox.share_id:
                        raise WorkflowConflictError(
                            "The public viewer returned a different share identifier."
                        )
                    if command.status == "committed" and outbox.status == "delivered":
                        return self._decode_share_command(command.result_json)
                    week = session.get(RosterWeekRecord, outbox.roster_week_id)
                    if (
                        week is None
                        or week.status != "published"
                        or week.version != outbox.roster_version
                        or outbox.status != "delivering"
                    ):
                        raise WorkflowConflictError(
                            "This roster was changed or withdrawn before share delivery completed."
                        )

                    durable_receipt = {
                        "status": "delivered",
                        "receipt": {
                            key: value
                            for key, value in delivered_receipt.items()
                            if key != "shareUrl"
                        },
                    }
                    command.status = "committed"
                    command.result_json = json.dumps(
                        durable_receipt,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    command.completed_at = now
                    outbox.status = "delivered"
                    outbox.error = None
                    outbox.updated_at = now
                    outbox.delivered_at = now
                    self._audit(
                        session,
                        "external_share_delivered",
                        outbox.roster_week_id,
                        {
                            "shareIdSuffix": outbox.share_id[-8:],
                            "rosterVersion": outbox.roster_version,
                            "contentDigest": outbox.content_digest,
                            "attempts": outbox.attempts,
                        },
                    )
                    session.commit()
                    return durable_receipt
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def fail_external_share_delivery(self, command_id: str, *, error_code: str) -> None:
        """Return a failed attempt to pending so the exact envelope can retry."""

        operation_id = self._operation_command_id(_OUTBOX_OPERATION, command_id)
        safe_error = (error_code or "delivery_failed").strip()[:160]
        try:
            with self.maintenance.serialized_operation():
                with self._session() as session:
                    self._begin_serialized_write(session)
                    outbox = session.scalar(
                        select(ExternalShareOutboxRecord).where(
                            ExternalShareOutboxRecord.command_id == operation_id
                        )
                    )
                    if outbox is None:
                        raise WorkflowError("The public-share outbox receipt was not found.")
                    if outbox.status == "delivered":
                        session.rollback()
                        return
                    outbox.status = "pending"
                    outbox.error = safe_error
                    outbox.updated_at = self._now()
                    session.commit()
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    def external_share_outbox(self, command_id: str) -> dict[str, object] | None:
        """Return privacy-bounded diagnostics without ciphertext or key material."""

        operation_id = self._operation_command_id(_OUTBOX_OPERATION, command_id)
        with self._session() as session:
            outbox = session.scalar(
                select(ExternalShareOutboxRecord).where(
                    ExternalShareOutboxRecord.command_id == operation_id
                )
            )
            if outbox is None:
                return None
            return {
                "commandId": outbox.command_id,
                "shareIdSuffix": outbox.share_id[-8:],
                "rosterWeekId": outbox.roster_week_id,
                "rosterVersion": outbox.roster_version,
                "contentDigest": outbox.content_digest,
                "status": outbox.status,
                "attempts": outbox.attempts,
                "error": outbox.error,
                "deliveredAt": outbox.delivered_at,
            }

    def pending_external_share_revocations(self) -> list[dict[str, object]]:
        """Return durable revocation work without exposing roster content."""

        with self._session() as session:
            rows = session.scalars(
                select(ExternalShareOutboxRecord)
                .where(ExternalShareOutboxRecord.status == "revocation_pending")
                .order_by(ExternalShareOutboxRecord.updated_at, ExternalShareOutboxRecord.id)
            ).all()
            return [
                {
                    "shareId": row.share_id,
                    "rosterWeekId": row.roster_week_id,
                    "attempts": row.attempts,
                }
                for row in rows
            ]

    def complete_external_share_revocation(self, share_id: str) -> None:
        normalized = share_id.strip()
        if not normalized:
            raise WorkflowError("The public share identifier is invalid.")
        with self._session() as session:
            self._begin_serialized_write(session)
            row = session.scalar(
                select(ExternalShareOutboxRecord).where(
                    ExternalShareOutboxRecord.share_id == normalized
                )
            )
            if row is None:
                raise WorkflowError("The public-share outbox receipt was not found.")
            if row.status == "revoked":
                session.rollback()
                return
            if row.status != "revocation_pending":
                raise WorkflowConflictError("This public share is not awaiting revocation.")
            row.status = "revoked"
            row.error = None
            row.updated_at = self._now()
            self._audit(
                session,
                "external_share_revoked",
                row.roster_week_id,
                {"shareIdSuffix": row.share_id[-8:]},
            )
            session.commit()

    def fail_external_share_revocation(self, share_id: str, *, error_code: str) -> None:
        normalized = share_id.strip()
        if not normalized:
            raise WorkflowError("The public share identifier is invalid.")
        safe_error = (error_code or "revocation_failed").strip()[:160]
        with self._session() as session:
            self._begin_serialized_write(session)
            row = session.scalar(
                select(ExternalShareOutboxRecord).where(
                    ExternalShareOutboxRecord.share_id == normalized
                )
            )
            if row is None:
                raise WorkflowError("The public-share outbox receipt was not found.")
            if row.status != "revocation_pending":
                session.rollback()
                return
            row.attempts += 1
            row.error = safe_error
            row.updated_at = self._now()
            session.commit()

    @staticmethod
    def _decode_share_command(raw: str) -> dict[str, object]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise WorkflowError("The saved public-share command is invalid.") from error
        if not isinstance(value, dict):
            raise WorkflowError("The saved public-share command is invalid.")
        return value
