from __future__ import annotations

from nicegui_app.ui.operation_gate import claim_durable_operation, release_durable_operation


def test_durable_operation_gate_rejects_a_second_claim_until_release() -> None:
    state: dict[str, object] = {}

    assert claim_durable_operation(state, "generate") is True
    assert claim_durable_operation(state, "publish") is False

    release_durable_operation(state)

    assert claim_durable_operation(state, "publish") is True


def test_releasing_an_idle_operation_gate_is_safe() -> None:
    state: dict[str, object] = {}

    release_durable_operation(state)

    assert state == {}
