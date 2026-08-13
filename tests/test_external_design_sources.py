from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from nicegui_app.ui.external_design_sources import (
    ExternalDesignSourceContractError,
    SOURCE_MANIFEST_PATH,
    load_external_design_sources,
)


def test_external_design_sources_are_versioned_and_non_executable_by_default() -> None:
    records = load_external_design_sources()

    assert {record.source_id for record in records} >= {
        "ibm-carbon-motion",
        "motion-primitives",
        "react-bits",
        "codrops-rotating-scroll",
        "motionsites-ai",
        "gsap",
    }
    assert [record.source_id for record in records if record.runtime_import] == ["gsap"]
    assert all(record.revision and record.license and record.asset_rights for record in records)
    assert all(record.removal for record in records)
    assert all(
        record.source_archive_sha256
        for record in records
        if record.decision in {"adopt-guidance", "adapt-behaviour", "reference-limited"}
    )
    gsap = next(record for record in records if record.source_id == "gsap")
    assert gsap.runtime_artifact_path == "nicegui_app/assets/vendor/gsap-3.13.0.min.js"
    assert gsap.license_evidence_path == "nicegui_app/assets/vendor/gsap-package.json"


def test_reference_only_sources_do_not_claim_asset_rights() -> None:
    records = {record.source_id: record for record in load_external_design_sources()}

    assert records["motionsites-ai"].decision == "moodboard-only"
    assert records["motionsites-ai"].adopted_concepts == ()
    assert records["react-bits"].decision == "reference-limited"
    assert "Commons Clause" in records["react-bits"].license
    assert records["codrops-rotating-scroll"].runtime_import is False


def test_manifest_rejects_an_unreviewed_runtime_import(tmp_path) -> None:
    payload = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["sources"][0]["runtimeImport"] = True
    candidate = tmp_path / "external-design-sources.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExternalDesignSourceContractError, match="Unreviewed executable"):
        load_external_design_sources(candidate)


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_manifest_requires_runtime_import_to_be_a_json_boolean(tmp_path, value) -> None:
    payload = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    payload["sources"][0]["runtimeImport"] = value
    candidate = tmp_path / "external-design-sources.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExternalDesignSourceContractError, match="JSON Boolean"):
        load_external_design_sources(candidate)


def test_runtime_import_is_bound_to_local_artifact_and_licence_hashes(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    manifest = root / "design_system" / "external_design_sources.v1.json"
    runtime_dir = root / "nicegui_app" / "assets" / "vendor"
    manifest.parent.mkdir(parents=True)
    runtime_dir.mkdir(parents=True)
    shutil.copy2(SOURCE_MANIFEST_PATH, manifest)
    source_root = SOURCE_MANIFEST_PATH.parents[1]
    for name in ("gsap-3.13.0.min.js", "gsap-package.json"):
        shutil.copy2(source_root / "nicegui_app" / "assets" / "vendor" / name, runtime_dir / name)

    assert next(record for record in load_external_design_sources(manifest) if record.runtime_import)
    (runtime_dir / "gsap-3.13.0.min.js").write_text("tampered", encoding="utf-8")
    with pytest.raises(ExternalDesignSourceContractError, match="runtime artifact digest mismatch"):
        load_external_design_sources(manifest)
