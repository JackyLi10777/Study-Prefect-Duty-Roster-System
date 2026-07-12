"""Safely clear only the isolated practice workspace, then let the launcher reseed it."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRACTICE_ROOT = (PROJECT_ROOT / "data" / "practice").resolve()


def _practice_service_running() -> bool:
    for port in range(8090, 8110):
        try:
            with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=0.2) as response:  # noqa: S310 - loopback only
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("application") == "sing-yin-roster" and payload.get("applicationMode") == "practice":
            return True
    return False


def reset_practice_data() -> None:
    expected = (PROJECT_ROOT / "data" / "practice").resolve()
    if PRACTICE_ROOT != expected or PRACTICE_ROOT.parent != (PROJECT_ROOT / "data").resolve():
        raise RuntimeError("Practice reset path did not pass the workspace boundary check.")
    if _practice_service_running():
        raise RuntimeError("Close the running Practice Mode window first, then double-click RESET_PRACTICE_MODE again.")
    if PRACTICE_ROOT.exists():
        shutil.rmtree(PRACTICE_ROOT)
    PRACTICE_ROOT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    try:
        reset_practice_data()
    except (OSError, RuntimeError) as error:
        print(f"PRACTICE RESET ERROR: {error}")
        return 1
    print("Practice data was reset. A fresh fictional workspace will now open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
