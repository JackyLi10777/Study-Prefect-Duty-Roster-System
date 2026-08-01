"""Verified off-site recovery export and replacement-location drill.

This module deliberately does not invent application-level encryption.  Its
caller must prove that the destination is an approved, externally removable
BitLocker volume before crossing this seam.  The module then owns the exact
copy, receipt, tamper checks, and isolated restore evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import tempfile
from time import perf_counter
from typing import Protocol
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from nicegui_app.services.roster_workflow import RosterWorkflow


_RECEIPT_NAME = "OFFSITE_RECEIPT.json"
_RECOVERY_ROOT_NAME = "SingYinRosterRecovery"
_TARGET_KIND = "bitlocker_external"
_BITLOCKER_METHODS = frozenset(
    {"Aes128", "Aes256", "XtsAes128", "XtsAes256", "HardwareEncryption"}
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_SAFE_ARTIFACT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,179}$")
_MAX_PACKAGE_BYTES = 512 * 1024 * 1024
_MAX_METADATA_BYTES = 256 * 1024
_MAX_TEXT_LENGTH = 128
_COUNTED_TABLES = (
    "prefects",
    "prefect_availability",
    "roster_weeks",
    "roster_assignments",
    "fairness_ledger",
    "leave_adjustments",
    "leave_declarations",
)
_TABLE_COUNT_SQL = {
    "prefects": 'SELECT COUNT(*) FROM "prefects"',
    "prefect_availability": 'SELECT COUNT(*) FROM "prefect_availability"',
    "roster_weeks": 'SELECT COUNT(*) FROM "roster_weeks"',
    "roster_assignments": 'SELECT COUNT(*) FROM "roster_assignments"',
    "fairness_ledger": 'SELECT COUNT(*) FROM "fairness_ledger"',
    "leave_adjustments": 'SELECT COUNT(*) FROM "leave_adjustments"',
    "leave_declarations": 'SELECT COUNT(*) FROM "leave_declarations"',
    "audit_events": 'SELECT COUNT(*) FROM "audit_events"',
}


class OffsiteRecoveryError(RuntimeError):
    """Raised when off-site recovery evidence cannot be trusted."""


class _RecoveryWorkflow(Protocol):
    def build_verified_handover_package(self): ...

    def verify_backup(self, backup_path: Path) -> dict[str, object]: ...


@dataclass(frozen=True)
class OffsiteTargetEvidence:
    """Non-sensitive proof supplied by the Windows volume adapter."""

    kind: str
    evidence_sha256: str
    encryption_method: str


@dataclass(frozen=True)
class OffsiteReleaseIdentity:
    """The immutable application source needed to interpret the snapshot."""

    release_ref: str
    commit: str
    source_tree: str


@dataclass(frozen=True)
class OffsiteExportResult:
    bundle_dir: Path
    bundle_name: str
    package_name: str
    package_sha256: str
    snapshot_sha256: str
    rpo_seconds_at_export: float

    def to_report(self) -> dict[str, object]:
        return {
            "bundleName": self.bundle_name,
            "packageName": self.package_name,
            "packageSha256": self.package_sha256,
            "snapshotSha256": self.snapshot_sha256,
            "rpoSecondsAtExport": self.rpo_seconds_at_export,
        }


@dataclass(frozen=True)
class OffsiteDrillResult:
    status: str
    bundle_name: str
    package_sha256: str
    snapshot_sha256: str
    rpo_seconds_at_export: float
    snapshot_age_seconds: float
    rto_seconds: float
    row_counts_matched: bool
    fairness_balanced: bool
    restore_audit_appended: bool

    def to_report(self) -> dict[str, object]:
        return {
            "status": self.status,
            "bundleName": self.bundle_name,
            "packageSha256": self.package_sha256,
            "snapshotSha256": self.snapshot_sha256,
            "rpoSecondsAtExport": self.rpo_seconds_at_export,
            "snapshotAgeSeconds": self.snapshot_age_seconds,
            "rtoSeconds": self.rto_seconds,
            "rowCountsMatched": self.row_counts_matched,
            "fairnessBalanced": self.fairness_balanced,
            "restoreAuditAppended": self.restore_audit_appended,
        }


@dataclass(frozen=True)
class _InspectedBundle:
    receipt: dict[str, object]
    package_sha256: str
    snapshot_name: str
    snapshot_content: bytes
    manifest_name: str
    manifest_content: bytes


def export_offsite_recovery(
    workflow: _RecoveryWorkflow,
    destination_root: Path,
    *,
    target: OffsiteTargetEvidence,
    release: OffsiteReleaseIdentity | None = None,
    now: datetime | None = None,
) -> OffsiteExportResult:
    """Atomically export the latest verified handover package to an approved volume."""

    _validate_target(target)
    if release is not None:
        _validate_release(release)
    if _is_link_like(destination_root):
        raise OffsiteRecoveryError("The approved destination root must not be a reparse point.")
    destination = destination_root.resolve(strict=True)
    if not destination.is_dir():
        raise OffsiteRecoveryError("The approved destination root is not a directory.")

    package = workflow.build_verified_handover_package()
    source_path = Path(package.source_backup_path)
    source_verification = workflow.verify_backup(source_path)
    if not source_verification.get("valid"):
        raise OffsiteRecoveryError("The selected source snapshot is no longer verified.")
    source_manifest_path = source_path.with_suffix(".manifest.json")
    source_manifest = _read_json_object(source_manifest_path, "source backup manifest")
    source_created_at = _parse_utc_timestamp(
        source_manifest.get("createdAt"),
        "source snapshot creation",
        allow_legacy_naive_utc=True,
    )

    exported_at = _as_utc(now or datetime.now(timezone.utc))
    rpo_seconds = max(0.0, (exported_at - source_created_at).total_seconds())
    package_content = bytes(package.content)
    if not package_content or len(package_content) > _MAX_PACKAGE_BYTES:
        raise OffsiteRecoveryError("The verified handover package has an unsafe size.")
    package_sha256 = hashlib.sha256(package_content).hexdigest()
    snapshot_sha256 = _required_sha256(source_verification.get("sha256"), "snapshot")
    manifest_sha256 = _required_sha256(source_verification.get("manifestSha256"), "manifest")
    schema_revision = _bounded_text(source_verification.get("schemaRevision"), "schema revision")
    package_name = _safe_filename(str(package.filename), suffix=".zip")
    snapshot_name = _safe_filename(source_path.name, suffix=".sqlite3")

    recovery_root = destination / _RECOVERY_ROOT_NAME
    recovery_root.mkdir(parents=True, exist_ok=True)
    if _is_link_like(recovery_root) or recovery_root.resolve(strict=True).parent != destination:
        raise OffsiteRecoveryError("The off-site recovery root must remain on the approved volume.")
    stamp = exported_at.strftime("%Y%m%dT%H%M%SZ")
    bundle_name = f"SYSS_Offsite_{stamp}_{snapshot_sha256[:12]}_{uuid4().hex[:8]}"
    final_dir = recovery_root / bundle_name
    partial_dir = recovery_root / f".{bundle_name}.partial"
    if final_dir.exists() or partial_dir.exists():
        raise OffsiteRecoveryError("The off-site bundle destination already exists.")

    receipt: dict[str, object] = {
        "schemaVersion": 1,
        "bundleId": bundle_name,
        "exportedAt": exported_at.isoformat(),
        "rpoSecondsAtExport": round(rpo_seconds, 3),
        "target": {
            "kind": target.kind,
            "evidenceSha256": target.evidence_sha256,
            "encryptionMethod": target.encryption_method,
        },
        "sourceSnapshot": {
            "filename": snapshot_name,
            "createdAt": source_created_at.isoformat(),
            "sha256": snapshot_sha256,
            "manifestSha256": manifest_sha256,
            "schemaRevision": schema_revision,
        },
        "handoverPackage": {
            "filename": package_name,
            "sha256": package_sha256,
            "bytes": len(package_content),
        },
        "release": _release_payload(release),
    }

    try:
        partial_dir.mkdir()
        _write_bytes_exclusive(partial_dir / package_name, package_content)
        _write_json_exclusive(partial_dir / _RECEIPT_NAME, receipt)
        inspected = _inspect_bundle(partial_dir, expected_bundle_id=bundle_name)
        if inspected.package_sha256 != package_sha256:
            raise OffsiteRecoveryError("The copied package digest changed during export.")
        partial_dir.replace(final_dir)
    except Exception:
        if partial_dir.exists():
            shutil.rmtree(partial_dir, ignore_errors=True)
        raise

    return OffsiteExportResult(
        bundle_dir=final_dir,
        bundle_name=bundle_name,
        package_name=package_name,
        package_sha256=package_sha256,
        snapshot_sha256=snapshot_sha256,
        rpo_seconds_at_export=round(rpo_seconds, 3),
    )


def drill_offsite_recovery(
    bundle_dir: Path,
    *,
    workspace_root: Path | None = None,
    now: datetime | None = None,
) -> OffsiteDrillResult:
    """Restore only from an exported bundle in an isolated replacement workspace."""

    started = perf_counter()
    if _is_link_like(bundle_dir):
        raise OffsiteRecoveryError("The off-site bundle must not be a reparse point.")
    inspected = _inspect_bundle(bundle_dir.resolve(strict=True))
    receipt = inspected.receipt
    source_receipt = _required_mapping(receipt.get("sourceSnapshot"), "sourceSnapshot")
    exported_rpo = _non_negative_number(receipt.get("rpoSecondsAtExport"), "rpoSecondsAtExport")
    source_created_at = _parse_utc_timestamp(source_receipt.get("createdAt"), "source snapshot creation")
    checked_at = _as_utc(now or datetime.now(timezone.utc))
    snapshot_age = max(0.0, (checked_at - source_created_at).total_seconds())

    parent = None
    if workspace_root is not None:
        parent = str(workspace_root.resolve(strict=True))
    with tempfile.TemporaryDirectory(prefix="sing-yin-offsite-drill-", dir=parent) as temporary:
        workspace = Path(temporary)
        backups = workspace / "backups"
        backups.mkdir()
        snapshot_path = backups / inspected.snapshot_name
        manifest_path = backups / inspected.manifest_name
        _write_bytes_exclusive(snapshot_path, inspected.snapshot_content)
        _write_bytes_exclusive(manifest_path, inspected.manifest_content)

        verifier = RosterWorkflow(
            database_path=workspace / "verification-placeholder.sqlite3",
            backup_dir=backups,
            seed_path=None,
        )
        verification = verifier.verify_backup(snapshot_path)
        if not verification.get("valid"):
            raise OffsiteRecoveryError("The off-site snapshot failed application verification.")
        if verification.get("sha256") != source_receipt.get("sha256"):
            raise OffsiteRecoveryError("The off-site snapshot digest does not match its receipt.")
        if verification.get("schemaRevision") != source_receipt.get("schemaRevision"):
            raise OffsiteRecoveryError("The off-site snapshot schema does not match its receipt.")

        source_counts = _operational_row_counts(snapshot_path)
        source_audits = _table_count(snapshot_path, "audit_events")
        restored_database = workspace / "restored.sqlite3"
        restored = RosterWorkflow(
            database_path=restored_database,
            backup_dir=backups,
            seed_path=None,
        )
        try:
            restored.bootstrap()
            restored.restore_backup(snapshot_path)
            fairness = restored.reconcile_fairness()
            restored_counts = _operational_row_counts(restored_database)
            restored_audits = _table_count(restored_database, "audit_events")
        finally:
            if restored.sessions is not None:
                restored.sessions.kw["bind"].dispose()
                restored.sessions = None

    row_counts_matched = source_counts == restored_counts
    fairness_balanced = bool(fairness.balanced)
    restore_audit_appended = restored_audits == source_audits + 1
    if not row_counts_matched:
        raise OffsiteRecoveryError("The isolated restore changed operational row counts.")
    if not fairness_balanced:
        raise OffsiteRecoveryError("The isolated restore failed fairness reconciliation.")
    if not restore_audit_appended:
        raise OffsiteRecoveryError("The isolated restore did not append one restore audit event.")

    return OffsiteDrillResult(
        status="pass",
        bundle_name=bundle_dir.name,
        package_sha256=inspected.package_sha256,
        snapshot_sha256=str(source_receipt["sha256"]),
        rpo_seconds_at_export=round(exported_rpo, 3),
        snapshot_age_seconds=round(snapshot_age, 3),
        rto_seconds=round(perf_counter() - started, 3),
        row_counts_matched=row_counts_matched,
        fairness_balanced=fairness_balanced,
        restore_audit_appended=restore_audit_appended,
    )


def _inspect_bundle(
    bundle_dir: Path,
    *,
    expected_bundle_id: str | None = None,
) -> _InspectedBundle:
    if not bundle_dir.is_dir():
        raise OffsiteRecoveryError("The off-site bundle directory is missing.")
    receipt_path = bundle_dir / _RECEIPT_NAME
    if _is_link_like(receipt_path):
        raise OffsiteRecoveryError("Off-site recovery artifacts must not be reparse points.")
    receipt = _read_json_object(receipt_path, "off-site receipt")
    expected_identity = expected_bundle_id or bundle_dir.name
    if receipt.get("schemaVersion") != 1 or receipt.get("bundleId") != expected_identity:
        raise OffsiteRecoveryError("The off-site receipt identity is invalid.")
    target = _required_mapping(receipt.get("target"), "target")
    _validate_target(
        OffsiteTargetEvidence(
            kind=str(target.get("kind", "")),
            evidence_sha256=str(target.get("evidenceSha256", "")),
            encryption_method=str(target.get("encryptionMethod", "")),
        )
    )
    release = receipt.get("release")
    if release is not None:
        release_mapping = _required_mapping(release, "release")
        _validate_release(
            OffsiteReleaseIdentity(
                release_ref=str(release_mapping.get("releaseRef", "")),
                commit=str(release_mapping.get("commit", "")),
                source_tree=str(release_mapping.get("sourceTree", "")),
            )
        )
    package_receipt = _required_mapping(receipt.get("handoverPackage"), "handoverPackage")
    source_receipt = _required_mapping(receipt.get("sourceSnapshot"), "sourceSnapshot")
    package_name = _safe_filename(str(package_receipt.get("filename", "")), suffix=".zip")
    snapshot_name = _safe_filename(str(source_receipt.get("filename", "")), suffix=".sqlite3")
    manifest_name = str(Path(snapshot_name).with_suffix(".manifest.json"))
    exported_at = _parse_utc_timestamp(receipt.get("exportedAt"), "off-site export")
    source_created_at = _parse_utc_timestamp(source_receipt.get("createdAt"), "source snapshot creation")
    recorded_rpo = _non_negative_number(receipt.get("rpoSecondsAtExport"), "RPO")
    calculated_rpo = max(0.0, (exported_at - source_created_at).total_seconds())
    if abs(recorded_rpo - calculated_rpo) > 1.0:
        raise OffsiteRecoveryError("The off-site RPO evidence does not match its timestamps.")
    _bounded_text(source_receipt.get("schemaRevision"), "schema revision")
    package_path = bundle_dir / package_name
    if _is_link_like(package_path):
        raise OffsiteRecoveryError("Off-site recovery artifacts must not be reparse points.")
    if not package_path.is_file():
        raise OffsiteRecoveryError("The off-site handover package is missing.")
    package_size = package_path.stat().st_size
    expected_size = package_receipt.get("bytes")
    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size <= 0
        or expected_size > _MAX_PACKAGE_BYTES
    ):
        raise OffsiteRecoveryError("The off-site package size receipt is invalid.")
    if package_size != expected_size:
        raise OffsiteRecoveryError("The off-site package size does not match its receipt.")
    package_sha256 = _sha256_file(package_path)
    expected_package_sha256 = _required_sha256(package_receipt.get("sha256"), "package")
    if package_sha256 != expected_package_sha256:
        raise OffsiteRecoveryError("The off-site package digest does not match its receipt.")

    try:
        with ZipFile(package_path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            expected_names = {snapshot_name, manifest_name, "README.txt"}
            if len(names) != len(set(names)) or set(names) != expected_names:
                raise OffsiteRecoveryError("The off-site package contains unexpected members.")
            if sum(info.file_size for info in infos) > _MAX_PACKAGE_BYTES:
                raise OffsiteRecoveryError("The off-site package expands beyond the safety limit.")
            info_by_name = {info.filename: info for info in infos}
            if (
                info_by_name[snapshot_name].file_size <= 0
                or info_by_name[manifest_name].file_size <= 0
                or info_by_name[manifest_name].file_size > _MAX_METADATA_BYTES
                or info_by_name["README.txt"].file_size <= 0
                or info_by_name["README.txt"].file_size > _MAX_METADATA_BYTES
            ):
                raise OffsiteRecoveryError("The off-site package member size is invalid.")
            for info in infos:
                _validate_archive_member(info.filename)
                if info.is_dir() or info.flag_bits & 0x1:
                    raise OffsiteRecoveryError("The off-site package member contract is invalid.")
                mode = info.external_attr >> 16
                if mode and stat.S_ISLNK(mode):
                    raise OffsiteRecoveryError("The off-site package must not contain symbolic links.")
            snapshot_content = archive.read(snapshot_name)
            manifest_content = archive.read(manifest_name)
    except (BadZipFile, KeyError, OSError) as error:
        raise OffsiteRecoveryError("The off-site handover package is unreadable.") from error

    expected_snapshot_sha256 = _required_sha256(source_receipt.get("sha256"), "snapshot")
    expected_manifest_sha256 = _required_sha256(source_receipt.get("manifestSha256"), "manifest")
    if hashlib.sha256(snapshot_content).hexdigest() != expected_snapshot_sha256:
        raise OffsiteRecoveryError("The off-site snapshot digest does not match its receipt.")
    if hashlib.sha256(manifest_content).hexdigest() != expected_manifest_sha256:
        raise OffsiteRecoveryError("The off-site manifest digest does not match its receipt.")
    try:
        manifest = json.loads(manifest_content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OffsiteRecoveryError("The off-site backup manifest is unreadable.") from error
    if not isinstance(manifest, Mapping) or manifest.get("sha256") != expected_snapshot_sha256:
        raise OffsiteRecoveryError("The off-site backup manifest does not identify the snapshot.")

    return _InspectedBundle(
        receipt=receipt,
        package_sha256=package_sha256,
        snapshot_name=snapshot_name,
        snapshot_content=snapshot_content,
        manifest_name=manifest_name,
        manifest_content=manifest_content,
    )


def _validate_target(target: OffsiteTargetEvidence) -> None:
    try:
        encryption_method = _bounded_text(target.encryption_method, "encryption method")
    except OffsiteRecoveryError as error:
        raise OffsiteRecoveryError("The off-site target evidence is invalid.") from error
    if (
        target.kind != _TARGET_KIND
        or _SHA256_RE.fullmatch(target.evidence_sha256) is None
        or encryption_method not in _BITLOCKER_METHODS
    ):
        raise OffsiteRecoveryError("The off-site target evidence is invalid.")


def _validate_release(release: OffsiteReleaseIdentity) -> None:
    if _RELEASE_REF_RE.fullmatch(release.release_ref) is None:
        raise OffsiteRecoveryError("The immutable release identity is invalid.")
    if _COMMIT_RE.fullmatch(release.commit) is None or _COMMIT_RE.fullmatch(release.source_tree) is None:
        raise OffsiteRecoveryError("The immutable release identity is invalid.")


def _release_payload(release: OffsiteReleaseIdentity | None) -> dict[str, str] | None:
    if release is None:
        return None
    return {
        "releaseRef": release.release_ref,
        "commit": release.commit,
        "sourceTree": release.source_tree,
    }


def _read_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        size = path.stat().st_size
        if size <= 0 or size > _MAX_METADATA_BYTES:
            raise OffsiteRecoveryError(f"The {label} has an unsafe size.")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OffsiteRecoveryError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OffsiteRecoveryError(f"The {label} is unreadable.") from error
    if not isinstance(payload, dict):
        raise OffsiteRecoveryError(f"The {label} must contain one JSON object.")
    return payload


def _required_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OffsiteRecoveryError(f"The off-site {label} receipt is invalid.")
    return value


def _required_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise OffsiteRecoveryError(f"The {label} SHA-256 evidence is invalid.")
    return value


def _safe_filename(value: str, *, suffix: str) -> str:
    candidate = Path(value)
    if (
        not value
        or candidate.name != value
        or candidate.suffix.lower() != suffix
        or _SAFE_ARTIFACT_RE.fullmatch(value) is None
        or any(ord(character) < 32 for character in value)
        or len(value) > 180
    ):
        raise OffsiteRecoveryError("The off-site artifact filename is unsafe.")
    return value


def _validate_archive_member(value: str) -> None:
    member = PurePosixPath(value)
    if member.is_absolute() or ".." in member.parts or len(member.parts) != 1 or "\\" in value:
        raise OffsiteRecoveryError("The off-site package contains an unsafe member path.")


def _bounded_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise OffsiteRecoveryError(f"The {label} is missing.")
    candidate = value.strip()
    if not candidate or len(candidate) > _MAX_TEXT_LENGTH or any(ord(character) < 32 for character in candidate):
        raise OffsiteRecoveryError(f"The {label} is invalid.")
    return candidate


def _parse_utc_timestamp(
    value: object,
    label: str,
    *,
    allow_legacy_naive_utc: bool = False,
) -> datetime:
    if not isinstance(value, str):
        raise OffsiteRecoveryError(f"The {label} timestamp is missing.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise OffsiteRecoveryError(f"The {label} timestamp is invalid.") from error
    if parsed.tzinfo is None:
        if not allow_legacy_naive_utc:
            raise OffsiteRecoveryError(f"The {label} timestamp must include a timezone.")
        # Existing backup manifests were intentionally persisted from the
        # application's naive-UTC database clock.  Preserve that one historical
        # contract while requiring every new off-site receipt to be timezone-aware.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise OffsiteRecoveryError("Recovery evidence timestamps must include a timezone.")
    return value.astimezone(timezone.utc)


def _non_negative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OffsiteRecoveryError(f"The {label} evidence is invalid.")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise OffsiteRecoveryError(f"The {label} evidence is invalid.")
    return result


def _write_bytes_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as destination:
        destination.write(content)
        destination.flush()
        os.fsync(destination.fileno())


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _write_json_exclusive(path: Path, payload: Mapping[str, object]) -> None:
    content = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_bytes_exclusive(path, content)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _operational_row_counts(path: Path) -> dict[str, int]:
    return {table: _table_count(path, table) for table in _COUNTED_TABLES}


def _table_count(path: Path, table: str) -> int:
    # A self-contained snapshot is verified separately with immutable=1.  The
    # freshly restored database is a live WAL database, so evidence reads must
    # remain read-only while still observing its committed WAL frames.
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        try:
            statement = _TABLE_COUNT_SQL[table]
        except KeyError as error:  # internal callers must use the closed evidence set
            raise OffsiteRecoveryError("The requested recovery evidence table is unsupported.") from error
        return int(connection.execute(statement).fetchone()[0])
    finally:
        connection.close()
