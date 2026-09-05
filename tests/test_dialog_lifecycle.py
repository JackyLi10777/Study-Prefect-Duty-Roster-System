from __future__ import annotations

import asyncio
from contextlib import contextmanager
import gc
import threading
from types import SimpleNamespace

import pytest

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui import page_shared
from nicegui_app.ui.operation_gate import OPERATION_LOCK_KEY


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


class _ProgressElement:
    def __init__(self, *, opened: asyncio.Event | None = None) -> None:
        self.opened = opened
        self.is_deleted = False
        self.value = 0.0
        self.handler = None

    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def classes(self, *_args: object):  # type: ignore[no-untyped-def]
        return self

    def props(self, *_args: object, **_kwargs: object):  # type: ignore[no-untyped-def]
        return self

    def on_value_change(self, handler: object) -> None:
        self.handler = handler

    def open(self) -> None:
        if self.opened is not None:
            self.opened.set()

    def close(self) -> None:
        return None

    def delete(self) -> None:
        self.is_deleted = True

    def set_text(self, _value: str) -> None:
        return None

    def update(self) -> None:
        return None


class _ProgressUi:
    def __init__(self, *, opened: asyncio.Event | None = None, fail_dialog: bool = False) -> None:
        self.opened = opened
        self.fail_dialog = fail_dialog

    def dialog(self):  # type: ignore[no-untyped-def]
        if self.fail_dialog:
            raise RuntimeError("dialog construction failed")
        return _ProgressElement(opened=self.opened)

    def notify(self, *_args: object, **_kwargs: object) -> None:
        return None

    def __getattr__(self, _name: str):  # type: ignore[no-untyped-def]
        return lambda *_args, **_kwargs: _ProgressElement()


def _stub_progress_dependencies(
    monkeypatch,
    *,
    state: dict[str, object],
    ui_double: _ProgressUi,
    io_bound,
) -> None:
    async def return_before_worker_settles(*_args: object, **_kwargs: object):  # type: ignore[no-untyped-def]
        return set(), set()

    monkeypatch.setattr(page_shared, "app", SimpleNamespace(storage=SimpleNamespace(client=state)))
    monkeypatch.setattr(page_shared, "ui", ui_double)
    @contextmanager
    def semantic_dialog_double(**_kwargs: object):
        with ui_double.dialog().props("persistent") as element:
            yield element

    monkeypatch.setattr(page_shared, "semantic_dialog", semantic_dialog_double)
    monkeypatch.setattr(page_shared, "run", SimpleNamespace(io_bound=io_bound))
    monkeypatch.setattr(page_shared.asyncio, "wait", return_before_worker_settles)
    monkeypatch.setattr(page_shared, "new_operation_reference", lambda: "test-reference")
    monkeypatch.setattr(page_shared, "record_operator_event", lambda **_kwargs: None)
    monkeypatch.setattr(page_shared, "record_operator_failure", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(page_shared, "emit_interface_feedback", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(page_shared, "play_interface_sound", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(page_shared, "t", lambda key, **_kwargs: key)


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


def test_progress_keeps_ui_responsive_and_emits_success_only_after_work_settles(monkeypatch) -> None:
    entered, released = threading.Event(), threading.Event()
    sounds = []
    result = object()

    async def scenario():
        ui_thread = threading.get_ident()

        def write():
            assert threading.get_ident() != ui_thread
            entered.set()
            assert released.wait(5)
            return result

        async def io_bound(action):
            return await asyncio.to_thread(action)

        _stub_progress_dependencies(monkeypatch, state={}, ui_double=_ProgressUi(), io_bound=io_bound)
        monkeypatch.setattr(page_shared, "play_interface_sound", sounds.append)
        task = asyncio.create_task(page_shared._run_with_progress(
            write, title_key="progress_draft_change_title",
            working_key="progress_draft_change_working", icon="save",
        ))
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            assert not task.done()
            assert sounds == ["working"]
        finally:
            released.set()
        assert await task is result
        assert sounds == ["working", "success"]

    asyncio.run(scenario())


def test_one_shot_cleanup_also_releases_framework_canary_owner(monkeypatch) -> None:
    loop = _FakeLoop()
    dialog, owner = _FakeDialog(), _FakeDialog()
    monkeypatch.setattr(page_shared.asyncio, "get_running_loop", lambda: loop)
    page_shared._delete_dialog_after_close(dialog, lifetime_owner=owner)
    dialog.handler(SimpleNamespace(value=False))
    loop.scheduled[0][1]()
    loop.scheduled[0][1]()
    assert dialog.delete_count == owner.delete_count == 1


def test_runtime_created_dialogs_register_cleanup_but_reusable_archive_dialog_does_not() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    people = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "people.py").read_text(encoding="utf-8")

    progress = shared.split("async def _run_with_progress(", 1)[1].split("def _navigate_with_feedback", 1)[0]
    export = shared.split("def _open_roster_export_dialog", 1)[1].split("def _tone_badge", 1)[0]
    prefect = people.split("def _show_prefect_dialog", 1)[1].split("def _render_fairness_panel", 1)[0]
    archive = people.split("with ui.dialog() as archive_dialog", 1)[1].split("def archive_selected", 1)[0]

    assert "_delete_dialog_after_close(dialog, lifetime_owner=progress_owner)" in progress
    # Export now reuses a page-owned native shell, but releases all payloads.
    assert "def release_export_dialog_resources()" in export
    assert "_clear_png_delivery_view(png_delivery_view[0])" in export
    assert 'dialog.on("close", lambda _event: finish_export_dialog_close())' in export
    assert "_delete_dialog_after_close(dialog)" not in export
    assert "_delete_dialog_after_close(dialog)" in prefect
    assert "_delete_dialog_after_close(archive_dialog)" not in archive


def test_shared_progress_uses_indeterminate_mode_without_invented_stages() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    progress = shared.split("async def _run_with_progress(", 1)[1].split("def _navigate_with_feedback", 1)[0]

    assert "data-progress-mode=indeterminate" in progress
    assert "data-wait-kind={normalized_wait_kind}" in progress
    assert 'normalized_wait_kind = "ai" if wait_kind == "ai" else "operation"' in progress
    assert "indeterminate aria-label=" in progress
    assert "sy-progress-dialog-phases" not in progress
    assert "progress_phase_preparing" not in progress
    assert 'progress.props(remove="indeterminate")' in progress
    assert "value=0.14" not in progress
    assert "progress.value = 0.56" not in progress


def test_shared_progress_starts_work_immediately_and_only_reveals_after_threshold() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    progress = shared.split("async def _run_with_progress(", 1)[1].split("def _navigate_with_feedback", 1)[0]

    task_start = "operation_task = asyncio.create_task(run.io_bound(action))"
    reveal_guard = "if not operation_task.done():"
    assert "_PROGRESS_REVEAL_DELAY_SECONDS = 0.14" in shared
    assert task_start in progress
    assert "timeout=_PROGRESS_REVEAL_DELAY_SECONDS" in progress
    assert "return_when=asyncio.FIRST_COMPLETED" in progress
    assert reveal_guard in progress
    assert progress.index(task_start) < progress.index(reveal_guard)

    before_reveal, after_reveal = progress.split(reveal_guard, 1)
    deferred_dialog = after_reveal.split("result = await asyncio.shield(operation_task)", 1)[0]
    assert "semantic_dialog(" not in before_reveal
    assert "semantic_dialog(" in deferred_dialog
    assert "dialog.open()" in deferred_dialog
    assert "result = await asyncio.shield(operation_task)" in progress
    assert "asyncio.sleep(" not in progress


def test_progress_cancellation_keeps_claim_until_worker_task_settles(monkeypatch) -> None:
    async def scenario() -> None:
        state: dict[str, object] = {}
        started = asyncio.Event()
        finish = asyncio.Event()
        dialog_opened = asyncio.Event()

        async def io_bound(action):  # type: ignore[no-untyped-def]
            started.set()
            await finish.wait()
            return action()

        _stub_progress_dependencies(
            monkeypatch,
            state=state,
            ui_double=_ProgressUi(opened=dialog_opened),
            io_bound=io_bound,
        )

        caller = asyncio.create_task(
            page_shared._run_with_progress(
                lambda: "completed",
                title_key="title",
                working_key="durable-write",
                icon="save",
            )
        )
        await dialog_opened.wait()
        await started.wait()
        caller.cancel()
        with pytest.raises(asyncio.CancelledError):
            await caller

        assert state[OPERATION_LOCK_KEY] == "durable-write"
        finish.set()
        for _ in range(10):
            await asyncio.sleep(0)
            if OPERATION_LOCK_KEY not in state:
                break
        assert OPERATION_LOCK_KEY not in state

    asyncio.run(scenario())


def test_progress_dialog_failure_keeps_claim_and_consumes_detached_worker_error(monkeypatch) -> None:
    async def scenario() -> None:
        state: dict[str, object] = {}
        started = asyncio.Event()
        finish = asyncio.Event()
        unhandled: list[dict[str, object]] = []
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda _loop, context: unhandled.append(context))

        async def io_bound(action):  # type: ignore[no-untyped-def]
            started.set()
            await finish.wait()
            action()
            raise RuntimeError("detached worker failed")

        _stub_progress_dependencies(
            monkeypatch,
            state=state,
            ui_double=_ProgressUi(fail_dialog=True),
            io_bound=io_bound,
        )

        try:
            result = await page_shared._run_with_progress(
                lambda: None,
                title_key="title",
                working_key="durable-write",
                icon="save",
            )
            await started.wait()
            assert result is page_shared._OPERATION_FAILED
            assert state[OPERATION_LOCK_KEY] == "durable-write"

            finish.set()
            for _ in range(10):
                await asyncio.sleep(0)
                if OPERATION_LOCK_KEY not in state:
                    break
            gc.collect()
            await asyncio.sleep(0)

            assert OPERATION_LOCK_KEY not in state
            assert unhandled == []
        finally:
            loop.set_exception_handler(previous_handler)

    asyncio.run(scenario())
