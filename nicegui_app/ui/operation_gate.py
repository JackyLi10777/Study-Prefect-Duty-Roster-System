"""Client-side admission control for long-running operator actions."""

from __future__ import annotations

from collections.abc import MutableMapping


OPERATION_LOCK_KEY = "durable_operation_in_progress"


def claim_durable_operation(state: MutableMapping[str, object], operation_name: str) -> bool:
    """Claim a NiceGUI client before the handler reaches its first await.

    This reduces accidental repeated requests; workflow transactions and
    database constraints remain the authoritative correctness boundary.
    """
    if state.get(OPERATION_LOCK_KEY):
        return False
    state[OPERATION_LOCK_KEY] = operation_name
    return True


def release_durable_operation(state: MutableMapping[str, object]) -> None:
    """Release an operation claim; releasing an already-idle state is safe."""
    state.pop(OPERATION_LOCK_KEY, None)
