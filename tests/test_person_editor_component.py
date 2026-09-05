from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nicegui_app.ui.person_editor import PersonEditor


def test_component_registers_one_listener_and_reuses_identity_across_people():
    editor = PersonEditor(labels={}, fields=[], on_snapshot=lambda event: None)
    element_id = editor.id
    listener_ids = tuple(editor._event_listeners)
    for generation in range(1, 21):
        editor.open_person({"personId": str(generation), "generation": generation}, title="Test", subtitle="Role")
        assert editor.id == element_id
        assert tuple(editor._event_listeners) == listener_ids
    editor.delete()


def test_finalized_binding_is_not_replayed_when_tab_panel_remounts(monkeypatch):
    editor = PersonEditor(labels={}, fields=[], on_snapshot=lambda event: None)
    monkeypatch.setattr(editor, "run_method", lambda *args: None)
    editor.open_person({"personId": "a", "generation": 1}, title="Test", subtitle="Role")
    editor.acknowledge({"personId": "a", "generation": 1, "sequence": 1, "action": "close", "accepted": True})
    assert editor._props["binding"] is None
    editor.delete()


def test_client_protocol_and_ime_scenarios():
    node = shutil.which("node")
    assert node, "Node.js is required to validate the client-side editor protocol."
    result = subprocess.run(
        [node, "--test", "tests/js/person_editor.test.mjs"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        encoding="utf-8", timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
