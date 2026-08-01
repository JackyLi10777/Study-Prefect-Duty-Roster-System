from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.project_governance import (
    architecture_violations,
    mutable_current_release_claims,
    render_current_status,
    synchronize_status,
    validate_project_contracts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_governance_contracts_are_self_consistent() -> None:
    assert validate_project_contracts(PROJECT_ROOT) == ()


def test_current_status_markdown_is_deterministic_from_machine_state() -> None:
    state = json.loads(
        (PROJECT_ROOT / "docs" / "status" / "current-release.json").read_text(
            encoding="utf-8"
        )
    )
    rendered = render_current_status(state)
    committed = (PROJECT_ROOT / "docs" / "status" / "CURRENT_STATUS.md").read_text(
        encoding="utf-8"
    )

    assert committed == rendered
    assert state["release"]["tag"] in committed
    assert state["release"]["commit"] in committed
    assert state["database"]["alembic_head"] in committed


def test_mutable_current_release_claims_do_not_confuse_historical_live_evidence() -> None:
    claims = mutable_current_release_claims(
        "Current rc46 production. 目前正式 rc46。現行 rc46。"
        "These behaviours remained in live rc27; rc20 is historical."
    )

    assert claims == ("Current rc46", "目前正式 rc46", "現行 rc46")


def test_architecture_contract_rejects_a_service_to_ui_dependency(tmp_path: Path) -> None:
    source_root = tmp_path / "nicegui_app" / "services"
    source_root.mkdir(parents=True)
    (source_root / "bad_dependency.py").write_text(
        "from nicegui_app import ui\n",
        encoding="utf-8",
    )
    contract = {
        "schema_version": 1,
        "rules": [
            {
                "name": "services-do-not-import-ui",
                "source_paths": ["nicegui_app/services"],
                "forbidden_import_prefixes": ["nicegui_app.ui"],
            }
        ],
    }

    violations = architecture_violations(tmp_path, contract)

    assert len(violations) == 1
    assert violations[0].code == "architecture.forbidden-import"
    assert violations[0].path == "nicegui_app/services/bad_dependency.py"
    assert "nicegui_app.ui" in violations[0].message


def test_status_sync_preflights_every_consumer_before_writing(tmp_path: Path) -> None:
    status_dir = tmp_path / "docs" / "status"
    status_dir.mkdir(parents=True)
    source_state = PROJECT_ROOT / "docs" / "status" / "current-release.json"
    (status_dir / "current-release.json").write_text(
        source_state.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    current_status = status_dir / "CURRENT_STATUS.md"
    current_status.write_text("unchanged status\n", encoding="utf-8")
    good_consumer = tmp_path / "GOOD.md"
    good_consumer.write_text(
        "# Good\n\n<!-- SING_YIN_CURRENT_STATUS:START -->\nold\n"
        "<!-- SING_YIN_CURRENT_STATUS:END -->\n",
        encoding="utf-8",
    )
    bad_consumer = tmp_path / "BAD.md"
    bad_consumer.write_text("# Missing markers\n", encoding="utf-8")
    manifest = {
        "status_source": "docs/status/current-release.json",
        "status_document": "docs/status/CURRENT_STATUS.md",
        "status_consumers": [
            {"path": "GOOD.md", "language": "en", "link": "docs/status/CURRENT_STATUS.md"},
            {"path": "BAD.md", "language": "en", "link": "docs/status/CURRENT_STATUS.md"},
        ],
    }
    (tmp_path / "docs" / "documentation-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="BAD.md"):
        synchronize_status(tmp_path)

    assert current_status.read_text(encoding="utf-8") == "unchanged status\n"
    assert "\nold\n" in good_consumer.read_text(encoding="utf-8")
