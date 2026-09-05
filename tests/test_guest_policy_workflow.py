from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from threading import Barrier

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import (
    GuestCapacityError, GuestSnapshotError, GuestWorkspaceError, GuestWorkspaceRegistry,
)
from nicegui_app.services.workflow_types import WorkflowConflictError
from roster_core.policy_settings import (
    PolicyCommandConflict, PolicyNotFound, PolicySettingsError, PolicyStorageError, PolicyVersionConflict,
)
from roster_policy.configurable import BusinessId, WeeklyPolicy, default_weekly_policy
from roster_policy.policy_codec import encode_weekly_policy


SECRET = b"guest-policy-workflow-test-secret-32-bytes"
YEAR = 2026


def custom_policy(room="509"):
    return WeeklyPolicy(tuple(
        replace(post, room=room) if post.business is BusinessId.STUDY_ROOM else post
        for post in default_weekly_policy().businesses
    ))


def adapter(registry, *, session="sid", workspace="work", tab="tab", publisher=None):
    context = PageContext.create(Principal(
        mode=AccessMode.GUEST, subject=f"guest:{session}", session_id=session,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    ), request_reference="GUEST-POLICY-TEST")
    return GuestWorkspaceAdapter(
        context, registry, workspace_id=workspace, tab_id=tab, snapshot_publisher=publisher,
    )


def view(registry):
    return registry.get_workspace(session_id="sid", workspace_id="work", tab_id="tab")


def test_policy_history_reset_and_original_receipts_live_in_one_workspace():
    registry = GuestWorkspaceRegistry(SECRET)
    published = []
    workflow = adapter(registry, publisher=published.append)
    with pytest.raises(PolicyNotFound):
        workflow.policy_current(YEAR)
    original = workflow.initialize_policy(YEAR, command_id="init")
    saved = workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    preview = workflow.policy_reset_preview(YEAR)
    assert view(registry).revision == 2
    reset = workflow.reset_policy(preview, command_id="reset")
    latest = workflow.save_policy(YEAR, custom_policy("600"), expected_revision=3, command_id="later")
    reopened = adapter(registry)
    assert reopened.policy_current(YEAR) == latest.policy_revision
    assert reopened.policy_revision(YEAR, 1) == original.policy_revision
    assert reopened.policy_revision(YEAR, 2) == saved.policy_revision
    assert reopened.initialize_policy(YEAR, command_id="init") == replace(original, replayed=True)
    assert reopened.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save") == replace(saved, replayed=True)
    assert reopened.reset_policy(preview, command_id="reset") == replace(reset, replayed=True)
    assert reopened.policy_command_result(command_id="save") == replace(saved, replayed=True)
    assert reopened.policy_command_result(command_id="missing") is None
    assert original.backup_status == saved.backup_status == reset.backup_status == "not_applicable"
    assert [item.revision for item in published] == [1, 2, 3, 4]
    assert view(registry).revision == 4


@pytest.mark.parametrize("difference", ["operation", "year", "revision", "policy"])
def test_same_command_cannot_change_policy_intent(difference):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    preview = workflow.policy_reset_preview(YEAR)
    original = workflow.save_policy(YEAR, default_weekly_policy(), expected_revision=1, command_id="save")
    before = view(registry)
    with pytest.raises(PolicyCommandConflict):
        if difference == "operation":
            workflow.reset_policy(preview, command_id="save")
        else:
            workflow.save_policy(
                YEAR + 1 if difference == "year" else YEAR,
                custom_policy() if difference == "policy" else default_weekly_policy(),
                expected_revision=2 if difference == "revision" else 1, command_id="save",
            )
    assert view(registry) == before
    assert workflow.policy_command_result(command_id="save") == replace(original, replayed=True)


def test_policy_commands_share_the_existing_receipt_identity_with_other_guest_commands():
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    original = view(registry)
    registry.replace_state(
        session_id="sid", workspace_id="work", tab_id="tab", expected_revision=0,
        command_id="same", state=original.state,
    )
    with pytest.raises(PolicyCommandConflict):
        workflow.initialize_policy(YEAR, command_id="same")
    assert workflow.policy_command_result(command_id="same") is None
    assert view(registry).revision == 1
    assert workflow.initialize_policy(YEAR, command_id="new").policy_revision.revision == 1


@pytest.mark.parametrize("invalid", [None, True, "", " \t", "x" * 65, "中" * 43, "😀" * 33, "id-\ud800"])
def test_invalid_command_identity_is_rejected_before_mutation_or_receipt(invalid):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    before = view(registry)
    with pytest.raises((PolicySettingsError, GuestCapacityError)):
        workflow.initialize_policy(YEAR, command_id=invalid)
    with pytest.raises((PolicySettingsError, GuestCapacityError)):
        workflow.policy_command_result(command_id=invalid)
    assert view(registry) == before
    assert workflow.initialize_policy(YEAR, command_id="valid").policy_revision.revision == 1


@pytest.mark.parametrize("valid", ["x" * 64, "中" * 42, "😀" * 32, "  canonical\t"])
def test_new_policy_ids_have_both_shared_character_and_guest_utf8_limits(valid):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    result = workflow.initialize_policy(YEAR, command_id=valid)
    assert result.command_id == valid.strip()
    assert workflow.initialize_policy(YEAR, command_id=valid.strip()) == replace(result, replayed=True)


def test_stale_save_and_reset_leave_state_unchanged_and_do_not_consume_command():
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    preview = workflow.policy_reset_preview(YEAR)
    latest = workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    with pytest.raises(PolicyVersionConflict):
        workflow.save_policy(YEAR, custom_policy("600"), expected_revision=1, command_id="stale")
    with pytest.raises(PolicyVersionConflict):
        workflow.reset_policy(preview, command_id="stale-reset")
    assert workflow.policy_command_result(command_id="stale") is None
    assert workflow.policy_command_result(command_id="stale-reset") is None
    assert workflow.policy_current(YEAR) == latest.policy_revision
    assert workflow.save_policy(YEAR, custom_policy("600"), expected_revision=2, command_id="stale").policy_revision.revision == 3


def test_invalid_policy_and_tampered_reset_preview_do_not_consume_receipts():
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    forged = custom_policy()
    object.__setattr__(forged, "businesses", (object(),))
    with pytest.raises(PolicySettingsError):
        workflow.save_policy(YEAR, forged, expected_revision=1, command_id="save")
    saved = workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    preview = workflow.policy_reset_preview(YEAR)
    with pytest.raises(PolicySettingsError):
        workflow.reset_policy(replace(preview, changes=()), command_id="reset")
    assert workflow.policy_current(YEAR) == saved.policy_revision
    assert workflow.policy_command_result(command_id="reset") is None
    assert workflow.reset_policy(preview, command_id="reset").policy_revision.revision == 3


def test_capacity_failure_does_not_publish_state_or_receipt_and_retry_can_succeed():
    registry = GuestWorkspaceRegistry(SECRET)
    published = []
    workflow = adapter(registry, publisher=published.append)
    original = workflow.initialize_policy(YEAR, command_id="init")
    before = view(registry)
    original_limit = registry.max_state_bytes
    registry.max_state_bytes = len(json.dumps(before.state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) + 1
    with pytest.raises(GuestCapacityError):
        workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    assert view(registry) == before
    assert workflow.policy_command_result(command_id="save") is None
    assert len(published) == 1
    registry.max_state_bytes = original_limit
    assert workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save").policy_revision.revision == 2
    assert workflow.policy_revision(YEAR, 1) == original.policy_revision


def test_expiry_rejects_policy_reads_writes_and_receipt_lookup():
    now = [1000]
    registry = GuestWorkspaceRegistry(SECRET, clock=lambda: now[0], ttl_seconds=30)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    now[0] = 1030
    for action in (
        lambda: workflow.policy_current(YEAR),
        lambda: workflow.policy_revision(YEAR, 1),
        lambda: workflow.policy_reset_preview(YEAR),
        lambda: workflow.policy_command_result(command_id="init"),
        lambda: workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save"),
    ):
        with pytest.raises(GuestWorkspaceError):
            action()
    assert registry.active_session_count == 0


@pytest.mark.parametrize("scope", ["session", "tab"])
def test_policy_state_receipts_and_signed_snapshots_do_not_cross_guest_workspaces(scope):
    registry = GuestWorkspaceRegistry(SECRET)
    first = adapter(registry)
    second = adapter(registry, session="other" if scope == "session" else "sid", workspace="other", tab="other")
    first.initialize_policy(YEAR, command_id="same")
    first.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    assert second.policy_command_result(command_id="same") is None
    with pytest.raises(PolicyNotFound):
        second.policy_current(YEAR)
    assert second.initialize_policy(YEAR, command_id="same").policy_revision.revision == 1
    assert second.policy_current(YEAR).policy == default_weekly_policy()
    token = registry.seal_snapshot(session_id="sid", workspace_id="work", tab_id="tab")
    with pytest.raises(GuestSnapshotError):
        registry.restore_snapshot(
            token, session_id="other" if scope == "session" else "sid", workspace_id="other", tab_id="other",
        )


@pytest.mark.parametrize("damage", ["document", "current", "schema", "boolean", "unknown", "history-rewrite", "history-remove", "huge-year"])
def test_forged_state_and_newer_signed_snapshot_cannot_replace_policy_history(damage):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    original = workflow.initialize_policy(YEAR, command_id="init")
    before = view(registry)
    state = deepcopy(before.state)
    payload = state["policySettings"]
    record = payload["years"][str(YEAR)]
    if damage == "document":
        record["revisions"][0] = '{"schemaVersion":99}'
    elif damage == "current":
        record["currentRevision"] = 2
    elif damage == "schema":
        payload["schemaVersion"] = 2
    elif damage == "boolean":
        record["currentRevision"] = True
    elif damage == "unknown":
        record["secondAuthority"] = {}
    elif damage == "history-rewrite":
        record["revisions"][0] = encode_weekly_policy(custom_policy())
    elif damage == "huge-year":
        payload["years"] = {"9" * 5000: record}
    else:
        del state["policySettings"]
    with pytest.raises(PolicyStorageError):
        registry.replace_state(
            session_id="sid", workspace_id="work", tab_id="tab", expected_revision=1,
            command_id="forged", state=state,
        )
    token = registry.codec.seal(
        session_id="sid", workspace_id="work", tab_id="tab", revision=2, state=state,
    )
    with pytest.raises(PolicyStorageError):
        registry.restore_snapshot(token, session_id="sid", workspace_id="work", tab_id="tab")
    assert view(registry) == before
    assert workflow.policy_command_result(command_id="forged") is None
    assert workflow.policy_command_result(command_id="init") == replace(original, replayed=True)


def test_bounded_receipt_eviction_returns_none_and_never_reconstructs_latest_as_old_result():
    registry = GuestWorkspaceRegistry(SECRET, max_receipts_per_workspace=2)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    saved = workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    workflow.save_policy(YEAR, custom_policy("600"), expected_revision=2, command_id="later")
    assert workflow.policy_command_result(command_id="init") is None
    with pytest.raises(PolicyVersionConflict):
        workflow.initialize_policy(YEAR, command_id="init")
    assert workflow.policy_command_result(command_id="save") == replace(saved, replayed=True)
    assert view(registry).revision == 3


def test_snapshot_publisher_failure_after_commit_can_be_resolved_by_original_receipt():
    registry = GuestWorkspaceRegistry(SECRET)

    def fail_publish(_view):
        raise RuntimeError("injected browser delivery failure")

    workflow = adapter(registry, publisher=fail_publish)
    with pytest.raises(RuntimeError, match="delivery failure"):
        workflow.initialize_policy(YEAR, command_id="init")
    receipt = workflow.policy_command_result(command_id="init")
    assert receipt is not None
    assert receipt.policy_revision.revision == 1
    assert receipt.replayed
    assert workflow.initialize_policy(YEAR, command_id="init") == receipt
    assert view(registry).revision == 1


@pytest.mark.parametrize("operation", ["reset", "restore"])
def test_explicit_demo_reset_and_restore_do_not_replay_stale_policy_receipts(operation):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    original = workflow.initialize_policy(YEAR, command_id="init")
    checkpoint = workflow.create_verified_backup()
    workflow.save_policy(YEAR, custom_policy(), expected_revision=1, command_id="save")
    if operation == "reset":
        workflow.reset_demo_fixture()
        with pytest.raises(PolicyNotFound):
            workflow.policy_current(YEAR)
        assert workflow.initialize_policy(YEAR, command_id="init").policy_revision.revision == 1
    else:
        workflow.restore_backup(checkpoint)
        assert workflow.policy_current(YEAR) == original.policy_revision
        assert workflow.policy_command_result(command_id="init") is None
        assert workflow.save_policy(YEAR, custom_policy("600"), expected_revision=1, command_id="save").policy_revision.revision == 2
    if operation == "reset":
        assert workflow.policy_command_result(command_id="save") is None


@pytest.mark.parametrize("same_command", [True, False])
def test_concurrent_guest_policy_commands_remain_atomic(same_command):
    registry = GuestWorkspaceRegistry(SECRET)
    workflow = adapter(registry)
    workflow.initialize_policy(YEAR, command_id="init")
    barrier = Barrier(2)

    def save(index):
        peer = adapter(registry)
        barrier.wait(timeout=5)
        try:
            return peer.save_policy(
                YEAR, custom_policy(), expected_revision=1,
                command_id="same" if same_command else f"save-{index}",
            )
        except (PolicyVersionConflict, WorkflowConflictError) as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, (1, 2)))
    if same_command:
        assert sum(result.replayed for result in results) == 1
        assert all(result.policy_revision.revision == 2 for result in results)
    else:
        assert sum(isinstance(result, (PolicyVersionConflict, WorkflowConflictError)) for result in results) == 1
    assert view(registry).revision == 2
    assert workflow.policy_current(YEAR).revision == 2
