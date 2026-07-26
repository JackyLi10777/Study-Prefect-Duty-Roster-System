[CmdletBinding()]
param(
    [string]$ExpectedSourceFingerprint = "",
    [string]$ObservedSourceFingerprint = "",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Get-AgeBucket {
    param([Nullable[datetime]]$Timestamp)
    if ($null -eq $Timestamp) { return "unknown" }
    $days = [math]::Max(0, ((Get-Date) - $Timestamp.Value).TotalDays)
    if ($days -lt 1) { return "lt_1_day" }
    if ($days -lt 3) { return "1_to_3_days" }
    if ($days -lt 8) { return "4_to_7_days" }
    return "over_7_days"
}

function Get-FreeSpaceBucket {
    try {
        $free = (Get-PSDrive -Name C -ErrorAction Stop).Free
        if ($free -lt 5GB) { return "under_5_gib" }
        if ($free -lt 20GB) { return "5_to_20_gib" }
        if ($free -lt 100GB) { return "20_to_100_gib" }
        return "over_100_gib"
    }
    catch { return "unknown" }
}

function Get-EventCount {
    param(
        [string]$LogName,
        [int[]]$Ids,
        [datetime]$StartTime
    )
    try {
        return @(
            Get-WinEvent -FilterHashtable @{
                LogName = $LogName
                Id = $Ids
                StartTime = $StartTime
            } -ErrorAction Stop
        ).Count
    }
    catch { return $null }
}

$defender = [ordered]@{
    available = $false
    serviceStatus = "unavailable"
    realtimeProtection = $null
    signatureAge = "unknown"
    detectionCount7d = $null
}
try {
    $service = Get-Service -Name WinDefend -ErrorAction Stop
    $defender.available = $true
    $defender.serviceStatus = $service.Status.ToString().ToLowerInvariant()
}
catch {}
try {
    $status = Get-MpComputerStatus -ErrorAction Stop
    $defender.available = $true
    $defender.realtimeProtection = [bool]$status.RealTimeProtectionEnabled
    $defender.signatureAge = Get-AgeBucket -Timestamp $status.AntivirusSignatureLastUpdated
}
catch {}
$defender.detectionCount7d = Get-EventCount `
    -LogName "Microsoft-Windows-Windows Defender/Operational" `
    -Ids @(1116, 1117) `
    -StartTime (Get-Date).AddDays(-7)

$firewall = [ordered]@{
    available = $false
    enabledProfileCount = $null
    disabledProfileCount = $null
}
try {
    $profiles = @(Get-NetFirewallProfile -ErrorAction Stop)
    $firewall.available = $true
    $firewall.enabledProfileCount = @($profiles | Where-Object Enabled).Count
    $firewall.disabledProfileCount = @($profiles | Where-Object { -not $_.Enabled }).Count
}
catch {}

$scheduledTask = [ordered]@{
    hostTaskPresent = $false
    stateCode = "unavailable"
}
try {
    $task = Get-ScheduledTask -TaskName "Sing Yin Roster Host" -ErrorAction Stop
    $scheduledTask.hostTaskPresent = $true
    $scheduledTask.stateCode = $task.State.ToString().ToLowerInvariant()
}
catch {}

$cloudflare = [ordered]@{
    servicePresent = $false
    serviceStatus = "unavailable"
}
try {
    $cloudflareService = Get-Service -Name cloudflared -ErrorAction Stop
    $cloudflare.servicePresent = $true
    $cloudflare.serviceStatus = $cloudflareService.Status.ToString().ToLowerInvariant()
}
catch {}

$fingerprintMatch = $null
if ($ExpectedSourceFingerprint -and $ObservedSourceFingerprint) {
    $fingerprintMatch = [string]::Equals(
        $ExpectedSourceFingerprint.Trim(),
        $ObservedSourceFingerprint.Trim(),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

$summary = [ordered]@{
    schemaVersion = 1
    collectedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    evidenceClass = "privacy_bounded_host_security_summary"
    platform = "windows"
    defender = $defender
    firewall = $firewall
    scheduledTask = $scheduledTask
    eventIndicators = [ordered]@{
        securityLogClearedCount7d = Get-EventCount -LogName "Security" -Ids @(1102) -StartTime (Get-Date).AddDays(-7)
        sshAuthenticationFailureCount24h = Get-EventCount -LogName "OpenSSH/Operational" -Ids @(4) -StartTime (Get-Date).AddHours(-24)
    }
    storage = [ordered]@{
        systemDriveFreeSpace = Get-FreeSpaceBucket
    }
    release = [ordered]@{
        fingerprintMatch = $fingerprintMatch
    }
    cloudflare = $cloudflare
    exclusions = @(
        "usernames",
        "hostnames",
        "ip_addresses",
        "full_paths",
        "command_lines",
        "raw_event_xml",
        "student_data"
    )
}

$json = $summary | ConvertTo-Json -Depth 6
if ($OutputPath) {
    $fullPath = [System.IO.Path]::GetFullPath($OutputPath)
    $parent = Split-Path -Parent $fullPath
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Output directory does not exist."
    }
    $temporary = Join-Path $parent ("." + [System.IO.Path]::GetFileName($fullPath) + ".tmp")
    [System.IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $fullPath -Force
}
$json
