"""Exercise the page's save seam without a browser or NiceGUI rendering mocks."""
from __future__ import annotations

import asyncio
from contextvars import Context, ContextVar
from datetime import date
import threading
from types import SimpleNamespace

import pytest

from nicegui_app.services.draft_editor import DraftEditor
from nicegui_app.services.workflow_types import CommittedWriteBackupError
from nicegui_app.ui.page_routes import weekly


class SavePort:
    def __init__(self, status: str, partial: bool, refresh_failed: bool):
        self.status, self.partial, self.refresh_failed = status, partial, refresh_failed
        self.entered, self.released = threading.Event(), threading.Event()
        self.committed = False
        self.calls = 0
        self.requests = []

    def apply_draft_patch(self, **kwargs):
        self.calls += 1
        self.requests.append(kwargs)
        self.entered.set()
        assert self.released.wait(5)
        self.committed = True
        if self.partial:
            raise CommittedWriteBackupError("draft_patch_applied", "fictional backup failure")
        return SimpleNamespace(version=2)

    def roster_schedule_snapshot(self, roster_week_id):
        if self.committed and self.refresh_failed:
            raise OSError("fictional snapshot read failure")
        return ({"id": 1, "weekStart": date(2026, 9, 7), "version": 3 if self.committed else 1,
                 "status": self.status if self.committed else "draft", "closedDays": [], "slotExceptions": []}, [])


@pytest.mark.parametrize("status,partial,refresh_failed", (
    ("published", False, False),
    ("withdrawn", False, False),
    ("published", True, False),
    ("draft", True, True),
    ("draft", False, True),
))
def test_cancelled_page_wait_still_settles_admitted_save(monkeypatch, status, partial, refresh_failed):
    async def progress(action, **kwargs):
        task = asyncio.create_task(asyncio.to_thread(action))
        task.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
        return await asyncio.shield(task)

    monkeypatch.setattr(weekly, "_run_with_progress", progress)

    async def scenario():
        port = SavePort(status, partial, refresh_failed)
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        settled = asyncio.Event()
        views = []
        callback_errors = []
        ui_thread = threading.get_ident()
        controls = [PublishControl(), PublishControl()]
        dialog = PublishDialog()

        def on_settled(outcome, error):
            assert threading.get_ident() == ui_thread
            view = weekly._draft_commit_view(editor)
            weekly._sync_draft_publish_controls(view, controls, dialog)
            views.append(view)
            callback_errors.append(error)
            settled.set()

        page_wait = asyncio.create_task(weekly._save_draft_with_progress(editor, "fictional reason", on_settled=on_settled))
        assert await asyncio.to_thread(port.entered.wait, 5)
        page_wait.cancel()
        with pytest.raises(asyncio.CancelledError):
            await page_wait
        assert editor.saving is True, "the admitted write must retain its claim"
        assert editor.stage_day("TUESDAY", True) is False
        port.released.set()
        await asyncio.wait_for(settled.wait(), 5)
        assert port.calls == 1 and len(views) == 1
        assert not editor.saving and not editor.dirty
        view = views[0]
        assert view.read_only and not view.can_publish
        assert view.saved_version == 2, "the saved receipt is not the later publication version"
        assert view.refresh_failed is refresh_failed
        assert view.recovery_required is partial
        assert all(not control.enabled and control.aria_disabled for control in controls)
        assert dialog.closed
        assert isinstance(callback_errors[0], CommittedWriteBackupError) is partial
        assert port.requests[0]["reason"] == "fictional reason"
        assert port.requests[0]["day_edits"] == ()
        for locale in ("zh-HK", "en"):
            title, body = weekly._draft_commit_notice(view, locale)
            assert "v2" in title
            assert body
            if not refresh_failed:
                assert "v3" in body
        assert editor.stage_candidate("MONDAY:ROOM_302:1", None).kind == "blocked"

    asyncio.run(scenario())


class PublishControl:
    enabled = True
    aria_disabled = False

    def set_enabled(self, enabled):
        self.enabled = enabled

    def props(self, value=None, *, remove=None):
        if remove == "aria-disabled":
            self.aria_disabled = False
        if value == "aria-disabled=true":
            self.aria_disabled = True


class PublishDialog:
    closed = False

    def close(self):
        self.closed = True


def test_settlement_restores_request_context_after_context_free_io_worker(monkeypatch):
    request_marker = ContextVar("draft_test_request", default=None)

    async def progress(action, **kwargs):
        # NiceGUI deliberately detaches request context from its IO worker.
        return await asyncio.to_thread(Context().run, action)

    monkeypatch.setattr(weekly, "_run_with_progress", progress)

    async def scenario():
        port = SavePort("draft", False, False)
        port.released.set()
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        observed = []
        settled = asyncio.Event()

        def on_settled(outcome, error):
            observed.append(request_marker.get())
            settled.set()

        token = request_marker.set("fictional-page-request")
        try:
            await weekly._save_draft_with_progress(editor, None, on_settled=on_settled)
            await asyncio.wait_for(settled.wait(), 5)
            assert observed == ["fictional-page-request"]
        finally:
            request_marker.reset(token)

    asyncio.run(scenario())


def test_progress_admission_failure_never_starts_a_save(monkeypatch):
    async def refused(action, **kwargs):
        return weekly._OPERATION_FAILED

    monkeypatch.setattr(weekly, "_run_with_progress", refused)

    async def scenario():
        port = SavePort("draft", False, False)
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        callbacks = []
        result = await weekly._save_draft_with_progress(editor, None, on_settled=lambda *args: callbacks.append(args))
        assert result is weekly._OPERATION_FAILED
        assert not editor.saving and editor.dirty
        assert callbacks == [] and port.calls == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("state", ("unchanged", "saving", "read_only"))
def test_page_save_guard_rejects_non_actionable_state_before_progress(monkeypatch, state):
    async def unexpected_progress(*args, **kwargs):
        raise AssertionError("non-actionable drafts must not start a durable operation")

    monkeypatch.setattr(weekly, "_run_with_progress", unexpected_progress)

    async def scenario():
        port = SavePort("draft", False, False)
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        if state != "unchanged":
            editor.stage_slot("MONDAY:ROOM_302:1", True)
        if state == "saving":
            editor.prepare_save()
        if state == "read_only":
            editor.close()
        result = await weekly._save_draft_with_progress(editor, None, on_settled=lambda *args: None)
        assert result is weekly._OPERATION_FAILED
        assert port.calls == 0

    asyncio.run(scenario())


def test_saved_draft_retains_selection_and_reenables_publishing(monkeypatch):
    async def progress(action, **kwargs):
        return await asyncio.to_thread(action)

    monkeypatch.setattr(weekly, "_run_with_progress", progress)

    async def scenario():
        port = SavePort("draft", False, False)
        port.released.set()
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.selected_cell = "MONDAY:ROOM_302:1"
        editor.stage_slot(editor.selected_cell, True)
        controls, dialog = [PublishControl(), PublishControl()], PublishDialog()
        weekly._sync_draft_publish_controls(weekly._draft_commit_view(editor), controls, dialog)
        assert all(not control.enabled for control in controls)
        done = asyncio.Event()

        def settled(outcome, error):
            assert error is None
            weekly._sync_draft_publish_controls(weekly._draft_commit_view(editor), controls, dialog)
            done.set()

        result = await weekly._save_draft_with_progress(editor, None, on_settled=settled)
        await asyncio.wait_for(done.wait(), 5)
        assert result.receipt.version == 2
        assert editor.selected_cell == "MONDAY:ROOM_302:1"
        assert not editor.read_only and not editor.dirty
        assert all(control.enabled and not control.aria_disabled for control in controls)

    asyncio.run(scenario())


def test_save_freezes_reviewed_intent_before_waiting_for_progress_worker(monkeypatch):
    async def scenario():
        entered, released = asyncio.Event(), asyncio.Event()

        async def progress(action, **kwargs):
            entered.set()
            await released.wait()
            return await asyncio.to_thread(action)

        monkeypatch.setattr(weekly, "_run_with_progress", progress)
        port = SavePort("draft", False, False)
        port.released.set()
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        task = asyncio.create_task(weekly._save_draft_with_progress(editor, "reviewed", on_settled=lambda *args: None))
        await asyncio.wait_for(entered.wait(), 5)
        assert editor.saving, "intent must be reserved before the first progress await"
        assert editor.stage_day("TUESDAY", True) is False
        released.set()
        await task
        assert port.requests[0]["day_edits"] == ()
        assert port.requests[0]["reason"] == "reviewed"

    asyncio.run(scenario())


def test_cancelling_while_admitted_worker_is_queued_keeps_reservation(monkeypatch):
    async def scenario():
        queued, start_worker = threading.Event(), threading.Event()

        async def progress(action, **kwargs):
            def queued_action():
                queued.set()
                assert start_worker.wait(5)
                return action()

            task = asyncio.create_task(asyncio.to_thread(queued_action))
            return await asyncio.shield(task)

        monkeypatch.setattr(weekly, "_run_with_progress", progress)
        port = SavePort("draft", False, False)
        port.released.set()
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        settled = asyncio.Event()
        task = asyncio.create_task(weekly._save_draft_with_progress(editor, None, on_settled=lambda *args: settled.set()))
        assert await asyncio.to_thread(queued.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert port.calls == 0 and editor.saving
        assert editor.stage_day("TUESDAY", True) is False
        start_worker.set()
        await asyncio.wait_for(settled.wait(), 5)
        assert port.calls == 1
        assert not editor.saving and not editor.dirty

    asyncio.run(scenario())


@pytest.mark.parametrize("snapshot", (None, ({"version": "bad"}, []), ({"version": 1}, []), ({"version": 3, "status": "unknown"}, [])))
def test_normal_commit_with_unusable_refresh_is_not_reported_as_unsaved(snapshot):
    async def scenario():
        port = SavePort("draft", False, False)
        port.released.set()
        editor = DraftEditor.from_snapshot(port, 1, port.roster_schedule_snapshot(1))
        editor.stage_slot("MONDAY:ROOM_302:1", True)
        port.roster_schedule_snapshot = lambda _week_id: snapshot
        outcome = await editor.save()
        assert outcome.receipt.version == 2
        assert editor.last_saved_version == 2
        assert editor.read_only and editor.snapshot_refresh_failed
        assert not editor.recovery_required and not editor.saving and not editor.dirty
        assert editor.command_id is None

    asyncio.run(scenario())
