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


def blocking_checks(
    payload: dict[str, object],
    *,
    strict: bool,
    allow_pending_cloudflare_access: bool,
) -> tuple[str, ...]:
    """Return checks that must stop the current release stage.

    A Windows-origin rollout necessarily precedes the matching Worker rollout.
    During that narrow stage, Cloudflare Access remains an explicit post-deploy
    obligation; every other warning and every failure still blocks the host.
    """

    blocking: list[str] = []
    for raw_check in payload.get("checks", []):
        if not isinstance(raw_check, dict):
            blocking.append("malformed_check")
            continue
        code = str(raw_check.get("code", "unknown"))
        status = str(raw_check.get("status", "fail"))
        if status == "fail":
            blocking.append(code)
        elif status == "warning" and strict:
            if allow_pending_cloudflare_access and code == "cloudflare_access":
                continue
            blocking.append(code)
    return tuple(blocking)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Return a failure code for warnings as well as failures.")
    parser.add_argument(
        "--allow-pending-cloudflare-access",
        action="store_true",
        help=(
            "During the controlled origin-first release stage, defer only the Cloudflare Access live-verification "
            "warning until the matching Worker has been deployed."
        ),
    )
    args = parser.parse_args()
    load_dotenv(APPLICATION_ROOT / ".env")
    settings = DeploymentSettings.from_environment()
    payload = readiness_payload(settings)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if blocking_checks(
        payload,
        strict=args.strict,
        allow_pending_cloudflare_access=args.allow_pending_cloudflare_access,
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
