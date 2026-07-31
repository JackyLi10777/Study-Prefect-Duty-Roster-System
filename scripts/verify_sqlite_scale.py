"""Produce privacy-safe SQLite scale and query-plan evidence.

The verifier creates disposable databases containing only synthetic records.
It never opens the configured school database and deliberately avoids importing
the production workflow singleton.  Use ``--profile smoke`` before a staged
release and ``--profile full`` for formal persistence changes.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from statistics import median
import sys
import tempfile
from time import perf_counter
import tracemalloc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.persistence.database import migrate_database


LEVELS = {
    "smoke": ((24, 52),),
    "full": ((24, 52), (240, 520), (2_400, 5_200)),
}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
    return ordered[position]


def _populate(connection: sqlite3.Connection, *, prefect_count: int, week_count: int) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
    prefect_rows = [
        (
            f"synthetic-{index:05d}",
            f"測試風紀{index:05d}",
            None,
            "F.5",
            f"{index % 8 + 1}A",
            "study_prefect",
            float(index % 11),
            index % 7,
            0.0,
            0,
            0,
            "NONE",
            "",
            1,
            1,
            now,
            now,
        )
        for index in range(prefect_count)
    ]
    connection.executemany(
        "INSERT INTO prefects "
        "(id,name_zh,name_en,form,class_name,role_code,history_weight,history_duties,"
        "history_weight_anchor,history_duties_anchor,needs_mentoring,fixed_general_duty,"
        "remarks,version,active,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        prefect_rows,
    )
    availability_rows = [
        (f"synthetic-{index:05d}", day)
        for index in range(prefect_count)
        for day in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")
    ]
    connection.executemany(
        "INSERT INTO prefect_availability (prefect_id,day) VALUES (?,?)",
        availability_rows,
    )
    first_monday = date(2020, 1, 6)
    week_rows = []
    for index in range(week_count):
        week_start = first_monday + timedelta(days=index * 7)
        week_rows.append(
            (
                week_start.isoformat(),
                "published",
                1,
                "2026.1",
                1.0,
                "flexible_weekly",
                now,
                now,
                None,
                None,
                now,
                now,
            )
        )
    connection.executemany(
        "INSERT INTO roster_weeks "
        "(week_start,status,version,policy_version,history_priority_multiplier,"
        "assist_assignment_mode,generated_at,published_at,withdrawn_at,withdrawal_reason,"
        "created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        week_rows,
    )
    roster_ids = [row[0] for row in connection.execute("SELECT id FROM roster_weeks ORDER BY id")]
    ledger_rows = [
        (
            f"synthetic-{index % prefect_count:05d}",
            roster_id,
            None,
            1.0,
            1,
            "published_assignment",
            "roster_week",
            str(roster_id),
            f"scale-{roster_id}",
            "",
            now,
        )
        for index, roster_id in enumerate(roster_ids)
    ]
    connection.executemany(
        "INSERT INTO fairness_ledger "
        "(prefect_id,roster_week_id,assignment_id,delta,duty_delta,event_type,source_type,"
        "source_id,operation_id,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ledger_rows,
    )
    backup_rows = [
        ("scale_verification", None, None, 1, None, now)
        for _ in range(min(week_count, 1_000))
    ]
    connection.executemany(
        "INSERT INTO backup_runs "
        "(event_type,roster_week_id,backup_path,success,error_message,created_at) "
        "VALUES (?,?,?,?,?,?)",
        backup_rows,
    )
    connection.commit()


def _plan(connection: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()) -> list[str]:
    return [str(row[3]) for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters)]


def _timings(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
    *,
    repetitions: int = 15,
) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(repetitions):
        started = perf_counter()
        connection.execute(sql, parameters).fetchall()
        samples.append((perf_counter() - started) * 1_000)
    return {
        "p50Ms": round(median(samples), 3),
        "p95Ms": round(_percentile(samples, 0.95), 3),
        "maxMs": round(max(samples), 3),
    }


def verify_level(*, prefect_count: int, week_count: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="sing-yin-sqlite-scale-") as temp_dir:
        database_path = Path(temp_dir) / "scale.sqlite3"
        migrate_database(database_path)
        tracemalloc.start()
        populate_started = perf_counter()
        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            _populate(connection, prefect_count=prefect_count, week_count=week_count)
            populate_ms = (perf_counter() - populate_started) * 1_000
            latest_roster_sql = (
                "SELECT id,week_start,status FROM roster_weeks "
                "WHERE status=? ORDER BY week_start DESC,id DESC LIMIT 1"
            )
            ledger_sql = (
                "SELECT id,delta,duty_delta FROM fairness_ledger "
                "WHERE roster_week_id=? ORDER BY created_at,id"
            )
            backup_sql = "SELECT id,created_at FROM backup_runs ORDER BY created_at DESC,id DESC LIMIT 1"
            plans = {
                "latestRoster": _plan(connection, latest_roster_sql, ("published",)),
                "weekLedger": _plan(connection, ledger_sql, (week_count,)),
                "latestBackup": _plan(connection, backup_sql),
            }
            timings = {
                "latestRoster": _timings(connection, latest_roster_sql, ("published",)),
                "weekLedger": _timings(connection, ledger_sql, (week_count,)),
                "latestBackup": _timings(connection, backup_sql),
            }
            connection.execute("PRAGMA optimize")
            connection.commit()
            backup_path = Path(temp_dir) / "scale-backup.sqlite3"
            backup_started = perf_counter()
            with closing(sqlite3.connect(backup_path)) as destination:
                connection.backup(destination)
            backup_ms = (perf_counter() - backup_started) * 1_000
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        wal_path = database_path.with_name(database_path.name + "-wal")
        return {
            "prefects": prefect_count,
            "weeks": week_count,
            "statementCount": 3 * 15,
            "populateMs": round(populate_ms, 3),
            "backupMs": round(backup_ms, 3),
            "databaseBytes": database_path.stat().st_size,
            "walBytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "memoryCurrentBytes": current_memory,
            "memoryPeakBytes": peak_memory,
            "plans": plans,
            "timings": timings,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(LEVELS), default="smoke")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "profile": args.profile,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "syntheticOnly": True,
        "levels": [
            verify_level(prefect_count=prefects, week_count=weeks)
            for prefects, weeks in LEVELS[args.profile]
        ],
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
