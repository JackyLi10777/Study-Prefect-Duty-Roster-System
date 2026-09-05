from __future__ import annotations

from copy import deepcopy

import pytest

from nicegui_app.ui.edit_sessions import PrefectEditSession
from nicegui_app.ui.person_editor_state import EditorSnapshotRejected, PersonEditorState
from nicegui_app.ui.prefect_editor_adapter import (
    PREFECT_EDITOR_SCHEMA, prefect_editor_values, validate_prefect_editor_values,
)


def row(person_id: str, role: str = "study_prefect") -> dict[str, object]:
    return {
        "id": person_id, "nameZh": person_id, "nameEn": None, "version": 3,
        "form": "F.4", "className": "4A", "availableDays": ["MONDAY"],
        "needsMentoring": False, "remarks": "", "roleCode": role,
        "fixedGeneralDuty": "NONE",
    }


def setup_editor():
    session = PrefectEditSession.from_rows([row("a"), row("b", "assistant_head")])

    def stage(person_id, values):
        for field, value in values.items():
            session.stage(person_id, field, value)

    editor = PersonEditorState(stage, validate_prefect_editor_values)
    return session, editor


def bind(editor, session, person_id):
    return editor.bind(
        person_id, values=prefect_editor_values(session.merged_row(person_id)),
        base_version=int(session.originals[person_id]["version"]),
        schema_revision=PREFECT_EDITOR_SCHEMA,
    )


def packet(binding, sequence=1, action="change", **changes):
    return {
        key: binding[key] for key in ("personId", "generation", "schemaRevision")
    } | {"sequence": sequence, "action": action, "values": deepcopy(binding["values"]) | changes}


def test_binding_hydration_never_stages_and_requires_final_ack_before_switch():
    session, editor = setup_editor()
    binding = bind(editor, session, "a")
    assert not session.pending
    binding["values"]["remarks"] = "client copy"
    assert not session.pending
    with pytest.raises(RuntimeError, match="Finalize"):
        bind(editor, session, "b")


def test_switching_a_b_a_preserves_each_person_and_rejects_late_a_packet():
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    editor.receive(packet(a, action="close", remarks="A final character 字"))
    b = bind(editor, session, "b")
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a, sequence=20, remarks="stale"))
    assert session.pending == {"a": {"remarks": "A final character 字"}}
    editor.receive(packet(b, action="close", className="4B"))
    again = bind(editor, session, "a")
    assert again["values"]["remarks"] == "A final character 字"
    assert session.pending["b"] == {"className": "4B"}


def test_newer_complete_snapshot_keeps_all_fields_when_packets_arrive_out_of_order():
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    editor.receive(packet(a, sequence=2, remarks="new", className="4Z"))
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a, sequence=1, remarks="old"))
    assert session.pending["a"] == {"className": "4Z", "remarks": "new"}


def test_duplicate_final_receipt_is_idempotent_but_cannot_repeat_action_or_change_values():
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    final = packet(a, action="full_edit", remarks="last")
    receipt, fresh = editor.receive(final)
    command_id = session.command_id
    assert fresh and receipt["action"] == "full_edit"
    again, fresh = editor.receive(deepcopy(final))
    assert not fresh and again == receipt
    assert session.command_id == command_id
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a, action="full_edit", remarks="different"))


@pytest.mark.parametrize("alter", [
    {"personId": "wrong"}, {"generation": True}, {"generation": 99},
    {"sequence": True}, {"sequence": 0}, {"sequence": "1"},
    {"schemaRevision": "other"}, {"action": "save_database"},
    {"baseVersion": 999}, {"values": {"remarks": "partial"}},
])
def test_invalid_envelopes_never_partially_stage(alter):
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a) | alter)
    assert session.pending == {}
    assert editor.sequence == 0


@pytest.mark.parametrize("changes", [
    {"availableDays": ["INVALID"], "remarks": "must not stage"},
    {"needsMentoring": "false"}, {"nameEn": 1}, {"remarks": []},
    {"fixedGeneralDuty": "MONDAY"},
])
def test_snapshot_is_fully_validated_before_any_field_is_staged(changes):
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a, **changes))
    assert session.pending == {}


def test_role_capability_and_optimistic_version_stay_in_adapter_and_session():
    session, editor = setup_editor()
    b = bind(editor, session, "b")
    assert b["baseVersion"] == 3
    editor.receive(packet(b, action="close", fixedGeneralDuty="MONDAY"))
    patch = session.patches()[0]
    assert patch.prefect_id == "b" and patch.expected_version == 3
    assert patch.changes == {"fixedGeneralDuty": "MONDAY"}


def test_conflict_reapplication_preserves_other_person_and_invalidates_old_binding():
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    editor.receive(packet(a, action="close", remarks="local a"))
    b = bind(editor, session, "b")
    editor.receive(packet(b, action="close", remarks="local b"))
    session.apply_save_result({"updated": [], "errors": [], "conflicts": [
        {"prefectId": "a", "latest": row("a") | {"version": 9}, "changes": {"remarks": "local a"}},
    ]})
    assert session.reapply_conflict("a")
    again = bind(editor, session, "a")
    assert again["baseVersion"] == 9
    assert again["values"]["remarks"] == "local a"
    assert session.pending["b"]["remarks"] == "local b"
    with pytest.raises(EditorSnapshotRejected):
        editor.receive(packet(a, sequence=999, remarks="stale"))


def test_closing_unchanged_person_does_not_create_a_save_intent():
    session, editor = setup_editor()
    a = bind(editor, session, "a")
    receipt, fresh = editor.receive(packet(a, action="close"))
    assert fresh and receipt["accepted"] and editor.closed
    assert not session.dirty and session.command_id is None
