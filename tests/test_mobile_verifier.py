from __future__ import annotations

from pathlib import Path

import pytest

from scripts import verify_nicegui_mobile
from scripts.verify_nicegui_mobile import (
    CANONICAL_BACKUPS,
    CANONICAL_DATABASE,
    isolated_paths,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _set_isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SING_YIN_E2E_ISOLATED", "1")
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", "E2E-ABCDEF123456")
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(tmp_path / "runtime.sqlite3"))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(verify_nicegui_mobile, "BASE_URL", "http://127.0.0.1:18767")


def test_mobile_verifier_requires_explicit_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SING_YIN_E2E_ISOLATED",
        "SING_YIN_E2E_RUN_ID",
        "SING_YIN_DATABASE_PATH",
        "SING_YIN_BACKUP_DIR",
        "SING_YIN_LOG_DIR",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="SING_YIN_E2E_ISOLATED"):
        isolated_paths()


def test_mobile_verifier_accepts_disposable_loopback_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_isolated_environment(monkeypatch, tmp_path)

    database_path, backup_dir, log_dir = isolated_paths()

    assert database_path == (tmp_path / "runtime.sqlite3").resolve()
    assert backup_dir == (tmp_path / "backups").resolve()
    assert log_dir == (tmp_path / "logs").resolve()


@pytest.mark.parametrize("run_id", ["", "E2E-short", "E2E-abcdef123456", "TEST-ABCDEF123456"])
def test_mobile_verifier_rejects_missing_or_malformed_run_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run_id: str,
) -> None:
    _set_isolated_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("SING_YIN_E2E_RUN_ID", run_id)

    with pytest.raises(RuntimeError, match="SING_YIN_E2E_RUN_ID"):
        isolated_paths()


@pytest.mark.parametrize(
    ("database_path", "backup_path"),
    [
        (CANONICAL_DATABASE, Path("D:/temporary-sing-yin-mobile-backups")),
        (Path("D:/temporary-sing-yin-mobile.sqlite3"), CANONICAL_BACKUPS),
    ],
)
def test_mobile_verifier_rejects_canonical_school_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    database_path: Path,
    backup_path: Path,
) -> None:
    _set_isolated_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("SING_YIN_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("SING_YIN_BACKUP_DIR", str(backup_path))

    with pytest.raises(RuntimeError, match="canonical school database"):
        isolated_paths()


def test_mobile_verifier_rejects_non_loopback_browser_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_isolated_environment(monkeypatch, tmp_path)
    monkeypatch.setattr(verify_nicegui_mobile, "BASE_URL", "https://example.com")

    with pytest.raises(RuntimeError, match="loopback"):
        isolated_paths()


def test_mobile_verifier_declares_real_touch_contexts_and_shared_route_matrix() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(encoding="utf-8")

    for dimensions in (
        'width=390,\n            height=844',
        'width=320,\n            height=760',
        'width=256,\n            height=700',
        'width=768,\n            height=1024',
        'width=820,\n            height=1180',
        'width=1024,\n            height=768',
        'width=844,\n            height=390',
    ):
        assert dimensions in source
    assert "is_mobile=True" in source
    assert "has_touch=True" in source
    assert '"console",' in source
    assert 'message.type == "error"' in source
    assert 'page.on("pageerror"' in source
    assert "document.documentElement.scrollWidth" in source
    assert 'get_by_test_id("mobile-bottom-navigation")' in source
    assert "tabs.count() != 4" in source
    assert "item.width < 44 || item.height < 44" in source
    for selector in (".q-toggle", ".q-checkbox", ".q-radio", ".q-item--clickable"):
        assert selector in source
    assert "drawer.evaluate" in source
    assert 'get_by_test_id("mobile-more")' in source
    assert "Opening mobile navigation must move focus into the drawer" in source
    assert 'page.keyboard.press("Shift+Tab")' in source
    assert "drawer did not cycle Tab to its first control" in source
    assert 'locator(".q-drawer__backdrop:visible")' in source
    assert 'page.keyboard.press("Escape")' in source
    assert "Backdrop-closing mobile navigation must restore focus to More" in source
    assert "document.activeElement === button" in source
    assert "button?.getAttribute('aria-label') === 'More'" in source
    assert "button?.dataset.syDrawerA11y === 'ready'" in source
    assert 'metrics["overflowY"]' in source
    assert "mainPaddingBottom" in source
    assert "navigationHeight" in source
    assert "_assert_responsive_table_cards(portrait_page)" in source
    assert '".sy-responsive-table-mobile:visible"' in source
    assert 'has_text="Dashboard"' in source
    assert "body.body--dark" in source
    for route in (
        '"/rosters"',
        '"/prefects"',
        '"/handover"',
        '"/settings"',
        '"/access-control"',
        '"/devotional"',
        '"/system-architecture"',
    ):
        assert route in source
    assert verify_nicegui_mobile.COMPACT_ROUTES["/handover"] == "Handover guide"


def test_touch_target_measurement_waits_for_stable_fonts_and_reports_diagnostics() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(encoding="utf-8")

    assert "document.fonts?.ready" in source
    assert "await document.fonts.ready" in source
    assert source.count("requestAnimationFrame(") >= 2
    assert "className: String(element.className" in source
    assert "testId: element.getAttribute('data-testid')" in source


def test_mobile_verifier_records_only_seven_non_sensitive_layout_screenshots() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_nicegui_mobile.py").read_text(encoding="utf-8")

    for filename in (
        "nicegui-mobile-390.png",
        "nicegui-mobile-320-drawer.png",
        "nicegui-mobile-256-reflow.png",
        "nicegui-tablet-768.png",
        "nicegui-tablet-820x1180.png",
        "nicegui-tablet-1024x768.png",
        "nicegui-mobile-landscape.png",
    ):
        assert filename in source
    assert source.count(".screenshot(") == 7


def test_release_candidate_runs_mobile_verification_after_the_write_pipeline() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_release_candidate.py").read_text(encoding="utf-8")
    write_pipeline = '"scripts/verify_nicegui_write_pipeline.py"'
    mobile_verifier = '"scripts/verify_nicegui_mobile.py"'

    assert write_pipeline in source
    assert mobile_verifier in source
    assert source.index(write_pipeline) < source.index(mobile_verifier)


def test_mobile_styles_reserve_safe_area_and_shared_main_content_space() -> None:
    mobile_css = (PROJECT_ROOT / "nicegui_app" / "assets" / "css" / "sing-yin-mobile-v1.css").read_text(
        encoding="utf-8"
    )

    assert "env(safe-area-inset-bottom)" in mobile_css
    assert ".sy-mobile-tabbar" in mobile_css
    assert ".sy-main" in mobile_css
    assert "--sy-mobile-tabbar-height" in mobile_css
