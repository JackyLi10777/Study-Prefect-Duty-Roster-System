from __future__ import annotations

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = PROJECT_ROOT / ".github" / "workflows"


def test_actions_are_immutable_and_use_least_privilege_checkout() -> None:
    workflows = [path.read_text(encoding="utf-8") for path in WORKFLOW_ROOT.glob("*.yml")]
    source = "\n".join(workflows)
    uses = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", source, flags=re.MULTILINE)

    assert uses
    assert all(re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", value) for value in uses)
    assert source.count("persist-credentials: false") == source.count("actions/checkout@")
    assert "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020" in source
    assert "corepack enable" in source
    assert all("permissions:\n  contents: read" in workflow for workflow in workflows)
    assert "pull_request_target" not in source


def test_security_checks_are_stable_required_check_candidates() -> None:
    quality = (WORKFLOW_ROOT / "quality.yml").read_text(encoding="utf-8")
    codeql = (WORKFLOW_ROOT / "codeql.yml").read_text(encoding="utf-8")

    assert "test-and-audit:" in quality
    assert "analyze:" in codeql
    assert "pull_request:" in quality and "pull_request:" in codeql
    assert "branches: [main, nicegui-self-hosted]" in quality
    assert "branches: [main, nicegui-self-hosted]" in codeql
    assert "paths:" not in codeql
    assert "languages: python,javascript-typescript" in codeql


def test_dependabot_covers_every_executable_dependency_surface() -> None:
    dependabot = (PROJECT_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    for ecosystem in ("pip", "github-actions", "npm"):
        assert f"package-ecosystem: {ecosystem}" in dependabot
    assert 'directory: "/cloudflare/roster_viewer"' in dependabot


def test_repository_security_ownership_and_private_reporting_are_documented() -> None:
    codeowners = (PROJECT_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    policy = (PROJECT_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    model = (PROJECT_ROOT / "docs" / "SECURITY_AND_PRIVACY.md").read_text(encoding="utf-8")

    assert "* @JackyLi10777" in codeowners
    for critical_path in ("/.github/", "/cloudflare/roster_viewer/", "/nicegui_app/persistence/"):
        assert critical_path in codeowners
    assert "Private vulnerability" in policy
    assert "SECURITY_AND_PRIVACY.md" in policy
    for contract in (
        "fail closed",
        "ADMIN_IDENTITY_ALLOWLIST",
        "test-and-audit",
        "analyze",
        "AUTH_EPOCH",
        "BitLocker",
    ):
        assert contract in model


def test_worker_public_config_contains_no_private_admin_identity() -> None:
    for name in ("wrangler.jsonc", "wrangler.template.jsonc"):
        source = (PROJECT_ROOT / "cloudflare" / "roster_viewer" / name).read_text(encoding="utf-8")
        variables = source.split('"vars":', 1)[1].split('"secrets":', 1)[0]
        assert "ADMIN_IDENTITY_ALLOWLIST" not in variables
        assert "@gmail.com" not in source
        assert "@outlook.com" not in source
    assert '"ADMIN_IDENTITY_ALLOWLIST"' in source.split('"secrets":', 1)[1]
