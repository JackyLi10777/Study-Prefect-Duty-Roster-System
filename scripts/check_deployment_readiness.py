"""Print a non-sensitive readiness report without configuring remote access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from nicegui_app.config import PROJECT_ROOT as APPLICATION_ROOT
from nicegui_app.deployment import DeploymentSettings, readiness_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Return a failure code for warnings as well as failures.")
    args = parser.parse_args()
    load_dotenv(APPLICATION_ROOT / ".env")
    settings = DeploymentSettings.from_environment()
    payload = readiness_payload(settings)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    statuses = {str(check["status"]) for check in payload["checks"]}  # type: ignore[index]
    if "fail" in statuses or (args.strict and "warning" in statuses):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
