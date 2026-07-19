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
    ExternalShareOutboxRecord,
    OperationCommandRecord,
)
from nicegui_app.services.operation_context import PageContextWorkflowAdapter
from nicegui_app.services.public_roster_share import (
    PublicRosterShareError,
    PublicRosterShareService,
    PublicRosterShareSettings,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


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


def _unpad(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


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
