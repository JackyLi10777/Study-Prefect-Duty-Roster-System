[CmdletBinding()]
param(
    [switch]$InstallCloudflared
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ($env:OS -ne "Windows_NT") { throw "This preparation script is for Windows only." }

$cloudflared = Find-SingYinCloudflared
if (-not $cloudflared -and $InstallCloudflared) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "winget is unavailable. Install App Installer from Microsoft Store first."
    }
    Write-Host "Installing cloudflared from Windows Package Manager..." -ForegroundColor Cyan
    & winget.exe install --id Cloudflare.cloudflared --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "cloudflared installation failed (exit $LASTEXITCODE)." }
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
    $cloudflared = Find-SingYinCloudflared
}
if (-not $cloudflared) {
    throw "cloudflared is not installed. Re-run with -InstallCloudflared."
}

& $cloudflared --version
if ($LASTEXITCODE -ne 0) { throw "cloudflared could not run." }

Write-Host "`nRemote-access software is prepared, but no public connection has been activated." -ForegroundColor Green
Write-Host "Complete the Cloudflare dashboard steps in docs\CLOUDFLARE_REMOTE_ACCESS_SETUP.md."
Write-Host "Then run scripts\activate_cloudflare_remote_access.ps1 with the three non-secret Access values."
