from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "deploy_cloudflare_worker.ps1"
HELPERS = PROJECT_ROOT / "scripts" / "worker_deployment_helpers.ps1"
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


def test_worker_release_gate_identity_comparison_is_order_independent_and_strict_safe() -> None:
    source = _source()

    assert "$reportIdentityDifferences = @(" in source
    assert "-ReferenceObject @($reportRequiredIdentities | Sort-Object)" in source
    assert "-DifferenceObject @($reportCheckNames | Sort-Object)" in source
    assert "$reportIdentityDifferences.Count -ne 0" in source
    assert "-SyncWindow 0" not in source


def test_worker_deployment_derives_its_default_source_from_its_own_checkout() -> None:
    source = _source()
    parameter_block = source.split("$ErrorActionPreference", 1)[0]

    assert '[string]$SourceRoot = ""' in parameter_block
    assert 'D:\\code_v3' not in parameter_block
    assert 'if ([string]::IsNullOrWhiteSpace($SourceRoot))' in source
    assert '$SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))' in source
    assert "explicit -SourceRoot remains available" in source


def test_worker_deployment_uses_pinned_wrangler_and_structured_events() -> None:
    source = _source()
    assert 'package.devDependencies.wrangler -cne "4.110.0"' in source
    assert "WRANGLER_OUTPUT_FILE_PATH" in source
    assert 'Read-WranglerEvent -Path $uploadOutput -Type "version-upload"' in source
    assert 'Read-WranglerEvent -Path $stageOutput -Type "version-deploy"' in source
    assert '"versions", "upload", "--dry-run", "--strict"' in source
    assert "function Assert-RequiredWorkerSecrets" in source
    assert '@("secret", "list", "--format", "json", "--config", $script:ConfigPath)' in source
    assert "Assert-RequiredWorkerSecrets" in source
    assert '"--secrets-file", $resolvedSecretOverlayPath' in source
    assert "Remove-SecretOverlay -Path $secretOverlayPathToDelete" in source
    assert "Assert-AdminIdentityAllowlistValue" in source
    assert "sing-yin-worker-secrets-" in source


def test_worker_secret_inventory_is_flattened_in_windows_powershell_51(tmp_path: Path) -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production deployment script")
    inventory = tmp_path / "worker-secrets.json"
    inventory.write_text(
        json.dumps(
            [
                {"name": "ADMIN_SESSION_SECRET", "type": "secret_text"},
                {"name": "GUEST_SESSION_SECRET", "type": "secret_text"},
            ]
        ),
        encoding="utf-8",
    )
    escaped_helpers = str(HELPERS).replace("'", "''")
    escaped_inventory = str(inventory).replace("'", "''")
    command = (
        f". '{escaped_helpers}'; "
        f"$json = Get-Content -LiteralPath '{escaped_inventory}' -Raw -Encoding UTF8; "
        "$names = @(ConvertFrom-WorkerSecretInventory -Json $json); "
        "if ($names.Count -ne 2 -or "
        "$names[0] -cne 'ADMIN_SESSION_SECRET' -or "
        "$names[1] -cne 'GUEST_SESSION_SECRET') { exit 2 }; "
        "Write-Output ($names -join ',')"
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
    assert result.stdout.strip() == "ADMIN_SESSION_SECRET,GUEST_SESSION_SECRET"


def test_invalid_allowlist_overlay_fails_before_deployment_and_is_deleted() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production deployment script")
    overlay = Path(tempfile.gettempdir()) / f"sing-yin-worker-secrets-{uuid.uuid4().hex}.json"
    overlay.write_text(
        json.dumps({"ADMIN_IDENTITY_ALLOWLIST": '{"emails":["UPPER@example.com"]}'}),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPT),
                "-SourceRoot",
                str(PROJECT_ROOT),
                "-ReleaseRef",
                "invalid-test-release",
                "-SecretOverlayPath",
                str(overlay),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode != 0
        assert "invalid or duplicate email entry" in result.stdout + result.stderr
        assert not overlay.exists()
    finally:
        overlay.unlink(missing_ok=True)


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


def test_worker_deployment_smoke_uses_the_unified_entrance_contract() -> None:
    source = _source()
    assert "$entrance.Content -notmatch 'data-guest-bootstrap='" in source
    assert "$entrance.Content -notmatch 'Study Prefect Duty Roster'" in source
    assert "$entrance.Content -notmatch 'Service Weave'" not in source


def test_worker_deployment_report_avoids_credentials_and_cleans_temp_output() -> None:
    source = _source()
    assert "Protect-Text" in source
    assert 'error = $failure' in source
    assert "ADMIN_BEARER_TOKEN" not in source
    assert "ADMIN_SESSION_SECRET" not in source
    assert 'Remove-Item -LiteralPath $outputDirectory -Recurse -Force' in source
    cleanup_index = source.index("Remove-SecretOverlay -Path $secretOverlayPathToDelete")
    pass_report_index = source.index('status = "pass"')
    assert cleanup_index < pass_report_index


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
