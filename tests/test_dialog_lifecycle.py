from __future__ import annotations

from types import SimpleNamespace

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui import page_shared


class _FakeLoop:
    def __init__(self) -> None:
        self.scheduled: list[tuple[float, object]] = []

    def call_later(self, delay: float, callback: object) -> None:
        self.scheduled.append((delay, callback))


class _FakeDialog:
    def __init__(self) -> None:
        self.handler = None
        self.is_deleted = False
        self.delete_count = 0

    def on_value_change(self, handler: object) -> None:
        self.handler = handler

    def delete(self) -> None:
        self.is_deleted = True
        self.delete_count += 1


def test_one_shot_dialog_cleanup_waits_for_close_and_runs_only_once(monkeypatch) -> None:
    loop = _FakeLoop()
    dialog = _FakeDialog()
    monkeypatch.setattr(page_shared.asyncio, "get_running_loop", lambda: loop)

    page_shared._delete_dialog_after_close(dialog)
    assert dialog.handler is not None

    dialog.handler(SimpleNamespace(value=True))
    assert loop.scheduled == []

    dialog.handler(SimpleNamespace(value=False))
    dialog.handler(SimpleNamespace(value=False))
    assert len(loop.scheduled) == 1
    delay, callback = loop.scheduled[0]
    assert delay >= 0.3

    callback()
    callback()
    assert dialog.delete_count == 1


def test_runtime_created_dialogs_register_cleanup_but_reusable_archive_dialog_does_not() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    people = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "people.py").read_text(encoding="utf-8")

    progress = shared.split("async def _run_with_progress(", 1)[1].split("def _navigate_with_feedback", 1)[0]
    export = shared.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]
    prefect = people.split("def _show_prefect_dialog", 1)[1].split("def _render_fairness_panel", 1)[0]
    archive = people.split("with ui.dialog() as archive_dialog", 1)[1].split("def archive_selected", 1)[0]

    assert "_delete_dialog_after_close(dialog)" in progress
    assert "_delete_dialog_after_close(dialog)" in export
    assert "_delete_dialog_after_close(dialog)" in prefect
    assert "_delete_dialog_after_close(archive_dialog)" not in archive
