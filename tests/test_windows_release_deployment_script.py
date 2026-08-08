from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "deploy_windows_release.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _powershell_function_source(name: str) -> str:
    source = _source()
    marker = f"function {name}"
    start = source.index(marker)
    next_function = re.search(
        r"(?m)^function\s+[A-Za-z0-9_-]+",
        source[start + len(marker) :],
    )
    if next_function is None:
        return source[start:]
    return source[start : start + len(marker) + next_function.start()]


def _run_required_boolean_contract() -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    function_source = _powershell_function_source("Test-RequiredBooleanProperty")
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
$payloads = @(
    '{{"sourceDirty":false}}',
    '{{"sourceDirty":true}}',
    '{{}}',
    '{{"sourceDirty":0}}',
    '{{"sourceDirty":1}}',
    '{{"sourceDirty":"false"}}',
    '{{"sourceDirty":null}}'
)
$results = @(
    foreach ($payload in $payloads) {{
        $candidate = $payload | ConvertFrom-Json
        [bool](Test-RequiredBooleanProperty -InputObject $candidate -Name "sourceDirty")
    }}
)
[ordered]@{{
    results = $results
    nullObject = [bool](Test-RequiredBooleanProperty -InputObject $null -Name "sourceDirty")
}} | ConvertTo-Json -Compress
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell Boolean validator emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _run_worker_gateway_parser(tmp_path: Path, configuration: str) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    configuration_path = tmp_path / "wrangler.jsonc"
    configuration_path.write_text(configuration, encoding="utf-8")
    escaped_path = str(configuration_path).replace("'", "''")
    function_source = _powershell_function_source("Get-WorkerGatewaySettings")
    python = str(Path(sys.executable)).replace("'", "''")
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
try {{
    $settings = Get-WorkerGatewaySettings -ConfigurationPath '{escaped_path}' -Python '{python}'
    [ordered]@{{
        ok = $true
        originPort = [int]$settings.OriginPort
        authEpoch = [long]$settings.AuthEpoch
        originPrincipalKid = [string]$settings.OriginPrincipalKid
    }} | ConvertTo-Json -Compress
}} catch {{
    [ordered]@{{
        ok = $false
        error = [string]$_.Exception.Message
    }} | ConvertTo-Json -Compress
}}
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell parser emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _run_bundle_fingerprint(bundle_path: Path) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped_path = str(bundle_path).replace("'", "''")
    function_source = _powershell_function_source(
        "Get-SingYinReleaseBundleFingerprint",
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
try {{
    $fingerprint = Get-SingYinReleaseBundleFingerprint -Path '{escaped_path}'
    [ordered]@{{
        ok = $true
        sha256 = [string]$fingerprint.Sha256
        fileCount = [int]$fingerprint.FileCount
    }} | ConvertTo-Json -Compress
}} catch {{
    [ordered]@{{
        ok = $false
        error = [string]$_.Exception.Message
    }} | ConvertTo-Json -Compress
}}
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell fingerprint emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _run_previous_release_identity(
    repository: Path,
    host_root: Path,
    task_working_directory: Path,
    expected_environment_hash: str,
) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped_repository = str(repository).replace("'", "''")
    escaped_host = str(host_root).replace("'", "''")
    escaped_working_directory = str(task_working_directory).replace("'", "''")
    function_source = "\n".join(
        (
            _powershell_function_source("Get-GitValue"),
            _powershell_function_source("Assert-ImmutableReleaseTag"),
            _powershell_function_source("Assert-SafeReleaseBundlePath"),
            _powershell_function_source("Get-SingYinReleaseBundleFingerprint"),
            _powershell_function_source(
                "Get-SingYinLegacyReleaseBundleFingerprint",
            ),
            _powershell_function_source("Get-SingYinPreviousReleaseIdentity"),
        )
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
try {{
    $identity = Get-SingYinPreviousReleaseIdentity `
        -Repository '{escaped_repository}' `
        -HostRoot '{escaped_host}' `
        -TaskWorkingDirectory '{escaped_working_directory}' `
        -ExpectedEnvironmentHash '{expected_environment_hash}'
    ConvertTo-Json -InputObject ([ordered]@{{
        ok = $true
        commit = [string]$identity.Commit
        releaseRef = [string]$identity.ReleaseRef
        source = [string]$identity.Source
        bundle = [string]$identity.Bundle
        repairCount = [int]$identity.RepairCount
        pendingNiceGuiStorage = @($identity.PendingNiceGuiStorageRelativePaths)
    }}) -Compress
}} catch {{
    ConvertTo-Json -InputObject ([ordered]@{{
        ok = $false
        error = [string]$_.Exception.Message
    }}) -Compress
}}
"""
    command_path = repository.parent / "previous-release-identity-test.ps1"
    command_path.write_text(command, encoding="utf-8-sig")
    try:
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(command_path),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
        )
    finally:
        command_path.unlink(missing_ok=True)

    assert result.returncode == 0, result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell identity check emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _run_legacy_nicegui_storage_migration(
    bundle: Path,
    host_root: Path,
    relative_paths: list[str],
    expected_sha256: str,
    expected_file_count: int,
) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped_bundle = str(bundle).replace("'", "''")
    escaped_host = str(host_root).replace("'", "''")
    paths = ", ".join(
        "'{}'".format(value.replace("'", "''")) for value in relative_paths
    )
    function_source = "\n".join(
        (
            _powershell_function_source("Get-SingYinFileSha256"),
            _powershell_function_source("Get-SingYinReleaseBundleFingerprint"),
            _powershell_function_source("Move-SingYinLegacyNiceGuiStorage"),
        )
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
function Protect-SingYinSensitivePath {{ param([string]$Path, [string]$RuntimeUser) }}
{function_source}
try {{
    $result = Move-SingYinLegacyNiceGuiStorage `
        -BundlePath '{escaped_bundle}' `
        -RelativePaths @({paths}) `
        -HostRoot '{escaped_host}' `
        -RuntimeUser 'test-runtime' `
        -ExpectedBundleSha256 '{expected_sha256}' `
        -ExpectedBundleFileCount {expected_file_count}
    [ordered]@{{
        ok = $true
        migratedCount = [int]$result.MigratedCount
        storageRoot = [string]$result.StorageRoot
    }} | ConvertTo-Json -Compress
}} catch {{
    [ordered]@{{
        ok = $false
        error = [string]$_.Exception.Message
    }} | ConvertTo-Json -Compress
}}
"""
    command_path = host_root.parent / "legacy-nicegui-migration-test.ps1"
    command_path.write_text(command, encoding="utf-8-sig")
    try:
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(command_path),
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
        )
    finally:
        command_path.unlink(missing_ok=True)
    assert result.returncode == 0, result.stdout + result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell migration emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _run_stopped_nicegui_storage_scan(
    bundle: Path,
    marker_created_at: datetime,
) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped_bundle = str(bundle).replace("'", "''")
    escaped_created_at = marker_created_at.isoformat().replace("'", "''")
    function_source = _powershell_function_source(
        "Get-SingYinStoppedNiceGuiStoragePaths",
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
try {{
    $paths = @(
        Get-SingYinStoppedNiceGuiStoragePaths `
            -BundlePath '{escaped_bundle}' `
            -MarkerCreatedAt ([DateTimeOffset]::Parse('{escaped_created_at}'))
    )
    [ordered]@{{
        ok = $true
        paths = $paths
    }} | ConvertTo-Json -Compress
}} catch {{
    [ordered]@{{
        ok = $false
        error = [string]$_.Exception.Message
    }} | ConvertTo-Json -Compress
}}
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    assert json_lines, f"PowerShell stopped-storage scan emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _create_trusted_release_bundle(
    tmp_path: Path,
) -> tuple[Path, Path, Path, dict[str, object], str]:
    repository = tmp_path / "repository"
    remote = tmp_path / "remote.git"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "config", "user.email", "release-test@example.invalid")
    (repository / "app.py").write_text("print('release')\n", encoding="utf-8")
    _git(repository, "add", "app.py")
    _git(repository, "commit", "-m", "Create trusted release")
    release_ref = "v1.2.0-rc.41"
    _git(repository, "tag", "-a", release_ref, "-m", "Trusted release")
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "main", "--tags")

    commit = _git(repository, "rev-parse", f"refs/tags/{release_ref}^{{commit}}")
    source_tree = _git(repository, "rev-parse", f"{commit}^{{tree}}")
    environment_bytes = b"SING_YIN_APP_MODE=official\r\n"
    environment_hash = hashlib.sha256(environment_bytes).hexdigest()
    host_root = tmp_path / "host"
    host_root.mkdir()
    (host_root / ".env").write_bytes(environment_bytes)
    bundle = (
        host_root
        / "releases"
        / f"{release_ref}-{commit[:12]}-{environment_hash[:12]}"
    )
    bundle.mkdir(parents=True)
    app = bundle / "app.py"
    app.write_text("print('release')\n", encoding="utf-8")
    fingerprint = _run_bundle_fingerprint(bundle)
    marker: dict[str, object] = {
        "schemaVersion": 2,
        "releaseRef": release_ref,
        "commit": commit,
        "sourceTree": source_tree,
        "environmentSha256": environment_hash,
        "bundleContentSha256": fingerprint["sha256"],
        "bundleFileCount": fingerprint["fileCount"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )
    return repository, host_root, bundle, marker, environment_hash


def _prepare_legacy_bytecode_marker(
    bundle: Path,
    marker: dict[str, object],
) -> datetime:
    cache = bundle / "package" / "__pycache__"
    cache.mkdir(parents=True, exist_ok=True)
    original_bytecode = cache / "module.cpython-312.pyc"
    original_bytecode.write_bytes(b"bytecode present when legacy marker was made")

    marker_created_at = datetime.now(timezone.utc)
    old_timestamp = (marker_created_at - timedelta(minutes=2)).timestamp()
    os.utime(original_bytecode, (old_timestamp, old_timestamp))
    legacy_fingerprint = _run_bundle_fingerprint(bundle)
    marker["bundleContentSha256"] = legacy_fingerprint["sha256"]
    marker["bundleFileCount"] = legacy_fingerprint["fileCount"]
    marker["createdAt"] = marker_created_at.isoformat()
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )
    return marker_created_at


def _worker_configuration(
    *,
    port: str = "8080",
    auth_epoch: str = "31",
    kid: str = '"rc31-origin"',
    extra_properties: str = "",
) -> str:
    return f"""{{
  // JSONC comments are valid outside active property lines.
  "vars": {{
    "ORIGIN_PORT": {port},
    "AUTH_EPOCH": {auth_epoch},
    "ORIGIN_PRINCIPAL_KID": {kid}{extra_properties}
  }}
}}
"""


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


def test_deployment_script_derives_its_default_source_from_its_own_checkout() -> None:
    source = _source()
    parameter_block = source.split("$ErrorActionPreference", 1)[0]

    assert '[string]$SourceRoot = ""' in parameter_block
    assert 'D:\\code_v3' not in parameter_block
    assert 'if ([string]::IsNullOrWhiteSpace($SourceRoot))' in source
    assert '$SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))' in source
    assert "Operators may still pass -SourceRoot" in source


def test_deployment_script_refreshes_origin_main_before_ancestor_checks() -> None:
    source = _source()
    explicit_refspec = '"+refs/heads/main:refs/remotes/origin/main"'
    source_ancestor_check = "merge-base --is-ancestor $releaseCommit origin/main"

    first_fetch = source.index(explicit_refspec)

    assert source.count(explicit_refspec) == 1
    assert first_fetch < source.index(source_ancestor_check)
    assert "$hostReleaseCommit" not in source
    assert '"origin",\n        "main"' not in source


def test_deployment_script_requires_the_current_release_gate_fingerprint() -> None:
    source = _source()
    required_checks = (
        "repository_hygiene",
        "security_gates",
        "cloudflare_gateway_tests",
        "motion_state_machine_tests",
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
        "rc31_theme_control_browser",
    )

    for check in required_checks:
        assert f'"{check}"' in source
    assert "$requiredCheckCount = $requiredChecks.Count" in source
    assert "$reportChecks.Count -ne $requiredCheckCount" in source
    assert "$passedNames.Count -ne $requiredCheckCount" in source
    assert "releaseChecksPassed = $requiredCheckCount" in source
    assert "release_source_fingerprint" in source
    assert "json.dumps({'fingerprint': fingerprint, 'fileCount': file_count})" in source
    assert 'json.dumps({"fingerprint": fingerprint, "fileCount": file_count})' not in source
    assert "sourceFingerprint" in source
    assert "sourceFileCount" in source
    assert "[int]$releaseReport.schemaVersion -ne 3" in source
    assert "$postVerificationSource = $releaseReport.postVerificationSource" in source
    assert "[string]$postVerificationSource.sourceFingerprint -cne [string]$releaseReport.sourceFingerprint" in source
    assert "[int]$postVerificationSource.sourceFileCount -ne [int]$releaseReport.sourceFileCount" in source
    assert "[string]$postVerificationSource.sourceCommit -cne [string]$releaseReport.sourceCommit" in source
    assert "[string]$postVerificationSource.sourceTree -cne [string]$releaseReport.sourceTree" in source
    assert "-not $releaseSourceDirtyIsBoolean" in source
    assert "-not $postSourceDirtyIsBoolean" in source
    assert "[bool]$postVerificationSource.sourceDirty" in source
    assert "The release report fingerprint does not match the immutable release source." in source
    assert "checks.Count -ne 12" not in source
    assert "twelve-gate" not in source.lower()


def test_deployment_script_rejects_missing_or_non_boolean_dirty_state() -> None:
    result = _run_required_boolean_contract()

    assert result == {
        "results": [True, True, False, False, False, False, False],
        "nullObject": False,
    }


def test_deployment_script_compares_release_gate_identities_without_order_semantics() -> None:
    source = _source()

    assert "$reportIdentityDifferences = @(" in source
    assert "-ReferenceObject @($requiredChecks | Sort-Object)" in source
    assert "-DifferenceObject @($reportRequiredChecks | Sort-Object)" in source
    assert "$reportIdentityDifferences.Count -ne 0" in source
    assert "-SyncWindow 0" not in source


def test_deployment_script_requires_worker_and_host_gateway_settings_to_match() -> None:
    source = _source()

    assert "function Get-WorkerGatewaySettings" in source
    assert "gateway settings do not support block comments" in source
    assert "function Assert-WorkerHostGatewayParity" in source

    preflight = source.index("$preflightGatewayParity = Assert-WorkerHostGatewayParity")
    host_clean = source.index(
        '$hostStatus = Get-GitValue -Repository $HostRoot -Arguments @(',
    )
    protect = source.index(
        "Protect-SingYinSensitivePath -Path $environmentPath",
        preflight,
    )
    merge = source.index("Merge-EnvironmentOverlay", preflight)
    post_apply = source.index(
        "$postApplyGatewayParity = Assert-WorkerHostGatewayParity",
        preflight,
    )
    stop = source.index('Write-Step "Stopping the owned task', preflight)

    assert source.count("Assert-WorkerHostGatewayParity `") == 2
    assert host_clean < preflight < protect < merge < post_apply < stop
    assert source.index(
        'throw "The installed host repository is not clean."',
        host_clean,
    ) < preflight
    host_status_block = source[host_clean:preflight]
    assert (
        '"--untracked-files=all",\n'
        '        "--",\n'
        '        ".",\n'
        '        ":(exclude)releases/**"'
    ) in host_status_block
    assert "function Get-SingYinReleaseBundleFingerprint" in source
    assert 'throw "The release bundle contains an unsupported reparse point."' in source
    assert "bundleContentSha256" in source
    assert "bundleFileCount" in source
    assert "[int]$marker.schemaVersion -ne 2" in source
    assert "[string]$marker.sourceTree -cne $sourceTree" in source
    assert source.index("$overlayPathToDelete = $resolvedOverlayPath") > preflight
    assert source.index("$environmentBytes = [IO.File]::ReadAllBytes", preflight) > preflight
    assert "workerOriginPort = $workerOriginPort" in source
    assert "hostAuthEpoch = $hostAuthEpoch" in source
    assert "workerAuthEpoch = $workerAuthEpoch" in source
    assert "hostOriginPrincipalKid = $hostOriginPrincipalKid" in source
    assert "workerOriginPrincipalKid = $workerOriginPrincipalKid" in source
    assert "preflightMatched = [bool]$preflightGatewayParity.Matches" in source
    assert "postApplyMatched = [bool]$postApplyGatewayParity.Matches" in source


def test_release_bundle_fingerprint_detects_content_changes_and_ignores_marker(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    nested = bundle / "nested"
    nested.mkdir(parents=True)
    (bundle / "app.py").write_text("print('first')\n", encoding="utf-8")
    (nested / "data.txt").write_text("stable\n", encoding="utf-8")

    first = _run_bundle_fingerprint(bundle)
    assert first["ok"] is True
    assert first["fileCount"] == 2
    assert re.fullmatch(r"[0-9a-f]{64}", str(first["sha256"]))

    (bundle / ".sing-yin-release.json").write_text("{}\n", encoding="utf-8")
    marker_only = _run_bundle_fingerprint(bundle)
    assert marker_only == first

    (bundle / "app.py").write_text("print('changed')\n", encoding="utf-8")
    changed = _run_bundle_fingerprint(bundle)
    assert changed["ok"] is True
    assert changed["fileCount"] == 2
    assert changed["sha256"] != first["sha256"]


def test_release_bundle_fingerprint_keeps_python_bytecode_in_integrity_scope(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    cache = bundle / "package" / "__pycache__"
    cache.mkdir(parents=True)
    (bundle / "app.py").write_text("print('stable')\n", encoding="utf-8")

    baseline = _run_bundle_fingerprint(bundle)
    (cache / "module.cpython-312.pyc").write_bytes(b"runtime bytecode")
    with_bytecode = _run_bundle_fingerprint(bundle)

    assert with_bytecode["fileCount"] == baseline["fileCount"] + 1
    assert with_bytecode["sha256"] != baseline["sha256"]

    (bundle / "module.pyc").write_bytes(b"not in __pycache__")
    outside_cache = _run_bundle_fingerprint(bundle)
    assert outside_cache["fileCount"] == baseline["fileCount"] + 2
    assert outside_cache["sha256"] != with_bytecode["sha256"]


def test_previous_release_identity_comes_from_verified_task_bundle(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity == {
        "ok": True,
        "commit": marker["commit"],
        "releaseRef": marker["releaseRef"],
        "source": "immutable-release-marker",
        "bundle": str(bundle),
        "repairCount": 0,
        "pendingNiceGuiStorage": [],
    }


def test_previous_release_identity_accepts_exact_legacy_runtime_bytecode_delta(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    marker_created_at = _prepare_legacy_bytecode_marker(bundle, marker)

    cache = bundle / "package" / "__pycache__"
    runtime_bytecode = cache / "runtime.cpython-312.pyc"
    runtime_bytecode.write_bytes(b"bytecode generated after application start")
    new_timestamp = (marker_created_at + timedelta(minutes=2)).timestamp()
    os.utime(runtime_bytecode, (new_timestamp, new_timestamp))

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity == {
        "ok": True,
        "commit": marker["commit"],
        "releaseRef": marker["releaseRef"],
        "source": "immutable-release-marker-legacy-bytecode-repaired",
        "bundle": str(bundle),
        "repairCount": 1,
        "pendingNiceGuiStorage": [],
    }
    assert not runtime_bytecode.exists()
    repaired_fingerprint = _run_bundle_fingerprint(bundle)
    assert repaired_fingerprint["sha256"] == marker["bundleContentSha256"]
    assert repaired_fingerprint["fileCount"] == marker["bundleFileCount"]


def test_previous_release_identity_defers_and_migrates_exact_nicegui_preference_delta(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    relative_path = (
        ".nicegui/storage-user-f32cba68-43d0-4d27-b84c-3cec7b584a99.json"
    )
    preference = bundle / Path(relative_path)
    preference.parent.mkdir(parents=True)
    preference.write_text('{"theme":"dark","sound":true}', encoding="utf-8")
    marker_created_at = datetime.fromisoformat(str(marker["createdAt"]))
    new_timestamp = (marker_created_at + timedelta(minutes=2)).timestamp()
    os.utime(preference, (new_timestamp, new_timestamp))

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity == {
        "ok": True,
        "commit": marker["commit"],
        "releaseRef": marker["releaseRef"],
        "source": "immutable-release-marker-legacy-nicegui-storage-pending",
        "bundle": str(bundle),
        "repairCount": 0,
        "pendingNiceGuiStorage": [relative_path],
    }
    assert preference.exists(), "a serving process may still be writing this file"

    migration = _run_legacy_nicegui_storage_migration(
        bundle,
        host_root,
        [relative_path],
        str(marker["bundleContentSha256"]),
        int(marker["bundleFileCount"]),
    )

    destination = host_root / "data" / "runtime" / "nicegui-storage" / preference.name
    assert migration == {
        "ok": True,
        "migratedCount": 1,
        "storageRoot": str(destination.parent),
    }
    assert not preference.exists()
    assert json.loads(destination.read_text(encoding="utf-8")) == {
        "theme": "dark",
        "sound": True,
    }
    repaired_fingerprint = _run_bundle_fingerprint(bundle)
    assert repaired_fingerprint["sha256"] == marker["bundleContentSha256"]
    assert repaired_fingerprint["fileCount"] == marker["bundleFileCount"]


def test_stopped_nicegui_scan_discovers_only_fresh_flat_preference_files(
    tmp_path: Path,
) -> None:
    _, _, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    relative_paths = [
        ".nicegui/storage-general.json",
        ".nicegui/storage-user-f32cba68-43d0-4d27-b84c-3cec7b584a99.json",
    ]
    marker_created_at = datetime.fromisoformat(str(marker["createdAt"]))
    new_timestamp = (marker_created_at + timedelta(minutes=2)).timestamp()
    for relative_path in relative_paths:
        preference = bundle / Path(relative_path)
        preference.parent.mkdir(parents=True, exist_ok=True)
        preference.write_text('{"sound":true}', encoding="utf-8")
        os.utime(preference, (new_timestamp, new_timestamp))

    result = _run_stopped_nicegui_storage_scan(bundle, marker_created_at)

    assert result == {"ok": True, "paths": relative_paths}


@pytest.mark.parametrize(
    ("relative_path", "content_size", "timestamp_offset_minutes"),
    (
        (".nicegui/storage-user-invalid.json", 2, 2),
        (".nicegui/nested/storage-general.json", 2, 2),
        (".nicegui/storage-general.json", 2, -2),
        (".nicegui/storage-general.json", 65537, 2),
    ),
    ids=("invalid-name", "nested-path", "pre-marker", "oversize"),
)
def test_stopped_nicegui_scan_rejects_unbounded_or_pre_marker_content(
    tmp_path: Path,
    relative_path: str,
    content_size: int,
    timestamp_offset_minutes: int,
) -> None:
    _, _, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    marker_created_at = datetime.fromisoformat(str(marker["createdAt"]))
    candidate = bundle / Path(relative_path)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_bytes(b"x" * content_size)
    candidate_timestamp = (
        marker_created_at + timedelta(minutes=timestamp_offset_minutes)
    ).timestamp()
    os.utime(candidate, (candidate_timestamp, candidate_timestamp))

    result = _run_stopped_nicegui_storage_scan(bundle, marker_created_at)

    assert result["ok"] is False
    assert "NiceGUI storage" in str(result["error"])


def test_legacy_nicegui_migration_rejects_non_object_json(
    tmp_path: Path,
) -> None:
    _, host_root, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    relative_path = (
        ".nicegui/storage-user-f32cba68-43d0-4d27-b84c-3cec7b584a99.json"
    )
    preference = bundle / Path(relative_path)
    preference.parent.mkdir(parents=True)
    preference.write_text("[]", encoding="utf-8")

    migration = _run_legacy_nicegui_storage_migration(
        bundle,
        host_root,
        [relative_path],
        str(marker["bundleContentSha256"]),
        int(marker["bundleFileCount"]),
    )

    assert migration["ok"] is False
    assert "not a JSON object" in str(migration["error"])
    assert preference.exists()


def test_legacy_nicegui_migration_validates_all_files_before_mutation(
    tmp_path: Path,
) -> None:
    _, host_root, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    relative_paths = [
        ".nicegui/storage-general.json",
        ".nicegui/storage-user-f32cba68-43d0-4d27-b84c-3cec7b584a99.json",
    ]
    first = bundle / Path(relative_paths[0])
    second = bundle / Path(relative_paths[1])
    first.parent.mkdir(parents=True)
    first.write_text('{"theme":"dark"}', encoding="utf-8")
    second.write_text("[]", encoding="utf-8")

    migration = _run_legacy_nicegui_storage_migration(
        bundle,
        host_root,
        relative_paths,
        str(marker["bundleContentSha256"]),
        int(marker["bundleFileCount"]),
    )

    destination_root = host_root / "data" / "runtime" / "nicegui-storage"
    assert migration["ok"] is False
    assert "not a JSON object" in str(migration["error"])
    assert first.exists()
    assert second.exists()
    assert not (destination_root / first.name).exists()


def test_legacy_nicegui_migration_refuses_a_different_existing_destination(
    tmp_path: Path,
) -> None:
    _, host_root, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    relative_path = ".nicegui/storage-general.json"
    source = bundle / Path(relative_path)
    source.parent.mkdir(parents=True)
    source.write_text('{"theme":"dark"}', encoding="utf-8")
    destination = (
        host_root / "data" / "runtime" / "nicegui-storage" / source.name
    )
    destination.parent.mkdir(parents=True)
    destination.write_text('{"theme":"light"}', encoding="utf-8")

    migration = _run_legacy_nicegui_storage_migration(
        bundle,
        host_root,
        [relative_path],
        str(marker["bundleContentSha256"]),
        int(marker["bundleFileCount"]),
    )

    assert migration["ok"] is False
    assert "already contains different data" in str(migration["error"])
    assert source.exists()
    assert destination.read_text(encoding="utf-8") == '{"theme":"light"}'


def test_legacy_nicegui_migration_reconciles_an_identical_existing_destination(
    tmp_path: Path,
) -> None:
    _, host_root, bundle, marker, _ = _create_trusted_release_bundle(tmp_path)
    relative_path = ".nicegui/storage-general.json"
    source = bundle / Path(relative_path)
    source.parent.mkdir(parents=True)
    content = '{"theme":"dark"}'
    source.write_text(content, encoding="utf-8")
    destination = (
        host_root / "data" / "runtime" / "nicegui-storage" / source.name
    )
    destination.parent.mkdir(parents=True)
    destination.write_text(content, encoding="utf-8")

    migration = _run_legacy_nicegui_storage_migration(
        bundle,
        host_root,
        [relative_path],
        str(marker["bundleContentSha256"]),
        int(marker["bundleFileCount"]),
    )

    assert migration["ok"] is True
    assert migration["migratedCount"] == 1
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == content
    repaired_fingerprint = _run_bundle_fingerprint(bundle)
    assert repaired_fingerprint["sha256"] == marker["bundleContentSha256"]
    assert repaired_fingerprint["fileCount"] == marker["bundleFileCount"]


@pytest.mark.parametrize(
    ("relative_path", "timestamp_offset_minutes"),
    (
        ("unexpected.txt", 2),
        ("package/runtime.pyc", 2),
        ("package/__pycache__/preexisting.cpython-312.pyc", -2),
        (".nicegui/storage-user-invalid.json", 2),
    ),
)
def test_previous_release_identity_rejects_non_runtime_legacy_delta(
    tmp_path: Path,
    relative_path: str,
    timestamp_offset_minutes: int,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    marker_created_at = _prepare_legacy_bytecode_marker(bundle, marker)

    extra = bundle / relative_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"untrusted delta")
    timestamp = (
        marker_created_at + timedelta(minutes=timestamp_offset_minutes)
    ).timestamp()
    os.utime(extra, (timestamp, timestamp))

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity["ok"] is False
    assert "identity marker is invalid or stale" in str(identity["error"])


def test_previous_release_identity_rejects_a_tampered_task_bundle(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, _, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    app = bundle / "app.py"
    app.write_text("print('tampered')\n", encoding="utf-8")

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity["ok"] is False
    assert "identity marker is invalid or stale" in str(identity["error"])


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("releaseRef", "v1.2.0-rc.40"),
        ("commit", "a" * 40),
        ("sourceTree", "b" * 40),
        ("environmentSha256", "c" * 64),
        ("createdAt", "not-a-timestamp"),
    ),
)
def test_previous_release_identity_rejects_marker_identity_tampering(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    marker[field] = replacement
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity["ok"] is False


def test_previous_release_identity_rejects_missing_marker_timestamp_cleanly(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, marker, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    del marker["createdAt"]
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )

    identity = _run_previous_release_identity(
        repository,
        host_root,
        bundle,
        environment_hash,
    )

    assert identity["ok"] is False
    assert identity["error"] == (
        "The startup task release bundle identity marker is invalid or stale."
    )


def test_previous_release_identity_rejects_a_renamed_release_bundle(
    tmp_path: Path,
) -> None:
    repository, host_root, bundle, _, environment_hash = (
        _create_trusted_release_bundle(tmp_path)
    )
    renamed_bundle = bundle.with_name(f"{bundle.name}-renamed")
    bundle.rename(renamed_bundle)

    identity = _run_previous_release_identity(
        repository,
        host_root,
        renamed_bundle,
        environment_hash,
    )

    assert identity["ok"] is False
    assert "trusted tag or environment evidence" in str(identity["error"])


def test_deployment_reports_previous_identity_from_the_task_target() -> None:
    source = _source()
    assignment = source.index(
        "$previousReleaseIdentity = Get-SingYinPreviousReleaseIdentity",
    )
    task_capture = source.index("$previousTaskAction = [pscustomobject]@{")

    assert task_capture < assignment
    assert "-Repository $SourceRoot" in source[assignment : assignment + 500]
    assert "-TaskWorkingDirectory $previousTaskAction.WorkingDirectory" in source
    assert "-ExpectedEnvironmentHash $previousEnvironmentHash" in source
    assert "$trustedCommit = Assert-ImmutableReleaseTag" in source
    assert '[string]$marker.sourceTree -cne $trustedTree' in source
    assert (
        '[string]$marker.environmentSha256 -cne $ExpectedEnvironmentHash'
        in source
    )
    assert '[IO.Path]::GetFileName($bundlePath) -cne $expectedBundleLeaf' in source
    assert "$previousCommit = [string]$previousReleaseIdentity.Commit" in source
    assert "previousReleaseRef = $previousReleaseRef" in source
    assert "previousReleaseSource = $previousReleaseSource" in source
    assert "previousReleaseRepairCount = $previousReleaseRepairCount" in source
    legacy_checkout_probe = (
        '$previousCommit = Get-GitValue -Repository $HostRoot '
        '-Arguments @("rev-parse", "HEAD")'
    )
    assert legacy_checkout_probe not in source
    assert '-Argument "-B -X utf8 -m nicegui_app.launcher"' in source
    assert '"immutable-release-marker-legacy-bytecode-repaired"' in source
    assert '"immutable-release-marker-legacy-nicegui-storage-pending"' in source
    assert '"immutable-release-marker-legacy-nicegui-storage-migrated"' in source
    assert "Get-SingYinLegacyReleaseBundleFingerprint" in source
    assert "Get-SingYinStoppedNiceGuiStoragePaths" in source
    assert "Move-SingYinLegacyNiceGuiStorage" in source
    assert "Remove-Item -LiteralPath $candidatePath -Force" in source
    stop = source.index("Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 30")
    scan = source.index("Get-SingYinStoppedNiceGuiStoragePaths", stop)
    migrate = source.index("$migration = Move-SingYinLegacyNiceGuiStorage")
    backup = source.index(
        'Write-Step "Creating a previous-schema rollback snapshot',
        migrate,
    )
    assert stop < scan < migrate < backup
    assert "$stoppedReleaseIdentity" not in source
    assert "$reconciledReleaseIdentity" not in source
    assert "legacyNiceGuiStorageMigration = [ordered]@{" in source


def test_deployment_rejects_legacy_or_missing_previous_bundle_before_path_use() -> None:
    source = _source()
    identity = source.index(
        "$previousReleaseIdentity = Get-SingYinPreviousReleaseIdentity",
    )
    guard = source.index(
        '[string]$previousReleaseIdentity.Source -ceq "legacy-host-checkout"',
        identity,
    )
    first_bundle_join = source.index("Join-Path $previousBundlePath", identity)
    guard_block = source[guard:first_bundle_join]

    assert identity < guard < first_bundle_join
    assert (
        "[string]::IsNullOrWhiteSpace("
        "[string]$previousReleaseIdentity.Bundle"
        ")"
    ) in guard_block
    assert "Establish and verify an immutable release baseline" in guard_block
    assert "$previousBundlePath = [string]$previousReleaseIdentity.Bundle" in guard_block
    assert source.count(
        "$previousBundlePath = [string]$previousReleaseIdentity.Bundle"
    ) == 1


def test_deployment_rotates_runtime_task_credential_without_persisting_it() -> None:
    source = _source()

    assert "function New-SingYinRuntimeTaskPassword" in source
    assert '[ValidateRange(32, 96)][int]$Length = 48' in source
    assert '$null = $builder.Append("Aa1!")' in source
    assert "[Array]::Clear($randomBytes, 0, $randomBytes.Length)" in source
    assert "Set-LocalUser `" in source
    assert "-Password $runtimeTaskSecurePassword" in source
    assert source.count("$runtimeTaskSecurePassword.Dispose()") == 2
    assert source.count("$runtimeTaskSecurePassword = $null") == 3
    assert "-Password $runtimeTaskPassword | Out-Null" in source
    assert "$taskCredentialRotated = $true" in source
    assert "($taskTargetSwitched -or $taskCredentialRotated)" in source
    assert "$restoreTaskParameters.Password = $runtimeTaskPassword" in source
    assert "$runtimeTaskPassword = $null" in source
    assert "taskCredentialRotated = $taskCredentialRotated" in source


def test_runtime_task_password_generator_produces_distinct_complex_values() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    function_source = _powershell_function_source("New-SingYinRuntimeTaskPassword")
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
$first = New-SingYinRuntimeTaskPassword
$second = New-SingYinRuntimeTaskPassword
[ordered]@{{
    firstLength = $first.Length
    secondLength = $second.Length
    hasUpper = [bool]($first -cmatch '[A-Z]')
    hasLower = [bool]($first -cmatch '[a-z]')
    hasDigit = [bool]($first -match '[0-9]')
    hasSpecial = [bool]($first -match '[!_-]')
    distinct = [bool]($first -cne $second)
}} | ConvertTo-Json -Compress
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload == {
        "firstLength": 48,
        "secondLength": 48,
        "hasUpper": True,
        "hasLower": True,
        "hasDigit": True,
        "hasSpecial": True,
        "distinct": True,
    }


def test_worker_gateway_parser_accepts_active_jsonc_and_ignores_line_comments(
    tmp_path: Path,
) -> None:
    payload = _run_worker_gateway_parser(
        tmp_path,
        """{
  "documentation": "https://developers.cloudflare.com/workers/",
  "vars": {
    // "ORIGIN_PORT": 9999,
    "ORIGIN_PORT": 8080, // active origin port
    // "AUTH_EPOCH": 999,
    "AUTH_EPOCH": 31,
    // "ORIGIN_PRINCIPAL_KID": "commented-out",
    "ORIGIN_PRINCIPAL_KID": "rc31-origin", // active key id
  },
}
""",
    )

    assert payload == {
        "ok": True,
        "originPort": 8080,
        "authEpoch": 31,
        "originPrincipalKid": "rc31-origin",
    }


@pytest.mark.parametrize(
    ("configuration", "message"),
    (
        (
            _worker_configuration(port="80"),
            "ORIGIN_PORT must be between 1024 and 65535",
        ),
        (
            _worker_configuration(port="999999999999999999999999"),
            "ORIGIN_PORT must be between 1024 and 65535",
        ),
        (
            _worker_configuration(auth_epoch="999999999999999999999999"),
            "AUTH_EPOCH must be between 0 and 9223372036854775807",
        ),
        (
            _worker_configuration(port='"8080"'),
            "top-level vars must define one integer ORIGIN_PORT",
        ),
        (
            _worker_configuration(auth_epoch='"31"'),
            "top-level vars must define one integer AUTH_EPOCH",
        ),
        (
            _worker_configuration(auth_epoch="-1"),
            "AUTH_EPOCH must be between 0 and 9223372036854775807",
        ),
        (
            _worker_configuration(kid='"bad kid"'),
            "ORIGIN_PRINCIPAL_KID contains unsupported characters",
        ),
        (
            _worker_configuration(kid=f'"{"a" * 65}"'),
            "ORIGIN_PRINCIPAL_KID contains unsupported characters",
        ),
        (
            _worker_configuration(kid='"rc31-origin" trailing-garbage'),
            "is not valid JSONC",
        ),
        (
            """{
  "vars": {
    "ORIGIN_PORT": 8080,
    "ORIGIN_PORT": 8081,
    "AUTH_EPOCH": 31,
    "ORIGIN_PRINCIPAL_KID": "rc31-origin"
  }
}
""",
            "contains duplicate JSON object keys",
        ),
        (
            """{
  "vars": {
    "ORIGIN_PORT": 8080,
    "AUTH_EPOCH": 31
  }
}
""",
            "must define one string ORIGIN_PRINCIPAL_KID",
        ),
        (
            """{
  /* ambiguous block comments are rejected before extracting gateway identity */
  "vars": {
    "ORIGIN_PORT": 8080,
    "AUTH_EPOCH": 31,
    "ORIGIN_PRINCIPAL_KID": "rc31-origin"
  }
}
""",
            "do not support block comments",
        ),
        (
            """not-json
"ORIGIN_PORT": 8080
"AUTH_EPOCH": 31
"ORIGIN_PRINCIPAL_KID": "rc31-origin"
""",
            "is not valid JSONC",
        ),
        (
            """{
  "unrelated": {
    "ORIGIN_PORT": 8080,
    "AUTH_EPOCH": 31,
    "ORIGIN_PRINCIPAL_KID": "rc31-origin"
  },
  "vars": {"OTHER": "value"}
}
""",
            "top-level vars must define one integer ORIGIN_PORT",
        ),
        (
            """{
  "vars": "ORIGIN_PORT=8080;AUTH_EPOCH=31;ORIGIN_PRINCIPAL_KID=rc31-origin"
}
""",
            "must define exactly one top-level vars object",
        ),
        (
            """{
  "other": true
}
""",
            "must define exactly one top-level vars object",
        ),
    ),
)
def test_worker_gateway_parser_rejects_ambiguous_or_unsafe_values(
    tmp_path: Path,
    configuration: str,
    message: str,
) -> None:
    payload = _run_worker_gateway_parser(tmp_path, configuration)

    assert payload["ok"] is False
    assert message in str(payload["error"])


def test_worker_host_gateway_parity_executes_and_rejects_each_mismatch() -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    functions = "\n".join(
        (
            _powershell_function_source("Assert-UnifiedGuestHostSettings"),
            _powershell_function_source("Assert-WorkerHostGatewayParity"),
        )
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{functions}
$values = @{{
    SING_YIN_UNIFIED_GUEST = '1'
    SING_YIN_REQUIRE_GATEWAY_PRINCIPAL = '1'
    ORIGIN_PRINCIPAL_SECRET = 'not-a-real-secret'
    ORIGIN_PRINCIPAL_KID = 'rc31-origin'
    AUTH_EPOCH = '31'
    SING_YIN_GUEST_SNAPSHOT_SECRET = 'not-a-real-snapshot-secret'
    SING_YIN_HOST = '127.0.0.1'
    SING_YIN_PORT = '8080'
}}
$worker = [pscustomobject]@{{
    OriginPort = 8080
    AuthEpoch = [long]31
    OriginPrincipalKid = 'rc31-origin'
}}
$result = [ordered]@{{}}
$result.match = [bool](Assert-WorkerHostGatewayParity -Values $values -WorkerSettings $worker).Matches
foreach ($case in @('port', 'epoch', 'kid')) {{
    $candidate = [pscustomobject]@{{
        OriginPort = if ($case -ceq 'port') {{ 8081 }} else {{ 8080 }}
        AuthEpoch = if ($case -ceq 'epoch') {{ [long]32 }} else {{ [long]31 }}
        OriginPrincipalKid = if ($case -ceq 'kid') {{ 'other-origin' }} else {{ 'rc31-origin' }}
    }}
    try {{
        $null = Assert-WorkerHostGatewayParity -Values $values -WorkerSettings $candidate
        $result[$case] = 'accepted'
    }} catch {{
        $result[$case] = [string]$_.Exception.Message
    }}
}}
$result | ConvertTo-Json -Compress
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["match"] is True
    assert "SING_YIN_PORT" in payload["port"]
    assert "AUTH_EPOCH" in payload["epoch"]
    assert "ORIGIN_PRINCIPAL_KID" in payload["kid"]


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


def test_release_database_safety_wrapper_executes_in_windows_powershell_51(
    tmp_path: Path,
) -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    function_source = "\n".join(
        (
            _powershell_function_source("Protect-ReportText"),
            _powershell_function_source("Invoke-Native"),
            _powershell_function_source("Invoke-ReleaseDatabaseSafety"),
        )
    )
    python = str(Path(sys.executable)).replace("'", "''")
    helper = str(PROJECT_ROOT / "scripts" / "release_database_safety.py").replace(
        "'", "''"
    )
    project_root = str(PROJECT_ROOT).replace("'", "''")
    native_log = str(tmp_path / "native.log").replace("'", "''")
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$script:NativeLogPath = '{native_log}'
{function_source}
$payload = Invoke-ReleaseDatabaseSafety `
    -Python '{python}' `
    -ScriptPath '{helper}' `
    -WorkingDirectory '{project_root}' `
    -CommandArguments @('head', '--release-root', '{project_root}')
$payload | ConvertTo-Json -Compress
"""
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

    assert result.returncode == 0, result.stdout + result.stderr
    json_lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    assert json_lines
    payload = json.loads(json_lines[-1])
    assert payload["status"] == "pass"
    assert len(payload["migrationHeads"]) == 1
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", payload["migrationHeads"][0])


def test_deployment_script_fences_data_and_preserves_the_protected_environment() -> None:
    source = _source()

    assert "Protect-SingYinSensitivePath -Path $environmentPath" in source
    assert "Get-SingYinAclStatus" in source
    assert "[IO.File]::ReadAllBytes($environmentPath)" in source
    assert "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)" in source
    capture_index = source.index("$environmentBytes = [IO.File]::ReadAllBytes($environmentPath)")
    protect_index = source.index("Protect-SingYinSensitivePath -Path $environmentPath")
    assert capture_index < protect_index
    assert "GetSecurityDescriptorSddlForm" in source
    assert "$environmentAclSddl" in source
    assert "SetSecurityDescriptorSddlForm" in source
    assert "Set-Acl -LiteralPath $environmentPath -AclObject $restoredAcl" in source
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
    assert "Wait-PortReleased -Port $deploymentPort" in source
    assert "scripts\\release_database_safety.py" in source
    assert "scripts\\verify_formal_backup_restore.py" not in source
    assert "-Python $previousPython" in source
    assert '"prepare",' in source
    assert '"--release-root", $previousBundlePath' in source
    assert '"--expected-revision", $previousMigrationHead' in source
    for proof in (
        "isolatedRestore",
        "fairnessBalanced",
        "rowCountsMatched",
        "restoreAuditAppended",
        "integrity",
        "sha256",
        "manifestSha256",
        "schemaRevision",
    ):
        assert proof in source
    assert "Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256" in source
    assert "Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256" in source
    assert "[IO.Path]::GetFileName([string]$backupReport.snapshotFile)" in source

    stopped = source.index("Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 30")
    previous_bundle_proof = source.index('"prepare",', stopped)
    task_switch = source.index(
        'Write-Step "Atomically switching the owned task to the immutable release bundle"',
        previous_bundle_proof,
    )
    candidate_start = source.index("$releaseTaskStartAttempted = $true", task_switch)
    assert stopped < previous_bundle_proof < task_switch < candidate_start


def test_deployment_proves_a_distinct_candidate_recovery_baseline_before_pass() -> None:
    source = _source()
    candidate_start = source.index("$releaseTaskStartAttempted = $true")
    strict_gate = source.index('"--allow-pending-cloudflare-access"', candidate_start)
    quiesce_step = source.index(
        'Write-Step "Stopping the candidate before current-schema recovery proof"',
        strict_gate,
    )
    candidate_disable = source.index(
        "Disable-ScheduledTask -TaskName $TaskName",
        quiesce_step,
    )
    candidate_stop = source.index(
        "Stop-ScheduledTask -TaskName $TaskName",
        candidate_disable,
    )
    candidate_fence = source.index(
        "Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 30",
        candidate_stop,
    )
    baseline_step = source.index(
        'Write-Step "Creating a current-schema recovery baseline',
        candidate_fence,
    )
    baseline_prepare = source.index(
        "$currentRecoveryEvidence = Invoke-ReleaseDatabaseSafety",
        baseline_step,
    )
    baseline_proof = source.index(
        "$currentRecoveryBaselineProved = $true",
        baseline_prepare,
    )
    restart_step = source.index(
        'Write-Step "Restarting the candidate and repeating health and write-readiness"',
        baseline_proof,
    )
    candidate_restart = source.index(
        "Start-ScheduledTask -TaskName $TaskName",
        restart_step,
    )
    post_health = source.index(
        "$health = Wait-LoopbackHealth -Port $deploymentPort",
        candidate_restart,
    )
    post_readiness = source.index(
        "$readiness = Wait-LoopbackReadiness -Port $deploymentPort",
        post_health,
    )
    post_strict = source.index(
        '"--allow-pending-cloudflare-access"',
        post_readiness,
    )
    post_gate_proof = source.index(
        "$candidatePostBaselineGatesPassed = $true",
        post_strict,
    )
    post_task_state = source.index(
        "The candidate task stopped after its post-baseline gates passed.",
        post_gate_proof,
    )
    success_report = source.index("Write-DeploymentReport -Payload", post_task_state)
    baseline_block = source[baseline_step:restart_step]
    normalized_baseline = " ".join(baseline_block.split())
    outer_catch = source.index(
        "\n    } catch {\n    $failedPhase = $deploymentPhase",
        success_report,
    )
    report_block = source[success_report:outer_catch]
    failure_report = source.index('status = "fail"', outer_catch)
    failure_block = source[
        failure_report : source.index("$deploymentExitCode = 1", failure_report)
    ]

    assert (
        candidate_start
        < strict_gate
        < quiesce_step
        < candidate_disable
        < candidate_stop
        < candidate_fence
        < baseline_step
        < baseline_prepare
        < baseline_proof
        < restart_step
        < candidate_restart
        < post_health
        < post_readiness
        < post_strict
        < post_gate_proof
        < post_task_state
        < success_report
    )
    assert source[candidate_start:success_report].count(
        '"--allow-pending-cloudflare-access"'
    ) == 2
    assert (
        "$candidateInitialGatesPassed = $true"
        in source[strict_gate:quiesce_step]
    )
    assert (
        "$currentRecoveryDatabaseQuiesced = $true"
        in source[candidate_fence:baseline_step]
    )
    assert (
        '$candidateDatabaseSafetyScript = Join-Path $releaseBundlePath '
        '"scripts\\release_database_safety.py"'
    ) in baseline_block
    assert "-Python $hostPython" in baseline_block
    assert "-ScriptPath $candidateDatabaseSafetyScript" in baseline_block
    assert "-WorkingDirectory $releaseBundlePath" in baseline_block
    assert '"--release-root", $releaseBundlePath' in baseline_block
    assert '"--expected-revision", $releaseMigrationHead' in baseline_block
    assert "current-recovery-baseline-$safeReleaseName.json" in baseline_block
    assert "release-rollback-snapshot-$safeReleaseName.json" not in baseline_block
    assert (
        "$currentRecoverySnapshotPath -ieq $rollbackSnapshotPath"
        in baseline_block
    )
    assert (
        "$currentRecoveryManifestPath -ieq $rollbackManifestPath"
        in baseline_block
    )
    assert (
        "Get-FileHash -LiteralPath $currentRecoverySnapshotPath -Algorithm SHA256"
        in baseline_block
    )
    assert (
        "Get-FileHash -LiteralPath $currentRecoveryManifestPath -Algorithm SHA256"
        in baseline_block
    )
    assert (
        "[string]$currentRecoveryManifest.schemaRevision -cne "
        "$releaseMigrationHead"
    ) in normalized_baseline
    assert (
        "[string]$currentRecoveryManifest.sha256 -cne "
        "$currentRecoverySnapshotSha256"
    ) in normalized_baseline
    assert "$currentRecoveryBaseline = [ordered]@{" in baseline_block
    assert "currentRecoveryBaseline = $currentRecoveryBaseline" in report_block
    for phase_field in (
        "initialGatesPassed = $candidateInitialGatesPassed",
        "databaseQuiesced = $currentRecoveryDatabaseQuiesced",
        "baselineProved = $currentRecoveryBaselineProved",
        "postBaselineGatesPassed = $candidatePostBaselineGatesPassed",
    ):
        assert phase_field in report_block
        assert phase_field in failure_block
    assert "failedPhase = $failedPhase" in source


def test_release_bundle_build_does_not_probe_the_live_database_with_candidate_code() -> None:
    bundle_source = _source().split("function New-SingYinReleaseBundle", 1)[1].split(
        "$resolvedOverlayPath = $null",
        1,
    )[0]

    assert (
        "from nicegui_app.launcher import configure_nicegui_storage_path; "
        "configure_nicegui_storage_path(); import nicegui; import nicegui_app.main"
    ) in bundle_source
    assert "check_deployment_readiness.py" not in bundle_source
    assert "candidate-readiness" not in bundle_source


def test_isolated_candidate_readiness_runs_for_every_bundle_before_downtime() -> None:
    source = _source()
    bundle_call = source.index("$releaseBundlePath = New-SingYinReleaseBundle")
    safe_bundle = source.index(
        "$releaseBundlePath = Assert-SafeReleaseBundlePath",
        bundle_call,
    )
    isolated_step = source.index(
        'Write-Step "Proving candidate migration and strict readiness on an isolated live-data copy"',
        safe_bundle,
    )
    isolated_call = source.index(
        "$candidateReadinessEvidence = Invoke-ReleaseDatabaseSafety",
        isolated_step,
    )
    isolated_proof = source.index(
        "$candidateIsolatedReadinessPassed = $true",
        isolated_call,
    )
    task_stop = source.index(
        'Write-Step "Stopping the owned task and fencing port $deploymentPort"',
        isolated_proof,
    )
    block = source[isolated_step:task_stop]
    normalized = " ".join(block.split())

    assert bundle_call < safe_bundle < isolated_step < isolated_call < isolated_proof < task_stop
    assert 'Join-Path $HostRoot "data\\deployment-proofs"' in block
    assert "$candidateProofParent = Assert-SafeDeploymentProofPath" in block
    assert "Protect-SingYinSensitivePath" in block
    assert "Get-SingYinAclStatus" in block
    assert 'Join-Path $releaseBundlePath ".venv\\Scripts\\python.exe"' in block
    assert "$candidateDatabaseSafetyScript = Join-Path" in block
    assert '"scripts\\release_database_safety.py"' in block
    assert "-Python $candidateBundlePython" in block
    assert "-ScriptPath $candidateDatabaseSafetyScript" in block
    assert "-WorkingDirectory $releaseBundlePath" in block
    assert '"candidate-readiness",' in block
    assert '"--database-path", $databasePath' in block
    assert '"--expected-source-revision", $previousMigrationHead' in block
    assert '"--expected-candidate-revision", $releaseMigrationHead' in block
    assert '"--workspace-parent", $candidateProofParent' in block
    assert "Get-SingYinReleaseBundleFingerprint" in block
    assert "Candidate isolated readiness changed the immutable release bundle." in block
    assert "Remove-Item -LiteralPath $candidateProofParent -Force -ErrorAction Stop" in normalized


def test_candidate_readiness_evidence_is_reported_on_success_and_failure() -> None:
    source = _source()
    success_report = source.index('status = "pass"')
    outer_catch = source.index(
        "\n    } catch {\n    $failedPhase = $deploymentPhase",
        success_report,
    )
    success_block = source[success_report:outer_catch]
    failure_report = source.index('status = "fail"', outer_catch)
    failure_block = source[
        failure_report : source.index("$deploymentExitCode = 1", failure_report)
    ]

    for block in (success_block, failure_block):
        assert "candidateIsolatedReadiness = $candidateReadinessEvidence" in block
        assert (
            "isolatedReadinessPassed = $candidateIsolatedReadinessPassed"
            in block
        )
    finally_block = source.split("\n} finally {", 1)[1]
    assert "$candidateProofParent" in finally_block
    assert "$residualProofItems.Count -eq 0" in finally_block
    assert "Protected candidate proof residue requires manual review" in finally_block
    outer_try = source.index("\ntry {", source.index("$resolvedOverlayPath = $null"))
    outer_initialization = source[source.index("$resolvedOverlayPath = $null"):outer_try]
    assert "$candidateProofParent = $null" in outer_initialization
    assert "Empty candidate proof workspace could not be removed" in finally_block
    cleanup_warning = finally_block.index(
        "Empty candidate proof workspace could not be removed"
    )
    password_cleanup = finally_block.index("$runtimeTaskSecurePassword.Dispose()")
    environment_cleanup = finally_block.index("$processEnvironmentCaptured")
    assert cleanup_warning < password_cleanup < environment_cleanup


def test_deployment_script_consumes_only_a_protected_one_use_environment_overlay() -> None:
    source = _source()

    assert "$EnvironmentOverlayPath" in source
    assert "Read-EnvironmentOverlay" in source
    assert "Merge-EnvironmentOverlay" in source
    assert "Remove-EnvironmentOverlay -Path $resolvedOverlayPath" not in source
    assert "} finally {" in source
    assert "Remove-EnvironmentOverlay -Path $overlayPathToDelete" in source
    assert "if ($deploymentExitCode -eq 0)" in source
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


def test_deployment_script_switches_to_an_immutable_bundle_and_requires_write_readiness() -> None:
    source = _source()

    assert '"archive", "--format=zip"' in source
    assert "New-SingYinReleaseBundle" in source
    assert 'Join-Path $stagingPath ".venv"' in source
    assert '"--require-hashes"' in source
    bundle_import_check = (
        "from nicegui_app.launcher import configure_nicegui_storage_path; "
        "configure_nicegui_storage_path(); import nicegui; import nicegui_app.main"
    )
    assert bundle_import_check in source
    assert "New-ScheduledTaskAction" in source
    assert "-Action $newTaskAction `" in source
    assert "-User $runtimeAccount.Name `" in source
    assert "-Password $runtimeTaskPassword | Out-Null" in source
    assert '"switch",' not in source
    assert "Get-SingYinTaskInspection" in source
    assert "Enable-ScheduledTask -TaskName $TaskName" in source
    assert "Start-ScheduledTask -TaskName $TaskName" in source
    assert "Get-SingYinConfiguredEndpoint -EnvironmentPath $environmentPath" in source
    assert '$deploymentPort = [int]$configuredEndpoint.Port' in source
    assert '"http://127.0.0.1:$Port/healthz"' in source
    assert '"http://127.0.0.1:$Port/readyz"' in source
    assert "Wait-LoopbackHealth -Port $deploymentPort" in source
    assert "Wait-LoopbackReadiness -Port $deploymentPort" in source
    assert "Wait-PortReleased -Port $deploymentPort" in source
    assert "Wait-PortReleased -Port 8080" not in source
    assert 'port = $deploymentPort' in source
    assert "http://127.0.0.1:8080/healthz" not in source
    assert '$ready.status -ceq "ready"' in source
    assert "$ready.writeReady -eq $true" in source
    assert "$ready.maintenance -eq $false" in source
    assert "$ready.recoveryRequired -eq $false" in source
    assert "[int]$ready.pendingBackupObligations -eq 0" in source
    assert "$ready.backupRepairFailed -eq $false" in source
    assert '"scripts\\check_deployment_readiness.py",' in source
    assert '"--strict"' in source
    assert '"--allow-pending-cloudflare-access"' in source
    assert 'Remove-Item -LiteralPath $archivePath -Force -ErrorAction Stop' in source
    assert "Release archive cleanup failed" in source
    assert 'Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue' not in source


def test_deployment_script_rolls_back_task_target_environment_and_task_state() -> None:
    source = _source()
    outer_catch = (
        "\n    } catch {\n"
        "    $failedPhase = $deploymentPhase\n"
        "    $failure = Protect-ReportText $_.Exception.Message"
    )
    assert outer_catch in source
    catch_block = source.split(outer_catch, 1)[1].split("\n} finally {", 1)[0]

    assert '$rollbackAttempted = $true' in source
    assert "$previousTaskAction" in catch_block
    assert "New-ScheduledTaskAction @restoreActionParameters" in catch_block
    assert "$restoreTaskParameters = @{" in catch_block
    assert "Action = $restoreTaskAction" in catch_block
    assert "$restoreTaskParameters.User = $runtimeAccount.Name" in catch_block
    assert "$restoreTaskParameters.Password = $runtimeTaskPassword" in catch_block
    assert "Set-ScheduledTask @restoreTaskParameters | Out-Null" in catch_block
    assert '$databaseRollbackAttempted = $true' in catch_block
    assert '"restore",' in catch_block
    assert '$databaseRollbackSucceeded = $true' in catch_block
    assert '"--expected-sha256", $rollbackSnapshotSha256' in catch_block
    assert '"--expected-revision", $previousMigrationHead' in catch_block
    assert "Protect-SingYinSensitivePath `\n                        -Path $databasePath" in catch_block
    assert '"switch",' not in catch_block
    assert '"pip"' not in catch_block
    assert "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)" in catch_block
    assert "Enable-ScheduledTask -TaskName $TaskName" in catch_block
    assert "Start-ScheduledTask -TaskName $TaskName" in catch_block
    assert "Wait-LoopbackHealth" in catch_block
    assert "rollbackSucceeded" in source
    assert "Protect-ReportText" in source
    assert "nativeLog = [IO.Path]::GetFileName" in source


def test_rollback_never_switches_task_target_until_the_production_port_is_released() -> None:
    source = _source()
    outer_catch = source.index(
        "\n    } catch {\n"
        "    $failedPhase = $deploymentPhase\n"
        "    $failure = Protect-ReportText $_.Exception.Message"
    )
    rollback_start = source.index("$rollbackAttempted = $true", outer_catch)
    rollback_catch = source.index("\n        } catch {", rollback_start)
    rollback = source[rollback_start:rollback_catch]
    wait_index = rollback.index("Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 15")
    database_restore_index = rollback.index('"restore",')
    database_proof_index = rollback.index("$databaseRollbackSucceeded = $true")
    task_switch_index = rollback.index("Set-ScheduledTask @restoreTaskParameters | Out-Null")
    environment_restore_index = rollback.index(
        "[IO.File]::WriteAllBytes($environmentPath, $environmentBytes)"
    )
    previous_task_start_index = rollback.index(
        "Start-ScheduledTask -TaskName $TaskName",
        task_switch_index,
    )

    assert (
        wait_index
        < database_restore_index
        < database_proof_index
        < task_switch_index
        < environment_restore_index
        < previous_task_start_index
    )
    assert "try { Wait-PortReleased" not in rollback
    assert "catch { }" not in rollback[:task_switch_index]


def test_database_rollback_failure_is_fail_closed_before_the_previous_task() -> None:
    source = _source()
    outer_catch = source.index(
        "\n    } catch {\n"
        "    $failedPhase = $deploymentPhase\n"
        "    $failure = Protect-ReportText $_.Exception.Message"
    )
    rollback_start = source.index("$rollbackAttempted = $true", outer_catch)
    rollback_catch = source.index("\n        } catch {", rollback_start)
    rollback = source[rollback_start:rollback_catch]
    guarded_restore = rollback.split("if ($releaseTaskStartAttempted) {", 1)[1]
    restore_index = guarded_restore.index("Invoke-ReleaseDatabaseSafety")
    proof_index = guarded_restore.index("$databaseRollbackSucceeded = $true")
    task_switch_index = guarded_restore.index(
        "Set-ScheduledTask @restoreTaskParameters | Out-Null"
    )
    previous_task_start_index = guarded_restore.index(
        "Start-ScheduledTask -TaskName $TaskName",
        task_switch_index,
    )
    rollback_success_index = guarded_restore.index("$rollbackSucceeded = $true")
    assert restore_index < proof_index < task_switch_index < previous_task_start_index
    assert previous_task_start_index < rollback_success_index
    assert "Write-DeploymentReport -Payload" not in rollback
    assert "The candidate may have migrated the database" in guarded_restore
    assert "database = [ordered]@{" in source
    assert "required = $releaseTaskStartAttempted" in source
    assert "attempted = $databaseRollbackAttempted" in source
    assert "succeeded = $databaseRollbackSucceeded" in source


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


def test_release_environment_copy_is_acl_first_and_utf8_without_bom() -> None:
    source = _source()

    create = source.index('$null = New-Item -ItemType File -Path $bundleEnvironment -Force')
    protect = source.index(
        'Protect-SingYinSensitivePath -Path $bundleEnvironment -RuntimeUser $RuntimeUser',
        create,
    )
    populate = source.index(
        '[IO.File]::WriteAllBytes($bundleEnvironment, [IO.File]::ReadAllBytes($EnvironmentPath))',
        protect,
    )
    assert create < protect < populate
    assert '[Text.UTF8Encoding]::new($false)' in source
    assert '[IO.File]::WriteAllText($temporaryPath, $content, $utf8WithoutBom)' in source
    assert '$output | Set-Content -LiteralPath $temporaryPath -Encoding UTF8' not in source


def test_host_environment_import_requires_every_gateway_control() -> None:
    function_source = _powershell_function_source("Import-HostEnvironment")

    for name in (
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET",
    ):
        assert f'"{name}"' in function_source
    assert "protected host environment is missing" in function_source


def test_release_environment_writer_executes_without_utf8_bom(tmp_path: Path) -> None:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    env_path = tmp_path / ".env"
    env_path.write_text("SING_YIN_PORT=8080\n", encoding="utf-8")
    escaped = str(env_path).replace("'", "''")
    function_source = _powershell_function_source("Set-ReleaseEnvironmentValue")
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
function Protect-SingYinSensitivePath {{ param($Path, $RuntimeUser) }}
{function_source}
Set-ReleaseEnvironmentValue -Path '{escaped}' -Name 'SING_YIN_PORT' -Value '8456' -RuntimeUser 'test-user'
$bytes = [IO.File]::ReadAllBytes('{escaped}')
[ordered]@{{
  prefix = if ($bytes.Length -ge 3) {{ "$($bytes[0])-$($bytes[1])-$($bytes[2])" }} else {{ '' }}
  text = [IO.File]::ReadAllText('{escaped}', [Text.UTF8Encoding]::new($false))
}} | ConvertTo-Json -Compress
"""
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-EncodedCommand", encoded],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(next(line for line in result.stdout.splitlines() if line.startswith("{")))
    assert payload["prefix"] != "239-187-191"
    assert payload["text"] == "SING_YIN_PORT=8456\r\n"
