[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicHostname,
    [Parameter(Mandatory = $true)][string]$TeamDomain
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PublicHostname = $PublicHostname.Trim().ToLowerInvariant().TrimEnd('.')
$TeamDomain = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
if ($PublicHostname -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$') { throw "Invalid public hostname." }
if ($TeamDomain -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') { throw "Invalid Cloudflare Access team domain." }

try {
    $local = Invoke-RestMethod -Uri "http://127.0.0.1:8080/healthz" -TimeoutSec 10
} catch {
    throw "Local health check failed. Remote access cannot be trusted until the local application is healthy."
}
if ($local.status -ne "ok" -or $local.database -ne "ok") {
    throw "Local health is degraded (status=$($local.status), database=$($local.database))."
}

$location = ""
$statusCode = 0
try {
    $response = Invoke-WebRequest -Uri "https://$PublicHostname/" -MaximumRedirection 0 -TimeoutSec 20 -UseBasicParsing
    $statusCode = [int]$response.StatusCode
    $location = [string]$response.Headers.Location
} catch {
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        $location = [string]$_.Exception.Response.Headers.Location
    } else {
        throw "Public hostname could not be reached: $($_.Exception.Message)"
    }
}

$accessRedirect = $statusCode -in @(301, 302, 303, 307, 308) -and (
    $location -match [regex]::Escape($TeamDomain) -or $location -match '\.cloudflareaccess\.com'
)
if (-not $accessRedirect) {
    throw "FAIL CLOSED: unauthenticated traffic was not redirected to Cloudflare Access (HTTP $statusCode). Stop the cloudflared service."
}

Write-Host "Cloudflare Access gate verified: unauthenticated traffic is redirected before it reaches NiceGUI." -ForegroundColor Green
Write-Host "Redirect host: $(([Uri]$location).Host)"
