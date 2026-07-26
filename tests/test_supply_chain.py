from __future__ import annotations

import json
from pathlib import Path
import shutil

from scripts.run_security_checks import (
    _SECRET_SCAN_TARGETS,
    _is_public_audit_digest,
    _is_public_pnpm_integrity,
    _service_weave_delivery_is_current,
)
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_and_verification_dependencies_are_hash_locked() -> None:
    runtime = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    development = (ROOT / "requirements-dev.lock").read_text(encoding="utf-8")

    for dependency in ("nicegui==", "sqlalchemy==", "alembic==", "reportlab=="):
        assert dependency in runtime.lower()
    for tool in ("pytest==", "pip-audit==", "bandit==", "detect-secrets=="):
        assert tool in development.lower()
    development_lines = development.lower().splitlines()
    assert any(line.startswith("pip==") for line in development_lines)
    assert any(line.startswith("setuptools==") for line in development_lines)
    assert "pip-compile --allow-unsafe --generate-hashes" in development.lower()
    assert "--hash=sha256:" in runtime
    assert "--hash=sha256:" in development


def test_direct_web_framework_dependencies_are_owned_and_locked() -> None:
    runtime_requirements = (
        (ROOT / "requirements.txt").read_text(encoding="utf-8").lower().splitlines()
    )
    runtime_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8").lower()

    assert "fastapi>=0.139,<0.140" in runtime_requirements
    assert "starlette>=1.3,<1.4" in runtime_requirements
    assert "fastapi==0.139.0" in runtime_lock
    assert "starlette==1.3.1" in runtime_lock


def test_hong_kong_timezone_data_is_available_and_locked_for_windows() -> None:
    runtime_requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    runtime_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8").lower()

    assert ZoneInfo("Asia/Hong_Kong").key == "Asia/Hong_Kong"
    assert any(line.startswith("tzdata") for line in runtime_requirements.splitlines())
    assert "tzdata==" in runtime_lock


def test_github_quality_gates_use_full_history_and_locked_dependencies() -> None:
    workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")

    assert "fetch-depth: 0" in workflow
    assert "--require-hashes -r requirements-dev.lock" in workflow
    assert "verify_update.py" in workflow
    assert "needs_deno" in workflow
    assert "deno-version: 2.9.2" in workflow
    assert "deno-version: v2.x" not in workflow
    assert "cancel-in-progress: true" in workflow


def test_codeql_and_dependabot_are_configured() -> None:
    codeql = (ROOT / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8")
    assert "pull_request:" in codeql
    assert "paths:" not in codeql
    assert "analyze:" in codeql
    assert "cancel-in-progress: true" in codeql
    assert "languages: python,javascript-typescript" in codeql
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: pip" in dependabot
    assert "package-ecosystem: github-actions" in dependabot
    assert "package-ecosystem: npm" in dependabot
    assert 'directory: "/cloudflare/roster_viewer"' in dependabot


def test_local_secret_scan_includes_the_cloudflare_gateway() -> None:
    security_gate = (ROOT / "scripts" / "run_security_checks.py").read_text(encoding="utf-8")

    assert '"cloudflare"' in security_gate
    assert '"design_system"' in security_gate
    assert '"pnpm-lock.yaml"' not in security_gate
    assert {"design_system", "docs", "README.md", "PROJECT_STATUS.md"} <= set(_SECRET_SCAN_TARGETS)


def test_local_dependency_gate_audits_python_and_worker_locks() -> None:
    security_gate = (ROOT / "scripts" / "run_security_checks.py").read_text(encoding="utf-8")

    assert '"pip_audit", "-r", "requirements.lock"' in security_gate
    assert "def _run_worker_dependency_audit()" in security_gate
    assert 'shutil.which("pnpm")' in security_gate
    assert '"--audit-level", "high", "--json"' in security_gate
    assert 'cwd=PROJECT_ROOT / "cloudflare" / "roster_viewer"' in security_gate


def test_secret_scan_ignores_only_standard_public_pnpm_integrity_lines() -> None:
    lock_lines = (ROOT / "cloudflare" / "roster_viewer" / "pnpm-lock.yaml").read_text(encoding="utf-8").splitlines()
    integrity_line = next(index for index, line in enumerate(lock_lines, start=1) if "integrity: sha512-" in line)

    assert _is_public_pnpm_integrity("cloudflare\\roster_viewer\\pnpm-lock.yaml", integrity_line)
    assert not _is_public_pnpm_integrity("cloudflare/roster_viewer/worker.js", integrity_line)
    assert not _is_public_pnpm_integrity("cloudflare/roster_viewer/pnpm-lock.yaml", 1)


def test_secret_scan_ignores_only_named_public_audit_digests(tmp_path: Path) -> None:
    relative_path = Path("docs/audits/CODEBASE_AUDIT_FINDINGS_2026-07-26.json")
    source = ROOT / relative_path
    audit = tmp_path / relative_path
    audit.parent.mkdir(parents=True)
    shutil.copy2(source, audit)
    lines = audit.read_text(encoding="utf-8").splitlines()
    commit_line = next(
        index for index, line in enumerate(lines, start=1) if '"commit"' in line
    )

    assert _is_public_audit_digest(str(relative_path), commit_line, tmp_path)

    unknown = audit.with_name("unknown.json")
    shutil.copy2(audit, unknown)
    assert not _is_public_audit_digest(
        "docs/audits/unknown.json", commit_line, tmp_path
    )

    payload = json.loads(audit.read_text(encoding="utf-8"))
    payload["nested"] = {"commit": payload["audit_metadata"]["commit"]}
    audit.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    duplicated_lines = audit.read_text(encoding="utf-8").splitlines()
    first_commit_line = next(
        index
        for index, line in enumerate(duplicated_lines, start=1)
        if '"commit"' in line
    )
    assert not _is_public_audit_digest(
        str(relative_path), first_commit_line, tmp_path
    )


def test_secret_scan_excludes_only_the_exact_manifest_generated_brand_payload(
    tmp_path: Path,
) -> None:
    source = ROOT / "nicegui_app" / "assets" / "brand" / "service-weave" / "service-weave-favicon-512-v1.png"
    generated = ROOT / "cloudflare" / "roster_viewer" / "service_weave_brand.generated.js"
    manifest = ROOT / "design_system" / "product-identity.v1.json"

    (tmp_path / "nicegui_app" / "assets" / "brand" / "service-weave").mkdir(parents=True)
    (tmp_path / "cloudflare" / "roster_viewer").mkdir(parents=True)
    (tmp_path / "design_system").mkdir(parents=True)
    (tmp_path / source.relative_to(ROOT)).write_bytes(source.read_bytes())
    (tmp_path / generated.relative_to(ROOT)).write_text(
        generated.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / manifest.relative_to(ROOT)).write_text(
        manifest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    assert _service_weave_delivery_is_current(tmp_path)
    with (tmp_path / generated.relative_to(ROOT)).open("a", encoding="utf-8") as output:
        output.write("export const UNREVIEWED_VALUE = 'not-approved';\n")
    assert not _service_weave_delivery_is_current(tmp_path)
