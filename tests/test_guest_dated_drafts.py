from dataclasses import replace

import pytest

from nicegui_app.services.guest_workspace import GuestCapacityError, GuestWorkspaceRegistry
from nicegui_app.services.workflow_types import WorkflowConflictError, WorkflowError
from tests.test_guest_policy_workflow import SECRET, adapter, custom_policy, view
from tests.test_dated_weekly_draft import MONDAY


def test_guest_uses_same_snapshot_and_replays_original_revision():
    registry = GuestWorkspaceRegistry(SECRET)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    first = guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert first.backup_status == "not_applicable"
    identity = first.snapshot.schedule_id
    assert len(first.snapshot.draft.cells) == 30
    guest.save_policy(2026, custom_policy(), expected_revision=1, command_id="policy")
    second = guest.adopt_dated_draft_policy(identity, 2, expected_version=1, command_id="adopt")
    assert second.snapshot.draft.policy_ref.revision == 2
    reopened = adapter(registry)
    assert reopened.dated_draft_snapshot(identity) == second.snapshot
    assert reopened.dated_draft_command_result(command_id="create").snapshot == first.snapshot
    assert reopened.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create") == replace(first, replayed=True)
    before = view(registry)
    with pytest.raises(WorkflowConflictError):
        reopened.regenerate_dated_draft(identity, expected_version=1, command_id="stale")
    assert view(registry) == before
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        reopened.roster_schedule_snapshot(identity)
    other = adapter(registry, session="other", workspace="other", tab="other")
    with pytest.raises(WorkflowError):
        other.dated_draft_snapshot(identity)


def test_guest_capacity_failure_is_atomic_and_keeps_original_history():
    registry = GuestWorkspaceRegistry(SECRET)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    before = view(registry)
    registry.max_state_bytes = len(str(before.state).encode("utf-8")) + 50
    with pytest.raises(GuestCapacityError):
        guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert view(registry) == before


def test_guest_original_receipt_eviction_and_explicit_reset_are_honest():
    registry = GuestWorkspaceRegistry(SECRET, max_receipts_per_workspace=2)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    first = guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    identity = first.snapshot.schedule_id
    guest.regenerate_dated_draft(identity, expected_version=1, command_id="second")
    guest.regenerate_dated_draft(identity, expected_version=2, command_id="third")
    assert guest.dated_draft_command_result(command_id="create") is None
    with pytest.raises(WorkflowConflictError):
        guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    guest.reset_demo_fixture()
    assert guest.dated_draft_command_result(command_id="third") is None
    with pytest.raises(WorkflowError):
        guest.dated_draft_snapshot(identity)


def test_guest_old_dispatchers_reject_new_draft_ids():
    from nicegui_app.services.roster_export import build_roster_pdf
    from nicegui_app.services.roster_image_export import build_roster_png_bundle
    registry = GuestWorkspaceRegistry(SECRET)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    identity = guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create").snapshot.schedule_id
    before = view(registry)
    for build in (build_roster_pdf, build_roster_png_bundle):
        with pytest.raises(WorkflowError, match="Dated drafts cannot"):
            build(guest, identity, practice=True)
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        guest.publish(identity, expected_week_version=1, command_id="forbidden-publish")
    with pytest.raises(WorkflowError, match="Dated drafts cannot"):
        guest.apply_leave_adjustment(roster_week_id=identity, assignment_id=1, replacement_prefect_id=None,
                                     expected_week_version=1, command_id="forbidden-adjust")
    assert view(registry) == before


def test_guest_cas_failure_does_not_initialize_ownership(monkeypatch):
    registry = GuestWorkspaceRegistry(SECRET)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    original = view(registry)
    commit = guest._commit

    def race(old_view, state, operation, **kwargs):
        registry.replace_state(session_id="sid", workspace_id="work", tab_id="tab",
                               expected_revision=old_view.revision, command_id="other-tab", state=old_view.state)
        return commit(old_view, state, operation, **kwargs)

    monkeypatch.setattr(guest, "_commit", race)
    with pytest.raises(WorkflowConflictError):
        guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    assert view(registry).state == original.state


def test_guest_exact_retry_never_repeats_generation_or_ownership(monkeypatch):
    registry = GuestWorkspaceRegistry(SECRET)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    first = guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create")
    before = view(registry)

    def forbidden(*args, **kwargs):
        raise AssertionError("Exact replay must not rerun generation or ownership")

    monkeypatch.setattr(guest, "_guest_generate_dated", forbidden)
    assert guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="create").snapshot == first.snapshot
    assert view(registry) == before


@pytest.mark.parametrize("legacy_date,use_legacy", [("2026-09-21", True), ("2026-08-31", False), ("2026-09-07", False)])
def test_guest_flexible_history_uses_latest_actual_date(legacy_date, use_legacy):
    from copy import deepcopy
    from datetime import date
    from roster_policy import AssistAssignmentMode, SchoolDay
    from roster_policy.configurable import BusinessId
    registry = GuestWorkspaceRegistry(SECRET, max_weeks=8)
    guest = adapter(registry)
    guest.initialize_policy(2026, command_id="init")
    dated = guest.create_dated_weekly_draft(2026, 1, MONDAY, command_id="dated", assist_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY)
    heads = [cell.prefect_id for cell in dated.snapshot.draft.cells if cell.key.business is BusinessId.ASSIST_IN_CHARGE]
    assert len(set(heads)) == 5
    shifted = heads[1:] + heads[:1]
    current = view(registry)
    state = deepcopy(current.state)
    state.setdefault("weeks", []).append({"id": 99, "weekStart": legacy_date, "status": "draft", "version": 1,
                                          "assignments": [{"day": day.name, "postCode": "ASSIST_IN_CHARGE", "prefectId": identity, "status": "active"}
                                                          for day, identity in zip(SchoolDay, shifted, strict=True)]})
    registry.replace_state(session_id="sid", workspace_id="work", tab_id="tab", expected_revision=current.revision,
                           command_id="fixture-prior", state=state)
    target = guest.create_dated_weekly_draft(2026, 1, date(2026, 9, 28), command_id="target", assist_mode=AssistAssignmentMode.FLEXIBLE_WEEKLY)
    assert dict(target.snapshot.draft.previous_assist) == dict(zip(SchoolDay, shifted if use_legacy else heads, strict=True))
