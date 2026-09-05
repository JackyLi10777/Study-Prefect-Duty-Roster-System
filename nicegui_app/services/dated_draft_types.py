"""Backend-only dated draft identities; never aliases for old integer weeks."""
from dataclasses import dataclass
import re
from typing import Literal

from roster_core.dated_draft import WeeklyDraft
from roster_policy.configurable import ScheduleExceptions, SeatKey
from nicegui_app.services.workflow_types import WorkflowError


def exception_payload(exceptions):
    if not isinstance(exceptions, ScheduleExceptions):
        raise WorkflowError("Explicit dated schedule exceptions are required.")
    return {"closed": [value.isoformat() for value in exceptions.closed_dates],
            "unavailable": [[entry.seat.value, entry.approval_reference] for entry in exceptions.unavailable]}


def edit_payload(changes):
    if not isinstance(changes, dict) or any(not isinstance(key, SeatKey) or (value is not None and type(value) is not str)
                                            for key, value in changes.items()):
        raise WorkflowError("Edits require actual-date seat keys and person IDs or explicit vacancy.")
    return sorted([[key.value, value] for key, value in changes.items()])


def draft_identity(value: str) -> str:
    if type(value) is not str or re.fullmatch(r"DRAFT-[0-9a-f]{32}", value) is None:
        raise WorkflowError("Select an existing dated draft identity.")
    return value


def draft_version(value: int) -> int:
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise WorkflowError("Select an explicit positive draft version.")
    return value


def reject_dated_draft(value) -> None:
    if isinstance(value, str) and value.startswith("DRAFT-"):
        raise WorkflowError("Dated drafts cannot use legacy publication, adjustment, sharing or export.")


@dataclass(frozen=True)
class DatedDraftSnapshot:
    schedule_id: str
    version: int
    draft: WeeklyDraft


@dataclass(frozen=True)
class DatedDraftCommandResult:
    command_id: str
    snapshot: DatedDraftSnapshot
    backup_status: Literal["verified", "pending", "not_applicable"]
    replayed: bool = False
