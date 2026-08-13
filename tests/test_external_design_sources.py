from __future__ import annotations

import json

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
