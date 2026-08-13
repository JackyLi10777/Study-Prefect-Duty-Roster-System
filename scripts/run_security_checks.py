"""Run release security gates without printing possible secret values."""

from __future__ import annotations

import argparse
import base64
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PNPM_LOCK_RELATIVE_PATH = "cloudflare/roster_viewer/pnpm-lock.yaml"
_SERVICE_WEAVE_GENERATED_RELATIVE_PATH = (
    "cloudflare/roster_viewer/service_weave_brand.generated.js"
)
_PNPM_PUBLIC_INTEGRITY = re.compile(
    r"^\s*resolution:\s*\{integrity:\s*sha512-[A-Za-z0-9+/]+={0,2}\}\s*$"
)
_PUBLIC_AUDIT_DIGEST = re.compile(
    r'^\s*"(?P<field>[A-Za-z][A-Za-z0-9]*)"\s*:\s*'
    r'"(?P<digest>[0-9a-f]{40}|[0-9a-f]{64})"\s*,?\s*$'
)
_PUBLIC_AUDIT_DIGEST_LOCATIONS = {
    "docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26.json": {
        ("audit_metadata", "commit"),
    },
    "docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26_R2.json": {
        ("audit", "baseline", "head"),
        ("audit", "baseline", "tree"),
        ("audit", "baseline", "remoteMain"),
        ("audit", "baseline", "rc26Commit"),
        ("audit", "baseline", "rc26Tree"),
        ("remediation", "baselineHead"),
    },
    "docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26_R3.json": {
        ("audit_metadata", "commit"),
    },
}
_CURRENT_RELEASE_RELATIVE_PATH = "docs/status/current-release.json"
_PUBLIC_CURRENT_RELEASE_DIGEST = re.compile(
    r'^\s*"(?P<field>commit|fingerprint_sha256|backup_sha256)"\s*:\s*'
    r'"(?P<digest>[0-9a-f]{40}|[0-9a-f]{64})"\s*,?\s*$'
)
_PUBLIC_CURRENT_RELEASE_DIGEST_LOCATIONS = {
    "commit": ("release", "commit"),
    "fingerprint_sha256": ("release", "fingerprint_sha256"),
    "backup_sha256": ("recovery", "backup_sha256"),
}
_DESIGN_SOURCE_LEDGER_RELATIVE_PATH = "design_system/external_design_sources.v1.json"
_PUBLIC_DESIGN_SOURCE_DIGEST = re.compile(
    r'^\s*"(?P<field>revision|licenseSha256|sourceArchiveSha256)"\s*:\s*'
    r'"(?P<digest>[0-9a-f]{40}|[0-9a-f]{64})"\s*,?\s*$'
)
_PUBLIC_DESIGN_SOURCE_DIGEST_FIELDS = {
    "revision": 40,
    "licenseSha256": 64,
    "sourceArchiveSha256": 64,
}
_CHECK_NAMES = ("dependency_audit", "static_analysis", "secret_scan")
_SECRET_SCAN_TARGETS = (
    "nicegui_app",
    "packages",
    "migrations",
    "scripts",
    ".github",
    "cloudflare",
    "design_system",
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


def _is_public_audit_digest(
    path: str,
    line_number: object,
    root: Path = PROJECT_ROOT,
) -> bool:
    """Recognize schema-bound public provenance digests in reviewed audit reports."""

    normalized = path.replace("\\", "/").lstrip("./")
    allowed_locations = _PUBLIC_AUDIT_DIGEST_LOCATIONS.get(normalized)
    if allowed_locations is None:
        return False
    relative_path = Path(normalized)
    try:
        index = int(line_number) - 1
        lines = (root / relative_path).read_text(encoding="utf-8").splitlines()
        line = lines[index]
        payload = json.loads("\n".join(lines))
    except (TypeError, ValueError, IndexError, OSError, json.JSONDecodeError):
        return False
    match = _PUBLIC_AUDIT_DIGEST.fullmatch(line)
    if match is None:
        return False

    field = match.group("field")
    digest = match.group("digest")
    same_field_count = sum(
        1
        for candidate in lines
        if (candidate_match := _PUBLIC_AUDIT_DIGEST.fullmatch(candidate)) is not None
        and candidate_match.group("field") == field
    )
    if same_field_count != 1:
        return False

    for location in allowed_locations:
        if location[-1] != field:
            continue
        value: object = payload
        try:
            for key in location:
                value = value[key]  # type: ignore[index]
        except (KeyError, TypeError):
            continue
        if value == digest:
            return True
    return False


def _is_public_current_release_digest(
    path: str,
    line_number: object,
    root: Path = PROJECT_ROOT,
) -> bool:
    """Recognize only public provenance hashes in the live status schema."""

    normalized = path.replace("\\", "/").lstrip("./")
    if normalized != _CURRENT_RELEASE_RELATIVE_PATH:
        return False
    relative_path = Path(normalized)
    try:
        index = int(line_number) - 1
        lines = (root / relative_path).read_text(encoding="utf-8").splitlines()
        line = lines[index]
        payload = json.loads("\n".join(lines))
    except (TypeError, ValueError, IndexError, OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping):
        return False
    if payload.get("schema_version") != 2 or payload.get("state") != "live":
        return False
    match = _PUBLIC_CURRENT_RELEASE_DIGEST.fullmatch(line)
    if match is None:
        return False

    field = match.group("field")
    digest = match.group("digest")
    location = _PUBLIC_CURRENT_RELEASE_DIGEST_LOCATIONS[field]
    value: object = payload
    try:
        for key in location:
            value = value[key]  # type: ignore[index]
    except (KeyError, TypeError):
        return False
    expected_length = 40 if field == "commit" else 64
    return len(digest) == expected_length and value == digest


def _is_public_design_source_digest(
    path: str,
    line_number: object,
    root: Path = PROJECT_ROOT,
) -> bool:
    """Recognize only schema-bound provenance hashes in the design-source ledger."""

    normalized = path.replace("\\", "/").lstrip("./")
    if normalized != _DESIGN_SOURCE_LEDGER_RELATIVE_PATH:
        return False
    relative_path = Path(normalized)
    try:
        index = int(line_number) - 1
        lines = (root / relative_path).read_text(encoding="utf-8").splitlines()
        line = lines[index]
        payload = json.loads("\n".join(lines))
    except (TypeError, ValueError, IndexError, OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, Mapping) or payload.get("contractVersion") != "1.0.0":
        return False
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return False
    canonical_lines = json.dumps(payload, ensure_ascii=False, indent=2).splitlines()
    if lines != canonical_lines:
        return False
    match = _PUBLIC_DESIGN_SOURCE_DIGEST.fullmatch(line)
    if match is None:
        return False
    # Canonical two-space JSON places only direct ``sources[*]`` fields at six
    # spaces.  Nested or top-level values must never inherit this exemption.
    if len(line) - len(line.lstrip(" ")) != 6:
        return False
    field = match.group("field")
    digest = match.group("digest")
    if len(digest) != _PUBLIC_DESIGN_SOURCE_DIGEST_FIELDS[field]:
        return False
    return sum(
        1
        for source in sources
        if isinstance(source, Mapping) and source.get(field) == digest
    ) == 1


def _render_verified_service_weave_module(payload: bytes) -> str:
    """Render the only high-entropy text artifact approved by this gate."""

    encoded = base64.b64encode(payload).decode("ascii")
    chunks = [encoded[index : index + 120] for index in range(0, len(encoded), 120)]
    chunk_lines = "\n".join(f"  '{chunk}'," for chunk in chunks)
    digest = hashlib.sha256(payload).hexdigest()
    return (
        "// Generated by scripts/generate_service_weave_delivery.py; do not edit manually.\n"
        "export const SERVICE_WEAVE_FAVICON_BASE64 = [\n"
        f"{chunk_lines}\n"
        "].join('');\n"
        f"export const SERVICE_WEAVE_FAVICON_SHA256 = '{digest}';\n"
        f"export const SERVICE_WEAVE_FAVICON_BYTE_LENGTH = {len(payload)};\n"
    )


def _service_weave_delivery_is_current(root: Path = PROJECT_ROOT) -> bool:
    """Verify the complete generated module before excluding its public PNG bytes.

    The file is never ignored by pathname alone.  Its manifest-selected source,
    generator format, digest, byte length, and every Base64 character must agree.
    """

    try:
        manifest = json.loads(
            (root / "design_system" / "product-identity.v1.json").read_text(
                encoding="utf-8"
            )
        )
        delivery = manifest["delivery"]
        if delivery["workerGeneratedModule"] != _SERVICE_WEAVE_GENERATED_RELATIVE_PATH:
            return False
        selected_key = delivery["faviconVariant"]
        variant = next(
            item
            for item in manifest["productMarkVariants"]
            if item["key"] == selected_key
        )
        source = (root / variant["relativePath"]).resolve()
        source.relative_to(root.resolve())
        output = root / _SERVICE_WEAVE_GENERATED_RELATIVE_PATH
        return (
            source.is_file()
            and output.is_file()
            and output.read_text(encoding="utf-8")
            == _render_verified_service_weave_module(source.read_bytes())
        )
    except (KeyError, StopIteration, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False


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


def _run_worker_dependency_audit() -> bool:
    """Audit the pinned Worker lock without exposing advisory details in public logs."""

    executable = shutil.which("pnpm")
    command = [executable, "audit"] if executable else [shutil.which("corepack") or "corepack", "pnpm", "audit"]
    try:
        result = subprocess.run(
            [*command, "--audit-level", "high", "--json"],
            cwd=PROJECT_ROOT / "cloudflare" / "roster_viewer",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


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
        python_audit_ok, _audit_output = _run(
            "dependency_audit",
            ["pip_audit", "-r", "requirements.lock", "--disable-pip"],
        )
        worker_audit_ok = _run_worker_dependency_audit()
        audit_ok = python_audit_ok and worker_audit_ok
        checks.append(
            {
                "name": "dependency_audit",
                "status": "pass" if audit_ok else "fail",
                "summary": (
                    "No known high/critical Python or Worker dependency vulnerabilities found"
                    if audit_ok
                    else "Python or Worker dependency audit requires review"
                ),
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
            service_weave_delivery_verified = _service_weave_delivery_is_current()
            result_groups = {
                path: [
                    item
                    for item in items
                    if not (
                        _is_public_pnpm_integrity(path, item.get("line_number"))
                        or _is_public_audit_digest(path, item.get("line_number"))
                        or _is_public_current_release_digest(
                            path, item.get("line_number")
                        )
                        or _is_public_design_source_digest(
                            path, item.get("line_number")
                        )
                        or (
                            path.replace("\\", "/").lstrip("./")
                            == _SERVICE_WEAVE_GENERATED_RELATIVE_PATH
                            and service_weave_delivery_verified
                        )
                    )
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
