"""A single lazily mounted Quasar editor with an explicit snapshot channel."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from nicegui.element import Element
from nicegui.events import GenericEventArguments


class PersonEditor(Element, component="person_editor.js"):
    def __init__(
        self, *, labels: Mapping[str, str], fields: list[dict[str, object]],
        on_snapshot: Callable[[GenericEventArguments], object],
    ) -> None:
        super().__init__()
        self._props.update({"labels": dict(labels), "fields": fields, "binding": None})
        self.on("editor-snapshot", on_snapshot)

    def open_person(self, binding: Mapping[str, object], *, title: str, subtitle: str) -> None:
        self._props["binding"] = {**binding, "title": title, "subtitle": subtitle}
        self.update()

    def acknowledge(self, receipt: Mapping[str, object]) -> None:
        self.run_method("acknowledge", dict(receipt))
        if receipt.get("action") in ("close", "full_edit"):
            # A tab panel may remount its children. Do not replay a finalized
            # binding into a fresh component and reopen the previous person.
            self._props["binding"] = None
            self.update()

    def reject(self, packet: object, message: str) -> None:
        if isinstance(packet, dict):
            self.run_method("reject", packet.get("generation"), packet.get("sequence"), message)
