from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
COMMON = PROJECT_ROOT / "scripts" / "windows_host_common.ps1"
POWERSHELL_UTF8_PREAMBLE = (
    "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
    "$OutputEncoding = [Console]::OutputEncoding; "
)


def _powershell(command: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the selected host model")
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"{POWERSHELL_UTF8_PREAMBLE}{command}",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=check,
    )


def _quoted(path: Path) -> str:
    return str(path).replace("'", "''")


def _powershell_block(source: str, marker: str) -> str:
    marker_index = source.index(marker)
    block_start = source.index("{", marker_index)
    depth = 0
    for index in range(block_start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[block_start + 1:index]
    raise AssertionError(f"PowerShell block after {marker!r} is not balanced")


def test_access_redirect_requires_exact_https_tenant_and_access_path() -> None:
    cases = {
        "https://school.cloudflareaccess.com/cdn-cgi/access/login/app": True,
        "http://school.cloudflareaccess.com/cdn-cgi/access/login/app": False,
        "https://other.cloudflareaccess.com/cdn-cgi/access/login/app": False,
        "https://example.org/?next=https://school.cloudflareaccess.com/cdn-cgi/access/login/app": False,
        "https://school.cloudflareaccess.com/not-access": False,
    }
    expression = ",".join(f"'{value}'" for value in cases)
    result = _powershell(
        f". '{_quoted(COMMON)}'; @({expression}) | ForEach-Object {{ "
        "[pscustomobject]@{ url=$_; valid=(Test-SingYinAccessRedirect -Location $_ "
        "-TeamDomain 'school.cloudflareaccess.com') } } | ConvertTo-Json"
    )
    payload = json.loads(result.stdout)
    assert {item["url"]: item["valid"] for item in payload} == cases


def test_configured_endpoint_uses_env_port_and_refuses_external_bind(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SING_YIN_DEPLOYMENT_MODE=local\nSING_YIN_HOST=127.0.0.1\nSING_YIN_PORT=8456\n",
        encoding="utf-8",
    )
    result = _powershell(
        f". '{_quoted(COMMON)}'; Get-SingYinConfiguredEndpoint -EnvironmentPath '{_quoted(env_path)}' "
        "| Select-Object Host,Port,Mode | ConvertTo-Json"
    )
    assert json.loads(result.stdout) == {"Host": "127.0.0.1", "Port": 8456, "Mode": "local"}

    env_path.write_text("SING_YIN_HOST=0.0.0.0\nSING_YIN_PORT=8456\n", encoding="utf-8")
    rejected = _powershell(
        f". '{_quoted(COMMON)}'; Get-SingYinConfiguredEndpoint -EnvironmentPath '{_quoted(env_path)}'",
        check=False,
    )
    assert rejected.returncode != 0
    assert "loopback-only" in rejected.stderr


@pytest.mark.parametrize(
    ("content", "message"),
    (
        ("SING_YIN_PORT=8456\tunsafe\n", "control character"),
        ("SING_YIN_PORT=8456\x00unsafe\n", "control character"),
        ("SING_YIN_PORT 8456\n", "malformed setting"),
        ("SING_YIN_PORT=8456\nSING_YIN_PORT=8457\n", "duplicate setting"),
    ),
)
def test_environment_map_rejects_ambiguous_or_control_character_entries(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(content, encoding="utf-8")

    rejected = _powershell(
        f". '{_quoted(COMMON)}'; Get-SingYinEnvironmentMap -Path '{_quoted(env_path)}'",
        check=False,
    )

    assert rejected.returncode != 0
    assert message in rejected.stderr


def test_environment_map_keeps_all_controlled_gateway_settings(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SING_YIN_UNIFIED_GUEST=1\n"
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL=true\n"
        "ORIGIN_PRINCIPAL_SECRET=not-a-production-secret\n"
        "ORIGIN_PRINCIPAL_KID=rc36-origin\n"
        "AUTH_EPOCH=36\n"
        "SING_YIN_GUEST_SNAPSHOT_SECRET=not-a-production-snapshot-secret\n",
        encoding="utf-8",
    )

    result = _powershell(
        f". '{_quoted(COMMON)}'; Get-SingYinEnvironmentMap -Path '{_quoted(env_path)}' "
        "| ConvertTo-Json -Compress"
    )
    payload = json.loads(result.stdout)

    assert payload["ORIGIN_PRINCIPAL_SECRET"] == "not-a-production-secret"
    assert payload["ORIGIN_PRINCIPAL_KID"] == "rc36-origin"
    assert payload["AUTH_EPOCH"] == "36"


@pytest.mark.parametrize(
    "content",
    (
        "ORIGIN_PRINCIPAL_SECRET secret\n",
        "ORIGIN_PRINCIPAL_KID kid\n",
        "AUTH_EPOCH 36\n",
    ),
)
def test_environment_map_rejects_malformed_gateway_settings(tmp_path: Path, content: str) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(content, encoding="utf-8")

    rejected = _powershell(
        f". '{_quoted(COMMON)}'; Get-SingYinEnvironmentMap -Path '{_quoted(env_path)}'",
        check=False,
    )

    assert rejected.returncode != 0
    assert "malformed setting" in rejected.stderr


def test_acl_helper_removes_broad_write_access_from_temporary_paths(tmp_path: Path) -> None:
    protected_dir = tmp_path / "runtime"
    protected_dir.mkdir()
    protected_file = tmp_path / ".env"
    protected_file.write_text("non-secret-test-value", encoding="utf-8")
    inherited_file = tmp_path / "inherited.env"
    inherited_file.write_text("non-secret-test-value", encoding="utf-8")
    result = _powershell(
        f". '{_quoted(COMMON)}'; "
        "$administratorsSid = 'S-1-5-32-544'; "
        f"Protect-SingYinSensitivePath -Path '{_quoted(protected_dir)}'; "
        f"Protect-SingYinSensitivePath -Path '{_quoted(protected_file)}'; "
        f"$paths = @('{_quoted(protected_dir)}','{_quoted(protected_file)}'); "
        "$present = Get-SingYinAclStatus -Paths $paths -RequiredIdentitySid $administratorsSid "
        "-RequiredRights ([Security.AccessControl.FileSystemRights]::FullControl); "
        "$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
        "$insufficient = Get-SingYinAclStatus -Paths $paths -RequiredIdentitySid $currentSid "
        "-RequiredRights ([Security.AccessControl.FileSystemRights]::FullControl); "
        "$missing = Get-SingYinAclStatus -Paths $paths "
        "-RequiredIdentitySid 'S-1-5-21-999999999-999999999-999999999-1001'; "
        f"$inheritedAcl = Get-SingYinFileSystemAcl -Path '{_quoted(inherited_file)}'; "
        "$inheritedAcl.SetAccessRuleProtection($false, $true); "
        f"Set-SingYinFileSystemAcl -Path '{_quoted(inherited_file)}' -Acl $inheritedAcl; "
        f"$unprotected = Get-SingYinAclStatus -Paths @('{_quoted(inherited_file)}'); "
        "[pscustomobject]@{ Present=$present; Missing=$missing; "
        "Insufficient=$insufficient; Unprotected=$unprotected } "
        "| ConvertTo-Json -Depth 3",
        check=False,
    )
    assert result.returncode == 0, result.stderr.strip()
    payload = json.loads(result.stdout)
    assert payload["Present"]["Checked"] == 2
    assert payload["Present"]["Weak"] == 0
    assert payload["Present"]["Unprotected"] == 0
    assert payload["Present"]["RequiredIdentityMissing"] == 0
    assert payload["Present"]["RequiredIdentityInsufficient"] == 0
    assert payload["Present"]["Compliant"] is True
    assert payload["Missing"]["RequiredIdentityMissing"] == 2
    assert payload["Missing"]["Compliant"] is False
    assert payload["Insufficient"]["RequiredIdentityMissing"] == 0
    assert payload["Insufficient"]["RequiredIdentityInsufficient"] == 2
    assert payload["Insufficient"]["Compliant"] is False
    assert payload["Unprotected"]["Checked"] == 1
    assert payload["Unprotected"]["Unprotected"] == 1
    assert payload["Unprotected"]["Compliant"] is False

    common_source = COMMON.read_text(encoding="utf-8-sig")
    assert "$acl.SetAccessRule($runtimeRule)" in common_source
    assert "$acl.SetAccessRule($systemRule)" in common_source
    assert "$acl.SetAccessRule($administratorsRule)" in common_source
    assert "Windows did not retain the required protected ACL" in common_source
    assert "function Get-SingYinFileSystemAcl" in common_source
    assert "function Set-SingYinFileSystemAcl" in common_source
    assert "Get-Acl" not in common_source
    assert "Set-Acl" not in common_source


def test_remote_access_doctor_is_redacted_and_reports_unprepared_host_state() -> None:
    script = PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1"
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the selected host model")
    result = _powershell(f"& '{_quoted(script)}'", check=False)
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["project"] == "sing-yin-study-prefect-duty-roster"
    assert payload["deploymentMode"] == "local"
    has_failure = any(check["status"] == "fail" for check in payload["checks"])
    assert result.returncode == (1 if has_failure else 0)
    access_gate = next(check for check in payload["checks"] if check["code"] == "access_gate")
    assert access_gate["status"] == "deferred"
    serialized = json.dumps(payload).lower()
    assert "tunnel token" not in serialized
    assert "youtube_api_key" not in serialized
    assert "storage_secret=" not in serialized
    assert "cf-access-client-secret" not in serialized


def test_activation_owns_service_rollback_and_uses_configured_port() -> None:
    activation = (PROJECT_ROOT / "scripts" / "activate_cloudflare_remote_access.ps1").read_text(encoding="utf-8")
    verification = (PROJECT_ROOT / "scripts" / "verify_cloudflare_access.ps1").read_text(encoding="utf-8")
    startup = (PROJECT_ROOT / "scripts" / "register_windows_startup_task.ps1").read_text(encoding="utf-8")

    assert "Get-SingYinTaskInspection" in activation
    assert "An unowned cloudflared Windows service already exists" in activation
    assert "$installedByThisRun" in activation
    assert "service uninstall" in activation
    assert "Remove-Item -LiteralPath $envBackup" in activation
    assert "$endpoint.Port" in activation
    assert "-Port $endpoint.Port" in activation
    assert "-match '\\.cloudflareaccess\\.com'" not in verification
    assert '"https://$PublicHostname/"' in verification
    assert "$publicProbe.StatusCode -ne 200" in verification
    assert '"https://$PublicHostname/auth/login"' in verification
    assert "the administrator login route was not redirected" in verification
    assert "$request.AllowAutoRedirect = $false" in verification
    assert "Test-SingYinAccessRedirect" in verification
    assert "Cloudflare One-time PIN verified" in verification
    assert "Invoke-SingYinAccessLoginPageRequest" in verification
    assert "totp-form" in verification and "verify-code" in verification
    assert "owner=sing-yin-roster-v1" not in startup  # supplied centrally by the common script
    assert "$script:SingYinTaskOwnerMarker" in startup


def test_domain_free_private_warp_activation_stays_loopback_only() -> None:
    activation = (PROJECT_ROOT / "scripts" / "activate_cloudflare_private_warp.ps1").read_text(encoding="utf-8")
    verification = (PROJECT_ROOT / "scripts" / "verify_cloudflare_private_warp.ps1").read_text(encoding="utf-8")
    doctor = (PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1").read_text(encoding="utf-8")

    assert 'Set-EnvValue $envPath "SING_YIN_HOST" "127.0.0.1"' in activation
    assert 'Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_PRIVATE_WARP" "true"' in activation
    assert "--token-file" in activation
    assert "Protect-SingYinSensitivePath -Path $TokenFile" in activation
    assert "Stop-ScheduledTask -TaskName $ApplicationTaskName" in activation
    assert "An unowned cloudflared Windows service already exists" in activation
    assert "127.0.0.1" in verification
    assert "private_host_header" in verification
    assert "verify_cloudflare_private_warp.ps1" in doctor


def test_windows_host_scripts_bind_permissions_and_task_to_dedicated_runtime_user() -> None:
    common = COMMON.read_text(encoding="utf-8")
    preparation = (PROJECT_ROOT / "scripts" / "prepare_windows_host.ps1").read_text(encoding="utf-8")
    startup = (PROJECT_ROOT / "scripts" / "register_windows_startup_task.ps1").read_text(encoding="utf-8")
    activation = (PROJECT_ROOT / "scripts" / "activate_cloudflare_remote_access.ps1").read_text(encoding="utf-8")
    doctor = (PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1").read_text(encoding="utf-8")

    assert "Get-SingYinRuntimeAccount" in common
    assert "must remain a standard user" in common
    assert "(Get-SingYinRuntimeAccount -UserName $RuntimeUser).Sid" in common
    assert 'RuntimeUser = "SingYinRosterSvc"' in preparation
    assert "Grant-SingYinRuntimeReadAccess" in preparation
    assert "Grant-SingYinVenvBasePythonReadAccess" in preparation
    assert "Grant-SingYinBatchLogonRight" in preparation
    assert "Grant-SingYinVenvBasePythonReadAccess" in startup
    assert "Grant-SingYinBatchLogonRight" in startup
    assert "SeBatchLogonRight" in common
    assert "Assert-SingYinAdministrator" in common
    assert (
        'Assert-SingYinAdministrator -Operation "Granting the Sing Yin roster batch-logon right"'
        in common
    )
    assert 'Assert-SingYinAdministrator -Operation "Registering the Sing Yin roster startup task"' in startup
    assert "LsaEnumerateAccountRights" in common
    assert "LsaFreeMemory" in common
    assert "HasRight" in common
    assert "secedit.exe" not in common
    assert "-RequiredIdentitySid $runtimeAccount.Sid.Value" in preparation
    assert 'RuntimeUser = "SingYinRosterSvc"' in startup
    assert '-Argument "-B -X utf8 -m nicegui_app.launcher"' in startup
    assert '"-X utf8 -m nicegui_app.launcher"' in common
    assert '"-B -X utf8 -m nicegui_app.launcher"' in common
    assert '"-X utf8 -m nicegui_app.main"' in common
    assert '"-B -X utf8 -m nicegui_app.main"' in common
    assert "$supportedArguments -ccontains $arguments" in common
    assert "not owned by this project and runtime account" in startup
    assert "if ($inspection.Exists) { $register.Force = $true }" in startup
    assert "[switch]$NoStart" in startup
    assert "if ($NoStart)" in startup
    no_start_branch = _powershell_block(startup, "if ($NoStart)")
    start_branch = _powershell_block(startup, "else {\n    Start-ScheduledTask")
    assert "Start-ScheduledTask" not in no_start_branch
    assert start_branch.count("Start-ScheduledTask -TaskName $TaskName") == 1
    assert startup.count("Start-ScheduledTask -TaskName $TaskName") == 1
    assert '"Register Windows scheduled task without starting it"' in startup
    assert 'RuntimeUser = "SingYinRosterSvc"' in activation
    activation_acl_calls = [
        line for line in activation.splitlines() if "Protect-SingYinSensitivePath" in line
    ]
    assert activation_acl_calls
    assert all("-RuntimeUser $runtimeAccount.Name" in line for line in activation_acl_calls)
    assert 'RuntimeUser = "SingYinRosterSvc"' in doctor
    assert 'Add-DoctorCheck "runtime_account" "pass"' in doctor


def test_windows_process_path_refresh_preserves_first_entry_and_removes_duplicates() -> None:
    common = COMMON.read_text(encoding="utf-8")
    preparation = (PROJECT_ROOT / "scripts" / "prepare_windows_host.ps1").read_text(
        encoding="utf-8"
    )
    cloudflare = (
        PROJECT_ROOT / "scripts" / "prepare_cloudflare_remote_access.ps1"
    ).read_text(encoding="utf-8")

    assert "function Join-SingYinProcessPath" in common
    assert "$seen.ContainsKey($comparisonKey)" in common
    assert "Update-SingYinProcessPath" in preparation
    assert "Update-SingYinProcessPath" in cloudflare
    assert '$env:Path = "$machine;$user"' not in preparation
    assert '$env:Path = "$machine;$user"' not in cloudflare

    result = _powershell(
        f". '{_quoted(COMMON)}'; "
        "Join-SingYinProcessPath -MachinePath 'C:\\Tools;C:\\Bin;C:\\Tools\\' "
        "-UserPath 'c:\\tools;C:\\UserBin;;'"
    )
    assert result.stdout.strip() == r"C:\Tools;C:\Bin;C:\UserBin"


def test_windows_scripts_do_not_resolve_psscriptroot_inside_parameter_defaults() -> None:
    for name in (
        "activate_cloudflare_remote_access.ps1",
        "activate_cloudflare_private_warp.ps1",
        "doctor_windows_remote_access.ps1",
        "prepare_windows_host.ps1",
        "register_windows_startup_task.ps1",
    ):
        source = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        parameter_block = source.split("$ErrorActionPreference", 1)[0]
        assert "Split-Path -Parent $PSScriptRoot" not in parameter_block
        assert "if ([string]::IsNullOrWhiteSpace($ProjectRoot))" in source


def test_windows_ssh_setup_is_key_only_loopback_only_and_fail_closed() -> None:
    setup = (PROJECT_ROOT / "scripts" / "configure_windows_ssh.ps1").read_text(
        encoding="utf-8"
    )
    verification = (PROJECT_ROOT / "scripts" / "verify_windows_ssh.ps1").read_text(
        encoding="utf-8"
    )

    assert 'Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"' in setup
    assert setup.count('Get-WindowsCapability -Online -Name "OpenSSH.Server*"') >= 2
    assert "ListenAddress 127.0.0.1" in setup
    assert "ListenAddress ::1" in setup
    assert "AuthenticationMethods publickey" in setup
    assert "PasswordAuthentication no" in setup
    assert "KbdInteractiveAuthentication no" in setup
    assert "AllowAgentForwarding no" in setup
    assert "AllowTcpForwarding no" in setup
    assert "GatewayPorts no" in setup
    assert "PermitTunnel no" in setup
    assert "AllowUsers $MaintenanceUser" in setup
    assert "administrators_authorized_keys" in setup
    assert "Set-RestrictedFileAcl" in setup
    assert "'^ssh_host_(rsa|ecdsa|ed25519)_key$'" in setup
    assert "-AllowedSids @($systemSid, $administratorsSid)" in setup
    assert "-AllowedSids @($account.SID, $systemSid)" in setup
    assert "Disable-NetFirewallRule" in setup
    assert "ssh-ed25519" in setup
    assert "PasswordAuthentication no" in setup.split(
        "# BEGIN SING YIN ROSTER MANAGED SSH", 1
    )[1]
    assert "configBackupCreated" in setup
    assert "Write-JsonReport -Payload $report" in setup

    assert "-o BatchMode=yes" in verification
    assert "-o ConnectTimeout=8" in verification
    assert (
        'powershell.exe -NoLogo -NoProfile -NonInteractive '
        '-ExecutionPolicy Bypass -EncodedCommand $encoded'
    ) in verification
    assert "isAdministrator" in verification
    assert 'Get-Service -Name "sshd"' in verification
    assert 'Get-ScheduledTask -TaskName "Sing Yin Roster Host"' in verification
    assert '[string]$HostRoot = "C:\\SingYinRoster"' in verification
    assert "__HOST_ROOT_PAYLOAD__" in verification
    assert 'safe.directory=$safeDirectory' in verification
    assert '-C $hostRoot rev-parse HEAD' in verification
    assert "'^[0-9a-f]{40}$'" in verification
    assert 'Get-SingYinConfiguredEndpoint -EnvironmentPath (Join-Path $hostRoot ".env")' in verification
    assert '"http://$($endpoint.Host):$($endpoint.Port)/healthz"' in verification
    assert '"http://127.0.0.1:8080/healthz"' not in verification
    assert '$remote.applicationMode -eq "official"' in verification
    assert '$remote.database -eq "ok"' in verification
