from contextlib import contextmanager
from types import SimpleNamespace

from nicegui_app.ui import page_shared


def test_export_sheet_is_mounted_in_page_slot_not_launching_receipt(monkeypatch) -> None:
    slots = ["receipt"]
    calls = []

    @contextmanager
    def page_content():
        slots.append("page")
        try:
            yield
        finally:
            slots.pop()

    monkeypatch.setattr(
        page_shared, "context",
        SimpleNamespace(client=SimpleNamespace(content=page_content())),
    )
    monkeypatch.setattr(
        page_shared, "_open_page_owned_roster_export_dialog",
        lambda week_id: calls.append((week_id, slots[-1])),
    )

    page_shared._open_roster_export_dialog(42)

    assert calls == [(42, "page")]
    assert slots == ["receipt"]
