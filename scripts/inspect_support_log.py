"""Safely inspect the newest local Sing Yin support records without opening a log editor."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATTERN = re.compile(r"^(?:OP|REQ)-[A-F0-9]{8}$")


def default_log_path() -> Path:
    return Path(os.getenv("SING_YIN_LOG_DIR", PROJECT_ROOT / "logs")) / "app.log"


def support_lines(log_path: Path, *, reference: str | None = None, tail: int = 30) -> list[str]:
    """Return recent diagnostic records, optionally narrowed to one safe support reference."""
    if tail < 1:
        raise ValueError("tail must be positive")
    if reference and not REFERENCE_PATTERN.fullmatch(reference):
        raise ValueError("reference must look like OP-1234ABCD or REQ-1234ABCD")
    if not log_path.is_file():
        return []
    lines = [line for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if reference:
        lines = [line for line in lines if reference in line]
    return lines[-tail:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the newest privacy-safe local Sing Yin support records.")
    parser.add_argument("--reference", help="Optional OP-... or REQ-... trace to find.")
    parser.add_argument("--tail", type=int, default=30, help="Maximum records to show (default: 30).")
    parser.add_argument("--log-path", type=Path, default=default_log_path(), help="Local app.log path.")
    args = parser.parse_args()
    try:
        lines = support_lines(args.log_path, reference=args.reference, tail=args.tail)
    except ValueError as error:
        parser.error(str(error))
    if not lines:
        print(f"No matching local support records found in: {args.log_path}")
        return 1
    print(f"Local support records from: {args.log_path}")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
