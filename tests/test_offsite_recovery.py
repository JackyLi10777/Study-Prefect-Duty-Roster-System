from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from nicegui_app.config import PREFECT_SEED_PATH
from nicegui_app.services.offsite_recovery import (
    OffsiteRecoveryError,
    OffsiteReleaseIdentity,
    OffsiteTargetEvidence,
    drill_offsite_recovery,
    export_offsite_recovery,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


WEEK_START = datetime(2026, 9, 7, tzinfo=timezone.utc).date()


def _official_fixture(root: Path) -> RosterWorkflow:
    workflow = RosterWorkflow(
        database_path=root / "runtime" / "sing-yin-roster.sqlite3",
        backup_dir=root / "backups",
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    workflow.generate_and_save_draft(WEEK_START)
    workflow.create_verified_backup()
    return workflow


def _target() -> OffsiteTargetEvidence:
    return OffsiteTargetEvidence(
        kind="bitlocker_external",
        evidence_sha256="a" * 64,
        encryption_method="XtsAes256",
    )


def _release() -> OffsiteReleaseIdentity:
    return OffsiteReleaseIdentity(
        release_ref="v1.2.0-test",
        commit="b" * 40,
        source_tree="c" * 40,
    )


def test_exported_bundle_restores_after_the_original_host_data_is_gone(tmp_path: Path) -> None:
    original_host = tmp_path / "lost-host"
    workflow = _official_fixture(original_host)
    destination = tmp_path / "approved-external-volume"
    destination.mkdir()

    exported = export_offsite_recovery(
        workflow,
        destination,
        target=_target(),
        release=_release(),
    )
    receipt_path = exported.bundle_dir / "OFFSITE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    serialized_receipt = json.dumps(receipt, ensure_ascii=False)

    assert exported.bundle_dir.parent == destination / "SingYinRosterRecovery"
    assert exported.bundle_dir.name.startswith("SYSS_Offsite_")
    assert receipt["schemaVersion"] == 1
    assert receipt["target"] == {
        "encryptionMethod": "XtsAes256",
        "evidenceSha256": "a" * 64,
        "kind": "bitlocker_external",
    }
    assert receipt["release"]["releaseRef"] == "v1.2.0-test"
    assert receipt["sourceSnapshot"]["schemaRevision"] == "0015"
    assert receipt["rpoSecondsAtExport"] >= 0
    assert str(original_host) not in serialized_receipt
    assert str(destination) not in serialized_receipt

    # The drill must use the copied artifact, not a path or database retained
    # from the original host.
    assert workflow.sessions is not None
    workflow.sessions.kw["bind"].dispose()
    workflow.sessions = None
    shutil.rmtree(original_host)
    drilled = drill_offsite_recovery(exported.bundle_dir)

    assert drilled.status == "pass"
    assert drilled.bundle_name == exported.bundle_dir.name
    assert drilled.row_counts_matched is True
    assert drilled.fairness_balanced is True
    assert drilled.restore_audit_appended is True
    assert drilled.rto_seconds >= 0
    assert drilled.snapshot_age_seconds >= receipt["rpoSecondsAtExport"]


def test_drill_rejects_a_package_changed_after_export(tmp_path: Path) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()
    exported = export_offsite_recovery(workflow, destination, target=_target(), release=_release())
    package_path = next(exported.bundle_dir.glob("*.zip"))
    changed = bytearray(package_path.read_bytes())
    changed[len(changed) // 2] ^= 0x01
    package_path.write_bytes(changed)

    with pytest.raises(OffsiteRecoveryError, match="package digest"):
        drill_offsite_recovery(exported.bundle_dir)


def test_drill_rejects_unexpected_archive_members_even_with_a_recomputed_receipt(
    tmp_path: Path,
) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()
    exported = export_offsite_recovery(workflow, destination, target=_target(), release=_release())
    package_path = next(exported.bundle_dir.glob("*.zip"))
    with ZipFile(package_path, mode="a", compression=ZIP_DEFLATED) as archive:
        archive.writestr("../unexpected.txt", "must be rejected")

    receipt_path = exported.bundle_dir / "OFFSITE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["handoverPackage"]["sha256"] = hashlib.sha256(package_path.read_bytes()).hexdigest()
    receipt["handoverPackage"]["bytes"] = package_path.stat().st_size
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    with pytest.raises(OffsiteRecoveryError, match="unexpected members"):
        drill_offsite_recovery(exported.bundle_dir)


@pytest.mark.parametrize(
    ("kind", "digest", "method"),
    [
        ("internal_disk", "a" * 64, "XtsAes256"),
        ("bitlocker_external", "not-a-digest", "XtsAes256"),
        ("bitlocker_external", "a" * 64, ""),
        ("bitlocker_external", "a" * 64, "None"),
    ],
)
def test_export_rejects_unapproved_or_unverifiable_target_evidence(
    kind: str,
    digest: str,
    method: str,
    tmp_path: Path,
) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()

    with pytest.raises(OffsiteRecoveryError, match="target evidence"):
        export_offsite_recovery(
            workflow,
            destination,
            target=OffsiteTargetEvidence(
                kind=kind,
                evidence_sha256=digest,
                encryption_method=method,
            ),
            release=_release(),
        )


def test_drill_recomputes_rpo_instead_of_trusting_the_receipt(tmp_path: Path) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()
    exported = export_offsite_recovery(workflow, destination, target=_target(), release=_release())
    receipt_path = exported.bundle_dir / "OFFSITE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["rpoSecondsAtExport"] = 99_999_999
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    with pytest.raises(OffsiteRecoveryError, match="RPO evidence"):
        drill_offsite_recovery(exported.bundle_dir)


@pytest.mark.parametrize("invalid_rpo", [float("nan"), float("inf"), -1])
def test_drill_rejects_non_finite_or_negative_rpo_evidence(
    invalid_rpo: float,
    tmp_path: Path,
) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()
    exported = export_offsite_recovery(workflow, destination, target=_target(), release=_release())
    receipt_path = exported.bundle_dir / "OFFSITE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["rpoSecondsAtExport"] = invalid_rpo
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    with pytest.raises(OffsiteRecoveryError, match="RPO evidence"):
        drill_offsite_recovery(exported.bundle_dir)


def test_export_rejects_an_unsafe_release_reference(tmp_path: Path) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()

    with pytest.raises(OffsiteRecoveryError, match="release identity"):
        export_offsite_recovery(
            workflow,
            destination,
            target=_target(),
            release=OffsiteReleaseIdentity(
                release_ref="v1.2.0-test with spaces",
                commit="b" * 40,
                source_tree="c" * 40,
            ),
        )


def test_export_rejects_a_missing_release_identity(tmp_path: Path) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()

    with pytest.raises(OffsiteRecoveryError, match="release identity is required"):
        export_offsite_recovery(
            workflow,
            destination,
            target=_target(),
            release=None,  # type: ignore[arg-type]
        )


def test_drill_rejects_a_receipt_without_release_identity(tmp_path: Path) -> None:
    workflow = _official_fixture(tmp_path / "host")
    destination = tmp_path / "external"
    destination.mkdir()
    exported = export_offsite_recovery(
        workflow,
        destination,
        target=_target(),
        release=_release(),
    )
    receipt_path = exported.bundle_dir / "OFFSITE_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["release"] = None
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    with pytest.raises(OffsiteRecoveryError, match="release receipt is invalid"):
        drill_offsite_recovery(exported.bundle_dir)
