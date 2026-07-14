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
    $request.UserAgent = "Mozilla/5.0 (compatible; SingYinRosterVerifier/1.0)"
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

function Invoke-SingYinAccessLoginPageRequest {
    param([Parameter(Mandatory = $true)][string]$Uri)

    $request = [System.Net.HttpWebRequest]::Create($Uri)
    $request.Method = "GET"
    $request.UserAgent = "Mozilla/5.0 (compatible; SingYinRosterVerifier/1.0)"
    $request.AllowAutoRedirect = $true
    $request.MaximumAutomaticRedirections = 5
    $request.CookieContainer = New-Object System.Net.CookieContainer
    $request.Timeout = 20000
    $response = $null
    $reader = $null
    try {
        $response = [System.Net.HttpWebResponse]$request.GetResponse()
        if ($response.ContentLength -gt 524288) {
            throw "Cloudflare Access login page exceeded the 512 KiB verification limit."
        }
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        $body = $reader.ReadToEnd()
        if ($body.Length -gt 524288) {
            throw "Cloudflare Access login page exceeded the 512 KiB verification limit."
        }
        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            FinalHost = $response.ResponseUri.Host.Trim().ToLowerInvariant().TrimEnd('.')
            Body = $body
        }
    } finally {
        if ($reader) { $reader.Dispose() }
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

try {
    $loginPage = Invoke-SingYinAccessLoginPageRequest -Uri "https://$PublicHostname/auth/login"
} catch {
    throw "Cloudflare Access login page could not be verified: $($_.Exception.Message)"
}

$oneTimePinForm = (
    $loginPage.StatusCode -eq 200 -and
    $loginPage.FinalHost -eq $TeamDomain -and
    $loginPage.Body -match '(?i)id=["'']totp-form["'']' -and
    $loginPage.Body -match '(?i)type=["'']email["'']' -and
    $loginPage.Body -match '(?i)verify-code'
)
$unexpectedAccountOAuth = $loginPage.Body -match '(?i)dash\.cloudflare\.com/oauth2|Unknown app'
if (-not $oneTimePinForm -or $unexpectedAccountOAuth) {
    throw "FAIL CLOSED: the expected Cloudflare One-time PIN email form was not found, or an unexpected Dashboard OAuth page was detected."
}

Write-Host "Public guest page verified: HTTP 200." -ForegroundColor Green
Write-Host "Cloudflare Access gate verified: the administrator login route redirects before it reaches NiceGUI." -ForegroundColor Green
Write-Host "Redirect host: $(([Uri]$authProbe.Location).Host)"
Write-Host "Cloudflare One-time PIN verified: email form present; Dashboard OAuth and Unknown app are absent." -ForegroundColor Green
