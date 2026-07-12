"""Run release security gates without printing possible secret values."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run(name: str, arguments: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main() -> int:
    checks: list[dict[str, object]] = []

    audit_ok, audit_output = _run("dependency_audit", ["pip_audit", "-r", "requirements.lock", "--disable-pip"])
    checks.append(
        {
            "name": "dependency_audit",
            "status": "pass" if audit_ok else "fail",
            "summary": "No known vulnerabilities found" if audit_ok else "Dependency audit requires review",
        }
    )

    bandit_ok, bandit_output = _run(
        "static_analysis",
        ["bandit", "-q", "-ll", "-r", "nicegui_app", "packages"],
    )
    checks.append(
        {
            "name": "static_analysis",
            "status": "pass" if bandit_ok else "fail",
            "summary": "No medium/high findings" if bandit_ok else "Static analysis requires review",
        }
    )

    secrets_ok, secrets_output = _run(
        "secret_scan",
        [
            "detect_secrets",
            "scan",
            "nicegui_app",
            "packages",
            "migrations",
            "scripts",
            ".github",
            ".env.example",
            "--exclude-files",
            r"requirements.*\.lock$|\.(woff2?|ttf|webp|png|jpg|jpeg|m4a|mp3|sqlite3|pdf|zip)$",
        ],
    )
    secret_findings = -1
    secret_files = -1
    secret_types: list[str] = []
    secret_locations: list[str] = []
    try:
        payload = json.loads(secrets_output)
        result_groups = payload.get("results", {})
        secret_files = len(result_groups)
        secret_findings = sum(len(items) for items in result_groups.values())
        secret_types = sorted({str(item.get("type", "unknown")) for items in result_groups.values() for item in items})
        secret_locations = sorted(
            f"{path}:{item.get('line_number', '?')}"
            for path, items in result_groups.items()
            for item in items
        )
        secrets_ok = secrets_ok and secret_findings == 0
    except (json.JSONDecodeError, TypeError, AttributeError):
        secrets_ok = False
    checks.append(
        {
            "name": "secret_scan",
            "status": "pass" if secrets_ok else "fail",
            "summary": "No candidates found" if secrets_ok else "Secret candidates require private review",
            "candidateFiles": secret_files,
            "candidateCount": secret_findings,
            "candidateTypes": secret_types,
            "candidateLocations": secret_locations,
        }
    )

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    print(json.dumps({"status": status, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
