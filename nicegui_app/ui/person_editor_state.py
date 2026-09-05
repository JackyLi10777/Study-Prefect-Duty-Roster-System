"""Ownership protocol for a reusable editor; independent of people/roster schemas.

One browser snapshot is one complete editing intent. Generations protect person
switches, while sequences protect duplicate and reordered messages within it.
Neither replaces the workflow's optimistic database version or command id.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field


class EditorSnapshotRejected(ValueError):
    """A packet cannot belong to the current editing intent."""


@dataclass
class PersonEditorState:
    stage: Callable[[str, Mapping[str, object]], None]
    validate: Callable[[Mapping[str, object]], dict[str, object]]
    generation: int = 0
    person_id: str | None = None
    sequence: int = 0
    closed: bool = True
    fields: frozenset[str] = frozenset()
    schema_revision: str = ""
    _last_packet: dict[str, object] | None = field(default=None, repr=False)
    _last_receipt: dict[str, object] | None = field(default=None, repr=False)

    def bind(
        self, person_id: str, *, values: Mapping[str, object],
        base_version: int, schema_revision: str,
    ) -> dict[str, object]:
        if not self.closed:
            raise RuntimeError("Finalize the current editor before replacing its binding.")
        self.generation += 1
        self.person_id = person_id
        self.sequence = 0
        self.closed = False
        self.fields = frozenset(values)
        self.schema_revision = schema_revision
        self._last_packet = None
        self._last_receipt = None
        return {
            "personId": person_id, "generation": self.generation,
            "baseVersion": base_version, "schemaRevision": schema_revision,
            "values": deepcopy(dict(values)),
        }

    def receive(self, packet: object) -> tuple[dict[str, object], bool]:
        """Stage synchronously before returning; ``fresh`` gates one-time actions.

        A duplicate final packet gets its original receipt but never repeats a
        navigation/save callback. Older generations cannot receive that receipt.
        """
        if not isinstance(packet, dict) or set(packet) != {
            "personId", "generation", "schemaRevision", "sequence", "action", "values",
        }:
            raise EditorSnapshotRejected("Invalid editor packet.")
        if (
            packet["personId"] != self.person_id
            or type(packet["generation"]) is not int
            or packet["generation"] != self.generation
            or packet["schemaRevision"] != self.schema_revision
        ):
            raise EditorSnapshotRejected("The editor binding has changed.")
        if packet == self._last_packet and self._last_receipt is not None:
            return deepcopy(self._last_receipt), False
        sequence = packet["sequence"]
        action = packet["action"]
        if self.closed or type(sequence) is not int or sequence <= self.sequence:
            raise EditorSnapshotRejected("The editor packet is no longer current.")
        if action not in ("change", "close", "full_edit"):
            raise EditorSnapshotRejected("Invalid editor action.")
        values = packet["values"]
        if not isinstance(values, dict) or set(values) != self.fields:
            raise EditorSnapshotRejected("Editable fields have changed.")
        # Validate the entire snapshot before staging any of its fields.
        validated = self.validate(deepcopy(values))
        self.stage(str(self.person_id), validated)
        self.sequence = sequence
        self.closed = action != "change"
        receipt = {
            "personId": self.person_id, "generation": self.generation,
            "sequence": sequence, "action": action, "accepted": True,
        }
        self._last_packet = deepcopy(packet)
        self._last_receipt = receipt
        return deepcopy(receipt), True
