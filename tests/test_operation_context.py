from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal, PrincipalExpiredError
from nicegui_app.gateway_identity import OriginPrincipalError
import nicegui_app.runtime as runtime
from nicegui_app.services.roster_workflow import PrefectInput, RosterWorkflow
from nicegui_app.services.operation_context import (
    PageContextWorkflowAdapter,
    current_operation_actor,
)


@dataclass
class _WorkflowProbe:
    observed: object = None

    def write(self, value: str) -> str:
        self.observed = current_operation_actor()
        return value


def test_page_context_adapter_binds_and_cleans_verified_actor() -> None:
    workflow = _WorkflowProbe()
    context = PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console"),
        request_reference="REQ-123",
    )

    adapter = PageContextWorkflowAdapter(workflow, context)

    assert adapter.write("saved") == "saved"
    assert workflow.observed is not None
    assert workflow.observed.mode == "local_maintenance"
    assert workflow.observed.subject == "local-console"
    assert workflow.observed.request_reference == "REQ-123"
    assert workflow.observed.command_id.startswith("ui-")
    assert current_operation_actor() is None


def test_page_context_adapter_delegates_non_callable_attributes() -> None:
    workflow = _WorkflowProbe()
    workflow.observed = "ready"
    context = PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console"),
    )

    assert PageContextWorkflowAdapter(workflow, context).observed == "ready"


def test_page_context_adapter_preserves_an_explicit_idempotency_key() -> None:
    class _CommandProbe:
        observed = None

        def write(self, *, command_id: str) -> str:
            self.observed = current_operation_actor()
            return command_id

    workflow = _CommandProbe()
    context = PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console"),
    )

    result = PageContextWorkflowAdapter(workflow, context).write(command_id="command-123")

    assert result == "command-123"
    assert workflow.observed.command_id == "command-123"


def test_page_context_adapter_rechecks_expiry_at_the_write_boundary() -> None:
    now = datetime.now(timezone.utc)
    context = PageContext.create(
        Principal(
            mode=AccessMode.ADMIN,
            subject="verified-head-prefect",
            session_id="admin-session",
            expires_at=now - timedelta(seconds=1),
        )
    )
    adapter = PageContextWorkflowAdapter(_WorkflowProbe(), context)
    with pytest.raises(PrincipalExpiredError, match="expired"):
        adapter.write("must-not-run")


def test_retry_sensitive_write_fails_closed_without_stable_command_id() -> None:
    class _CommandProbe:
        def write(self, *, command_id: str) -> str:
            return command_id

    context = PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console")
    )
    with pytest.raises(ValueError, match="stable command_id"):
        PageContextWorkflowAdapter(_CommandProbe(), context).write(command_id="")


@pytest.mark.parametrize("mode", [AccessMode.PUBLIC, AccessMode.GUEST])
def test_official_workflow_adapter_rejects_non_administrative_modes(mode) -> None:
    principal = Principal(
        mode=mode,
        subject=f"{mode.value}-principal",
        session_id="guest-session" if mode is AccessMode.GUEST else None,
        expires_at=(
            datetime.now(timezone.utc) + timedelta(minutes=10)
            if mode is AccessMode.GUEST
            else None
        ),
    )

    with pytest.raises(PermissionError, match="administrative principal"):
        PageContextWorkflowAdapter(_WorkflowProbe(), PageContext.create(principal))


def test_runtime_never_resolves_official_workflow_for_public_traffic(monkeypatch) -> None:
    context = PageContext.create(
        Principal(mode=AccessMode.PUBLIC, subject="public-entry")
    )
    admin_resolution_attempted = False

    def fail_admin_resolution():
        nonlocal admin_resolution_attempted
        admin_resolution_attempted = True
        raise AssertionError("public traffic must not resolve the official workflow")

    monkeypatch.setattr(runtime, "current_page_context", lambda: context)
    monkeypatch.setattr(runtime, "get_admin_workflow", fail_admin_resolution)

    with pytest.raises(OriginPrincipalError, match="public traffic"):
        runtime.get_workflow()

    assert admin_resolution_attempted is False


def test_verified_actor_and_command_reference_are_saved_with_audited_write(tmp_path) -> None:
    database_path = tmp_path / "sing-yin.sqlite3"
    workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=tmp_path / "backups",
    )
    workflow.bootstrap()
    context = PageContext.create(
        Principal(
            mode=AccessMode.ADMIN,
            subject="verified-head-prefect",
            session_id="admin-session-1",
        ),
        request_reference="REQ-AUDIT-123",
    )

    PageContextWorkflowAdapter(workflow, context).create_prefect(
        PrefectInput(
            name_zh="許朗然",
            form="F.4",
            class_name="4H",
            role_code="study_prefect",
            available_days=("MONDAY", "WEDNESDAY"),
        ),
        command_id="audit-prefect-create",
    )

    with sqlite3.connect(database_path) as connection:
        actor_subject, actor_mode, command_id, request_reference = connection.execute(
            "SELECT actor_subject, actor_mode, command_id, request_reference "
            "FROM audit_events WHERE event_type = 'prefect_created' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert actor_subject == "verified-head-prefect"
    assert actor_mode == "admin"
    assert command_id == "audit-prefect-create"
    assert request_reference == "REQ-AUDIT-123"
