from __future__ import annotations

import asyncio

from nicegui import core, ui
from nicegui.client import Client
import pytest

from nicegui_app.services.roster_workflow import (
    PrefectInput, PrefectPatch, RosterWorkflow, WorkflowConflictError,
)
from nicegui_app.ui.edit_sessions import PrefectEditSession
from nicegui_app.ui.page_routes import people


@pytest.mark.parametrize("external_update", [True, False])
def test_archive_uses_only_the_directory_reviewed_version(tmp_path, monkeypatch, external_update):
    """Read-latest must not bypass CAS; our own atomic flush must advance CAS."""
    workflow = RosterWorkflow(
        database_path=tmp_path / "fictional.sqlite3", backup_dir=tmp_path / "backups", seed_path=None,
    )
    workflow.bootstrap()
    row = workflow.create_prefect(PrefectInput(
        name_zh="虛構甲", form="F.4", class_name="4A", role_code="study_prefect",
        available_days=("MONDAY",), remarks="reviewed",
    ))
    person_id = str(row["id"])
    reviewed_version = int(row["version"])
    session = PrefectEditSession.from_rows([row])
    monkeypatch.setattr(people.PrefectEditSession, "from_rows", lambda _rows: session)

    async def immediate(operation, **_kwargs):
        return operation()
    monkeypatch.setattr(people, "_run_with_progress", immediate)
    monkeypatch.setattr(ui, "notify", lambda *args, **kwargs: None)

    async def run():
        monkeypatch.setattr(core, "loop", asyncio.get_running_loop())
        client = Client(ui.page("/test-archive-guard"))
        with client, ui.column() as host:
            guard = people._render_inline_prefect_directory(workflow, [row], on_full_edit=lambda row: None)
        try:
            if external_update:
                workflow.patch_prefects_batch(
                    (PrefectPatch(person_id, {"remarks": "unreviewed external edit"}, reviewed_version),),
                    command_id="external-edit",
                )
                with host:
                    assert await guard.flush()
                assert guard.reviewed_version(person_id) == reviewed_version
                with pytest.raises(WorkflowConflictError):
                    workflow.archive_prefect(person_id, expected_version=guard.reviewed_version(person_id), command_id="archive-stale")
                assert person_id in {item["id"] for item in workflow.prefects()}
            else:
                session.stage(person_id, "remarks", "our own buffered edit")
                with host:
                    assert await guard.flush()
                assert guard.reviewed_version(person_id) == reviewed_version + 1
                workflow.archive_prefect(person_id, expected_version=guard.reviewed_version(person_id), command_id="archive-after-flush")
                assert person_id not in {item["id"] for item in workflow.prefects()}
            await asyncio.sleep(0)
        finally:
            host.delete()
            client.delete()
    asyncio.run(run())
