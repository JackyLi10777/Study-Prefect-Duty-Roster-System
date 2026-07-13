[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory = $true)][string]$TunnelId,
    [string]$PrivateHostname = "roster.singyin.internal",
    [string]$TeamDomain = "restless-hall-73b2.cloudflareaccess.com",
    [string]$ProjectRoot = "",
    [string]$ApplicationTaskName = "Sing Yin Roster Host",
    [string]$RuntimeUser = "SingYinRosterSvc",
    [string]$TokenFile = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }

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

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    throw "Run PowerShell as Administrator before activating the private WARP connector."
}
if ($TunnelId -notmatch '^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$') {
    throw "TunnelId must be one valid Cloudflare Tunnel UUID."
}
$PrivateHostname = $PrivateHostname.Trim().ToLowerInvariant().TrimEnd('.')
$TeamDomain = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
if ($PrivateHostname -notmatch '^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$') {
    throw "PrivateHostname must be one valid private FQDN."
}
if ($TeamDomain -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') {
    throw "TeamDomain must be one valid Cloudflare Zero Trust team domain."
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw ".env is missing. Run prepare_windows_host.ps1 first."
}
if ([string]::IsNullOrWhiteSpace($TokenFile)) {
    $TokenFile = Join-Path $ProjectRoot "data\runtime\cloudflared-private-tunnel.token"
}
$tokenParent = Split-Path -Parent $TokenFile
if (-not (Test-Path -LiteralPath $TokenFile -PathType Leaf)) {
    throw "The managed Tunnel token file is missing. Provision it before activation."
}
$tokenValue = (Get-Content -LiteralPath $TokenFile -Raw -Encoding UTF8).Trim()
if ($tokenValue.Length -lt 64 -or $tokenValue -match '\s') {
    throw "The managed Tunnel token file is invalid."
}
$tokenValue = $null

$cloudflared = Find-SingYinCloudflared
if (-not $cloudflared) { throw "cloudflared is missing. Run prepare_cloudflare_remote_access.ps1 first." }
$versionLine = (& $cloudflared --version 2>$null | Select-Object -First 1)
if ($versionLine -notmatch '(?<year>\d{4})\.(?<month>\d{1,2})\.(?<patch>\d+)') {
    throw "The installed cloudflared version could not be verified."
}
$versionNumber = [version]::new([int]$Matches.year, [int]$Matches.month, [int]$Matches.patch)
if ($versionNumber -lt [version]::new(2025, 7, 0)) {
    throw "Private hostname routing requires cloudflared 2025.7.0 or later."
}

$endpoint = Get-SingYinConfiguredEndpoint -EnvironmentPath $envPath
$runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
$taskInspection = Get-SingYinTaskInspection `
    -TaskName $ApplicationTaskName `
    -ProjectRoot $ProjectRoot `
    -RuntimeUser $runtimeAccount.Name
if (-not $taskInspection.Exists) { throw "The '$ApplicationTaskName' task is missing or inaccessible." }
if (-not $taskInspection.Owned) { throw "The '$ApplicationTaskName' task is not owned by this project and runtime account." }

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($endpoint.Port)/healthz" -TimeoutSec 10
} catch {
    throw "The local NiceGUI health endpoint is unavailable."
}
if ($health.status -ne "ok" -or $health.database -ne "ok") {
    throw "NiceGUI or SQLite is not healthy enough for remote activation."
}

$ownerMarkerPath = Join-Path $ProjectRoot "data\runtime\cloudflare-service-owner.json"
$existingService = Get-Service cloudflared -ErrorAction SilentlyContinue
$serviceOwned = $false
if ($existingService) {
    if (-not (Test-Path -LiteralPath $ownerMarkerPath -PathType Leaf)) {
        throw "An unowned cloudflared Windows service already exists."
    }
    try {
        $owner = Get-Content -LiteralPath $ownerMarkerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $serviceOwned = $owner.owner -ceq "sing-yin-roster-v1" -and
            $owner.accessMode -ceq "private_warp" -and
            [IO.Path]::GetFullPath([string]$owner.projectRoot).TrimEnd('\') -ieq $ProjectRoot.TrimEnd('\') -and
            ([string]$owner.tunnelId).ToLowerInvariant() -ceq $TunnelId.ToLowerInvariant() -and
            ([string]$owner.privateHostname).ToLowerInvariant().TrimEnd('.') -ceq $PrivateHostname
    } catch { $serviceOwned = $false }
    if (-not $serviceOwned) { throw "The existing cloudflared service belongs to another configuration." }
}

if (-not $PSCmdlet.ShouldProcess($PrivateHostname, "Activate domain-free Cloudflare private WARP access")) { return }

$envBackup = "$envPath.before-private-warp"
$hostsPath = Join-Path $env:SystemRoot "System32\drivers\etc\hosts"
$hostsBackup = Join-Path $env:TEMP ("sing-yin-hosts-" + [guid]::NewGuid().ToString("N") + ".bak")
$installedByThisRun = $false
Copy-Item -LiteralPath $envPath -Destination $envBackup -Force
Copy-Item -LiteralPath $hostsPath -Destination $hostsBackup -Force

try {
    $hostsContent = Get-Content -LiteralPath $hostsPath -Raw -ErrorAction Stop
    $conflicts = @(
        Get-Content -LiteralPath $hostsPath |
            Where-Object { $_ -match ('^\s*(?!#)(?<ip>\S+)\s+' + [regex]::Escape($PrivateHostname) + '(?:\s|$)') } |
            Where-Object { $_ -notmatch '^\s*127\.0\.0\.1\s+' }
    )
    if ($conflicts.Count -gt 0) { throw "The Windows hosts file contains a conflicting private-hostname mapping." }
    if ($hostsContent -notmatch ('(?im)^\s*127\.0\.0\.1\s+' + [regex]::Escape($PrivateHostname) + '(?:\s|$)')) {
        $hostsContent = $hostsContent.TrimEnd() + "`r`n127.0.0.1`t$PrivateHostname`t# Sing Yin Roster private WARP`r`n"
        Set-Content -LiteralPath $hostsPath -Value $hostsContent -Encoding ASCII -NoNewline
    }

    if (-not (Test-Path -LiteralPath $tokenParent -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $tokenParent -Force
    }
    Protect-SingYinSensitivePath -Path $TokenFile -RuntimeUser $runtimeAccount.Name

    if (-not $existingService) {
        $binaryPath = '"' + $cloudflared + '" --no-autoupdate tunnel run --token-file "' + $TokenFile + '"'
        New-Service `
            -Name "cloudflared" `
            -DisplayName "Sing Yin Roster Cloudflare Private Tunnel" `
            -Description "Outbound-only private WARP connector for the Sing Yin roster host" `
            -BinaryPathName $binaryPath `
            -StartupType Automatic | Out-Null
        $installedByThisRun = $true
    }

    Set-EnvValue $envPath "SING_YIN_DEPLOYMENT_MODE" "server"
    Set-EnvValue $envPath "SING_YIN_HOST" "127.0.0.1"
    Set-EnvValue $envPath "SING_YIN_REMOTE_ACCESS_ENABLED" "true"
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_PRIVATE_WARP" "true"
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME" $PrivateHostname
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_TEAM_DOMAIN" $TeamDomain
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS" "false"
    Set-EnvValue $envPath "SING_YIN_CLOUDFLARE_ACCESS_AUD" ""
    Set-EnvValue $envPath "SING_YIN_PUBLIC_HOSTNAME" ""
    $environmentValues = Get-SingYinEnvironmentMap -Path $envPath
    if (-not $environmentValues.ContainsKey("SING_YIN_STORAGE_SECRET") -or
        ([string]$environmentValues["SING_YIN_STORAGE_SECRET"]).Length -lt 32) {
        Set-EnvValue $envPath "SING_YIN_STORAGE_SECRET" (New-StorageSecret)
    }
    Protect-SingYinSensitivePath -Path $envPath -RuntimeUser $runtimeAccount.Name

    $ownerMarker = [ordered]@{
        owner = "sing-yin-roster-v1"
        accessMode = "private_warp"
        projectRoot = $ProjectRoot
        tunnelId = $TunnelId.ToLowerInvariant()
        privateHostname = $PrivateHostname
        teamDomain = $TeamDomain
        tokenFile = [IO.Path]::GetFullPath($TokenFile)
        activatedAtUtc = [DateTime]::UtcNow.ToString("o")
    }
    $ownerMarker | ConvertTo-Json | Set-Content -LiteralPath $ownerMarkerPath -Encoding UTF8
    Protect-SingYinSensitivePath -Path $ownerMarkerPath -RuntimeUser $runtimeAccount.Name

    Start-Service cloudflared
    # A running scheduled task does not reload the updated .env when started again.
    # Stop it explicitly so the private hostname allow-list is active in the new process.
    Stop-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $ApplicationTaskName
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    do {
        Start-Sleep -Seconds 2
        $service = Get-Service cloudflared
        try {
            $response = Invoke-WebRequest `
                -UseBasicParsing `
                -Uri "http://127.0.0.1:$($endpoint.Port)/healthz" `
                -Headers @{ Host = "$PrivateHostname`:$($endpoint.Port)" } `
                -TimeoutSec 5
        } catch { $response = $null }
    } while (($service.Status -ne "Running" -or -not $response -or $response.StatusCode -ne 200) -and
        [DateTime]::UtcNow -lt $deadline)
    if ($service.Status -ne "Running") { throw "The cloudflared service did not remain running." }
    if (-not $response -or $response.StatusCode -ne 200) {
        throw "NiceGUI did not accept the configured private hostname after restart."
    }

    Remove-Item -LiteralPath $envBackup -Force
    Remove-Item -LiteralPath $hostsBackup -Force
    Write-Host "Private WARP connector is active without a public hostname." -ForegroundColor Green
    Write-Host "Remote address after WARP enrollment: http://$PrivateHostname`:$($endpoint.Port)"
} catch {
    Stop-Service cloudflared -ErrorAction SilentlyContinue
    if ($installedByThisRun) {
        sc.exe delete cloudflared | Out-Null
    }
    if (Test-Path -LiteralPath $envBackup -PathType Leaf) {
        Copy-Item -LiteralPath $envBackup -Destination $envPath -Force
        Remove-Item -LiteralPath $envBackup -Force
    }
    if (Test-Path -LiteralPath $hostsBackup -PathType Leaf) {
        Copy-Item -LiteralPath $hostsBackup -Destination $hostsPath -Force
        Remove-Item -LiteralPath $hostsBackup -Force
    }
    Remove-Item -LiteralPath $ownerMarkerPath -Force -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $ApplicationTaskName -ErrorAction SilentlyContinue
    throw
}
