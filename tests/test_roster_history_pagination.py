from datetime import date, datetime, timedelta, timezone

import pytest

from nicegui_app.access_context import AccessMode, PageContext, Principal
from nicegui_app.persistence.models import RosterWeekRecord
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.roster_workflow import RosterWorkflow
from roster_policy import DAYS


@pytest.mark.parametrize("mode", ["formal", "guest"])
@pytest.mark.parametrize("count", [25, 26, 27])
def test_history_lookahead_never_skips_or_repeats_a_week(tmp_path, mode, count, monkeypatch):
    first_week = date(2026, 9, 7)
    if mode == "formal":
        workflow = RosterWorkflow(database_path=tmp_path / "history.sqlite3",
                                  backup_dir=tmp_path / "backups", seed_path=None)
        workflow.bootstrap()
        with workflow._session() as session:
            records = [RosterWeekRecord(week_start=first_week + timedelta(weeks=index),
                                        policy_version="fictional-history",
                                        generated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                                        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                                        updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc))
                       for index in range(count)]
            session.add_all(records)
            session.flush()
            ids = [row.id for row in records]
            session.commit()
    else:
        context = PageContext.create(Principal(mode=AccessMode.GUEST,
            subject="guest:history-fixture", session_id="history-fixture",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)),
            request_reference="HISTORY-FIXTURE")
        workflow = GuestWorkspaceAdapter(context,
            GuestWorkspaceRegistry(b"history-fixture-only-secret-32-bytes", max_weeks=100),
            workspace_id="history-fixture", tab_id="history-fixture")
        ids = [workflow.generate_and_save_draft(first_week + timedelta(weeks=index),
                    closed_days=DAYS).id for index in range(count)]
    monkeypatch.setattr(workflow, "roster_weeks", lambda: pytest.fail("History must not request all output rows"))
    collected = []
    has_next_flags = []
    for page in range(1, 4):
        rows = workflow.roster_week_history(page=page, page_size=12, lookahead=True)
        assert len(rows) <= 13
        has_next_flags.append(len(rows) > 12)
        collected.extend(row["id"] for row in rows[:12])
        ordinary = workflow.roster_week_history(page=page, page_size=12)
        assert [row["id"] for row in ordinary] == [row["id"] for row in rows[:12]]
    assert collected == ids[::-1]
    assert len(set(collected)) == count
    assert has_next_flags == [True, True, False]
    assert workflow.roster_week_history(page=4, page_size=12, lookahead=True) == []
