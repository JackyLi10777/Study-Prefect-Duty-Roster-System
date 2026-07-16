from __future__ import annotations

import io
from pathlib import Path
import sqlite3

import pytest

from nicegui_app.release_evidence import RELEASE_SOURCE_FILES
from scripts import verify_release_candidate, verify_unified_guest_ui
from scripts.verify_unified_guest_ui import (
    EDITORIAL_PARITY_ROUTES,
    SHARED_ROUTES,
    UnifiedGuestVerificationError,
    isolated_inputs,
    logical_database_fingerprint,
)


def _isolated_guest_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    database_path = tmp_path / "guest.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence (value) VALUES ('fictional')")
    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", "E2E-ABCDEF123456")
    monkeypatch.setenv("SING_YIN_E2E_ACCESS_MODE", "guest")
    monkeypatch.setenv("SING_YIN_UNIFIED_GUEST", "1")
    monkeypatch.setenv("SING_YIN_ADMIN_TEST_URL", "http://127.0.0.1:18101")
    monkeypatch.setenv("SING_YIN_GUEST_TEST_URL", "http://127.0.0.1:18102")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("SING_YIN_UNIFIED_GUEST_EVIDENCE_DIR", str(tmp_path / "evidence"))
    return database_path


def test_unified_guest_verifier_accepts_only_explicit_disposable_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = _isolated_guest_environment(monkeypatch, tmp_path)

    admin_url, guest_url, resolved_database, evidence_dir = isolated_inputs()

    assert admin_url == "http://127.0.0.1:18101"
    assert guest_url == "http://127.0.0.1:18102"
    assert resolved_database == database_path.resolve()
    assert evidence_dir == (tmp_path / "evidence").resolve()
    assert evidence_dir.is_dir()


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("SING_YIN_E2E_ISOLATED", "0", "SING_YIN_E2E_ISOLATED"),
        ("SING_YIN_E2E_RUN_ID", "E2E-short", "SING_YIN_E2E_RUN_ID"),
        ("SING_YIN_E2E_ACCESS_MODE", "admin", "SING_YIN_E2E_ACCESS_MODE"),
        ("SING_YIN_UNIFIED_GUEST", "0", "SING_YIN_UNIFIED_GUEST"),
        ("SING_YIN_GUEST_TEST_URL", "https://example.com", "loopback"),
    ],
)
def test_unified_guest_verifier_fails_closed_on_unsafe_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    value: str,
    message: str,
) -> None:
    _isolated_guest_environment(monkeypatch, tmp_path)
    monkeypatch.setenv(name, value)

    with pytest.raises(UnifiedGuestVerificationError, match=message):
        isolated_inputs()


def test_unified_guest_database_fingerprint_detects_any_logical_write(tmp_path: Path) -> None:
    database_path = tmp_path / "guest.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence (value) VALUES ('fixture')")

    before, before_counts = logical_database_fingerprint(database_path)
    unchanged, unchanged_counts = logical_database_fingerprint(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO evidence (value) VALUES ('unexpected-write')")
    after, after_counts = logical_database_fingerprint(database_path)

    assert before == unchanged
    assert before_counts == unchanged_counts == {"evidence": 1}
    assert after != before
    assert after_counts == {"evidence": 2}


def test_unified_guest_verifier_covers_shared_product_and_editorial_parity() -> None:
    assert {
        "/",
        "/rosters",
        "/prefects",
        "/handover",
        "/settings",
        "/access-control",
        "/platform",
        "/engineering",
        "/system-architecture",
        "/getting-started",
        "/guide",
        "/devotional",
    } == set(SHARED_ROUTES)
    assert set(EDITORIAL_PARITY_ROUTES) < set(SHARED_ROUTES)

    source = Path(verify_unified_guest_ui.__file__).read_text(encoding="utf-8")
    for contract in (
        "logical_database_fingerprint",
        "_assert_route_parity",
        "_exercise_cross_tab_isolation",
        "_exercise_broadcast_cleanup",
        "_wait_for_guest_sessions",
        "/readyz",
        "guest-mode-banner",
        "guest-restricted-state",
    ):
        assert contract in source


def test_release_candidate_launches_separate_unified_operator_and_guest_origins(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_environments: list[dict[str, str]] = []
    captured_check: dict[str, object] = {}

    def fake_start(environment: dict[str, str], _log_path: Path):  # type: ignore[no-untyped-def]
        captured_environments.append(environment)
        return object(), io.StringIO()

    def fake_check(
        name: str,
        command: list[str],
        environment: dict[str, str],
        _report: dict[str, object],
    ) -> None:
        captured_check.update(name=name, command=command, environment=environment)

    monkeypatch.setattr(verify_release_candidate, "_start_server", fake_start)
    monkeypatch.setattr(verify_release_candidate, "_wait_until_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(verify_release_candidate, "_run_check", fake_check)
    monkeypatch.setattr(verify_release_candidate, "_stop_server", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(verify_release_candidate, "_assert_server_console_clean", lambda *_args: None)

    verify_release_candidate._run_unified_access_phase(root=tmp_path, report={})

    assert len(captured_environments) == 2
    admin, guest = captured_environments
    assert admin["SING_YIN_UNIFIED_GUEST"] == "1"
    assert guest["SING_YIN_UNIFIED_GUEST"] == "1"
    assert admin["SING_YIN_E2E_ACCESS_MODE"] == ""
    assert guest["SING_YIN_E2E_ACCESS_MODE"] == "guest"
    assert guest["SING_YIN_ADMIN_TEST_URL"] == admin["SING_YIN_TEST_URL"]
    assert guest["SING_YIN_GUEST_TEST_URL"] == guest["SING_YIN_TEST_URL"]
    assert captured_check["name"] == "verify_unified_guest_ui"
    assert "scripts/verify_unified_guest_ui.py" in captured_check["command"]


def test_release_candidate_waits_for_write_readiness_not_only_liveness() -> None:
    source = Path(verify_release_candidate.__file__).read_text(encoding="utf-8")

    assert 'endpoint = "readyz" if require_write_ready else "healthz"' in source
    assert 'payload.get("status") == "ready"' in source
    assert 'payload.get("writeReady") is True' in source
    assert "require_write_ready=not blocked_backup" in source


def test_release_fingerprint_tracks_unified_guest_verifier() -> None:
    assert (
        verify_unified_guest_ui.PROJECT_ROOT / "scripts" / "verify_unified_guest_ui.py"
        in RELEASE_SOURCE_FILES
    )
