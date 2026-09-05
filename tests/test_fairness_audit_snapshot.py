"""Audit exports must never mix roster state and a later fairness ledger."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from threading import Event
from types import SimpleNamespace

from pypdf import PdfReader
import pytest

from nicegui_app.access_context import (
    AccessMode,
    PageContext,
    Principal,
    PrincipalExpiredError,
)
from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services import roster_export
from nicegui_app.services.guest_adapter import GuestWorkspaceAdapter
from nicegui_app.services.guest_workspace import GuestWorkspaceRegistry
from nicegui_app.services.operation_context import PageContextWorkflowAdapter
from nicegui_app.services.roster_workflow import RosterWorkflow, WorkflowError


WEEK_START = date(2026, 9, 7)


def _guest_context(*, expired=False):
    return PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest:audit-test",
            session_id="audit-test-session",
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=-1 if expired else 30),
        )
    )


@pytest.fixture(params=["official", "guest"])
def audit_sources(request, tmp_path):
    if request.param == "official":
        reader = RosterWorkflow(
            database_path=tmp_path / "fictional-audit.sqlite3",
            backup_dir=tmp_path / "backups",
            seed_path=PREFECT_SEED_PATH,
        )
        reader.bootstrap()
        writer = RosterWorkflow(
            database_path=reader.database_path,
            backup_dir=reader.backup_dir,
        )
        writer.bootstrap()
    else:
        registry = GuestWorkspaceRegistry(b"audit-test-secret-at-least-thirty-two-bytes")
        reader, writer = (
            GuestWorkspaceAdapter(
                _guest_context(), registry, workspace_id="audit-workspace", tab_id="audit-tab",
            )
            for _ in range(2)
        )
    draft = reader.generate_and_save_draft(WEEK_START)
    yield reader, writer, draft
    if request.param == "official":
        reader._dispose_database_connections()
        writer._dispose_database_connections()


def test_audit_pdf_reads_only_one_snapshot_before_rendering(monkeypatch):
    snapshot = SimpleNamespace(
        week={"id": 7, "weekStart": WEEK_START, "status": "published", "version": 3},
        active_assignment_count=26,
        fairness_rows=({
            "id": "fictional", "nameZh": "測試風紀", "form": "F.4", "className": "4A",
            "historyWeight": 12.5, "historyDuties": 8,
        },),
    )
    calls = []

    class SnapshotOnlySource:
        def roster_fairness_audit_snapshot(self, roster_week_id):
            calls.append(roster_week_id)
            return snapshot

        def __getattr__(self, name):
            pytest.fail(f"Audit renderer must not use a separate workflow read: {name}")

    register_fonts = roster_export._register_cjk_fonts

    def render_after_snapshot():
        assert calls == [7], "All database/workspace reads must finish before rendering"
        return register_fonts()

    monkeypatch.setattr(roster_export, "_register_cjk_fonts", render_after_snapshot)
    export = roster_export.build_fairness_audit_pdf(SnapshotOnlySource(), 7, language="en")
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(export.content)).pages)
    assert calls == [7]
    assert "Published" in text and "Active assignments: 26" in text
    assert "測試風紀" in text and "12.5" in text
    assert export.filename == "SYSS_Fairness_Audit_20260907_EN.pdf"


@pytest.mark.parametrize("change", ["publish", "withdraw"])
def test_audit_snapshot_survives_concurrent_publication_or_withdrawal(
    audit_sources, monkeypatch, change,
):
    reader, writer, draft = audit_sources
    if change == "withdraw":
        writer.publish(draft.id, expected_week_version=draft.version)
    before_week = reader.roster_week(draft.id)
    before_fairness = reader.fairness_rows()
    before_active = sum(row["status"] == "active" for row in reader.assignments(draft.id))
    # Fail immediately on a missing contract, before starting coordinated workers.
    snapshot_read = reader.roster_fairness_audit_snapshot
    week_read = Event()
    committed = Event()
    hook_name = "_week_or_error" if isinstance(reader, RosterWorkflow) else "_week_record"
    original_week_read = getattr(reader, hook_name)

    def pause_after_week(*args, **kwargs):
        week = original_week_read(*args, **kwargs)
        week_read.set()
        assert committed.wait(15), "Writer should commit while audit read snapshot remains open"
        return week

    monkeypatch.setattr(reader, hook_name, pause_after_week)

    def change_roster():
        assert week_read.wait(15), "Audit reader did not reach its first roster read"
        try:
            if change == "publish":
                writer.publish(draft.id, expected_week_version=int(before_week["version"]))
            else:
                writer.withdraw_published_roster(
                    draft.id, expected_version=int(before_week["version"]),
                    reason="Fictional concurrency test", command_id="audit-withdraw-test",
                )
        finally:
            committed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        mutation = pool.submit(change_roster)
        snapshot = pool.submit(snapshot_read, draft.id).result(timeout=20)
        mutation.result(timeout=20)
    assert snapshot.week == before_week
    assert list(snapshot.fairness_rows) == before_fairness
    assert snapshot.active_assignment_count == before_active
    assert writer.roster_week(draft.id)["status"] != before_week["status"]
    assert writer.fairness_rows() != before_fairness


def test_audit_snapshot_is_detached_and_read_only(audit_sources, monkeypatch):
    reader, _writer, draft = audit_sources
    before_week = reader.roster_week(draft.id)
    before_fairness = reader.fairness_rows()
    snapshot = reader.roster_fairness_audit_snapshot(draft.id)
    snapshot.week["closedDays"].append("MONDAY")
    snapshot.fairness_rows[0]["historyWeight"] = -1000
    assert reader.roster_week(draft.id) == before_week
    assert reader.fairness_rows() == before_fairness

    if isinstance(reader, GuestWorkspaceAdapter):
        state = reader._state()
        unchanged_state = deepcopy(state)
        reads = []

        def read_once():
            reads.append(True)
            assert len(reads) == 1, "Guest audit must use exactly one protected workspace copy"
            return state

        monkeypatch.setattr(reader, "_state", read_once)
        reader.roster_fairness_audit_snapshot(draft.id)
        assert state == unchanged_state, "Reading an audit must not mutate the workspace copy"
        assert reads == [True]


def test_audit_snapshot_missing_week_fails_closed(audit_sources):
    reader, _writer, _draft = audit_sources
    with pytest.raises(WorkflowError, match="was not found"):
        reader.roster_fairness_audit_snapshot(999_999)


def test_official_audit_releases_session_before_pdf_rendering(audit_sources, monkeypatch):
    reader, _writer, draft = audit_sources
    if not isinstance(reader, RosterWorkflow):
        pytest.skip("SQLite connection ownership only applies to the official adapter")
    session_scope = reader._session
    active_sessions = []

    @contextmanager
    def tracked_session():
        with session_scope() as session:
            active_sessions.append(session)
            try:
                yield session
            finally:
                active_sessions.remove(session)

    register_fonts = roster_export._register_cjk_fonts

    def no_session_during_render():
        assert active_sessions == []
        return register_fonts()

    monkeypatch.setattr(reader, "_session", tracked_session)
    monkeypatch.setattr(roster_export, "_register_cjk_fonts", no_session_during_render)
    assert roster_export.build_fairness_audit_pdf(reader, draft.id).content.startswith(b"%PDF")


def test_guest_audit_requires_active_principal(audit_sources):
    reader, _writer, draft = audit_sources
    if not isinstance(reader, GuestWorkspaceAdapter):
        pytest.skip("Guest expiry is checked by the Guest adapter")
    reader._context = _guest_context(expired=True)
    with pytest.raises(PrincipalExpiredError):
        reader.roster_fairness_audit_snapshot(draft.id)


def test_official_audit_adapter_rechecks_principal(audit_sources):
    reader, _writer, draft = audit_sources
    if not isinstance(reader, RosterWorkflow):
        pytest.skip("Official page identity is checked by the page-scoped adapter")
    context = PageContext.create(Principal(
        mode=AccessMode.ADMIN, subject="audit-test", session_id="audit-admin",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    ))
    guarded = PageContextWorkflowAdapter(reader, context)
    with pytest.raises(PrincipalExpiredError):
        guarded.roster_fairness_audit_snapshot(draft.id)
