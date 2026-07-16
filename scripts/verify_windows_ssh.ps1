[CmdletBinding()]
param(
    [string]$HostAlias = "sing-yin-roster-host",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-JsonReport {
    param([Parameter(Mandatory = $true)][hashtable]$Payload)
    $json = $Payload | ConvertTo-Json -Depth 6
    if (-not [string]::IsNullOrWhiteSpace($ReportPath)) {
        $parent = Split-Path -Parent $ReportPath
        if ($parent) { $null = New-Item -ItemType Directory -Path $parent -Force }
        [IO.File]::WriteAllText($ReportPath, $json, [Text.UTF8Encoding]::new($false))
    }
    $json
}

$ssh = Get-Command "ssh.exe" -ErrorAction Stop
$probeScript = @'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/healthz" -TimeoutSec 5
$sshd = Get-Service -Name "sshd" -ErrorAction Stop
$rosterTask = Get-ScheduledTask -TaskName "Sing Yin Roster Host" -ErrorAction Stop
$productionCommit = (
    & git -c safe.directory=C:/SingYinRoster -C C:\SingYinRoster rev-parse HEAD 2>$null |
        Out-String
).Trim()
[ordered]@{
    identity = $identity.Name
    computer = $env:COMPUTERNAME
    isAdministrator = $isAdmin
    sshdStatus = [string]$sshd.Status
    rosterTaskState = [string]$rosterTask.State
    productionCommit = $productionCommit
    websiteStatus = $health.status
    applicationMode = $health.applicationMode
    database = $health.database
} | ConvertTo-Json -Compress
'@
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($probeScript))
$output = & $ssh.Source `
    -o BatchMode=yes `
    -o ConnectTimeout=8 `
    -o ConnectionAttempts=1 `
    $HostAlias `
    "powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand $encoded" 2>&1
$exitCode = $LASTEXITCODE
$text = ($output | Out-String).Trim()
$report = @{
    status = "fail"
    hostAlias = $HostAlias
    completedAt = (Get-Date).ToString("o")
}

if ($exitCode -ne 0) {
    $report.error = "SSH exited with code $exitCode."
    $report.diagnostic = $text
    Write-JsonReport -Payload $report
    exit 1
}

$jsonLine = $text.Split([Environment]::NewLine) |
    Where-Object { $_.TrimStart().StartsWith("{") } |
    Select-Object -Last 1
if (-not $jsonLine) {
    $report.error = "The remote SSH probe did not return JSON."
    $report.diagnostic = $text
    Write-JsonReport -Payload $report
    exit 1
}

try {
    $remote = $jsonLine | ConvertFrom-Json
} catch {
    $report.error = "The remote SSH probe returned invalid JSON."
    $report.diagnostic = $text
    Write-JsonReport -Payload $report
    exit 1
}

$passed = (
    $remote.isAdministrator -eq $true -and
    $remote.sshdStatus -eq "Running" -and
    $remote.rosterTaskState -in @("Ready", "Running") -and
    $remote.productionCommit -match '^[0-9a-f]{40}$' -and
    $remote.websiteStatus -eq "ok" -and
    $remote.applicationMode -eq "official" -and
    $remote.database -eq "ok"
)
$report.status = if ($passed) { "pass" } else { "fail" }
$report.remote = $remote
if (-not $passed) { $report.error = "The remote identity or website health contract failed." }
Write-JsonReport -Payload $report
if (-not $passed) { exit 1 }
