"""Application-layer fencing for writes which return a recovery snapshot."""

from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar, overload

from nicegui_app.services.maintenance import MaintenanceModeError
from nicegui_app.services.workflow_types import WorkflowMaintenanceError


P = ParamSpec("P")
R = TypeVar("R")


@overload
def fenced_workflow_write(method: Callable[P, R]) -> Callable[P, R]: ...


@overload
def fenced_workflow_write(*, internal_backup: bool) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def fenced_workflow_write(
    method: Callable[P, R] | None = None,
    *,
    internal_backup: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Keep a committed write and its automatic backup in one host-wide fence."""

    if method is None:
        return lambda target: fenced_workflow_write(
            target,
            internal_backup=internal_backup,
        )

    @wraps(method)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        workflow = args[0]
        try:
            with workflow.maintenance.serialized_operation():
                if not internal_backup:
                    workflow._assert_business_write_admitted(
                        method.__name__,
                        args[1:],
                        kwargs,
                    )
                return method(*args, **kwargs)
        except MaintenanceModeError as error:
            raise WorkflowMaintenanceError(str(error)) from error

    return wrapped
