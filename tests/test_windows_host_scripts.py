from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
COMMON = PROJECT_ROOT / "scripts" / "windows_host_common.ps1"


def _powershell(command: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the selected host model")
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=check,
    )


def _quoted(path: Path) -> str:
    return str(path).replace("'", "''")


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


def test_acl_helper_removes_broad_write_access_from_temporary_paths(tmp_path: Path) -> None:
    protected_dir = tmp_path / "runtime"
    protected_dir.mkdir()
    protected_file = tmp_path / ".env"
    protected_file.write_text("non-secret-test-value", encoding="utf-8")
    result = _powershell(
        f". '{_quoted(COMMON)}'; "
        "$runtimeSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
        f"Protect-SingYinSensitivePath -Path '{_quoted(protected_dir)}'; "
        f"Protect-SingYinSensitivePath -Path '{_quoted(protected_file)}'; "
        f"Get-SingYinAclStatus -Paths @('{_quoted(protected_dir)}','{_quoted(protected_file)}') "
        "-RequiredIdentitySid $runtimeSid | ConvertTo-Json"
    )
    payload = json.loads(result.stdout)
    assert payload["Checked"] == 2
    assert payload["Weak"] == 0
    assert payload["RequiredIdentityMissing"] == 0
    assert payload["Compliant"] is True


def test_remote_access_doctor_is_redacted_and_reports_unprepared_host_state() -> None:
    script = PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1"
    if not POWERSHELL:
        pytest.skip("Windows PowerShell is required for the selected host model")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        check=False,
    )
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
    assert "Test-SingYinAccessRedirect" in verification
    assert "owner=sing-yin-roster-v1" not in startup  # supplied centrally by the common script
    assert "$script:SingYinTaskOwnerMarker" in startup


def test_windows_host_scripts_bind_permissions_and_task_to_dedicated_runtime_user() -> None:
    common = COMMON.read_text(encoding="utf-8")
    preparation = (PROJECT_ROOT / "scripts" / "prepare_windows_host.ps1").read_text(encoding="utf-8")
    startup = (PROJECT_ROOT / "scripts" / "register_windows_startup_task.ps1").read_text(encoding="utf-8")
    doctor = (PROJECT_ROOT / "scripts" / "doctor_windows_remote_access.ps1").read_text(encoding="utf-8")

    assert "Get-SingYinRuntimeAccount" in common
    assert "must remain a standard user" in common
    assert 'RuntimeUser = "SingYinRosterSvc"' in preparation
    assert "Grant-SingYinRuntimeReadAccess" in preparation
    assert "-RequiredIdentitySid $runtimeAccount.Sid.Value" in preparation
    assert 'RuntimeUser = "SingYinRosterSvc"' in startup
    assert "not owned by this project and runtime account" in startup
    assert "if ($inspection.Exists) { $register.Force = $true }" in startup
    assert 'RuntimeUser = "SingYinRosterSvc"' in doctor
    assert 'Add-DoctorCheck "runtime_account" "pass"' in doctor


def test_windows_scripts_do_not_resolve_psscriptroot_inside_parameter_defaults() -> None:
    for name in (
        "activate_cloudflare_remote_access.ps1",
        "doctor_windows_remote_access.ps1",
        "prepare_windows_host.ps1",
        "register_windows_startup_task.ps1",
    ):
        source = (PROJECT_ROOT / "scripts" / name).read_text(encoding="utf-8")
        parameter_block = source.split("$ErrorActionPreference", 1)[0]
        assert "Split-Path -Parent $PSScriptRoot" not in parameter_block
        assert "if ([string]::IsNullOrWhiteSpace($ProjectRoot))" in source
