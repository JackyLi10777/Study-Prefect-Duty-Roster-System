from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "deploy_cloudflare_worker.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_worker_deployment_is_bound_to_an_immutable_published_release() -> None:
    source = _source()
    assert '"status", "--porcelain", "--untracked-files=all"' in source
    assert '"cat-file", "-t", $tagRef' in source
    assert '"ls-remote", "--tags", "origin"' in source
    assert "merge-base --is-ancestor" in source
    assert "Source HEAD does not match the release tag." in source
    assert "is not contained in origin/main" in source


def test_worker_deployment_uses_pinned_wrangler_and_structured_events() -> None:
    source = _source()
    assert 'package.devDependencies.wrangler -cne "4.110.0"' in source
    assert "WRANGLER_OUTPUT_FILE_PATH" in source
    assert 'Read-WranglerEvent -Path $uploadOutput -Type "version-upload"' in source
    assert 'Read-WranglerEvent -Path $stageOutput -Type "version-deploy"' in source
    assert '"versions", "upload", "--dry-run", "--strict"' in source


def test_worker_deployment_stages_tests_promotes_and_rolls_back() -> None:
    source = _source()
    assert '"versions", "deploy", "$previousVersionId@100%", "$newVersionId@0%"' in source
    assert 'Cloudflare-Workers-Version-Overrides' in source
    assert 'Assert-Traffic -Status $stageStatus' in source
    assert '"versions", "deploy", "$newVersionId@100%"' in source
    assert 'Assert-Traffic -Status $promoteStatus' in source
    assert '"rollback", $previousVersionId' in source
    assert "$rollbackRequired = $true" in source
    assert "if ($rollbackRequired" in source
    assert 'Assert-Traffic -Status $rollbackStatus' in source
    assert 'rollbackCompleted = $rollbackCompleted' in source


def test_worker_deployment_report_avoids_credentials_and_cleans_temp_output() -> None:
    source = _source()
    assert "Protect-Text" in source
    assert 'error = $failure' in source
    assert "ADMIN_BEARER_TOKEN" not in source
    assert "ADMIN_SESSION_SECRET" not in source
    assert 'Remove-Item -LiteralPath $outputDirectory -Recurse -Force' in source


def test_worker_deployment_script_parses_in_windows_powershell_51() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production deployment script")
    escaped = str(SCRIPT).replace("'", "''")
    command = (
        f"$tokens=$null; $errors=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{escaped}', [ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
