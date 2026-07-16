"""Run release security gates without printing possible secret values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PNPM_LOCK_RELATIVE_PATH = "cloudflare/roster_viewer/pnpm-lock.yaml"
_PNPM_PUBLIC_INTEGRITY = re.compile(
    r"^\s*resolution:\s*\{integrity:\s*sha512-[A-Za-z0-9+/]+={0,2}\}\s*$"
)
_CHECK_NAMES = ("dependency_audit", "static_analysis", "secret_scan")
_SECRET_SCAN_TARGETS = (
    "nicegui_app",
    "packages",
    "migrations",
    "scripts",
    ".github",
    "cloudflare",
    "docs",
    "archive/README.md",
    ".env.example",
    "README.md",
    "README-EN.md",
    "CODEX_PROMPTS.md",
    "CONTRIBUTING.md",
    "NOTICE.md",
    "Professional_Design_System.md",
    "PROJECT_STATUS.md",
    "LICENSE",
)


def _is_public_pnpm_integrity(path: str, line_number: object) -> bool:
    """Recognize only standard public SHA-512 package checksums in the pinned lockfile."""
    normalized = path.replace("\\", "/").lstrip("./")
    if normalized != _PNPM_LOCK_RELATIVE_PATH:
        return False
    try:
        index = int(line_number) - 1
        line = (PROJECT_ROOT / _PNPM_LOCK_RELATIVE_PATH).read_text(encoding="utf-8").splitlines()[index]
    except (TypeError, ValueError, IndexError, OSError):
        return False
    return _PNPM_PUBLIC_INTEGRITY.fullmatch(line) is not None


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        action="append",
        choices=_CHECK_NAMES,
        help="Run only the named gate; repeat to select more than one. Default: all gates.",
    )
    args = parser.parse_args()
    selected = set(args.only or _CHECK_NAMES)
    checks: list[dict[str, object]] = []

    if "dependency_audit" in selected:
        audit_ok, _audit_output = _run("dependency_audit", ["pip_audit", "-r", "requirements.lock", "--disable-pip"])
        checks.append(
            {
                "name": "dependency_audit",
                "status": "pass" if audit_ok else "fail",
                "summary": "No known vulnerabilities found" if audit_ok else "Dependency audit requires review",
            }
        )

    if "static_analysis" in selected:
        bandit_ok, _bandit_output = _run(
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

    if "secret_scan" in selected:
        secrets_ok, secrets_output = _run(
            "secret_scan",
            [
                "detect_secrets",
                "scan",
                *_SECRET_SCAN_TARGETS,
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
            raw_groups = payload.get("results", {})
            result_groups = {
                path: [
                    item
                    for item in items
                    if not _is_public_pnpm_integrity(path, item.get("line_number"))
                ]
                for path, items in raw_groups.items()
            }
            result_groups = {path: items for path, items in result_groups.items() if items}
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
