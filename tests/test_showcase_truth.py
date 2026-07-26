from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT


def test_engineering_showcase_uses_current_release_evidence_instead_of_stale_counts() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")

    assert '("208", "science"' not in source
    assert '("08", "verified"' not in source
    assert "evidence.passed_checks" in source and "evidence.total_checks" in source
    assert "engineering_fact_full_suite" in source
    assert "engineering_gate_runtime" in source
    assert "engineering_gate_cloudflare" in source
    assert "engineering_gate_mobile" in source
    assert "engineering_gate_guest" in source
    assert source.count('"engineering_gate_') == 13
    assert 'tag="h2"' in source


def test_dashboard_keeps_one_primary_generation_action_and_progressively_discloses_tone_settings() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "home.py").read_text(encoding="utf-8")
    dashboard = source.split('@ui.page("/dashboard")', 1)[0]

    assert dashboard.count('action_key="create_draft"') == 1
    assert 'action_key="empty_start_action"' not in dashboard
    assert dashboard.index('ui.expansion(reflection.get("title"') < dashboard.index("tone_select = ui.select")


def test_release_evidence_tone_preserves_operator_meaning() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")

    assert '"pass": "stable"' in source
    assert '"running": "action"' in source
    assert '"fail": "danger"' in source
    assert '"stale": "attention"' in source
    assert 'classes(f"sy-engineering-gate-icon sy-fg-{evidence_tone}")' in source
    assert 'evidence_tone = _release_evidence_tone(evidence.state)' in source


def test_engineering_evidence_index_classifies_every_current_release_gate() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")
    engineering_page = source.split('@ui.page("/engineering")', 1)[1].split(
        '@ui.page("/system-architecture")', 1
    )[0]

    assert engineering_page.count('"engineering_gate_') == 13
    assert '("verified_user", "engineering_gate_guest", "access")' in engineering_page
    assert 't(f"engineering_evidence_type_{type_code}")' in engineering_page
    for evidence_type in ("repository", "access", "quality", "runtime", "recovery"):
        assert f'"{evidence_type}"' in engineering_page
    assert 'data-testid=engineering-evidence-index' in engineering_page
    assert 'test_id="engineering-evidence-table"' in engineering_page
    assert "ui.timer(" not in engineering_page
    assert "requestAnimationFrame" in engineering_page


def test_platform_explains_the_software_identity_without_replacing_the_school_crest() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")
    platform_page = source.split('@ui.page("/platform")', 1)[1].split(
        '@ui.page("/engineering")', 1
    )[0]

    assert 'render_service_weave_mark(context="display", test_id="platform-product-mark")' in platform_page
    assert 't("service_weave_name")' in platform_page
    assert 't("app_name")' in platform_page


def test_developer_reference_exposes_real_health_release_and_extension_boundaries() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")
    architecture_page = source.split('@ui.page("/system-architecture")', 1)[1]

    assert 'data-testid=developer-reference' in architecture_page
    assert architecture_page.count('"developer_reference_') >= 20
    assert "http://127.0.0.1:8080/healthz" in architecture_page
    assert "http://127.0.0.1:8080/readyz" in architecture_page
    assert "scripts/verify_update.py --release" in architecture_page
    assert "scripts/verify_release_candidate.py" in architecture_page


def test_showcase_limits_template_kickers_and_avoids_fictional_offices() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "showcase.py").read_text(encoding="utf-8")
    messages = (PROJECT_ROOT / "nicegui_app" / "ui" / "i18n_catalog" / "platform.py").read_text(encoding="utf-8")

    assert "show_kicker: bool = False" in source
    assert source.count("show_kicker=True") <= 3
    for inflated_label in (
        "Weekly Operations Office",
        "Fairness Assurance Office",
        "Service Experience Office",
        "Systems Continuity Office",
        "enterprise-style capabilities",
    ):
        assert inflated_label not in messages
