from __future__ import annotations

from base64 import urlsafe_b64decode
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
from threading import Barrier, Lock

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pytest
from sqlalchemy import select

from nicegui_app.access_context import (
    AccessMode,
    CapabilityDeniedError,
    PageContext,
    Principal,
)
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.persistence.models import (
    AuditEventRecord,
    BackupObligationRecord,
    ExternalShareOutboxRecord,
    LeaveAdjustmentRecord,
    OperationCommandRecord,
)
from nicegui_app.services.operation_context import PageContextWorkflowAdapter
from nicegui_app.services.public_roster_share import (
    PublicRosterShareError,
    PublicRosterShareService,
    PublicRosterShareSettings,
)
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowMaintenanceError
from nicegui_app.ui import access_control


WEEK_START = date(2026, 9, 7)
FIXED_NOW = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)


class CommitThenLoseGateway:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.failures_remaining = 1

    def create(self, payload):
        self.created.append(dict(payload))
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise PublicRosterShareError("simulated response loss")
        return {
            "shareId": payload["shareId"],
            "createdAt": payload["createdAt"],
        }

    def list(self):
        return []

    def revoke(self, _share_id: str):
        return None


class RecordingGateway:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []

    def create(self, payload):
        self.created.append(dict(payload))
        return {
            "shareId": payload["shareId"],
            "createdAt": payload["createdAt"],
        }

    def list(self):
        return []

    def revoke(self, _share_id: str):
        return None


class FlakyRevocationService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.failures_remaining = 1

    def revoke_share(self, share_id: str) -> None:
        self.calls.append(share_id)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise PublicRosterShareError("simulated revocation failure")


class ConcurrentIdempotentGateway:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self._barrier = Barrier(2)
        self._lock = Lock()

    def create(self, payload):
        with self._lock:
            self.created.append(dict(payload))
        self._barrier.wait(timeout=10)
        return {
            "shareId": payload["shareId"],
            "createdAt": payload["createdAt"],
        }

    def list(self):
        return []

    def revoke(self, _share_id: str):
        return None


def _settings() -> PublicRosterShareSettings:
    return PublicRosterShareSettings(
        enabled=True,
        base_url="https://roster-view.example.workers.dev",
        admin_token="a" * 48,
    )


def _workflow(tmp_path) -> tuple[RosterWorkflow, int]:
    workflow = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    return workflow, draft.id


def _add_pending_backup_obligation(workflow: RosterWorkflow, command_id: str) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with workflow._session() as session:
        session.add(
            OperationCommandRecord(
                command_id=command_id,
                operation_type="test_committed_write",
                request_fingerprint="0" * 64,
                status="committed",
                result_json="{}",
                created_at=now,
                completed_at=now,
            )
        )
        session.flush()
        session.add(
            BackupObligationRecord(
                command_id=command_id,
                operation_type="test_committed_write",
                roster_week_id=None,
                status="failed",
                created_at=now,
            )
        )
        session.commit()


def _unpad(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_pending_backup_obligation_blocks_new_share_before_gateway_or_outbox(
    tmp_path,
) -> None:
    workflow, roster_id = _workflow(tmp_path)
    _add_pending_backup_obligation(workflow, "unsafe-share-fence")
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    with pytest.raises(WorkflowMaintenanceError, match="read-only"):
        service.create_share(roster_id, command_id="blocked-public-share")

    assert gateway.created == []
    with workflow._session() as session:
        assert session.scalar(select(ExternalShareOutboxRecord)) is None
        assert session.get(OperationCommandRecord, "blocked-public-share") is None


def test_response_loss_replays_exact_durable_envelope_and_erases_key_after_delivery(
    tmp_path,
) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = CommitThenLoseGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    with pytest.raises(PublicRosterShareError, match="simulated response loss"):
        service.create_share(roster_id)

    with workflow._session() as session:
        outbox = session.scalar(select(ExternalShareOutboxRecord))
        assert outbox is not None
        command = session.get(OperationCommandRecord, outbox.command_id)
        assert command is not None
        pending = json.loads(command.result_json)
        assert outbox.status == "pending"
        assert outbox.attempts == 1
        assert command.status == "pending"
        assert pending["shareKey"]
        assert pending["deliveryPayload"] == gateway.created[0]
        assert outbox.roster_version == workflow.roster_week(roster_id)["version"]
        assert len(outbox.content_digest) == 64

    receipt = service.create_share(roster_id)

    assert len(gateway.created) == 2
    assert gateway.created[1] == gateway.created[0]
    assert receipt.share_id == gateway.created[0]["shareId"]
    with workflow._session() as session:
        outbox = session.scalar(select(ExternalShareOutboxRecord))
        assert outbox is not None
        command = session.get(OperationCommandRecord, outbox.command_id)
        assert command is not None
        durable = json.loads(command.result_json)
        assert outbox.status == "delivered"
        assert outbox.attempts == 2
        assert outbox.delivered_at is not None
        assert command.status == "committed"
        assert "shareKey" not in durable
        assert "deliveryPayload" not in durable
        assert "shareUrl" not in json.dumps(durable)

    fragment = receipt.share_url.split("#", 1)[1]
    _, encoded_key = fragment.split(".", 1)
    plaintext = AESGCM(_unpad(encoded_key)).decrypt(
        _unpad(str(gateway.created[1]["nonce"])),
        _unpad(str(gateway.created[1]["ciphertext"])),
        f"sing-yin-roster-share-v1:{receipt.share_id}".encode("ascii"),
    )
    assert json.loads(plaintext)["version"] == workflow.roster_week(roster_id)["version"]


def test_replaying_delivered_command_never_creates_a_second_external_share(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    service.create_share(roster_id, command_id="public-share-test-replay")

    with pytest.raises(PublicRosterShareError, match="already delivered"):
        service.create_share(roster_id, command_id="public-share-test-replay")
    assert len(gateway.created) == 1


def test_withdrawing_a_delivered_share_creates_durable_revocation_work(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    service.create_share(roster_id, command_id="public-share-withdrawal-test")
    share_id = str(gateway.created[0]["shareId"])
    current = workflow.roster_week(roster_id)

    result = workflow.withdraw_published_roster(
        roster_id,
        expected_version=int(current["version"]),
        reason="Published the wrong reviewed roster",
        command_id="withdraw-public-share-test",
    )

    assert result.share_ids_to_revoke == (share_id,)
    assert workflow.pending_external_share_revocations() == [
        {"shareId": share_id, "rosterWeekId": roster_id, "attempts": 1}
    ]
    workflow.complete_external_share_revocation(share_id)
    assert workflow.pending_external_share_revocations() == []
    assert workflow.external_share_outbox("public-share-withdrawal-test")["status"] == "revoked"


def test_adjustment_queues_only_older_delivered_share_versions_for_revocation(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    service.create_share(roster_id, command_id="public-share-before-adjustment")
    old_share_id = str(gateway.created[-1]["shareId"])
    reviewed = workflow.roster_week(roster_id)
    assignment = next(row for row in workflow.assignments(roster_id) if row["status"] == "active")

    result = workflow.apply_leave_adjustment(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason="Prefect reported an absence after publication",
        command_id="adjust-public-share-test",
        expected_week_version=int(reviewed["version"]),
    )

    assert result.share_ids_to_revoke == (old_share_id,)
    assert workflow.pending_external_share_revocations() == [
        {"shareId": old_share_id, "rosterWeekId": roster_id, "attempts": 1}
    ]

    service.create_share(roster_id, command_id="public-share-after-adjustment")
    new_share_id = str(gateway.created[-1]["shareId"])
    replay = workflow.apply_leave_adjustment(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason="Prefect reported an absence after publication",
        command_id="adjust-public-share-test",
        expected_week_version=int(reviewed["version"]),
    )

    assert replay.idempotent is True
    assert replay.share_ids_to_revoke == (old_share_id,)
    assert workflow.external_share_outbox("public-share-after-adjustment")["status"] == "delivered"
    assert new_share_id != old_share_id


def test_adjustment_revokes_response_lost_share_and_scrubs_queued_secret(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = CommitThenLoseGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    with pytest.raises(PublicRosterShareError, match="simulated response loss"):
        service.create_share(roster_id, command_id="response-lost-before-adjustment")
    share_id = str(gateway.created[0]["shareId"])
    reviewed = workflow.roster_week(roster_id)
    assignment = next(row for row in workflow.assignments(roster_id) if row["status"] == "active")

    result = workflow.apply_leave_adjustment(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason="Prefect reported an absence after publication",
        command_id="adjust-response-lost-share",
        expected_week_version=int(reviewed["version"]),
    )

    assert result.share_ids_to_revoke == (share_id,)
    with workflow._session() as session:
        outbox = session.scalar(
            select(ExternalShareOutboxRecord).where(
                ExternalShareOutboxRecord.share_id == share_id
            )
        )
        assert outbox is not None
        command = session.get(OperationCommandRecord, outbox.command_id)
        assert command is not None
        assert outbox.status == "revocation_pending"
        assert command.status == "committed"
        assert "shareKey" not in command.result_json
        assert "deliveryPayload" not in command.result_json
        assert "ciphertext" not in command.result_json


def test_legacy_adjustment_replay_recovers_revocation_receipt_and_scrubs_queued_secret(
    tmp_path,
) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = CommitThenLoseGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    with pytest.raises(PublicRosterShareError, match="simulated response loss"):
        service.create_share(roster_id, command_id="response-lost-before-legacy-replay")
    share_id = str(gateway.created[0]["shareId"])
    reviewed = workflow.roster_week(roster_id)
    assignment = next(row for row in workflow.assignments(roster_id) if row["status"] == "active")
    command_id = "legacy-adjustment-replay"
    reason = "Legacy adjustment committed before durable command receipts"
    fingerprint = workflow._leave_adjustment_request_fingerprint(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason=reason,
    )
    with workflow._session() as session:
        session.add(
            LeaveAdjustmentRecord(
                roster_week_id=roster_id,
                assignment_id=int(assignment["id"]),
                original_prefect_id=str(assignment["prefectId"]),
                original_prefect_name=str(assignment["prefectName"]),
                replacement_prefect_id=None,
                replacement_prefect_name=None,
                reason=reason,
                status="vacant",
                command_id=command_id,
                request_fingerprint=fingerprint,
                committed_version=int(reviewed["version"]) + 1,
                created_at=FIXED_NOW.replace(tzinfo=None),
            )
        )
        session.commit()

    result = workflow.apply_leave_adjustment(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason=reason,
        command_id=command_id,
        expected_week_version=int(reviewed["version"]),
    )

    assert result.idempotent is True
    assert result.share_ids_to_revoke == (share_id,)
    with workflow._session() as session:
        outbox = session.scalar(
            select(ExternalShareOutboxRecord).where(
                ExternalShareOutboxRecord.share_id == share_id
            )
        )
        assert outbox is not None
        share_command = session.get(OperationCommandRecord, outbox.command_id)
        replay_command = session.get(OperationCommandRecord, command_id)
        assert share_command is not None
        assert replay_command is not None
        assert outbox.status == "revocation_pending"
        assert share_command.status == "committed"
        assert "shareKey" not in share_command.result_json
        assert "deliveryPayload" not in share_command.result_json
        assert "ciphertext" not in share_command.result_json
        assert json.loads(replay_command.result_json)["shareIdsToRevoke"] == [share_id]


def test_revocation_retry_only_replays_worker_delete_and_preserves_roster_change(
    tmp_path,
    monkeypatch,
) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    service.create_share(roster_id, command_id="share-before-revocation-retry")
    old_share_id = str(gateway.created[-1]["shareId"])
    reviewed = workflow.roster_week(roster_id)
    assignment = next(row for row in workflow.assignments(roster_id) if row["status"] == "active")
    adjustment = workflow.apply_leave_adjustment(
        roster_week_id=roster_id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason="Prefect reported an absence after publication",
        command_id="adjust-before-revocation-retry",
        expected_week_version=int(reviewed["version"]),
    )
    service.create_share(roster_id, command_id="share-after-revocation-retry")
    new_share_id = str(gateway.created[-1]["shareId"])
    committed_version = int(workflow.roster_week(roster_id)["version"])
    adjustment_count = workflow.leave_adjustment_count(roster_id)

    revoker = FlakyRevocationService()
    context = PageContext.create(
        Principal(AccessMode.LOCAL_MAINTENANCE, "revocation-retry-test")
    )
    monkeypatch.setattr(access_control, "current_page_context", lambda: context)
    monkeypatch.setattr(
        access_control,
        "_public_share_service",
        lambda *_args, **_kwargs: revoker,
    )

    assert access_control.revoke_roster_shares(
        workflow, adjustment.share_ids_to_revoke
    ) == (0, 1)
    assert workflow.pending_external_share_revocations() == [
        {"shareId": old_share_id, "rosterWeekId": roster_id, "attempts": 2}
    ]
    assert workflow.leave_adjustment_count(roster_id) == adjustment_count
    assert int(workflow.roster_week(roster_id)["version"]) == committed_version
    assert workflow.external_share_outbox("share-after-revocation-retry")["status"] == "delivered"

    assert access_control.revoke_roster_shares(
        workflow, adjustment.share_ids_to_revoke
    ) == (1, 0)
    assert workflow.pending_external_share_revocations() == []
    assert revoker.calls == [old_share_id, old_share_id]
    assert old_share_id != new_share_id
    assert workflow.leave_adjustment_count(roster_id) == adjustment_count
    assert int(workflow.roster_week(roster_id)["version"]) == committed_version
    assert workflow.external_share_outbox("share-after-revocation-retry")["status"] == "delivered"


def test_withdrawal_revokes_response_lost_share_instead_of_cancelling_it(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = CommitThenLoseGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )
    with pytest.raises(PublicRosterShareError, match="simulated response loss"):
        service.create_share(roster_id, command_id="response-lost-before-withdrawal")
    share_id = str(gateway.created[0]["shareId"])
    current = workflow.roster_week(roster_id)

    result = workflow.withdraw_published_roster(
        roster_id,
        expected_version=int(current["version"]),
        reason="Published the wrong reviewed roster",
        command_id="withdraw-response-lost-share",
    )

    assert result.share_ids_to_revoke == (share_id,)
    assert workflow.pending_external_share_revocations() == [
        {"shareId": share_id, "rosterWeekId": roster_id, "attempts": 1}
    ]


def test_two_admin_tabs_replay_one_exact_share_command_concurrently(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    gateway = ConcurrentIdempotentGateway()
    service = PublicRosterShareService(
        workflow,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = list(
            executor.map(
                lambda _index: service.create_share(
                    roster_id,
                    command_id="public-share-concurrent-test",
                ),
                range(2),
            )
        )

    assert len(gateway.created) == 2
    assert gateway.created[0] == gateway.created[1]
    assert receipts[0].share_id == receipts[1].share_id
    assert receipts[0].share_url == receipts[1].share_url
    outbox = workflow.external_share_outbox("public-share-concurrent-test")
    assert outbox is not None
    assert outbox["status"] == "delivered"
    assert outbox["attempts"] == 2


def test_share_outbox_audit_uses_verified_admin_actor_and_request_reference(tmp_path) -> None:
    workflow, roster_id = _workflow(tmp_path)
    context = PageContext.create(
        Principal(
            AccessMode.ADMIN,
            "admin@example.test",
            session_id="admin-session",
        ),
        request_reference="REQ-SHARE-123",
    )
    adapter = PageContextWorkflowAdapter(workflow, context)
    gateway = RecordingGateway()
    service = PublicRosterShareService(
        adapter,
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    service.create_share(roster_id, command_id="public-share-audit-test")

    with workflow._session() as session:
        events = session.scalars(
            select(AuditEventRecord)
            .where(
                AuditEventRecord.event_type.in_(
                    ("external_share_queued", "external_share_delivered")
                )
            )
            .order_by(AuditEventRecord.id)
        ).all()
    assert [event.event_type for event in events] == [
        "external_share_queued",
        "external_share_delivered",
    ]
    assert all(event.actor_mode == AccessMode.ADMIN.value for event in events)
    assert all(event.actor_subject == "admin@example.test" for event in events)
    assert all(event.command_id == "public-share-audit-test" for event in events)
    assert all(event.request_reference == "REQ-SHARE-123" for event in events)


def test_guest_adapter_mode_is_rejected_before_snapshot_or_gateway_access() -> None:
    class GuestLikeWorkflow:
        access_mode = AccessMode.GUEST

    gateway = RecordingGateway()
    service = PublicRosterShareService(
        GuestLikeWorkflow(),
        settings=_settings(),
        gateway=gateway,
        now=lambda: FIXED_NOW,
    )

    with pytest.raises(CapabilityDeniedError):
        service.create_share(1)
    assert gateway.created == []
