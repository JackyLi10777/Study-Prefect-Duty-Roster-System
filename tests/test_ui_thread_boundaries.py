from __future__ import annotations

import asyncio
from threading import get_ident
from types import SimpleNamespace

import pytest

from nicegui_app.ui import page_shared


@pytest.mark.parametrize("include_audit", [False, True])
def test_pdf_export_captures_page_identity_before_entering_worker_thread(
    monkeypatch: pytest.MonkeyPatch,
    include_audit: bool,
) -> None:
    ui_thread = get_ident()
    workflow = object()
    calls: dict[str, object] = {}
    export = SimpleNamespace(filename="demo.pdf", content=b"%PDF-demo")

    def resolve_workflow() -> object:
        calls["workflow_thread"] = get_ident()
        return workflow

    def resolve_practice() -> bool:
        calls["practice_thread"] = get_ident()
        return True

    def build_pdf(bound_workflow: object, roster_week_id: int, **kwargs: object) -> object:
        calls["builder_thread"] = get_ident()
        calls["workflow"] = bound_workflow
        calls["roster_week_id"] = roster_week_id
        calls["practice"] = kwargs["practice"]
        return export

    async def run_in_worker(action, **_kwargs):  # type: ignore[no-untyped-def]
        return await asyncio.get_running_loop().run_in_executor(None, action)

    monkeypatch.setattr(page_shared, "get_workflow", resolve_workflow)
    monkeypatch.setattr(page_shared, "is_demo_export", resolve_practice)
    monkeypatch.setattr(page_shared, "build_roster_pdf", build_pdf)
    monkeypatch.setattr(page_shared, "build_fairness_audit_pdf", build_pdf)
    monkeypatch.setattr(page_shared, "_run_with_progress", run_in_worker)

    result = asyncio.run(
        page_shared._prepare_roster_pdf(
            41,
            "zh",
            include_audit=include_audit,
        )
    )

    assert result is export
    assert calls["workflow"] is workflow
    assert calls["roster_week_id"] == 41
    assert calls["practice"] is True
    assert calls["workflow_thread"] == ui_thread
    assert calls["practice_thread"] == ui_thread
    assert calls["builder_thread"] != ui_thread
