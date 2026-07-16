from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from nicegui_app.access_context import AccessMode, PageContext, Principal
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
