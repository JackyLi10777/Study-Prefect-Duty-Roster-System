import asyncio
from types import SimpleNamespace

import pytest

from nicegui_app.services import roster_image_export
from nicegui_app.services.roster_export_session import RosterExportSession
from nicegui_app.ui import page_shared


def test_pdf_first_then_png_reuses_one_capture_at_ui_boundary(monkeypatch):
    captured = []
    rendered = []
    workflow = object()
    document = object()

    def capture(source, week_id):
        assert source is workflow and week_id == 42
        captured.append(week_id)
        return document

    def render_pdf(source_document, **_options):
        rendered.append(("pdf", source_document))
        return SimpleNamespace(content=b"%PDF", filename="test.pdf")

    def render_png(source_document, **_options):
        rendered.append(("png", source_document))
        return SimpleNamespace(avatar=object(), whatsapp=object())

    async def progress(action, **_options):
        return action()

    monkeypatch.setattr(page_shared, "get_workflow", lambda: workflow)
    monkeypatch.setattr(page_shared, "is_demo_export", lambda: False)
    monkeypatch.setattr(page_shared, "capture_roster_document", capture)
    monkeypatch.setattr(page_shared, "render_roster_pdf", render_pdf)
    monkeypatch.setattr(roster_image_export, "render_roster_png_bundle", render_png)
    monkeypatch.setattr(page_shared, "_run_with_progress", progress)

    async def scenario():
        session = RosterExportSession()
        session.open()
        pdf_request = session.begin()
        pdf_document = await page_shared._prepare_export_document(42, pdf_request)
        await page_shared._prepare_roster_pdf(42, "zh", document=pdf_document)
        assert session.complete(pdf_request, pdf_document)
        png_request = session.begin()
        png_document = await page_shared._prepare_export_document(42, png_request)
        await page_shared._prepare_roster_png_bundle(42, "zh", document=png_document)
        assert session.complete(png_request, png_document)

    asyncio.run(scenario())
    assert captured == [42]
    assert rendered == [("pdf", document), ("png", document)]


@pytest.mark.parametrize("raises", [False, True])
def test_direct_audit_delivery_failure_always_settles_preparing(monkeypatch, raises):
    session = RosterExportSession()
    session.open()
    request = session.begin()

    def reject(_export):
        if raises:
            raise PermissionError("Expired identity")
        return False

    monkeypatch.setattr(page_shared, "_deliver_prepared_roster_pdf", reject)
    if raises:
        with pytest.raises(PermissionError):
            page_shared._finish_direct_pdf_delivery(session, request, object())
    else:
        assert not page_shared._finish_direct_pdf_delivery(session, request, object())
    assert session.phase == "failed"
    assert session.begin().generation > request.generation


def test_closed_audit_request_does_not_issue_a_download(monkeypatch):
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.close()
    issued = []
    monkeypatch.setattr(page_shared, "_deliver_prepared_roster_pdf", lambda export: issued.append(export))
    assert not page_shared._finish_direct_pdf_delivery(session, request, object())
    assert not issued
    assert session.phase == "closed"
