"""Build a non-secret GitHub archive from fictional data and release evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = PROJECT_ROOT / "archive"
PROTECTED_TABLES = (
    "roster_weeks",
    "roster_assignments",
    "fairness_ledger",
    "leave_adjustments",
    "leave_declarations",
)
_SECRET_PATTERN = re.compile(
    r"(?:gho_|github_pat_)[A-Za-z0-9_]+|"
    r"SING_YIN_(?:STORAGE_SECRET|YOUTUBE_API_KEY|CLOUDFLARE[^=]*)\s*=\s*\S+|"
    r"TUNNEL_TOKEN\s*=\s*\S+|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def public_fixture_counts(database_path: Path) -> dict[str, int]:
    """Return protected row counts, rejecting an incomplete or unreadable database."""
    if not database_path.is_file():
        raise RuntimeError("The runtime SQLite database does not exist.")
    connection = sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True, timeout=3)
    try:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError("The runtime SQLite database did not pass quick_check.")
        available = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        missing = [table for table in PROTECTED_TABLES if table not in available]
        if missing:
            raise RuntimeError("The runtime SQLite database is missing required roster tables.")
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in PROTECTED_TABLES
        }
    finally:
        connection.close()


def assert_public_fixture_database(database_path: Path) -> None:
    counts = public_fixture_counts(database_path)
    if any(counts.values()):
        raise RuntimeError(
            "Public archive refused: SQLite contains roster, assignment, fairness, leave, or adjustment rows."
        )


def _copy_text_evidence(source: Path, destination: Path) -> None:
    content = source.read_bytes()
    if source.suffix.lower() in {".log", ".json", ".txt"}:
        text = content.decode("utf-8", errors="replace")
        if _SECRET_PATTERN.search(text):
            raise RuntimeError("Public archive refused: release evidence contains a credential-like value.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def _replace_owned_directory(path: Path) -> None:
    archive = ARCHIVE_ROOT.resolve()
    resolved = path.resolve()
    if archive not in resolved.parents:
        raise RuntimeError("Public archive cleanup escaped the archive directory.")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def build_public_archive(project_root: Path = PROJECT_ROOT) -> Path:
    database_path = project_root / "data" / "runtime" / "sing-yin-roster.sqlite3"
    assert_public_fixture_database(database_path)

    fictional_dir = ARCHIVE_ROOT / "fictional-data"
    evidence_dir = ARCHIVE_ROOT / "release-evidence"
    preferences_dir = ARCHIVE_ROOT / "operator-preferences"
    _replace_owned_directory(fictional_dir)
    _replace_owned_directory(evidence_dir)
    _replace_owned_directory(preferences_dir)

    snapshot_path = fictional_dir / "sing-yin-roster-fictional.sqlite3"
    with sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True) as source:
        with sqlite3.connect(snapshot_path) as destination:
            source.backup(destination)
            # A public fixture is a portable, single-file snapshot rather than
            # a live WAL database. Normalise the copied journal mode before
            # later verification so no transient -wal/-shm files are archived.
            destination.execute("PRAGMA journal_mode=DELETE")

    for suffix in ("-wal", "-shm"):
        sidecar = snapshot_path.with_name(f"{snapshot_path.name}{suffix}")
        if sidecar.exists():
            sidecar.unlink()

    logs_dir = project_root / "logs"
    if logs_dir.is_dir():
        for source in sorted(logs_dir.iterdir()):
            if source.is_file():
                _copy_text_evidence(source, evidence_dir / "logs" / source.name)

    output_dir = project_root / "output"
    if output_dir.is_dir():
        for source in sorted(output_dir.rglob("*")):
            if source.is_file():
                _copy_text_evidence(source, evidence_dir / "output" / source.relative_to(output_dir))

    custom_library = project_root / "music" / "custom-library.json"
    if custom_library.is_file():
        _copy_text_evidence(custom_library, preferences_dir / custom_library.name)

    files = [path for path in ARCHIVE_ROOT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"]
    manifest = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "databaseClassification": "fictional-seed-only",
        "protectedRowCounts": public_fixture_counts(snapshot_path),
        "files": [
            {
                "path": path.relative_to(project_root).as_posix(),
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(files)
        ],
    }
    manifest_path = ARCHIVE_ROOT / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    try:
        manifest_path = build_public_archive()
    except (OSError, RuntimeError, sqlite3.Error) as error:
        print(f"PUBLIC ARCHIVE ERROR: {error}")
        return 1
    print(f"Public fictional-data archive ready: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
