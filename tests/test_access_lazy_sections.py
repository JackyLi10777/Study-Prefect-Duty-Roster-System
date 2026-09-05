import asyncio
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.access_context import AccessMode, Capability
from nicegui_app.ui.page_routes import access


@pytest.mark.parametrize("mode", [AccessMode.ADMIN, AccessMode.GUEST])
def test_access_summary_does_not_construct_technical_workflow_until_first_use(monkeypatch, mode):
    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        monkeypatch.setattr(access, "page_shell", lambda _: nullcontext())
        monkeypatch.setattr(access, "t", lambda key, **kw: key)
        monkeypatch.setattr(access, "_is_guest_mode", lambda: mode is AccessMode.GUEST)
        monkeypatch.setattr(access, "_render_restricted_capability", lambda **_: None)
        calls = []
        monkeypatch.setattr(access, "get_workflow", lambda: calls.append("workflow"))
        monkeypatch.setattr(access, "render_access_control_console", lambda _: calls.append("console"))
        monkeypatch.setattr(access, "current_page_context", lambda: SimpleNamespace(
            principal=SimpleNamespace(subject="fictional operator", expires_at=None),
            capabilities=(), require=lambda cap: calls.append(cap)), raising=False)
        with Client(ui.page("/test-access-lazy")) as client:
            try:
                access.access_control_page()
                assert calls == []
                summaries = [e for e in client.elements.values() if e._props.get("data-testid") == "access-status-summary"]
                assert len(summaries) == 1
                panels = [e for e in client.elements.values() if e._props.get("data-testid") == "access-technical-controls"]
                if mode is AccessMode.GUEST:
                    assert panels == []
                else:
                    for _ in range(20):
                        panels[0].set_value(True)
                        panels[0].set_value(False)
                    assert calls == [Capability.EXTERNAL_DELIVERY, "workflow", "console"]
            finally:
                await asyncio.sleep(0)
                client.delete()
    asyncio.run(run())
