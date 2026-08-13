"""Validate the non-executable evidence ledger for external design references."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Literal


Decision = Literal[
    "adopt-guidance",
    "adapt-behaviour",
    "reference-limited",
    "moodboard-only",
    "existing-runtime",
]

SOURCE_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "design_system"
    / "external_design_sources.v1.json"
)
_ALLOWED_RUNTIME_SOURCE = "gsap"


class ExternalDesignSourceContractError(RuntimeError):
    """Raised when the evidence ledger could admit unreviewed executable code."""


@dataclass(frozen=True, slots=True)
class ExternalDesignSourceRecord:
    """One reviewed design source and the narrow decision made about it."""

    source_id: str
    source_url: str
    revision: str
    author: str
    license: str
    license_sha256: str | None
    source_archive_sha256: str | None
    asset_rights: str
    decision: Decision
    adopted_concepts: tuple[str, ...]
    runtime_import: bool
    removal: str


def load_external_design_sources(
    path: Path = SOURCE_MANIFEST_PATH,
) -> tuple[ExternalDesignSourceRecord, ...]:
    """Load and fail closed on incomplete, duplicated, or executable references."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contractVersion") != "1.0.0":
        raise ExternalDesignSourceContractError("Unsupported design-source contract version")
    policy = payload.get("policy", {})
    if policy.get("runtimeImportDefault") != "deny":
        raise ExternalDesignSourceContractError("External runtime imports must remain deny-by-default")
    if policy.get("formalDataAllowed") is not False:
        raise ExternalDesignSourceContractError("Reference environments must not receive formal data")
    if policy.get("externalOriginsAllowed") is not False:
        raise ExternalDesignSourceContractError("Reference environments must not add product origins")

    records: list[ExternalDesignSourceRecord] = []
    seen_ids: set[str] = set()
    for raw in payload.get("sources", []):
        required = (
            "id",
            "sourceUrl",
            "revision",
            "author",
            "license",
            "assetRights",
            "decision",
            "runtimeImport",
            "removal",
        )
        missing = [key for key in required if not raw.get(key) and raw.get(key) is not False]
        if missing:
            raise ExternalDesignSourceContractError(
                f"Design source {raw.get('id', '<unknown>')} is missing: {', '.join(missing)}"
            )
        source_id = str(raw["id"])
        if source_id in seen_ids:
            raise ExternalDesignSourceContractError(f"Duplicate design source: {source_id}")
        seen_ids.add(source_id)
        runtime_import = bool(raw["runtimeImport"])
        if runtime_import and source_id != _ALLOWED_RUNTIME_SOURCE:
            raise ExternalDesignSourceContractError(
                f"Unreviewed executable design source is forbidden: {source_id}"
            )
        records.append(
            ExternalDesignSourceRecord(
                source_id=source_id,
                source_url=str(raw["sourceUrl"]),
                revision=str(raw["revision"]),
                author=str(raw["author"]),
                license=str(raw["license"]),
                license_sha256=raw.get("licenseSha256"),
                source_archive_sha256=raw.get("sourceArchiveSha256"),
                asset_rights=str(raw["assetRights"]),
                decision=raw["decision"],
                adopted_concepts=tuple(str(item) for item in raw.get("adoptedConcepts", [])),
                runtime_import=runtime_import,
                removal=str(raw["removal"]),
            )
        )
    if not records:
        raise ExternalDesignSourceContractError("Design-source ledger must not be empty")
    return tuple(records)
