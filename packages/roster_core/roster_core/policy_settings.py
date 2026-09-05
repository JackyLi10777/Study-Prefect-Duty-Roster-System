"""Immutable policy decisions shared by Official and Guest storage.

This Module owns policy validation, reset decisions and command identity. The
internal storage Seam owns only atomic revision/receipt persistence. Admission,
authorization and backup obligations belong to the outer workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from threading import RLock
from typing import Literal, Protocol

from .command_identity import CommandIdentityError, normalize_command_id

from roster_policy.configurable import (
    BusinessId, BusinessSettings, ConfigurationError, DutyTimes, TimeWindow, WeeklyPolicy, default_weekly_policy,
)
from roster_policy.policy_codec import decode_weekly_policy, encode_weekly_policy


_MAX_POLICY_REVISION = 2**63 - 1


class PolicySettingsError(ValueError):
    """A policy-settings request is invalid."""


class PolicyNotFound(PolicySettingsError):
    """The requested school year or immutable revision does not exist."""


class PolicyVersionConflict(PolicySettingsError):
    """A new command was based on a revision that is no longer current."""


class PolicyCommandConflict(PolicySettingsError):
    """A command identity was reused for different work."""


class PolicyStorageError(PolicySettingsError):
    """Stored policy data could not be read or committed reliably."""


def _year(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 9998:
        raise PolicySettingsError("School year start must be an integer from 1 to 9998.")


def _revision(value: int) -> None:
    if type(value) is not int or not 1 <= value <= _MAX_POLICY_REVISION:
        raise PolicySettingsError("Policy revision must be a positive signed 64-bit integer.")


def _command(value: str) -> str:
    try:
        return normalize_command_id(value)
    except CommandIdentityError as error:
        raise PolicySettingsError("Policy command ID is invalid.") from error


@dataclass(frozen=True)
class PolicyRevision:
    year_start: int
    revision: int
    policy: WeeklyPolicy

    def __post_init__(self) -> None:
        _year(self.year_start)
        _revision(self.revision)
        if not isinstance(self.policy, WeeklyPolicy):
            raise PolicySettingsError("A policy revision requires WeeklyPolicy.")


ChangeValue = str | int | bool | None | tuple[int, ...] | TimeWindow


@dataclass(frozen=True)
class PolicyChange:
    business: BusinessId
    field: str
    before: ChangeValue
    after: ChangeValue

    def __post_init__(self) -> None:
        if not isinstance(self.business, BusinessId) or type(self.field) is not str:
            raise PolicySettingsError("A policy change requires a stable business identity.")
        for value in (self.before, self.after):
            valid = False
            if self.field == "room":
                valid = value is None or type(value) is str
            elif self.field == "capacity":
                valid = type(value) is int
            elif self.field in {"enabled", "linked"}:
                valid = type(value) is bool
            elif self.field == "weekdays":
                valid = type(value) is tuple and all(type(day) is int for day in value)
            elif self.field in {"opening", "service"}:
                valid = type(value) is TimeWindow
            if not valid:
                raise PolicySettingsError("A policy change has an invalid field or value type.")


@dataclass(frozen=True)
class ResetPreview:
    year_start: int
    expected_revision: int
    changes: tuple[PolicyChange, ...]
    target_policy: WeeklyPolicy

    def __post_init__(self) -> None:
        _year(self.year_start)
        _revision(self.expected_revision)
        if type(self.changes) is not tuple or not all(type(change) is PolicyChange for change in self.changes):
            raise PolicySettingsError("Reset changes require an immutable tuple of PolicyChange values.")
        # Revalidate nested values rather than relying on dataclass equality:
        # Python considers a forged True equal to the integer capacity 1.
        object.__setattr__(self, "changes", tuple(
            PolicyChange(change.business, change.field, change.before, change.after) for change in self.changes
        ))
        if not isinstance(self.target_policy, WeeklyPolicy):
            raise PolicySettingsError("A reset preview requires an explicit WeeklyPolicy target.")


@dataclass(frozen=True)
class StoredPolicyRevision:
    year_start: int
    revision: int
    document: str


PolicyOperation = Literal["initialize", "save", "reset"]


def policy_request_digest(
    operation: PolicyOperation, year_start: int, expected_revision: int, document: str,
) -> str:
    """Fingerprint validated intent and canonical document, including operation.

    Both command creation and durable receipt lookup use this exact encoding;
    lookup must never attach an existing but unrelated revision to a command.
    """
    payload = json.dumps(
        {"operation": operation, "year_start": year_start, "expected_revision": expected_revision, "policy": document},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PolicyRepository(Protocol):
    """Internal storage Seam; implementations must replay before checking CAS."""

    def read(self, year_start: int, revision: int | None = None) -> StoredPolicyRevision | None: ...

    def commit(
        self, year_start: int, expected_revision: int, document: str,
        command_id: str, request_digest: str, *, operation: PolicyOperation,
    ) -> StoredPolicyRevision: ...


def _encoded(policy: WeeklyPolicy) -> str:
    if not isinstance(policy, WeeklyPolicy) or type(policy.businesses) is not tuple:
        raise PolicySettingsError("Policy settings require a WeeklyPolicy with immutable business values.")
    try:
        posts = []
        for post in policy.businesses:
            if not isinstance(post, BusinessSettings) or not isinstance(post.times, DutyTimes):
                raise PolicySettingsError("Every policy business requires BusinessSettings and DutyTimes.")
            if not isinstance(post.times.opening, TimeWindow) or not isinstance(post.times.service, TimeWindow):
                raise PolicySettingsError("Policy hours require explicit TimeWindow values.")
            posts.append(replace(post, times=replace(
                post.times, opening=replace(post.times.opening), service=replace(post.times.service),
            )))
        # Validate the entire document before storage, even when a caller has
        # bypassed a frozen dataclass's constructor or supplied a subclass.
        # Re-encoding also fixes business/day order for command fingerprints.
        validated = WeeklyPolicy(tuple(posts))
        return encode_weekly_policy(decode_weekly_policy(encode_weekly_policy(validated)))
    except ConfigurationError as error:
        raise PolicySettingsError("The requested weekly policy is invalid.") from error


def _decoded(stored: StoredPolicyRevision) -> PolicyRevision:
    try:
        return PolicyRevision(stored.year_start, stored.revision, decode_weekly_policy(stored.document))
    except (ConfigurationError, PolicySettingsError) as error:
        raise PolicyStorageError("The stored policy revision is invalid.") from error


def _preview(current: PolicyRevision) -> ResetPreview:
    target = default_weekly_policy()
    changes = []
    for before, after in zip(current.policy.businesses, target.businesses, strict=True):
        for field, old, new in (
            ("room", before.room, after.room),
            ("capacity", before.capacity, after.capacity),
            ("enabled", before.enabled, after.enabled),
            ("weekdays", before.open_weekdays, after.open_weekdays),
            ("opening", before.times.opening, after.times.opening),
            ("service", before.times.service, after.times.service),
            ("linked", before.times.linked, after.times.linked),
        ):
            if old != new:
                changes.append(PolicyChange(before.business, field, old, new))
    return ResetPreview(current.year_start, current.revision, tuple(changes), target)


class PolicySettings:
    def __init__(self, repository: PolicyRepository) -> None:
        self._repository = repository

    def initialize(self, year_start: int, *, command_id: str) -> PolicyRevision:
        return self._commit("initialize", year_start, 0, default_weekly_policy(), command_id)

    def current(self, year_start: int) -> PolicyRevision:
        _year(year_start)
        stored = self._repository.read(year_start)
        if stored is None:
            raise PolicyNotFound("No policy has been initialized for this school year.")
        return _decoded(stored)

    def revision(self, year_start: int, revision: int) -> PolicyRevision:
        _year(year_start)
        _revision(revision)
        stored = self._repository.read(year_start, revision)
        if stored is None:
            raise PolicyNotFound("The requested policy revision does not exist.")
        return _decoded(stored)

    def save(
        self, year_start: int, policy: WeeklyPolicy, *, expected_revision: int, command_id: str,
    ) -> PolicyRevision:
        _revision(expected_revision)
        return self._commit("save", year_start, expected_revision, policy, command_id)

    def preview_reset(self, year_start: int) -> ResetPreview:
        return _preview(self.current(year_start))

    def reset(self, preview: ResetPreview, *, command_id: str) -> PolicyRevision:
        if type(preview) is not ResetPreview:
            raise PolicySettingsError("Reset requires the explicitly reviewed ResetPreview.")
        preview = ResetPreview(preview.year_start, preview.expected_revision, preview.changes, preview.target_policy)
        # Read the immutable reviewed revision, not today's pointer: an exact
        # retry must reach the storage receipt even after this reset committed.
        expected = _preview(self.revision(preview.year_start, preview.expected_revision))
        if preview != expected or _encoded(preview.target_policy) != _encoded(expected.target_policy):
            raise PolicySettingsError("Reset preview no longer matches the reviewed policy and defaults.")
        return self._commit("reset", preview.year_start, preview.expected_revision, expected.target_policy, command_id)

    def _commit(
        self, operation: PolicyOperation, year_start: int, expected_revision: int,
        policy: WeeklyPolicy, command_id: str,
    ) -> PolicyRevision:
        _year(year_start)
        command_id = _command(command_id)
        if expected_revision >= _MAX_POLICY_REVISION:
            raise PolicySettingsError("Policy revision capacity is exhausted; no new revision can be saved.")
        document = _encoded(policy)
        digest = policy_request_digest(operation, year_start, expected_revision, document)
        stored = self._repository.commit(year_start, expected_revision, document, command_id, digest, operation=operation)
        return _decoded(stored)


class MemoryPolicyRepository:
    """Pure test Adapter; live Guest settings belong to the bounded workspace."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._revisions: dict[tuple[int, int], StoredPolicyRevision] = {}
        self._current: dict[int, int] = {}
        self._commands: dict[str, tuple[str, StoredPolicyRevision]] = {}

    def read(self, year_start: int, revision: int | None = None) -> StoredPolicyRevision | None:
        with self._lock:
            selected = self._current.get(year_start) if revision is None else revision
            return self._revisions.get((year_start, selected))

    def commit(
        self, year_start: int, expected_revision: int, document: str,
        command_id: str, request_digest: str, *, operation: PolicyOperation,
    ) -> StoredPolicyRevision:
        with self._lock:
            receipt = self._commands.get(command_id)
            if receipt is not None:
                if receipt[0] != request_digest:
                    raise PolicyCommandConflict("This command ID was already used for different policy work.")
                return receipt[1]
            if self._current.get(year_start, 0) != expected_revision:
                raise PolicyVersionConflict("The current policy changed; reload before saving.")
            stored = StoredPolicyRevision(year_start, expected_revision + 1, document)
            self._revisions[(year_start, stored.revision)] = stored
            self._current[year_start] = stored.revision
            self._commands[command_id] = (request_digest, stored)
            return stored
