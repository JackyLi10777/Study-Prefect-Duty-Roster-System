"""Request-bound audit identity for transactional workflow operations.

The official workflow is process-local and shared by many NiceGUI clients.
Therefore actor information must never be stored on the workflow instance:
doing so would allow concurrent tabs to overwrite one another.  A context
variable keeps the verified principal attached to the current call instead.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from dataclasses import replace
from functools import wraps
from inspect import signature
from typing import Any, Callable, Iterator
from uuid import uuid4

from nicegui_app.access_context import AccessMode, PageContext


@dataclass(frozen=True)
class OperationActor:
    """Privacy-bounded identity copied from one verified page context."""

    mode: str
    subject: str
    request_reference: str
    command_id: str | None = None


_CURRENT_ACTOR: ContextVar[OperationActor | None] = ContextVar(
    "sing_yin_operation_actor",
    default=None,
)


def current_operation_actor() -> OperationActor | None:
    """Return the actor bound to the current workflow call, if any."""

    return _CURRENT_ACTOR.get()


@contextmanager
def bind_operation_actor(actor: OperationActor) -> Iterator[None]:
    """Bind one actor without leaking it into later requests."""

    token: Token[OperationActor | None] = _CURRENT_ACTOR.set(actor)
    try:
        yield
    finally:
        _CURRENT_ACTOR.reset(token)


class PageContextWorkflowAdapter:
    """Attach a verified page identity to every official workflow call."""

    def __init__(self, workflow: Any, context: PageContext) -> None:
        if context.principal.mode not in {
            AccessMode.ADMIN,
            AccessMode.LOCAL_MAINTENANCE,
        }:
            raise PermissionError(
                "the official workflow requires an administrative principal"
            )
        self._workflow = workflow
        self._principal = context.principal
        self._actor = OperationActor(
            mode=context.principal.mode.value,
            subject=context.principal.subject,
            request_reference=context.request_reference,
        )

    @property
    def access_mode(self) -> AccessMode:
        """Expose the verified mode without exposing the mutable page context."""

        return AccessMode(self._actor.mode)

    def __getattr__(self, name: str) -> Any:
        attribute = getattr(self._workflow, name)
        if not callable(attribute):
            return attribute

        requires_command = "command_id" in signature(attribute).parameters

        @wraps(attribute)
        def invoke(*args: Any, **kwargs: Any) -> Any:
            # A rendered page or websocket can outlive the verified session.
            # Re-check at the exact workflow boundary; client polling is only UX.
            self._principal.require_active()
            supplied_command = kwargs.get("command_id")
            if requires_command and not (
                isinstance(supplied_command, str) and supplied_command.strip()
            ):
                raise ValueError(
                    f"{name} requires one stable command_id for the user intent"
                )
            command_id = (
                supplied_command.strip()
                if isinstance(supplied_command, str) and supplied_command.strip()
                else f"ui-{uuid4().hex}"
            )
            with bind_operation_actor(replace(self._actor, command_id=command_id)):
                return attribute(*args, **kwargs)

        return invoke


__all__ = [
    "OperationActor",
    "PageContextWorkflowAdapter",
    "bind_operation_actor",
    "current_operation_actor",
]
