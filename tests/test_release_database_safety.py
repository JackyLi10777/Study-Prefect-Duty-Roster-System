from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from alembic import command
import pytest

from nicegui_app.persistence.database import (
    _alembic_config,
    create_session_factory,
    current_migration_heads,
)
from scripts import release_database_safety


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "release_database_safety.py"


def _run_helper(
    *arguments: object,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.update(environment_overrides or {})
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


def _single_migration_head() -> str:
    heads = sorted(str(head) for head in current_migration_heads())
    assert len(heads) == 1
    return heads[0]


def test_head_is_loaded_from_the_requested_release_root() -> None:
    expected_revision = _single_migration_head()
    result = _run_helper("head", "--release-root", PROJECT_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload == {
        "migrationHeads": [expected_revision],
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
    expected_revision = _single_migration_head()

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
    connection = sqlite3.connect(
        f"file:{snapshot_path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchall() == [
            (expected_revision,)
        ]
    finally:
        connection.close()


def test_candidate_readiness_proves_live_schema_upgrade_without_mutating_source(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    sessions = create_session_factory(database_path)
    engine = sessions.kw.get("bind")
    assert engine is not None
    engine.dispose()
    command.downgrade(_alembic_config(database_path), "0012")
    source_sha256 = _sha256(database_path)
    source_mtime_ns = database_path.stat().st_mtime_ns
    report_path = tmp_path / "reports" / "candidate-readiness.json"
    workspace_parent = tmp_path / "candidate-workspaces"
    workspace_parent.mkdir()

    result = _run_helper(
        "candidate-readiness",
        "--release-root",
        PROJECT_ROOT,
        "--database-path",
        database_path,
        "--report-path",
        report_path,
        "--expected-source-revision",
        "0012",
        "--expected-candidate-revision",
        "0013",
        "--workspace-parent",
        workspace_parent,
        environment_overrides={
            "SING_YIN_APP_MODE": "official",
            "SING_YIN_DEPLOYMENT_MODE": "local",
            "SING_YIN_HOST": "127.0.0.1",
            "SING_YIN_PORT": "8080",
            "SING_YIN_REMOTE_ACCESS_ENABLED": "0",
            "SING_YIN_STORAGE_SECRET": "candidate-readiness-test-secret-0123456789abcdef",
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["status"] == "pass"
    assert payload["sourceSchemaRevision"] == "0012"
    assert payload["candidateSchemaRevision"] == "0013"
    assert payload["onlineSnapshot"] is True
    assert payload["migrationProved"] is True
    assert payload["strictReadiness"] is True
    assert payload["verifiedBackup"] is True
    assert payload["isolatedRestore"] is True
    assert payload["fairnessBalanced"] is True
    assert payload["rowCountsMatched"] is True
    assert payload["restoreAuditAppended"] is True
    assert int(payload["readinessCheckCount"]) > 0
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert _sha256(database_path) == source_sha256
    assert database_path.stat().st_mtime_ns == source_mtime_ns
    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchall() == [
            ("0012",)
        ]
        assert "roster_day_closures" not in {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert list(workspace_parent.iterdir()) == []


def test_candidate_readiness_rejects_wrong_source_revision_before_workspace_use(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "runtime" / "roster.sqlite3"
    database_path.parent.mkdir()
    sessions = create_session_factory(database_path)
    engine = sessions.kw.get("bind")
    assert engine is not None
    engine.dispose()
    workspace_parent = tmp_path / "candidate-workspaces"
    workspace_parent.mkdir()

    result = _run_helper(
        "candidate-readiness",
        "--release-root",
        PROJECT_ROOT,
        "--database-path",
        database_path,
        "--report-path",
        tmp_path / "reports" / "candidate-readiness.json",
        "--expected-source-revision",
        "0012",
        "--expected-candidate-revision",
        "0013",
        "--workspace-parent",
        workspace_parent,
    )

    assert result.returncode == 1
    assert "schema revision" in result.stderr.lower()
    assert list(workspace_parent.iterdir()) == []


def test_candidate_readiness_preserves_subprocess_and_cleanup_failure_causes() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    candidate_start = source.index("def _candidate_readiness(")
    candidate_end = source.index("\ndef _validated_restore_source(", candidate_start)
    candidate = source[candidate_start:candidate_end]

    returncode_check = candidate.index("if readiness.returncode != 0:")
    stdout_parse = candidate.index("readiness_payload = _read_json_stdout")
    assert returncode_check < stdout_parse
    assert "exit code {readiness.returncode}" in candidate
    assert "readiness.stderr" in candidate
    assert "active_error = sys.exc_info()[1]" in candidate
    assert "if active_error is None:" in candidate
    assert "file=sys.stderr" in candidate


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
        "databaseQuarantineRemoved": True,
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
    connection = sqlite3.connect(
        f"file:{database_path.resolve().as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0012",
        )
        assert connection.execute("SELECT value FROM payload").fetchone() == (
            "pre-switch",
        )
    finally:
        connection.close()


def test_restore_reports_success_when_verified_database_quarantine_cleanup_is_locked(
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
    sidecar_paths = [Path(f"{database_path}{suffix}") for suffix in ("-wal", "-shm")]
    for sidecar in sidecar_paths:
        sidecar.write_bytes(b"old-sidecar")

    original_unlink = Path.unlink

    def reject_database_quarantine_unlink(
        path: Path,
        missing_ok: bool = False,
    ) -> None:
        if (
            path.parent == database_path.parent
            and path.name.startswith(f".{database_path.name}.release-rollback-")
            and path.name.endswith(".quarantine")
        ):
            raise PermissionError("Injected database quarantine lock.")
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", reject_database_quarantine_unlink)
    arguments = argparse.Namespace(
        database_path=database_path,
        snapshot_path=snapshot_path,
        manifest_path=manifest_path,
        expected_sha256=snapshot_sha256,
        expected_revision="0012",
    )

    payload = release_database_safety._restore(arguments)

    assert payload["status"] == "pass"
    assert payload["restored"] is True
    assert payload["databaseQuarantineRemoved"] is False
    assert payload["sidecarsRemoved"] == len(sidecar_paths)
    assert _sha256(database_path) == snapshot_sha256
    assert all(not sidecar.exists() for sidecar in sidecar_paths)
    quarantines = list(database_path.parent.glob("*.release-rollback-*.quarantine"))
    assert len(quarantines) == 1
    assert _sha256(quarantines[0]) != snapshot_sha256


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
    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (
            "0013",
        )
        assert connection.execute("SELECT value FROM payload").fetchone() == (
            "migrated",
        )
    finally:
        connection.close()
    assert not list(database_path.parent.glob("*.release-rollback-*"))
