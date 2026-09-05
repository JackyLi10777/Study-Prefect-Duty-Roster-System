"""First-use controls must not change support submission or privacy semantics."""
import asyncio
from types import SimpleNamespace

import pytest
from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.access_context import Capability
from nicegui_app.ui.page_routes import support


@pytest.mark.parametrize("expand", [False, True])
@pytest.mark.parametrize("retry", [False, True])
def test_admin_submit_without_optional_controls_and_retained_reopen(monkeypatch, expand, retry):
    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        monkeypatch.setattr(support, "t", lambda key, **kw: key)
        monkeypatch.setattr(support, "status", lambda *a: None)
        checks, reports = [], []
        monkeypatch.setattr(support, "current_page_context", lambda: SimpleNamespace(
            require=checks.append, request_reference=""))
        monkeypatch.setattr(support, "current_application_mode", lambda: SimpleNamespace(mode="test"))
        monkeypatch.setattr(support, "current_locale", lambda: "zh-HK")
        monkeypatch.setattr(support, "release_source_fingerprint", lambda: ("fictional", 0))
        def action(label, test_id="", on_click=None, **kw):
            button = ui.button(label).props(f"data-testid={test_id}")
            if on_click:
                button.on("click", on_click)
            return button
        monkeypatch.setattr(support, "action", action)
        monkeypatch.setattr(support, "SupportInbox", lambda: SimpleNamespace(create_incident=lambda report, **kw:
                            (reports.append((report, kw)), SimpleNamespace(incident_id="INC-20260905-12345678"))[1]))
        failures = [retry]
        async def progress(fn, **kw):
            if failures and failures.pop():
                return support._OPERATION_FAILED
            return fn()
        monkeypatch.setattr(support, "_run_with_progress", progress)
        with Client(ui.page("/test-support-lazy")) as client:
            try:
                support._render_admin_support("/rosters/12/adjustments")
                def find(test_id):
                    return [e for e in client.elements.values() if e._props.get("data-testid") == test_id]
                def field(label):
                    return next(e for e in client.elements.values() if e._props.get("label") == label)
                def handler(test_id):
                    return next(l.handler for l in find(test_id)[0]._event_listeners.values() if l.type == "click")
                assert find("support-lookup-id") == []
                assert not any(isinstance(e, ui.upload) for e in client.elements.values())
                assert not any(e._props.get("label") == "support_route_category" for e in client.elements.values())
                field("support_expected").set_value("Fictional expected")
                field("support_actual").set_value("Fictional actual")
                field("support_reproduction").set_value("Fictional step")
                if expand:
                    details = find("support-progressive-details")[0]
                    details.set_value(True)
                    field("support_impact (optional)").set_value("Retained fictional impact")
                    uploader = next(e for e in client.elements.values() if isinstance(e, ui.upload))
                    async def read_file():
                        return b"fictional attachment"
                    await uploader._upload_handlers[0](SimpleNamespace(file=SimpleNamespace(
                        name="fictional.txt", read=read_file)))
                    assert uploader._props["max-file-size"] == support.MAX_ATTACHMENT_BYTES
                    assert uploader._props["max-files"] == support.MAX_ATTACHMENTS
                    first_ids = set(client.elements)
                    for _ in range(20):
                        details.set_value(False)
                        details.set_value(True)
                    assert set(client.elements) == first_ids
                    assert field("support_route_category").value == "roster_workflow"
                handler("preview-support-incident")()
                for e in list(client.elements.values()):
                    if isinstance(e, ui.checkbox):
                        e.set_value(True)
                await handler("save-support-incident")()
                if retry:
                    assert reports == [] and find("support-incident-id") == []
                    assert field("support_expected").value == "Fictional expected"
                    if expand:
                        assert field("support_impact (optional)").value == "Retained fictional impact"
                        assert any(getattr(e, "text", "") == "support_attachment_added" for e in client.elements.values())
                    handler("preview-support-incident")()
                    await handler("save-support-incident")()
                assert len(reports) == 1
                report, kwargs = reports[0]
                assert report.route_category == "roster_workflow"
                assert report.workflow_action == "page_view"
                assert report.impact == ("Retained fictional impact" if expand else "")
                assert len(kwargs["attachments"]) == int(expand)
                if expand:
                    assert kwargs["attachments"][0].content == b"fictional attachment"
                assert not any(getattr(e, "text", "") == "support_attachment_added" for e in client.elements.values())
                assert find("support-incident-id")[0].text == "INC-20260905-12345678"
                assert field("support_expected").value == "Fictional expected"
                assert all(cap == Capability.PERSISTENT_WRITE for cap in checks)
                history = find("support-history-lookup")[0]
                history.set_value(True)
                lookup = find("support-lookup-id")[0]
                lookup.set_value("INC-20260905-12345678")
                first_ids = set(client.elements)
                for _ in range(20):
                    history.set_value(False)
                    history.set_value(True)
                assert set(client.elements) == first_ids
                assert find("support-lookup-id")[0] is lookup
                assert lookup.value == "INC-20260905-12345678"
                # A retained lookup must recheck authorization at the operation,
                # not rely on the permission used when the section was mounted.
                def deny(_):
                    raise PermissionError("fictional expired session")
                monkeypatch.setattr(support, "current_page_context", lambda: SimpleNamespace(require=deny))
                with pytest.raises(PermissionError):
                    await handler("lookup-support-incident")()
                if expand:
                    with pytest.raises(PermissionError):
                        await uploader._upload_handlers[0](SimpleNamespace())
            finally:
                await asyncio.sleep(0)
                client.delete()
    asyncio.run(run())
