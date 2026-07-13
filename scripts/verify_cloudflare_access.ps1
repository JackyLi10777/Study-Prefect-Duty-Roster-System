[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PublicHostname,
    [Parameter(Mandatory = $true)][string]$TeamDomain,
    [ValidateRange(1024, 65535)][int]$Port = 8080
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

$PublicHostname = $PublicHostname.Trim().ToLowerInvariant().TrimEnd('.')
$TeamDomain = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
if ($PublicHostname -notmatch '^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$') { throw "Invalid public hostname." }
if ($TeamDomain -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') { throw "Invalid Cloudflare Access team domain." }

function Invoke-SingYinNoRedirectRequest {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $request = [System.Net.HttpWebRequest]::Create($Uri)
    $request.Method = "GET"
    $request.AllowAutoRedirect = $false
    $request.Timeout = 20000
    $response = $null
    try {
        $response = [System.Net.HttpWebResponse]$request.GetResponse()
    } catch [System.Net.WebException] {
        $response = [System.Net.HttpWebResponse]$_.Exception.Response
        if (-not $response) { throw }
    }
    try {
        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Location = [string]$response.Headers["Location"]
        }
    } finally {
        if ($response) { $response.Dispose() }
    }
}

try {
    $local = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 10
} catch {
    throw "Local health check failed. Remote access cannot be trusted until the local application is healthy."
}
if ($local.status -ne "ok" -or $local.database -ne "ok") {
    throw "Local health is degraded (status=$($local.status), database=$($local.database))."
}

try {
    $publicProbe = Invoke-SingYinNoRedirectRequest -Uri "https://$PublicHostname/"
} catch {
    throw "Public hostname could not be reached: $($_.Exception.Message)"
}

if ($publicProbe.StatusCode -ne 200) {
    throw "Public guest page is unavailable (HTTP $($publicProbe.StatusCode))."
}

try {
    $authProbe = Invoke-SingYinNoRedirectRequest -Uri "https://$PublicHostname/auth/login"
} catch {
    throw "Administrator login route could not be reached: $($_.Exception.Message)"
}

$accessRedirect = $authProbe.StatusCode -in @(301, 302, 303, 307, 308) -and (
    Test-SingYinAccessRedirect -Location $authProbe.Location -TeamDomain $TeamDomain
)
if (-not $accessRedirect) {
    throw "FAIL CLOSED: the administrator login route was not redirected to Cloudflare Access (HTTP $($authProbe.StatusCode)). Stop the cloudflared service."
}

Write-Host "Public guest page verified: HTTP 200." -ForegroundColor Green
Write-Host "Cloudflare Access gate verified: the administrator login route redirects before it reaches NiceGUI." -ForegroundColor Green
Write-Host "Redirect host: $(([Uri]$authProbe.Location).Host)"
