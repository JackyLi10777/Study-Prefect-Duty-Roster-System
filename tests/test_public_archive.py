from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

import scripts.build_public_archive as public_archive
from scripts.build_public_archive import PROTECTED_TABLES, assert_public_fixture_database, public_fixture_counts


def _fixture_database(path: Path, *, roster_rows: int = 0) -> None:
    with sqlite3.connect(path) as connection:
        for table in PROTECTED_TABLES:
            connection.execute(f'CREATE TABLE "{table}" (id INTEGER PRIMARY KEY)')
        if roster_rows:
            connection.executemany(
                "INSERT INTO roster_weeks (id) VALUES (?)",
                ((index + 1,) for index in range(roster_rows)),
            )


def test_public_archive_accepts_only_an_integral_empty_operational_fixture(tmp_path: Path) -> None:
    database = tmp_path / "fictional.sqlite3"
    _fixture_database(database)

    assert_public_fixture_database(database)

    assert public_fixture_counts(database) == {table: 0 for table in PROTECTED_TABLES}


def test_public_archive_rejects_even_one_roster_row(tmp_path: Path) -> None:
    database = tmp_path / "operational.sqlite3"
    _fixture_database(database, roster_rows=1)

    with pytest.raises(RuntimeError, match="contains roster"):
        assert_public_fixture_database(database)


def test_public_archive_rejects_an_incomplete_sqlite_schema(tmp_path: Path) -> None:
    database = tmp_path / "incomplete.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE roster_weeks (id INTEGER PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="missing required roster tables"):
        assert_public_fixture_database(database)


def test_public_archive_emits_a_single_file_sqlite_snapshot(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "data" / "runtime" / "sing-yin-roster.sqlite3"
    database.parent.mkdir(parents=True)
    _fixture_database(database)
    archive_root = tmp_path / "archive"
    monkeypatch.setattr(public_archive, "ARCHIVE_ROOT", archive_root)

    public_archive.build_public_archive(tmp_path)

    snapshot = archive_root / "fictional-data" / "sing-yin-roster-fictional.sqlite3"
    assert snapshot.is_file()
    assert not list(snapshot.parent.glob("*.sqlite3-*"))
