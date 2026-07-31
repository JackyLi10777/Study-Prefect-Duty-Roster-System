from __future__ import annotations

import base64
import json
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
    host_root: Path,
    task_working_directory: Path,
) -> dict[str, object]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the production host script")
    escaped_host = str(host_root).replace("'", "''")
    escaped_working_directory = str(task_working_directory).replace("'", "''")
    function_source = "\n".join(
        (
            _powershell_function_source("Assert-SafeReleaseBundlePath"),
            _powershell_function_source("Get-SingYinReleaseBundleFingerprint"),
            _powershell_function_source("Get-SingYinPreviousReleaseIdentity"),
        )
    )
    command = f"""
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
{function_source}
try {{
    $identity = Get-SingYinPreviousReleaseIdentity `
        -HostRoot '{escaped_host}' `
        -TaskWorkingDirectory '{escaped_working_directory}'
    [ordered]@{{
        ok = $true
        commit = [string]$identity.Commit
        releaseRef = [string]$identity.ReleaseRef
        source = [string]$identity.Source
        bundle = [string]$identity.Bundle
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
    assert json_lines, f"PowerShell identity check emitted no JSON payload: {result.stdout!r}"
    return json.loads(json_lines[-1])


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
    assert "The release report fingerprint does not match the immutable release source." in source
    assert "checks.Count -ne 12" not in source
    assert "twelve-gate" not in source.lower()


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


def test_previous_release_identity_comes_from_verified_task_bundle(
    tmp_path: Path,
) -> None:
    host_root = tmp_path / "host"
    bundle = host_root / "releases" / "v1.2.0-rc.41-example"
    bundle.mkdir(parents=True)
    (bundle / "app.py").write_text("print('release')\n", encoding="utf-8")
    fingerprint = _run_bundle_fingerprint(bundle)
    marker = {
        "schemaVersion": 2,
        "releaseRef": "v1.2.0-rc.41",
        "commit": "7" * 40,
        "sourceTree": "8" * 40,
        "environmentSha256": "9" * 64,
        "bundleContentSha256": fingerprint["sha256"],
        "bundleFileCount": fingerprint["fileCount"],
    }
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )

    identity = _run_previous_release_identity(host_root, bundle)

    assert identity == {
        "ok": True,
        "commit": "7" * 40,
        "releaseRef": "v1.2.0-rc.41",
        "source": "immutable-release-marker",
        "bundle": str(bundle),
    }


def test_previous_release_identity_rejects_a_tampered_task_bundle(
    tmp_path: Path,
) -> None:
    host_root = tmp_path / "host"
    bundle = host_root / "releases" / "v1.2.0-rc.41-example"
    bundle.mkdir(parents=True)
    app = bundle / "app.py"
    app.write_text("print('release')\n", encoding="utf-8")
    fingerprint = _run_bundle_fingerprint(bundle)
    marker = {
        "schemaVersion": 2,
        "releaseRef": "v1.2.0-rc.41",
        "commit": "7" * 40,
        "sourceTree": "8" * 40,
        "environmentSha256": "9" * 64,
        "bundleContentSha256": fingerprint["sha256"],
        "bundleFileCount": fingerprint["fileCount"],
    }
    (bundle / ".sing-yin-release.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )
    app.write_text("print('tampered')\n", encoding="utf-8")

    identity = _run_previous_release_identity(host_root, bundle)

    assert identity["ok"] is False
    assert "identity marker is invalid or stale" in str(identity["error"])


def test_deployment_reports_previous_identity_from_the_task_target() -> None:
    source = _source()
    assignment = source.index(
        "$previousReleaseIdentity = Get-SingYinPreviousReleaseIdentity",
    )
    task_capture = source.index("$previousTaskAction = [pscustomobject]@{")

    assert task_capture < assignment
    assert "-TaskWorkingDirectory $previousTaskAction.WorkingDirectory" in source
    assert "$previousCommit = [string]$previousReleaseIdentity.Commit" in source
    assert "previousReleaseRef = $previousReleaseRef" in source
    assert "previousReleaseSource = $previousReleaseSource" in source
    assert '$previousCommit = Get-GitValue -Repository $HostRoot -Arguments @("rev-parse", "HEAD")' not in source


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
    rollback = source.split("$rollbackAttempted = $true", 1)[1]
    wait_index = rollback.index("Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 15")
    task_switch_index = rollback.index("Set-ScheduledTask @restoreTaskParameters | Out-Null")

    assert wait_index < task_switch_index
    assert "try { Wait-PortReleased" not in rollback
    assert "catch { }" not in rollback[:task_switch_index]


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
