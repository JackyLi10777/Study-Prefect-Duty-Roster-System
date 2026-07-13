[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$PrivateHostname = "roster.singyin.internal"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$endpoint = Get-SingYinConfiguredEndpoint -EnvironmentPath (Join-Path $ProjectRoot ".env")
$checks = @()

function Add-Check([string]$Code, [bool]$Passed, [string]$Message) {
    $script:checks += [ordered]@{ code = $Code; status = $(if ($Passed) { "pass" } else { "fail" }); message = $Message }
}

$service = Get-Service cloudflared -ErrorAction SilentlyContinue
Add-Check "connector_service" ($service -and $service.Status -eq "Running") `
    $(if ($service -and $service.Status -eq "Running") { "The private Tunnel connector is running." } else { "The private Tunnel connector is not running." })

$resolved = @([Net.Dns]::GetHostAddresses($PrivateHostname) | ForEach-Object { $_.ToString() })
Add-Check "private_dns_origin" ($resolved -contains "127.0.0.1") `
    $(if ($resolved -contains "127.0.0.1") { "The origin resolves the private hostname to loopback." } else { "The private hostname does not resolve to loopback on the origin." })

try {
    $response = Invoke-WebRequest `
        -UseBasicParsing `
        -Uri "http://127.0.0.1:$($endpoint.Port)/healthz" `
        -Headers @{ Host = "$PrivateHostname`:$($endpoint.Port)" } `
        -TimeoutSec 10
    $hostHeaderOk = $response.StatusCode -eq 200
} catch { $hostHeaderOk = $false }
Add-Check "private_host_header" $hostHeaderOk `
    $(if ($hostHeaderOk) { "NiceGUI accepts only the declared private hostname and loopback hosts." } else { "NiceGUI did not accept the declared private hostname." })

$ownerMarkerPath = Join-Path $ProjectRoot "data\runtime\cloudflare-service-owner.json"
$ownerOk = $false
if (Test-Path -LiteralPath $ownerMarkerPath -PathType Leaf) {
    try {
        $owner = Get-Content -LiteralPath $ownerMarkerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $ownerOk = $owner.owner -ceq "sing-yin-roster-v1" -and
            $owner.accessMode -ceq "private_warp" -and
            ([string]$owner.privateHostname).ToLowerInvariant().TrimEnd('.') -ceq $PrivateHostname.ToLowerInvariant().TrimEnd('.')
    } catch { $ownerOk = $false }
}
Add-Check "ownership_marker" $ownerOk `
    $(if ($ownerOk) { "The connector is owned by this project and private hostname." } else { "The connector ownership marker is missing or invalid." })

$failed = @($checks | Where-Object { $_.status -eq "fail" }).Count
[ordered]@{
    schemaVersion = 1
    mode = "private_warp"
    status = $(if ($failed -eq 0) { "pass" } else { "fail" })
    remoteAddress = "http://$PrivateHostname`:$($endpoint.Port)"
    checks = $checks
} | ConvertTo-Json -Depth 5

if ($failed -gt 0) { exit 1 }
