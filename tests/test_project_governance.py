from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.project_governance import (
    _status_schema_violations,
    architecture_violations,
    documentation_violations,
    mutable_current_release_claims,
    render_current_status,
    render_status_block,
    synchronize_status,
    validate_project_contracts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _release_state() -> dict[str, object]:
    return json.loads(
        (PROJECT_ROOT / "docs" / "status" / "current-release.json").read_text(
            encoding="utf-8"
        )
    )


def test_project_governance_contracts_are_self_consistent() -> None:
    assert validate_project_contracts(PROJECT_ROOT) == ()


def test_current_status_markdown_is_deterministic_from_machine_state() -> None:
    state = _release_state()
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


def test_status_schema_rejects_candidate_partial_gates_and_code_only_rollback() -> None:
    candidate = _release_state()
    candidate["state"] = "candidate"
    partial_gates = _release_state()
    partial_gates["release"]["formal_gates"]["passed"] = 14  # type: ignore[index]
    unsafe_rollback = _release_state()
    unsafe_rollback["database"]["rollback_requires_compatible_restore"] = False  # type: ignore[index]
    unresolved_origin = _release_state()
    unresolved_origin["origin"]["maintenance"] = True  # type: ignore[index]

    assert "status.state" in {
        item.code for item in _status_schema_violations(candidate, "state.json")
    }
    assert "status.gates" in {
        item.code for item in _status_schema_violations(partial_gates, "state.json")
    }
    assert "status.rollback" in {
        item.code for item in _status_schema_violations(unsafe_rollback, "state.json")
    }
    assert "status.origin-obligations" in {
        item.code for item in _status_schema_violations(unresolved_origin, "state.json")
    }


def test_status_rendering_fails_closed_for_language_and_acceptance() -> None:
    state = _release_state()
    with pytest.raises(ValueError, match="unsupported status language"):
        render_status_block(state, language="fr", link="CURRENT_STATUS.md")

    state["acceptance"]["supervised_human"] = "unknown"  # type: ignore[index]
    rendered = render_current_status(state)
    assert "未通過（狀態無效） / Not passed (invalid state)" in rendered
    assert "尚待完成 / Pending" not in rendered


def test_documentation_validation_reports_unsupported_consumer_language(
    tmp_path: Path,
) -> None:
    state = _release_state()
    status_path = tmp_path / "docs" / "status" / "CURRENT_STATUS.md"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(render_current_status(state), encoding="utf-8")
    consumer = tmp_path / "README.md"
    consumer.write_text(
        "# Entry\n\n"
        + render_status_block(
            state,
            language="en",
            link="docs/status/CURRENT_STATUS.md",
        )
        + "\n",
        encoding="utf-8",
    )
    collection_document = tmp_path / "docs" / "audits" / "sample.md"
    collection_document.parent.mkdir(parents=True)
    collection_document.write_text("[missing](missing.md)\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "status_document": "docs/status/CURRENT_STATUS.md",
        "document_classes": {
            "entrypoint": ["README.md"],
            "living": ["docs/status/CURRENT_STATUS.md"],
        },
        "collections": {"docs/audits": "evidence"},
        "topic_owners": {},
        "status_consumers": [
            {
                "path": "README.md",
                "language": "fr",
                "link": "docs/status/CURRENT_STATUS.md",
            }
        ],
    }

    violations = documentation_violations(tmp_path, manifest, state)

    assert "documentation.unrenderable-status-consumer" in {
        item.code for item in violations
    }
    assert any(
        item.code == "documentation.broken-link"
        and item.path == "docs/audits/sample.md"
        for item in violations
    )


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


def test_architecture_contract_resolves_relative_service_imports(tmp_path: Path) -> None:
    source_root = tmp_path / "nicegui_app" / "services"
    source_root.mkdir(parents=True)
    (source_root / "bad_relative_dependency.py").write_text(
        "from ..ui import components\n",
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


def test_status_sync_rejects_invalid_schema_before_writing(tmp_path: Path) -> None:
    status_dir = tmp_path / "docs" / "status"
    status_dir.mkdir(parents=True)
    state = _release_state()
    state["state"] = "candidate"
    (status_dir / "current-release.json").write_text(
        json.dumps(state),
        encoding="utf-8",
    )
    current_status = status_dir / "CURRENT_STATUS.md"
    current_status.write_text("unchanged status\n", encoding="utf-8")
    consumer = tmp_path / "README.md"
    consumer.write_text(
        "# Entry\n\n<!-- SING_YIN_CURRENT_STATUS:START -->\nold\n"
        "<!-- SING_YIN_CURRENT_STATUS:END -->\n",
        encoding="utf-8",
    )
    manifest = {
        "status_source": "docs/status/current-release.json",
        "status_document": "docs/status/CURRENT_STATUS.md",
        "status_consumers": [
            {
                "path": "README.md",
                "language": "en",
                "link": "docs/status/CURRENT_STATUS.md",
            }
        ],
    }
    (tmp_path / "docs" / "documentation-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid release state"):
        synchronize_status(tmp_path)

    assert current_status.read_text(encoding="utf-8") == "unchanged status\n"
    assert "\nold\n" in consumer.read_text(encoding="utf-8")
