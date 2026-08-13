"""Validate the non-executable evidence ledger for external design references."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
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
    runtime_artifact_path: str | None = None
    license_evidence_path: str | None = None


def _verified_file_digest(
    *,
    manifest_path: Path,
    relative_path: object,
    expected_digest: object,
    evidence_name: str,
) -> str:
    """Verify one repository-relative runtime or licence artifact."""

    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ExternalDesignSourceContractError(f"GSAP {evidence_name} path is required")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ExternalDesignSourceContractError(f"GSAP {evidence_name} SHA-256 is required")
    try:
        int(expected_digest, 16)
    except ValueError as exc:
        raise ExternalDesignSourceContractError(
            f"GSAP {evidence_name} SHA-256 is malformed"
        ) from exc

    repository_root = manifest_path.resolve().parent.parent
    candidate = (repository_root / relative_path).resolve()
    try:
        candidate.relative_to(repository_root)
    except ValueError as exc:
        raise ExternalDesignSourceContractError(
            f"GSAP {evidence_name} must remain inside the repository"
        ) from exc
    if not candidate.is_file():
        raise ExternalDesignSourceContractError(f"GSAP {evidence_name} file is missing")
    actual_digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if actual_digest != expected_digest.lower():
        raise ExternalDesignSourceContractError(f"GSAP {evidence_name} digest mismatch")
    return relative_path


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
        if "runtimeImport" in raw and not isinstance(raw["runtimeImport"], bool):
            raise ExternalDesignSourceContractError(
                f"Design source {raw.get('id', '<unknown>')} runtimeImport must be a JSON Boolean"
            )
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
        runtime_import = raw["runtimeImport"]
        if runtime_import and source_id != _ALLOWED_RUNTIME_SOURCE:
            raise ExternalDesignSourceContractError(
                f"Unreviewed executable design source is forbidden: {source_id}"
            )
        runtime_artifact_path: str | None = None
        license_evidence_path: str | None = None
        if runtime_import:
            runtime_artifact_path = _verified_file_digest(
                manifest_path=path,
                relative_path=raw.get("runtimeArtifactPath"),
                expected_digest=raw.get("sourceArchiveSha256"),
                evidence_name="runtime artifact",
            )
            license_evidence_path = _verified_file_digest(
                manifest_path=path,
                relative_path=raw.get("licenseEvidencePath"),
                expected_digest=raw.get("licenseSha256"),
                evidence_name="licence evidence",
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
                runtime_artifact_path=runtime_artifact_path,
                license_evidence_path=license_evidence_path,
            )
        )
    if not records:
        raise ExternalDesignSourceContractError("Design-source ledger must not be empty")
    return tuple(records)
