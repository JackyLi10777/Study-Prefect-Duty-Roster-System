from __future__ import annotations

import io
from pathlib import Path
import sqlite3

import pytest

from nicegui_app.release_evidence import RELEASE_SOURCE_FILES
from scripts import verify_release_candidate, verify_unified_guest_ui
from scripts.verify_unified_guest_ui import (
    EDITORIAL_PARITY_ROUTES,
    FIXTIONAL_PREFECT_NAMES,
    SHARED_ROUTES,
    UnifiedGuestVerificationError,
    _assert_clean_browser,
    _demo_download_evidence,
    _is_navigation_context_reset,
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
    support_dir = tmp_path / "admin-support"
    support_dir.mkdir()
    monkeypatch.setenv("SING_YIN_ADMIN_SUPPORT_DIR", str(support_dir))
    return database_path


def test_unified_guest_verifier_accepts_only_explicit_disposable_inputs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = _isolated_guest_environment(monkeypatch, tmp_path)

    admin_url, guest_url, resolved_database, evidence_dir, support_dir = isolated_inputs()

    assert admin_url == "http://127.0.0.1:18101"
    assert guest_url == "http://127.0.0.1:18102"
    assert resolved_database == database_path.resolve()
    assert evidence_dir == (tmp_path / "evidence").resolve()
    assert evidence_dir.is_dir()
    assert support_dir == (tmp_path / "admin-support").resolve()


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
        "/support",
    } == set(SHARED_ROUTES)
    assert set(EDITORIAL_PARITY_ROUTES) < set(SHARED_ROUTES)

    source = Path(verify_unified_guest_ui.__file__).read_text(encoding="utf-8")
    for contract in (
        "logical_database_fingerprint",
        "_assert_route_parity",
        "_exercise_weekly_workflow",
        "_exercise_summary_downloads",
        "_reload_and_verify_signed_snapshot",
        "_exercise_handover_reset_restore",
        "_exercise_support_flows",
        "_exercise_true_duplicate_and_tamper",
        "_demo_download_evidence",
        "_exercise_broadcast_cleanup",
        "_wait_for_guest_sessions",
        "/readyz",
        "guest-mode-banner",
        "guest-restricted-state",
        "pre-generation-leave-prefect",
        "pre-generation-leave-reason",
        "draft-change-reason",
        "leave-adjustment-reason",
        "download-summary-json",
        "school-year-rollover-confirmation",
        "page.expect_navigation(",
        "late ``ui.navigate.reload()``",
        "safe-fixture",
        "main#main-content .q-select:visible",
    ):
        assert contract in source
    assert source.count('page.locator("main#main-content .q-select:visible")') == 2

    weekly_source = (
        Path(__file__).parents[1] / "nicegui_app" / "ui" / "page_routes" / "weekly.py"
    ).read_text(encoding="utf-8")
    assert "data-testid=pre-generation-leave-prefect" in weekly_source


def test_unified_guest_verifier_accepts_only_explicit_fictional_demo_json() -> None:
    content = (
        b'{"demo":true,"fictional":true,'
        b'"evidenceType":"sing-yin-study-prefect-demo-period-summary"}'
    )

    evidence = _demo_download_evidence(
        filename="SYSS_DEMO_Service_Summary_20260720.json",
        content=content,
        kind="json",
    )

    assert evidence["filename"] == "SYSS_DEMO_Service_Summary_20260720.json"
    assert evidence["kind"] == "json"
    assert evidence["bytes"] == len(content)
    assert len(evidence["sha256"]) == 64
    assert all(name for name in FIXTIONAL_PREFECT_NAMES)

    with pytest.raises(UnifiedGuestVerificationError, match="fictional DEMO"):
        _demo_download_evidence(
            filename="SYSS_Service_Summary_20260720.json",
            content=b'{"demo":false,"fictional":false,"evidenceType":"official"}',
            kind="json",
        )


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
    assert admin["SING_YIN_LOCAL_MAINTENANCE"] == "1"
    assert admin["SING_YIN_REQUIRE_GATEWAY_PRINCIPAL"] == "0"
    assert guest["SING_YIN_LOCAL_MAINTENANCE"] == "1"
    assert guest["SING_YIN_REQUIRE_GATEWAY_PRINCIPAL"] == "0"
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


def test_app_wait_retries_only_the_expected_safe_navigation_context_reset() -> None:
    expected = verify_unified_guest_ui.PlaywrightError(
        "Page.evaluate: Execution context was destroyed, most likely because of a navigation"
    )
    unrelated = verify_unified_guest_ui.PlaywrightError("Page.evaluate: JavaScript exception")

    assert _is_navigation_context_reset(expected) is True
    assert _is_navigation_context_reset(unrelated) is False

    source = Path(verify_unified_guest_ui.__file__).read_text(encoding="utf-8")
    assert "for attempt in range(3):" in source
    assert "if not _is_navigation_context_reset(error) or attempt == 2:" in source


def test_browser_error_failure_preserves_bounded_diagnostics() -> None:
    with pytest.raises(UnifiedGuestVerificationError) as captured:
        _assert_clean_browser(
            ["asset failed", "websocket closed"],
            ["uncaught error"],
        )

    message = str(captured.value)
    assert "console=2, page=1" in message
    assert "console: asset failed" in message
    assert "console: websocket closed" in message
    assert "page: uncaught error" in message


def test_broadcast_cleanup_probe_respects_production_media_csp() -> None:
    source = Path(verify_unified_guest_ui.__file__).read_text(encoding="utf-8")
    cleanup = source.split("def _exercise_broadcast_cleanup", 1)[1].split(
        "def _assert_clean_browser", 1
    )[0]

    assert "document.createElement('audio')" in cleanup
    assert "data:audio" not in cleanup
    assert "getAttribute('src') === null" in cleanup


def test_duplicate_isolation_precedes_mobile_disconnect_cleanup_race() -> None:
    source = Path(verify_unified_guest_ui.__file__).read_text(encoding="utf-8")
    main_phase = source.split("def main() -> int:", 1)[1]

    assert main_phase.index("_exercise_true_duplicate_and_tamper(") < main_phase.index(
        "mobile_context = browser.new_context("
    )
    assert main_phase.index("mobile_context = browser.new_context(") < main_phase.index(
        "_exercise_broadcast_cleanup("
    )
    assert main_phase.index("_exercise_broadcast_cleanup(") < main_phase.index(
        "mobile_context.close()"
    )
