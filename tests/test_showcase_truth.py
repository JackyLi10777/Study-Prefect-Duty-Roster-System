from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT


def test_engineering_showcase_uses_current_release_evidence_instead_of_stale_counts() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")

    assert '("208", "science"' not in source
    assert '("08", "verified"' not in source
    assert "evidence.passed_checks" in source and "evidence.total_checks" in source
    assert "engineering_fact_full_suite" in source
    assert "engineering_gate_runtime" in source
    assert 'tag="h2"' in source


def test_dashboard_keeps_one_primary_generation_action_and_progressively_discloses_tone_settings() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "home.py").read_text(encoding="utf-8")
    dashboard = source.split('@ui.page("/dashboard")', 1)[0]

    assert dashboard.count('action_key="create_draft"') == 1
    assert 'action_key="empty_start_action"' not in dashboard
    assert dashboard.index('ui.expansion(reflection.get("title"') < dashboard.index("tone_select = ui.select")
