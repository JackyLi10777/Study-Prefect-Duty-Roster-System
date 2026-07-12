[CmdletBinding()]
param(
    [switch]$InstallCloudflared
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") { throw "This preparation script is for Windows only." }

function Find-Cloudflared {
    $command = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($path in @(
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )) {
        if ($path -and (Test-Path -LiteralPath $path)) { return (Resolve-Path -LiteralPath $path).Path }
    }
    return $null
}

$cloudflared = Find-Cloudflared
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
    $cloudflared = Find-Cloudflared
}
if (-not $cloudflared) {
    throw "cloudflared is not installed. Re-run with -InstallCloudflared."
}

& $cloudflared --version
if ($LASTEXITCODE -ne 0) { throw "cloudflared could not run." }

Write-Host "`nRemote-access software is prepared, but no public connection has been activated." -ForegroundColor Green
Write-Host "Complete the Cloudflare dashboard steps in docs\CLOUDFLARE_REMOTE_ACCESS_SETUP.md."
Write-Host "Then run scripts\activate_cloudflare_remote_access.ps1 with the three non-secret Access values."
