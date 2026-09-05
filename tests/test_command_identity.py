from __future__ import annotations

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.services.operation_context import (
    PageContextWorkflowAdapter,
    current_operation_actor,
)
from nicegui_app.services.workflow_parts.persistence import PersistenceWorkflowMixin
from nicegui_app.services.workflow_types import WorkflowError


class CommandProbe:
    observed = None

    def save(self, *, command_id: str) -> str:
        self.observed = current_operation_actor()
        return command_id


def adapter(probe: CommandProbe) -> PageContextWorkflowAdapter:
    return PageContextWorkflowAdapter(probe, PageContext.create(
        Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="test-console"),
        request_reference="test-request",
    ))


def test_actor_and_target_receive_the_same_normalized_command() -> None:
    probe = CommandProbe()
    result = adapter(probe).save(command_id="  policy-save-1  ")
    assert result == "policy-save-1"
    assert probe.observed.command_id == result
    assert current_operation_actor() is None


@pytest.mark.parametrize("invalid", [None, "", "  ", True, 123, "x" * 65, "bad\ud800"])
def test_invalid_command_never_reaches_the_target(invalid) -> None:
    probe = CommandProbe()
    with pytest.raises(ValueError, match="command_id"):
        adapter(probe).save(command_id=invalid)
    assert probe.observed is None
    assert current_operation_actor() is None


@pytest.mark.parametrize("value", ["a", "中" * 64, "x" * 64, "\U00020000-command", "  save-1  "])
def test_identity_is_valid_unicode_and_normalized_once(value) -> None:
    from roster_core.command_identity import normalize_command_id

    assert normalize_command_id(value) == value.strip()
    assert normalize_command_id(normalize_command_id(value)) == value.strip()
    assert PersistenceWorkflowMixin()._operation_command_id("policy_save", value) == value.strip()


@pytest.mark.parametrize("invalid", [None, "", "  ", False, 123, b"command", "x" * 65, "bad\udfff"])
def test_shared_identity_rejects_ambiguous_or_unrepresentable_values(invalid) -> None:
    from roster_core.command_identity import CommandIdentityError, normalize_command_id

    with pytest.raises(CommandIdentityError):
        normalize_command_id(invalid)


@pytest.mark.parametrize("invalid", ["", " ", False, 123, "x" * 65, "bad\ud800"])
def test_direct_workflow_does_not_silently_replace_an_invalid_explicit_id(invalid) -> None:
    with pytest.raises(WorkflowError, match="command ID"):
        PersistenceWorkflowMixin()._operation_command_id("policy_save", invalid)


def test_direct_workflow_keeps_its_optional_generated_identity() -> None:
    generated = PersistenceWorkflowMixin()._operation_command_id("policy_save", None)
    assert generated.startswith("policy_save:")
    assert len(generated) <= 64
