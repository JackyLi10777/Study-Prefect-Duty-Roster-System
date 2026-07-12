[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$PublicHostname,
    [Parameter(Mandatory = $true)][string]$TeamDomain,
    [Parameter(Mandatory = $true)][string]$AccessAudience,
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$ApplicationTaskName = "Sing Yin Roster Host"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Set-EnvValue([string]$Path, [string]$Name, [string]$Value) {
    $content = Get-Content -Raw -LiteralPath $Path -Encoding UTF8
    $pattern = "(?m)^\s*" + [regex]::Escape($Name) + "=.*$"
    $line = "$Name=$Value"
    if ([regex]::IsMatch($content, $pattern)) {
        $content = [regex]::Replace($content, $pattern, $line)
    } else {
        $content = $content.TrimEnd() + "`r`n$line`r`n"
    }
    Set-Content -LiteralPath $Path -Encoding UTF8 -NoNewline -Value $content
}

function New-StorageSecret {
    $bytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

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

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run PowerShell as Administrator before activating the Windows cloudflared service."
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) { throw ".env is missing. Run prepare_windows_host.ps1 first." }
$cloudflared = Find-Cloudflared
if (-not $cloudflared) { throw "cloudflared is missing. Run prepare_cloudflare_remote_access.ps1 -InstallCloudflared first." }
if (-not (Get-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue)) {
    throw "The '$ApplicationTaskName' task is missing. Register and test the local host first."
}

$PublicHostname = $PublicHostname.Trim().ToLowerInvariant().TrimEnd('.')
$TeamDomain = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
$AccessAudience = $AccessAudience.Trim()
if ($PublicHostname -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$') { throw "Invalid public hostname." }
if ($TeamDomain -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') { throw "Invalid team domain." }
if ($AccessAudience.Length -lt 16) { throw "The Access audience tag looks incomplete." }

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/healthz" -TimeoutSec 10
} catch {
    throw "The local host is not healthy. Start and verify it before remote activation."
}
if ($health.status -ne "ok" -or $health.database -ne "ok") { throw "The local health check is degraded." }

if (-not $PSCmdlet.ShouldProcess("https://$PublicHostname", "Activate Cloudflare Access protected remote use")) { return }

Write-Host "`nBefore continuing, Cloudflare Zero Trust must already contain:" -ForegroundColor Yellow
Write-Host "  1. a self-hosted Access application for https://$PublicHostname"
Write-Host "  2. an Allow policy containing only the intended people"
Write-Host "  3. no permanent Bypass or Everyone policy"
Write-Host "  4. a remotely-managed Tunnel whose public hostname points to http://127.0.0.1:8080"
$confirmation = Read-Host "Type ACCESS READY exactly after checking all four items"
if ($confirmation -cne "ACCESS READY") { throw "Remote activation cancelled; local-only mode was preserved." }

$secureToken = Read-Host "Paste the one-time Tunnel service token (it will not be displayed)" -AsSecureString
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
$plainToken = ""
$envBackup = "$envPath.before-remote"
Copy-Item -LiteralPath $envPath -Destination $envBackup -Force

try {
    $plainToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    if ([string]::IsNullOrWhiteSpace($plainToken)) { throw "Tunnel token was empty." }
    if (-not (Get-Service cloudflared -ErrorAction SilentlyContinue)) {
        & $cloudflared service install $plainToken
        if ($LASTEXITCODE -ne 0) { throw "cloudflared service installation failed." }
    }

    Set-EnvValue $envPath "SING_YIN_DEPLOYMENT_MODE" "server"
    Set-EnvValue $envPath "SING_YIN_HOST" "127.0.0.1"
    Set-EnvValue $envPath "SING_YIN_REMOTE_ACCESS_ENABLED" "true"
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS" "true"
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_ACCESS_AUD" $AccessAudience
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_TEAM_DOMAIN" $TeamDomain
    Set-EnvValue $envPath "SING_YIN_PUBLIC_HOSTNAME" $PublicHostname
    $existingSecret = Select-String -LiteralPath $envPath -Pattern '^SING_YIN_STORAGE_SECRET=(.{32,})$' | Select-Object -First 1
    if (-not $existingSecret) { Set-EnvValue $envPath "SING_YIN_STORAGE_SECRET" (New-StorageSecret) }

    Stop-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-ScheduledTask -TaskName $ApplicationTaskName
    Start-Service cloudflared -ErrorAction SilentlyContinue

    $deadline = (Get-Date).AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        try { $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/healthz" -TimeoutSec 3 } catch { $health = $null }
    } until (($health -and $health.status -eq "ok") -or (Get-Date) -ge $deadline)
    if (-not $health -or $health.status -ne "ok") { throw "The NiceGUI host did not become healthy after server-mode restart." }

    & (Join-Path $PSScriptRoot "verify_cloudflare_access.ps1") -PublicHostname $PublicHostname -TeamDomain $TeamDomain
    if ($LASTEXITCODE -ne 0) { throw "Cloudflare Access verification failed." }
    Remove-Item -LiteralPath $envBackup -Force
    Write-Host "Remote access is active and protected by the verified Access redirect." -ForegroundColor Green
} catch {
    Write-Host "Activation failed; stopping cloudflared and returning NiceGUI to the previous environment." -ForegroundColor Red
    Stop-Service cloudflared -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $envBackup) { Copy-Item -LiteralPath $envBackup -Destination $envPath -Force }
    Stop-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Start-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue
    throw
} finally {
    $plainToken = $null
    if ($tokenPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer) }
    $secureToken = $null
}
