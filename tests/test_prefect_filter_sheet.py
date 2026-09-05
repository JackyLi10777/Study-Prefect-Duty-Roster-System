from __future__ import annotations

from copy import deepcopy
import asyncio

from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.ui.edit_sessions import PrefectDirectoryFilter, PrefectEditSession
from nicegui_app.ui.page_routes import people


def test_filter_count_includes_nondefault_sort_but_not_search():
    filters = PrefectDirectoryFilter(query="retained query")
    assert people._prefect_active_filter_count(filters) == 0
    filters.sort = "name_desc"
    filters.form = "F.4"
    filters.role = "assistant_head"
    filters.support = "new"
    assert people._prefect_active_filter_count(filters) == 4


def test_filter_sheet_mounts_once_and_clear_preserves_buffered_changes(monkeypatch):
    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        with Client(ui.page("/test-filter-sheet")) as client:
            try:
                await _check_filter_sheet(monkeypatch)
            finally:
                client.delete()
    asyncio.run(run())


async def _check_filter_sheet(monkeypatch):
    rows = [
        {"id": "a", "nameZh": "甲", "nameEn": "Alpha", "form": "F.4", "className": "4A",
         "roleCode": "study_prefect", "historyWeight": 0, "historyDuties": 0,
         "needsMentoring": False, "version": 1, "remarks": ""},
        {"id": "b", "nameZh": "乙", "nameEn": "Beta", "form": "F.5", "className": "5A",
         "roleCode": "assistant_head", "historyWeight": 2, "historyDuties": 1,
         "needsMentoring": False, "version": 1, "remarks": ""},
    ]
    session = PrefectEditSession.from_rows(rows)
    session.stage("a", "remarks", "unfinished input")
    pending = deepcopy(session.pending)
    command_id = session.command_id
    monkeypatch.setattr(people.PrefectEditSession, "from_rows", lambda _rows: session)
    with ui.column() as host:
        people._render_inline_prefect_directory(object(), rows, on_full_edit=lambda row: None)
    client = host.client

    def find(test_id):
        return [element for element in client.elements.values() if element._props.get("data-testid") == test_id]

    def click(test_id):
        button, = find(test_id)
        handler, = [listener.handler for listener in button._event_listeners.values() if listener.type == "click"]
        with host:
            handler(None)

    try:
        assert find("prefect-filter-sheet") == []
        assert all(find(f"prefect-filter-{key}") == [] for key in people._PREFECT_FILTER_DEFAULTS)
        click("open-prefect-filters")
        dialog, = find("prefect-filter-sheet")
        first_ids = {key: find(f"prefect-filter-{key}")[0].id for key in people._PREFECT_FILTER_DEFAULTS}
        assert dialog.value is True
        dialog.close()
        click("open-prefect-filters")
        assert len(find("prefect-filter-sheet")) == 1
        assert {key: find(f"prefect-filter-{key}")[0].id for key in people._PREFECT_FILTER_DEFAULTS} == first_ids

        find("prefect-directory-search")[0].set_value("A")
        find("prefect-filter-form")[0].set_value("F.4")
        find("prefect-filter-sort")[0].set_value("name_desc")
        await asyncio.sleep(0)
        assert session.filters.query == "A"
        assert people._prefect_active_filter_count(session.filters) == 2
        assert find("prefect-filter-summary")[0].text == people.t("prefect_filter_active_count", count=2)

        refreshes = []
        visible_rows = session.visible_rows
        monkeypatch.setattr(session, "visible_rows", lambda: (refreshes.append(1), visible_rows())[1])
        click("clear-prefect-filters")
        await asyncio.sleep(0)
        assert len(refreshes) == 1
        assert session.filters.query == "A"
        assert people._prefect_active_filter_count(session.filters) == 0
        assert find("prefect-filter-form")[0].value == "all"
        assert find("prefect-filter-sort")[0].value == "name_asc"
        assert session.pending == pending and session.command_id == command_id
    finally:
        for dialog in find("prefect-filter-sheet"):
            dialog.delete()
        host.delete()
