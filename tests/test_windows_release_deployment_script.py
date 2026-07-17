from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "deploy_windows_release.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_deployment_script_is_generic_and_requires_an_immutable_published_tag() -> None:
    source = _source()
    parameter_block = source.split("$ErrorActionPreference", 1)[0]

    for parameter in (
        "SourceRoot",
        "HostRoot",
        "ReleaseRef",
        "TaskName",
        "RuntimeUser",
        "EnvironmentOverlayPath",
    ):
        assert f"${parameter}" in parameter_block
    assert "ExpectedFingerprint" not in parameter_block
    assert "ExpectedCommit" not in parameter_block
    assert "ReportPath" not in parameter_block
    assert "rc.15" not in source.lower()
    assert "windows-release-deployment-$safeReleaseName.json" in source
    assert "refs/tags/$TagName" in source
    assert '"cat-file", "-t", $tagReference' in source
    assert '"$tagReference^{tag}"' in source
    assert '"$tagReference^{commit}"' in source
    assert "ls-remote --tags origin" in source
    assert "The local release tag does not match the immutable tag published to origin." in source
    assert "merge-base --is-ancestor $releaseCommit origin/main" in source
    assert 'if ($sourceHead -cne $releaseCommit)' in source


def test_deployment_script_refreshes_origin_main_before_ancestor_checks() -> None:
    source = _source()
    explicit_refspec = '"+refs/heads/main:refs/remotes/origin/main"'
    source_ancestor_check = "merge-base --is-ancestor $releaseCommit origin/main"
    host_ancestor_check = "merge-base --is-ancestor $hostReleaseCommit origin/main"

    first_fetch = source.index(explicit_refspec)
    second_fetch = source.index(explicit_refspec, first_fetch + 1)

    assert source.count(explicit_refspec) == 2
    assert first_fetch < source.index(source_ancestor_check)
    assert second_fetch < source.index(host_ancestor_check)
    assert '"origin",\n        "main"' not in source


def test_deployment_script_requires_the_current_thirteen_gate_fingerprint() -> None:
    source = _source()
    required_checks = (
        "repository_hygiene",
        "security_gates",
        "cloudflare_gateway_tests",
        "automated_test_suite",
        "python_compile",
        "dependency_integrity",
        "verify_nicegui_ui",
        "verify_runtime_performance",
        "verify_nicegui_write_pipeline",
        "verify_nicegui_mobile",
        "strict_deployment_readiness",
        "verify_unified_guest_ui",
        "verify_nicegui_partial_backup",
    )

    for check in required_checks:
        assert f'"{check}"' in source
    assert "$reportChecks.Count -ne 13" in source
    assert "$passedNames.Count -ne 13" in source
    assert "release_source_fingerprint" in source
    assert "json.dumps({'fingerprint': fingerprint, 'fileCount': file_count})" in source
    assert 'json.dumps({"fingerprint": fingerprint, "fileCount": file_count})' not in source
    assert "sourceFingerprint" in source
    assert "sourceFileCount" in source
    assert "The release report fingerprint does not match the immutable release source." in source
    assert "checks.Count -ne 12" not in source
    assert "twelve-gate" not in source.lower()


def test_deployment_fingerprint_snippet_executes_in_windows_powershell_51() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    source = _source()
    snippet = source.split("$code = @'", 1)[1].split("'@", 1)[0].strip()
    python = str(Path(sys.executable)).replace("'", "''")
    command = f"$code = @'\n{snippet}\n'@\n& '{python}' -X utf8 -c $code"
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")

    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["fingerprint"]
    assert payload["fileCount"] > 0


def test_deployment_script_fences_data_and_preserves_the_protected_environment() -> None:
    source = _source()

    assert "Protect-SingYinSensitivePath -Path $environmentPath" in source
    assert "Get-SingYinAclStatus" in source
    assert "[IO.File]::ReadAllBytes($environmentPath)" in source
    assert "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)" in source
    assert "environmentProtected = $true" in source
    for setting in (
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET",
    ):
        assert f'"{setting}"' in source

    assert "Disable-ScheduledTask -TaskName $TaskName" in source
    assert "Stop-ScheduledTask -TaskName $TaskName" in source
    assert source.index("Stop-ScheduledTask -TaskName $TaskName") < source.index(
        "Disable-ScheduledTask -TaskName $TaskName"
    )
    assert "Wait-PortReleased -Port 8080" in source
    assert "scripts\\verify_formal_backup_restore.py" in source
    for proof in (
        "isolatedRestore",
        "fairnessBalanced",
        "rowCountsMatched",
        "restoreAuditAppended",
        "integrity",
        "sha256",
    ):
        assert proof in source
    assert "Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256" in source
    assert "[IO.Path]::GetFileName([string]$backupReport.snapshotFile)" in source


def test_deployment_script_consumes_only_a_protected_one_use_environment_overlay() -> None:
    source = _source()

    assert "$EnvironmentOverlayPath" in source
    assert "Read-EnvironmentOverlay" in source
    assert "Merge-EnvironmentOverlay" in source
    assert "Remove-EnvironmentOverlay -Path $resolvedOverlayPath" in source
    assert "} finally {" in source
    assert "Remove-EnvironmentOverlay -Path $overlayPathToDelete" in source
    assert (
        "^sing-yin-release-overlay-[A-Za-z0-9_-]{8,128}\\.env$"
        in source
    )
    assert "[IO.Path]::GetTempPath()" in source
    assert "The environment overlay must not be a reparse point." in source
    assert "The environment overlay exceeds the 64 KiB safety limit." in source
    assert "Get-SingYinAclStatus -Paths @($Path)" in source
    assert "Get-SingYinFileSystemAcl -Path $Path" in source
    assert '$broadSids = @("S-1-1-0", "S-1-5-11", "S-1-5-32-545")' in source
    assert "grants access to a broad Windows identity" in source
    assert "contains an unsupported setting" in source
    assert "contains a duplicate setting" in source
    assert "contains a malformed entry" in source
    assert "contains an unsafe or empty value" in source
    assert "does not contain any supported settings" in source
    assert "environmentOverlayApplied = $environmentOverlayApplied" in source
    assert "Write-Host $environmentOverlay" not in source
    assert "Write-Host $environmentValues" not in source

    allowed_block = source.split("function Read-EnvironmentOverlay", 1)[1].split(
        "$values = @{}", 1
    )[0]
    allowed_names = {
        line.strip().strip('",')
        for line in allowed_block.splitlines()
        if line.strip().startswith('"')
    }
    assert allowed_names == {
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET",
    }


def test_deployment_script_requires_gateway_principal_and_restores_overlay_state() -> None:
    source = _source()

    assert (
        'if ([string]$Values["SING_YIN_REQUIRE_GATEWAY_PRINCIPAL"] '
        "-notmatch '^(1|true)$')"
    ) in source
    assert "must be 1 or true for a controlled release" in source
    assert "$deployedEnvironmentBytes = [IO.File]::ReadAllBytes($environmentPath)" in source
    assert "ComputeHash($deployedEnvironmentBytes)" in source
    assert "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)" in source
    assert "$taskStopped -or $null -ne $environmentBytes" in source
    assert "$processEnvironmentSnapshot[$name]" in source
    assert '$processEnvironmentCaptured = $true' in source
    assert '[Environment]::SetEnvironmentVariable(' in source


def test_deployment_script_switches_locked_host_and_requires_write_readiness() -> None:
    source = _source()

    assert '"switch",' in source and '"--detach",' in source
    assert '"--require-hashes"' in source
    assert "scripts\\prepare_windows_host.ps1" in source
    assert "Get-SingYinTaskInspection" in source
    assert "Enable-ScheduledTask -TaskName $TaskName" in source
    assert "Start-ScheduledTask -TaskName $TaskName" in source
    assert "http://127.0.0.1:8080/healthz" in source
    assert "http://127.0.0.1:8080/readyz" in source
    assert '$ready.status -ceq "ready"' in source
    assert "$ready.writeReady -eq $true" in source
    assert "$ready.maintenance -eq $false" in source
    assert "$ready.recoveryRequired -eq $false" in source
    assert "[int]$ready.pendingBackupObligations -eq 0" in source
    assert "$ready.backupRepairFailed -eq $false" in source
    assert '"scripts\\check_deployment_readiness.py",' in source
    assert '"--strict"' in source


def test_deployment_script_rolls_back_commit_dependencies_environment_and_task() -> None:
    source = _source()
    catch_block = source.split("} catch {", 1)[1]

    assert '$rollbackAttempted = $true' in source
    assert '"switch",' in catch_block and "$previousCommit" in catch_block
    assert '"--require-hashes"' in catch_block
    assert "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)" in catch_block
    assert "Enable-ScheduledTask -TaskName $TaskName" in catch_block
    assert "Start-ScheduledTask -TaskName $TaskName" in catch_block
    assert "Wait-LoopbackHealth" in catch_block
    assert "rollbackSucceeded" in source
    assert "Protect-ReportText" in source
    assert "nativeLog = [IO.Path]::GetFileName" in source


def test_deployment_script_parses_in_windows_powershell_51() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped = str(SCRIPT).replace("'", "''")
    command = (
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
        "$tokens=$null; $errors=$null; "
        f"[void][System.Management.Automation.Language.Parser]::ParseFile('{escaped}',"
        "[ref]$tokens,[ref]$errors); "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { [Console]::Error.WriteLine($_.Message) }; exit 1 }"
    )
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=False,
    )

    assert result.returncode == 0, result.stderr
