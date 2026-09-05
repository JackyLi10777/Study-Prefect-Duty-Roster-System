"""Real NiceGUI controls with isolated service boundaries, not browser evidence."""

import asyncio
from types import SimpleNamespace

import pytest
from nicegui import core, ui
from nicegui.client import Client

from nicegui_app.ui import restore_controls as controls


def run_case(monkeypatch, check, *, guest=False):
    calls = []

    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        monkeypatch.setattr(controls, "t", lambda key, **kw: key)

        async def progress(action, **kwargs):
            return action()

        monkeypatch.setattr(controls, "_run_with_progress", progress)
        workflow = SimpleNamespace(
            verify_backup=lambda path: {"valid": True, "sha256": "a" * 64, "schemaRevision": "fictional"},
            review_demo_backup=lambda path: {"demo": True, "workspaceRevision": 3},
            restore_backup=lambda path, **kwargs: calls.append((str(path), kwargs)) or {"demo": guest},
        )
        with Client(ui.page("/restore-controls-test")) as client:
            try:
                panel = controls.RestoreControls(workflow, {"one.db": "Fictional one", "two.db": "Fictional two"}, guest=guest)
                await check(panel, calls, client)
            finally:
                await asyncio.sleep(0)
                client.delete()
    asyncio.run(run())


def test_explicit_choice_and_exact_phrase_are_required(monkeypatch):
    async def check(panel, calls, _):
        assert panel.selector.value is None and not panel.ready.enabled
        assert "sy-button-attention" in panel.ready._classes
        await panel.review_selected()
        assert not panel.dialog.value
        panel.selector.set_value("one.db")
        await panel.review_selected()
        assert panel.dialog.value and panel.dialog._props["role"] == "alertdialog"
        assert panel.confirm._props["color"] == "negative"
        assert not panel.confirm.enabled
        panel.phrase.set_value("wrong")
        await panel.submit()
        assert calls == []
        panel.phrase.set_value("restore_confirmation_phrase")
        assert panel.confirm.enabled
        await panel.submit()
        assert calls == [("one.db", {"expected_sha256": "a" * 64})]
        assert panel.receipt.visible and not panel.dialog.value
    run_case(monkeypatch, check)


@pytest.mark.parametrize("guest", [False, True])
def test_twenty_reopens_clear_consent_without_mounting_more_elements(monkeypatch, guest):
    async def check(panel, calls, client):
        panel.selector.set_value("one.db")
        initial = set(client.elements)
        for _ in range(20):
            await panel.review_selected()
            assert not panel.confirm.enabled and panel.phrase.value == ""
            panel.phrase.set_value("restore_confirmation_phrase")
            panel.cancel()
            await panel.submit()
        assert calls == [] and set(client.elements) == initial
    run_case(monkeypatch, check, guest=guest)


def test_selection_change_invalidates_review_and_guest_uses_only_revision(monkeypatch):
    async def check(panel, calls, _):
        panel.selector.set_value("one.db")
        await panel.review_selected()
        panel.phrase.set_value("restore_confirmation_phrase")
        panel.selector.set_value("two.db")
        await panel.submit()
        assert calls == [] and not panel.dialog.value
        await panel.review_selected()
        panel.phrase.set_value("restore_confirmation_phrase")
        await panel.submit()
        assert calls == [("two.db", {"expected_workspace_revision": 3})]
        assert panel.receipt.text == "restore_demo_complete"
    run_case(monkeypatch, check, guest=True)


def test_busy_rejects_duplicate_submit_and_failure_has_no_success_receipt(monkeypatch):
    async def check(panel, calls, _):
        panel.selector.set_value("one.db")
        await panel.review_selected()
        panel.phrase.set_value("restore_confirmation_phrase")
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(action, **kwargs):
            started.set()
            await release.wait()
            action()
            return controls._OPERATION_FAILED

        monkeypatch.setattr(controls, "_run_with_progress", delayed)
        pending = asyncio.create_task(panel.submit())
        await started.wait()
        await panel.submit()
        release.set()
        await pending
        assert len(calls) == 1 and not panel.receipt.visible
        assert panel.failure.visible and panel.phrase.value == ""
    run_case(monkeypatch, check)


def test_late_review_does_not_reopen_after_selection_change(monkeypatch):
    async def check(panel, calls, _):
        panel.selector.set_value("one.db")
        started, release = asyncio.Event(), asyncio.Event()

        async def delayed(action, **kwargs):
            started.set()
            await release.wait()
            return action()

        monkeypatch.setattr(controls, "_run_with_progress", delayed)
        pending = asyncio.create_task(panel.review_selected())
        await started.wait()
        panel.selector.set_value("two.db")
        release.set()
        await pending
        assert not panel.dialog.value and calls == []
    run_case(monkeypatch, check)
