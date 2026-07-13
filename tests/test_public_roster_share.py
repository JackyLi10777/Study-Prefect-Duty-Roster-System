from __future__ import annotations

from base64 import urlsafe_b64decode
from datetime import date, datetime, timedelta, timezone
import json
from urllib.error import HTTPError

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import pytest

from nicegui_app.services.public_roster_share import (
    PublicRosterShareError,
    PublicRosterShareService,
    PublicRosterShareSettings,
    CloudflarePublicRosterShareGateway,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


WEEK_START = date(2026, 9, 7)
FIXED_NOW = datetime(2026, 9, 7, 8, 0, tzinfo=timezone.utc)


class FakeGateway:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.revoked: list[str] = []
        self.listed: list[dict[str, object]] = []

    def create(self, payload):
        self.created.append(dict(payload))
        return None

    def list(self):
        return list(self.listed)

    def revoke(self, share_id: str):
        self.revoked.append(share_id)


def _settings(*, enabled: bool = True) -> PublicRosterShareSettings:
    return PublicRosterShareSettings(
        enabled=enabled,
        base_url="https://roster-view.example.workers.dev",
        admin_token="a" * 48,
    )


@pytest.fixture
def workflow(tmp_path) -> RosterWorkflow:
    service = RosterWorkflow(
        database_path=tmp_path / "sing-yin.sqlite3",
        backup_dir=tmp_path / "backups",
    )
    service.bootstrap()
    return service


def _published(workflow: RosterWorkflow):
    draft = workflow.generate_and_save_draft(WEEK_START)
    workflow.publish(draft.id, expected_week_version=draft.version)
    return draft


def _unpad_base64url(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _decrypt(receipt, payload: dict[str, object]) -> dict[str, object]:
    fragment = receipt.share_url.split("#", 1)[1]
    share_id, encoded_key = fragment.split(".", 1)
    assert share_id == receipt.share_id == payload["shareId"]
    plaintext = AESGCM(_unpad_base64url(encoded_key)).decrypt(
        _unpad_base64url(str(payload["nonce"])),
        _unpad_base64url(str(payload["ciphertext"])),
        f"sing-yin-roster-share-v1:{share_id}".encode("ascii"),
    )
    return json.loads(plaintext.decode("utf-8"))


def test_share_is_published_only_and_requires_complete_configuration(workflow: RosterWorkflow) -> None:
    draft = workflow.generate_and_save_draft(WEEK_START)

    disabled = PublicRosterShareService(workflow, settings=_settings(enabled=False), gateway=FakeGateway())
    with pytest.raises(PublicRosterShareError, match="not enabled"):
        disabled.create_share(draft.id)

    incomplete = PublicRosterShareService(
        workflow,
        settings=PublicRosterShareSettings(True, "http://viewer.invalid", "short"),
        gateway=FakeGateway(),
    )
    assert incomplete.settings.enabled is True
    assert incomplete.settings.configured is False
    with pytest.raises(PublicRosterShareError, match="administrator configuration"):
        incomplete.create_share(draft.id)

    configured = PublicRosterShareService(workflow, settings=_settings(), gateway=FakeGateway())
    with pytest.raises(PublicRosterShareError, match="Only a published roster"):
        configured.create_share(draft.id)


def test_settings_load_only_the_dedicated_public_viewer_environment(monkeypatch) -> None:
    monkeypatch.setenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL", "https://viewer.example.workers.dev/")
    monkeypatch.setenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN", "s" * 48)
    monkeypatch.setenv("SING_YIN_PUBLIC_ROSTER_VIEWER_TIMEOUT_SECONDS", "7")

    settings = PublicRosterShareSettings.from_environment()

    assert settings.enabled is True
    assert settings.configured is True
    assert settings.base_url == "https://viewer.example.workers.dev"
    assert settings.admin_token == "s" * 48
    assert settings.timeout_seconds == 7


def test_encrypted_public_snapshot_contains_only_approved_roster_fields(workflow: RosterWorkflow) -> None:
    roster = _published(workflow)
    gateway = FakeGateway()
    service = PublicRosterShareService(workflow, settings=_settings(), gateway=gateway, now=lambda: FIXED_NOW)

    receipt = service.create_share(roster.id)

    assert len(gateway.created) == 1
    outbound = gateway.created[0]
    serialized_outbound = json.dumps(outbound, ensure_ascii=False)
    for assignment in workflow.assignments(roster.id):
        assert str(assignment["prefectName"]) not in serialized_outbound
        assert str(assignment["prefectId"]) not in serialized_outbound
    snapshot = _decrypt(receipt, outbound)
    assert set(outbound) == {
        "schemaVersion",
        "shareId",
        "weekStart",
        "createdAt",
        "expiresAt",
        "nonce",
        "ciphertext",
    }
    assert set(snapshot) == {
        "schemaVersion",
        "schoolNameZh",
        "schoolNameEn",
        "titleZh",
        "titleEn",
        "weekStart",
        "version",
        "days",
        "rows",
    }
    assert snapshot["weekStart"] == WEEK_START.isoformat()
    assert len(snapshot["days"]) == 5
    assert len(snapshot["rows"]) == 6
    assert all(set(day) == {"code", "date", "labelZh", "labelEn"} for day in snapshot["days"])
    assert all(
        set(row) == {"postCode", "slotIndex", "labelZh", "labelEn", "dutyTime", "cells"}
        for row in snapshot["rows"]
    )
    assert all(row["dutyTime"] == {"start": "15:40", "end": "17:00"} for row in snapshot["rows"])
    cells = [cell for row in snapshot["rows"] for cell in row["cells"]]
    assert all(set(cell) in ({"status"}, {"status", "nameZh"}) for cell in cells)
    assert all(cell.get("nameZh", "").isascii() is False for cell in cells if "nameZh" in cell)
    assert {cell["status"] for cell in cells} == {"assigned", "closed"}
    banned_keys = {
        "id",
        "rosterWeekId",
        "prefectId",
        "role",
        "roleCode",
        "leave",
        "historyWeight",
        "fairness",
        "audit",
        "weight",
    }

    def all_keys(value):
        if isinstance(value, dict):
            yield from value.keys()
            for child in value.values():
                yield from all_keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from all_keys(child)

    assert banned_keys.isdisjoint(set(all_keys(snapshot)))
    assert receipt.share_url.startswith("https://roster-view.example.workers.dev/view#")
    assert receipt.created_at == FIXED_NOW
    assert receipt.expires_at == datetime(2026, 9, 13, 15, 59, 59, tzinfo=timezone.utc)


def test_share_refuses_non_chinese_authoritative_name(workflow: RosterWorkflow) -> None:
    roster = _published(workflow)
    original_assignments = workflow.assignments

    def assignments_with_invalid_name(roster_week_id: int):
        rows = original_assignments(roster_week_id)
        return [{**row, "prefectName": "English Name"} if index == 0 else row for index, row in enumerate(rows)]

    workflow.assignments = assignments_with_invalid_name  # type: ignore[method-assign]
    service = PublicRosterShareService(workflow, settings=_settings(), gateway=FakeGateway(), now=lambda: FIXED_NOW)

    with pytest.raises(PublicRosterShareError, match="Chinese display name"):
        service.create_share(roster.id)


def test_post_publication_vacancy_is_shared_without_original_name_or_adjustment_reason(
    workflow: RosterWorkflow,
) -> None:
    roster = _published(workflow)
    assignment = next(item for item in workflow.assignments(roster.id) if item["postCode"] == "ROOM_302")
    workflow.apply_leave_adjustment(
        roster_week_id=roster.id,
        assignment_id=int(assignment["id"]),
        replacement_prefect_id=None,
        reason="Approved confidential reason",
        command_id="public-snapshot-vacancy",
        expected_week_version=int(workflow.roster_week(roster.id)["version"]),
    )
    gateway = FakeGateway()
    service = PublicRosterShareService(workflow, settings=_settings(), gateway=gateway, now=lambda: FIXED_NOW)

    receipt = service.create_share(roster.id)
    snapshot = _decrypt(receipt, gateway.created[0])
    serialized = json.dumps(snapshot, ensure_ascii=False)
    day_index = next(
        index for index, item in enumerate(snapshot["days"]) if item["code"] == assignment["day"]
    )
    shared_row = next(
        item
        for item in snapshot["rows"]
        if item["postCode"] == assignment["postCode"] and item["slotIndex"] == assignment["slotIndex"]
    )

    assert shared_row["cells"][day_index] == {"status": "vacant"}
    assert "nameZh" not in shared_row["cells"][day_index]
    assert "Approved confidential reason" not in serialized
    assert "VACANT" not in serialized


def test_list_maps_minimum_lifecycle_metadata_to_local_roster_and_revoke(workflow: RosterWorkflow) -> None:
    roster = _published(workflow)
    gateway = FakeGateway()
    gateway.listed = [
        {
            "shareId": "valid_share_identifier_1234",
            "weekStart": WEEK_START.isoformat(),
            "createdAt": "2026-09-07T08:00:00Z",
            "expiresAt": "2026-09-13T15:59:59Z",
        }
    ]
    service = PublicRosterShareService(workflow, settings=_settings(), gateway=gateway)

    shares = service.list_shares()
    service.revoke_share(shares[0].share_id)

    assert shares[0].roster_week_id == roster.id
    assert shares[0].week_start == WEEK_START
    assert shares[0].created_at == FIXED_NOW
    assert gateway.revoked == ["valid_share_identifier_1234"]


def test_expiry_must_be_time_zone_aware_and_is_bounded(workflow: RosterWorkflow) -> None:
    roster = _published(workflow)
    service = PublicRosterShareService(workflow, settings=_settings(), gateway=FakeGateway(), now=lambda: FIXED_NOW)

    with pytest.raises(PublicRosterShareError, match="time zone"):
        service.create_share(roster.id, expires_at=datetime(2026, 9, 8, 8, 0))
    with pytest.raises(PublicRosterShareError, match="in the future"):
        service.create_share(roster.id, expires_at=FIXED_NOW + timedelta(seconds=30))
    with pytest.raises(PublicRosterShareError, match="at most 31 days"):
        service.create_share(roster.id, expires_at=FIXED_NOW + timedelta(days=32))


def test_cloudflare_gateway_never_exposes_raw_network_errors_or_admin_token() -> None:
    settings = _settings()

    def rejected(*_args, **_kwargs):
        raise HTTPError("https://viewer", 403, "secret leaked", {}, None)

    gateway = CloudflarePublicRosterShareGateway(settings, opener=rejected)

    with pytest.raises(PublicRosterShareError) as captured:
        gateway.list()
    assert "credential" in str(captured.value)
    assert settings.admin_token not in str(captured.value)
    assert "secret leaked" not in str(captured.value)


def test_cloudflare_gateway_uses_bearer_auth_and_same_origin_json_endpoint() -> None:
    settings = _settings()
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit):
            return b'{"shares":[]}'

    def open_request(request, *, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return Response()

    gateway = CloudflarePublicRosterShareGateway(settings, opener=open_request)

    assert gateway.list() == []
    assert captured == {
        "url": "https://roster-view.example.workers.dev/api/admin/shares",
        "method": "GET",
        "authorization": f"Bearer {settings.admin_token}",
        "timeout": 10.0,
    }
