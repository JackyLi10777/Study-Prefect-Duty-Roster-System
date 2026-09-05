# Reusable person editor

The directory mounts at most 20 read-only cards and creates one editor only when
a person is selected. The current prefect adapter owns editable field/role
rules; `PersonEditorState` does not know about posts, rooms, or roster policy.

The editor uses existing Quasar fields inside a native modal `dialog`.
`showModal()` / `close()` retain the input DOM, unlike a closed Quasar portal.
Role-specific fields use `v-show`; the six-option weekday picker is native so it
cannot be teleported outside the modal top layer. Escape and backdrop clicks
request a final snapshot and never directly close the editor.

## State and persistence

- A binding has a person ID, UI generation, schema revision, and server-owned
  optimistic data version. These identifiers serve different purposes.
- Every event has its originating person/generation, an increasing sequence,
  an action, and a complete JSON value snapshot.
- Hydration never emits an event. The browser keeps an independent local model;
  no NiceGUI `ValueElement` callback can stage programmatic updates.
- The server validates the entire packet before staging any fields. Earlier
  sequences, closed generations, wrong identities, and unknown fields fail.
- Done waits for any active IME composition, captures the final native text,
  and waits for acknowledgement. A retry sends the identical final packet.
  Duplicate final packets receive the same receipt without repeating actions.
- Acknowledgement means the page buffer accepted the edit, **not** that SQLite
  committed it. The existing atomic save, optimistic versions, `command_id`,
  workflow errors, and Guest workspace isolation remain authoritative.
- Full edit captures its target before awaiting a buffered save. A failed save
  or conflict keeps the user on the directory and restores search focus.
- Finalized bindings are cleared on the server so remounting a tab cannot reopen
  an old person. Changing people within the directory reuses controls.

## Verification

Run `python -m pytest tests/test_person_editor_state.py tests/test_person_editor_component.py`
for protocol/ownership and client-side event tests. The latter runs Node's native
test runner against the real component methods, including Vue-style proxies,
IME, retries, focus fallback, and stale acknowledgement behavior.

Run `python -X utf8 scripts/verify_person_editor.py` for a disposable Chromium
functional smoke. It creates a fictional 22-person SQLite database, backups,
logs and screenshots under a fresh OS temporary directory, then closes its own
server and browser. It verifies A/B/A values, native select, final text, IME,
Escape/backdrop, atomic save, full-edit identity/conflict focus, tab remount,
pagination, zero console errors, retained input DOM and 20 dialog cycles.

This is not the full release gate: shared browser scenarios must be updated for
the sheet's `data-person-id` and `[data-editor-field]` selectors. Throttled p75,
the complete viewport/browser matrix, and physical phone checks remain separate.
