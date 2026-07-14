from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT


def test_desktop_and_write_verifiers_gate_uncaught_page_errors() -> None:
    for name in ("verify_nicegui_ui.py", "verify_nicegui_write_pipeline.py"):
        source = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert 'page.on("pageerror"' in source, name
        assert "assert not page_errors" in source, name
