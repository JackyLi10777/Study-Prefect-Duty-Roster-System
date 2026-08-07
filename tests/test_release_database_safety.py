from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from nicegui_app.persistence.database import (
    create_session_factory,
    current_migration_heads,
)
from scripts import release_database_safety


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "release_database_safety.py"


def _run_helper(*arguments: object) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(SCRIPT),
            *(str(argument) for argument in arguments),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert lines, result.stdout + result.stderr
    return json.loads(lines[-1])


def _write_database(path: Path, *, revision: str, value: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
        connection.execute("CREATE TABLE payload (value TEXT NOT NULL)")
        connection.execute("INSERT INTO payload VALUES (?)", (value,))
        connection.commit()
    finally:
        connection.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_head_is_loaded_from_the_requested_release_root() -> None:
    result = _run_helper("head", "--release-root", PROJECT_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload == {
        "migrationHeads": sorted(current_migration_heads()),
        "status": "pass",
    }


def test_prepare_uses_release_code_and_proves_an_exact_head_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    sessions = create_session_factory(database_path)
    engine = sessions.kw.get("bind")
    assert engine is not None
    engine.dispose()
    backup_dir = tmp_path / "backups"
    report_path = tmp_path / "reports" / "rollback-snapshot.json"
    expected_revision = next(iter(current_migration_heads()))

    result = _run_helper(
        "prepare",
        "--release-root",
        PROJECT_ROOT,
        "--database-path",
        database_path,
        "--backup-dir",
        backup_dir,
        "--report-path",
        report_path,
        "--expected-revision",
        expected_revision,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["status"] == "pass"
    assert payload["schemaRevision"] == expected_revision
    assert payload["isolatedRestore"] is True
    assert payload["fairnessBalanced"] is True
    assert payload["rowCountsMatched"] is True
    assert payload["restoreAuditAppended"] is True
    assert payload["integrity"] == "ok"
    snapshot_path = backup_dir / str(payload["snapshotFile"])
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    assert snapshot_path.is_file()
    assert manifest_path.is_file()
    assert _sha256(snapshot_path) == payload["sha256"]
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest["sha256"] == payload["sha256"]
    assert manifest["schemaRevision"] == expected_revision
    assert hashlib.sha256(manifest_bytes).hexdigest() == payload["manifestSha256"]
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    with sqlite3.connect(
        f"file:{snapshot_path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    ) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (expected_revision,)
        ]


def test_restore_atomically_installs_exact_snapshot_and_removes_old_sidecars(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "backups" / "pre-switch.sqlite3"
    snapshot_path.parent.mkdir()
    _write_database(snapshot_path, revision="0012", value="pre-switch")
    snapshot_sha256 = _sha256(snapshot_path)
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps({"schemaRevision": "0012", "sha256": snapshot_sha256}),
        encoding="utf-8",
    )
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    _write_database(database_path, revision="0013", value="migrated")
    for suffix in ("-wal", "-shm", "-journal"):
        Path(f"{database_path}{suffix}").write_bytes(f"old{suffix}".encode())

    result = _run_helper(
        "restore",
        "--database-path",
        database_path,
        "--snapshot-path",
        snapshot_path,
        "--manifest-path",
        manifest_path,
        "--expected-sha256",
        snapshot_sha256,
        "--expected-revision",
        "0012",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload == {
        "atomicReplace": True,
        "integrity": "ok",
        "restored": True,
        "schemaRevision": "0012",
        "sha256": snapshot_sha256,
        "sidecarsRemoved": 3,
        "status": "pass",
    }
    assert _sha256(database_path) == snapshot_sha256
    for suffix in ("-wal", "-shm", "-journal"):
        assert not Path(f"{database_path}{suffix}").exists()
    with sqlite3.connect(
        f"file:{database_path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    ) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0012",
        )
        assert connection.execute("SELECT value FROM payload").fetchone() == (
            "pre-switch",
        )


def test_restore_fails_before_target_mutation_when_manifest_is_not_bound(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "backups" / "pre-switch.sqlite3"
    snapshot_path.parent.mkdir()
    _write_database(snapshot_path, revision="0012", value="pre-switch")
    snapshot_sha256 = _sha256(snapshot_path)
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps({"schemaRevision": "0012", "sha256": "0" * 64}),
        encoding="utf-8",
    )
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    _write_database(database_path, revision="0013", value="migrated")
    database_sha256 = _sha256(database_path)
    sidecar_path = Path(f"{database_path}-wal")
    sidecar_path.write_bytes(b"must-remain-before-install")

    result = _run_helper(
        "restore",
        "--database-path",
        database_path,
        "--snapshot-path",
        snapshot_path,
        "--manifest-path",
        manifest_path,
        "--expected-sha256",
        snapshot_sha256,
        "--expected-revision",
        "0012",
    )

    assert result.returncode == 1
    assert _sha256(database_path) == database_sha256
    assert sidecar_path.read_bytes() == b"must-remain-before-install"
    assert "manifest" in result.stderr.lower()


def test_restore_fails_before_target_mutation_for_the_wrong_schema(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "backups" / "pre-switch.sqlite3"
    snapshot_path.parent.mkdir()
    _write_database(snapshot_path, revision="0013", value="wrong-head")
    snapshot_sha256 = _sha256(snapshot_path)
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps({"schemaRevision": "0012", "sha256": snapshot_sha256}),
        encoding="utf-8",
    )
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    _write_database(database_path, revision="0013", value="migrated")
    database_sha256 = _sha256(database_path)

    result = _run_helper(
        "restore",
        "--database-path",
        database_path,
        "--snapshot-path",
        snapshot_path,
        "--manifest-path",
        manifest_path,
        "--expected-sha256",
        snapshot_sha256,
        "--expected-revision",
        "0012",
    )

    assert result.returncode == 1
    assert _sha256(database_path) == database_sha256
    assert "schema revision" in result.stderr.lower()


def test_restore_reinstalls_original_database_when_post_install_proof_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_path = tmp_path / "backups" / "pre-switch.sqlite3"
    snapshot_path.parent.mkdir()
    _write_database(snapshot_path, revision="0012", value="pre-switch")
    snapshot_sha256 = _sha256(snapshot_path)
    manifest_path = snapshot_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps({"schemaRevision": "0012", "sha256": snapshot_sha256}),
        encoding="utf-8",
    )
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    _write_database(database_path, revision="0013", value="migrated")
    database_sha256 = _sha256(database_path)
    sidecar_payloads = {
        suffix: f"preserve{suffix}".encode()
        for suffix in ("-wal", "-shm", "-journal")
    }
    for suffix, payload in sidecar_payloads.items():
        Path(f"{database_path}{suffix}").write_bytes(payload)

    original_validator = release_database_safety._require_database_revision

    def fail_installed_proof(
        path: Path,
        *,
        expected_revision: str,
        immutable: bool,
        label: str,
    ) -> dict[str, object]:
        if label == "Installed rollback database":
            raise release_database_safety.ReleaseDatabaseSafetyError(
                "Injected post-install proof failure."
            )
        return original_validator(
            path,
            expected_revision=expected_revision,
            immutable=immutable,
            label=label,
        )

    monkeypatch.setattr(
        release_database_safety,
        "_require_database_revision",
        fail_installed_proof,
    )
    arguments = argparse.Namespace(
        database_path=database_path,
        snapshot_path=snapshot_path,
        manifest_path=manifest_path,
        expected_sha256=snapshot_sha256,
        expected_revision="0012",
    )

    with pytest.raises(
        release_database_safety.ReleaseDatabaseSafetyError,
        match="Injected post-install proof failure",
    ):
        release_database_safety._restore(arguments)

    assert _sha256(database_path) == database_sha256
    for suffix, payload in sidecar_payloads.items():
        assert Path(f"{database_path}{suffix}").read_bytes() == payload
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0013",
        )
        assert connection.execute("SELECT value FROM payload").fetchone() == (
            "migrated",
        )
    assert not list(database_path.parent.glob("*.release-rollback-*"))
