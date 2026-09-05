"""Policy storage Adapter over one bounded Guest workspace, never a second store.

The state validator uses only the pure policy codec. Revision histories travel
with the signed workspace; small references travel in its existing receipts.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from typing import Any

from roster_core.command_identity import CommandIdentityError, normalize_command_id
from roster_core.policy_settings import (
    PolicyCommandConflict, PolicyOperation, PolicySettingsError, PolicyStorageError,
    PolicyVersionConflict, StoredPolicyRevision,
)
from roster_policy.configurable import ConfigurationError
from roster_policy.policy_codec import decode_weekly_policy, encode_weekly_policy

from nicegui_app.services.guest_workspace import (
    MAX_COMMAND_ID_BYTES, GuestCapacityError, GuestCommandConflict,
    GuestWorkspaceRegistry, GuestWorkspaceView,
)


POLICY_STATE_SCHEMA_VERSION = 1


def guest_policy_command_id(value: str) -> str:
    try:
        normalized = normalize_command_id(value)
    except CommandIdentityError as error:
        raise PolicySettingsError("Policy command ID is invalid.") from error
    if len(normalized.encode("utf-8")) > MAX_COMMAND_ID_BYTES:
        raise GuestCapacityError("command_id exceeds the receipt metadata limit")
    return normalized


def validate_policy_state(state: Mapping[str, Any]) -> dict[str, Any]:
    payload = state.get("policySettings", {"schemaVersion": POLICY_STATE_SCHEMA_VERSION, "years": {}})
    if (
        type(payload) is not dict or set(payload) != {"schemaVersion", "years"}
        or type(payload["schemaVersion"]) is not int or payload["schemaVersion"] != POLICY_STATE_SCHEMA_VERSION
        or type(payload["years"]) is not dict
    ):
        raise PolicyStorageError("Guest policy state has an unsupported schema.")
    for year, record in payload["years"].items():
        if (
            type(year) is not str or not 1 <= len(year) <= 4 or not year.isascii() or not year.isdigit()
            or not 1 <= int(year) <= 9998 or year != str(int(year))
            or type(record) is not dict or set(record) != {"currentRevision", "revisions"}
            or type(record["revisions"]) is not list or not record["revisions"]
            or type(record["currentRevision"]) is not int
            or record["currentRevision"] != len(record["revisions"])
        ):
            raise PolicyStorageError("Guest policy history or current revision is invalid.")
        for document in record["revisions"]:
            try:
                if type(document) is not str or encode_weekly_policy(decode_weekly_policy(document)) != document:
                    raise PolicyStorageError("Guest policy revisions must contain canonical policy documents.")
            except ConfigurationError as error:
                raise PolicyStorageError("Guest policy revision contains an invalid document.") from error
    return payload


def validate_policy_transition(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    old_years = validate_policy_state(before)["years"]
    new_years = validate_policy_state(after)["years"]
    for year, old in old_years.items():
        new = new_years.get(year)
        if new is None or new["revisions"][:len(old["revisions"])] != old["revisions"]:
            raise PolicyStorageError("Existing Guest policy history cannot be overwritten or removed.")


def policy_reference_revision(state: Mapping[str, Any], reference: tuple[int, int] | None) -> StoredPolicyRevision:
    if (
        type(reference) is not tuple or len(reference) != 2
        or type(reference[0]) is not int or not 1 <= reference[0] <= 9998
        or type(reference[1]) is not int or reference[1] < 1
    ):
        raise PolicyStorageError("Guest policy receipt reference is invalid.")
    year, revision = reference
    record = validate_policy_state(state)["years"].get(str(year))
    if record is None or revision > len(record["revisions"]):
        raise PolicyStorageError("Guest policy receipt refers to missing history.")
    return StoredPolicyRevision(year, revision, record["revisions"][revision - 1])


class GuestPolicyRepository:
    """One command/read view; workspace CAS protects its atomic replacement."""

    def __init__(
        self, registry: GuestWorkspaceRegistry, view: GuestWorkspaceView,
        commit: Callable[..., GuestWorkspaceView],
    ) -> None:
        self._registry = registry
        self._view = view
        self._commit = commit
        self.replayed = False
        validate_policy_state(view.state)

    def read(self, year_start: int, revision: int | None = None) -> StoredPolicyRevision | None:
        record = validate_policy_state(self._view.state)["years"].get(str(year_start))
        if record is None:
            return None
        selected = record["currentRevision"] if revision is None else revision
        if selected > len(record["revisions"]):
            return None
        return StoredPolicyRevision(year_start, selected, record["revisions"][selected - 1])

    def commit(
        self, year_start: int, expected_revision: int, document: str,
        command_id: str, request_digest: str, *, operation: PolicyOperation,
    ) -> StoredPolicyRevision:
        command_id = guest_policy_command_id(command_id)
        try:
            replay = self._registry.replay_command(
                session_id=self._view.session_id, workspace_id=self._view.workspace_id,
                tab_id=self._view.tab_id, command_id=command_id, request_digest=request_digest,
            )
            if replay is None:
                current = self.read(year_start)
                if (current.revision if current else 0) != expected_revision:
                    raise PolicyVersionConflict("The current policy changed; reload before saving.")
                state = deepcopy(self._view.state)
                payload = state.setdefault("policySettings", {"schemaVersion": POLICY_STATE_SCHEMA_VERSION, "years": {}})
                record = payload["years"].setdefault(str(year_start), {"currentRevision": 0, "revisions": []})
                record["revisions"].append(document)
                record["currentRevision"] = expected_revision + 1
                replay = self._commit(
                    self._view, state, f"policy-{operation}", command_id=command_id,
                    request_digest=request_digest, policy_result_reference=(year_start, expected_revision + 1),
                )
        except GuestCommandConflict as error:
            raise PolicyCommandConflict("This command ID was already used for different Guest work.") from error
        stored = policy_reference_revision(replay.state, replay.policy_result_reference)
        if (stored.year_start, stored.revision, stored.document) != (year_start, expected_revision + 1, document):
            raise PolicyStorageError("Guest policy receipt does not match the requested immutable revision.")
        self.replayed = replay.replayed
        return stored
