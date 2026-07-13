[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$ApplicationTaskName = "Sing Yin Roster Host",
    [string]$RuntimeUser = "SingYinRosterSvc",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }

$checks = [Collections.Generic.List[object]]::new()
function Add-DoctorCheck([string]$Code, [string]$Status, [string]$Message) {
    $checks.Add([ordered]@{ code = $Code; status = $Status; message = $Message })
}

if ($env:OS -ne "Windows_NT") {
    Add-DoctorCheck "windows_host" "fail" "This doctor is for the selected Windows dedicated-host model."
    [ordered]@{ schemaVersion = 1; status = "fail"; checks = $checks } | ConvertTo-Json -Depth 5
    exit 1
}

try { $ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path } catch {
    Add-DoctorCheck "project_root" "fail" "The project root is unavailable."
    [ordered]@{ schemaVersion = 1; status = "fail"; checks = $checks } | ConvertTo-Json -Depth 5
    exit 1
}
$envPath = Join-Path $ProjectRoot ".env"
$runtimeAccount = $null
try {
    $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser
    Add-DoctorCheck "runtime_account" "pass" "The dedicated runtime account exists, is enabled, and is not an administrator."
} catch {
    Add-DoctorCheck "runtime_account" "fail" "The dedicated non-administrator runtime account is unavailable or unsafe."
}
try {
    $endpoint = Get-SingYinConfiguredEndpoint -EnvironmentPath $envPath
    Add-DoctorCheck "loopback_origin" "pass" "NiceGUI is configured for a loopback-only origin."
    Add-DoctorCheck "deployment_profile" "pass" "The declared profile is $($endpoint.Mode)."
} catch {
    Add-DoctorCheck "loopback_origin" "fail" "The local endpoint configuration is missing or unsafe."
    $endpoint = [pscustomobject]@{ Host = "127.0.0.1"; Port = 8080; Mode = "local"; Values = @{} }
}

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    Add-DoctorCheck "python_runtime" "pass" "The project Python virtual environment is present."
} else {
    Add-DoctorCheck "python_runtime" "fail" "The project Python virtual environment is missing."
}

$taskInspection = Get-SingYinTaskInspection -TaskName $ApplicationTaskName -ProjectRoot $ProjectRoot -RuntimeUser $RuntimeUser
if ($taskInspection.Owned) {
    Add-DoctorCheck "startup_task" "pass" "The Windows startup task belongs to this project root."
} elseif ($taskInspection.Exists) {
    Add-DoctorCheck "startup_task" "fail" "A same-named Windows task points elsewhere and will not be controlled."
} else {
    Add-DoctorCheck "startup_task" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
        "The managed Windows startup task has not been registered yet."
}

$listenerStatus = "unknown"
if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $endpoint.Port -ErrorAction SilentlyContinue)
    if ($listeners.Count -eq 0) {
        $listenerStatus = "stopped"
        Add-DoctorCheck "origin_listener" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
            "Nothing is listening on the configured local port."
    } elseif (@($listeners | Where-Object { $_.LocalAddress -notin @("127.0.0.1", "::1") }).Count -gt 0) {
        $listenerStatus = "unsafe"
        Add-DoctorCheck "origin_listener" "fail" "A configured-port listener is reachable beyond loopback."
    } else {
        $listenerStatus = "loopback"
        Add-DoctorCheck "origin_listener" "pass" "The configured-port listener is loopback-only."
    }
} else {
    Add-DoctorCheck "origin_listener" "warning" "Windows could not inspect the configured port listener."
}

if ($listenerStatus -eq "loopback") {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($endpoint.Port)/healthz" -TimeoutSec 5
        if ($health.status -eq "ok" -and $health.database -eq "ok") {
            Add-DoctorCheck "application_health" "pass" "NiceGUI and SQLite report healthy."
        } else {
            Add-DoctorCheck "application_health" "fail" "NiceGUI reports a degraded local state."
        }
    } catch {
        Add-DoctorCheck "application_health" "fail" "The local health endpoint did not answer safely."
    }
} else {
    Add-DoctorCheck "application_health" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
        "Application health is unavailable while the host is stopped."
}

$cloudflared = Find-SingYinCloudflared
if ($cloudflared) {
    $versionLine = (& $cloudflared --version 2>$null | Select-Object -First 1)
    Add-DoctorCheck "cloudflared_binary" "pass" "cloudflared is installed$($(if ($versionLine){': ' + $versionLine}else{''}))."
} else {
    Add-DoctorCheck "cloudflared_binary" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
        "cloudflared is not installed yet."
}

$cloudflaredService = Get-Service cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredService) {
    $ownerMarkerPath = Join-Path $ProjectRoot "data\runtime\cloudflare-service-owner.json"
    $owned = $false
    if (Test-Path -LiteralPath $ownerMarkerPath -PathType Leaf) {
        try {
            $owner = Get-Content -LiteralPath $ownerMarkerPath -Encoding UTF8 -Raw | ConvertFrom-Json
            $owned = $owner.owner -ceq "sing-yin-roster-v1" -and
                [IO.Path]::GetFullPath([string]$owner.projectRoot).TrimEnd('\') -ieq $ProjectRoot.TrimEnd('\')
        } catch { $owned = $false }
    }
    if (-not $owned) {
        Add-DoctorCheck "cloudflared_service" "fail" "A cloudflared service exists without this project's ownership marker."
    } elseif ($cloudflaredService.Status -eq [System.ServiceProcess.ServiceControllerStatus]::Running) {
        Add-DoctorCheck "cloudflared_service" "pass" "The owned cloudflared service is running."
    } else {
        Add-DoctorCheck "cloudflared_service" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
            "The owned cloudflared service is stopped."
    }
} else {
    Add-DoctorCheck "cloudflared_service" $(if ($endpoint.Mode -eq "server") { "fail" } else { "deferred" }) `
        "No Tunnel service is active; local-only use remains unchanged."
}

$sensitivePaths = @(
    $envPath,
    (Join-Path $ProjectRoot "data\runtime"),
    (Join-Path $ProjectRoot "data\backups"),
    (Join-Path $ProjectRoot "logs")
)
$requiredSid = if ($runtimeAccount) { $runtimeAccount.Sid.Value } else { "" }
$aclState = Get-SingYinAclStatus -Paths $sensitivePaths -RequiredIdentitySid $requiredSid
if ($aclState.Compliant) {
    Add-DoctorCheck "local_permissions" "pass" "Sensitive local paths are restricted to privileged host identities."
} else {
    Add-DoctorCheck "local_permissions" $(if ($endpoint.Mode -eq "server") { "fail" } else { "warning" }) `
        "Sensitive local paths still allow a broad Windows group to write. Run prepare_windows_host.ps1."
}

try {
    $drive = Get-Item -LiteralPath $ProjectRoot
    $rootName = [IO.Path]::GetPathRoot($drive.FullName)
    $driveInfo = [IO.DriveInfo]::new($rootName)
    $freeGb = [math]::Round($driveInfo.AvailableFreeSpace / 1GB, 1)
    Add-DoctorCheck "disk_space" $(if ($freeGb -ge 30) { "pass" } else { "warning" }) `
        "The project drive has $freeGb GB free."
} catch {
    Add-DoctorCheck "disk_space" "warning" "Free disk space could not be measured."
}

if ((Test-Path -LiteralPath $venvPython) -and (Test-Path -LiteralPath (Join-Path $ProjectRoot "scripts\check_deployment_readiness.py"))) {
    $readinessOutput = & $venvPython -X utf8 (Join-Path $ProjectRoot "scripts\check_deployment_readiness.py") 2>$null
    if ($LASTEXITCODE -eq 0) {
        Add-DoctorCheck "application_readiness" "pass" "Database, storage-secret, and managed-backup readiness were inspected."
    } else {
        Add-DoctorCheck "application_readiness" "fail" "The application readiness check failed."
    }
}

$privateWarpActive = $endpoint.Mode -eq "server" -and
    $endpoint.Values.ContainsKey("SING_YIN_CLOUDFLARE_PRIVATE_WARP") -and
    ([string]$endpoint.Values["SING_YIN_CLOUDFLARE_PRIVATE_WARP"]).ToLowerInvariant() -in @("1", "true", "yes", "on")
if ($privateWarpActive -and $endpoint.Values.ContainsKey("SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME")) {
    try {
        & (Join-Path $PSScriptRoot "verify_cloudflare_private_warp.ps1") `
            -ProjectRoot $ProjectRoot `
            -PrivateHostname ([string]$endpoint.Values["SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME"]) | Out-Null
        Add-DoctorCheck "access_gate" "pass" "The domain-free private WARP origin and connector checks passed."
    } catch {
        Add-DoctorCheck "access_gate" "fail" "The private WARP origin or connector verification failed."
    }
} elseif ($endpoint.Mode -eq "server" -and
    $endpoint.Values.ContainsKey("SING_YIN_PUBLIC_HOSTNAME") -and
    -not [string]::IsNullOrWhiteSpace([string]$endpoint.Values["SING_YIN_PUBLIC_HOSTNAME"]) -and
    $endpoint.Values.ContainsKey("SING_YIN_CLOUDFLARE_TEAM_DOMAIN")) {
    try {
        & (Join-Path $PSScriptRoot "verify_cloudflare_access.ps1") `
            -PublicHostname ([string]$endpoint.Values["SING_YIN_PUBLIC_HOSTNAME"]) `
            -TeamDomain ([string]$endpoint.Values["SING_YIN_CLOUDFLARE_TEAM_DOMAIN"]) `
            -Port $endpoint.Port | Out-Null
        Add-DoctorCheck "access_gate" "pass" "Unauthenticated traffic reaches the exact configured Access tenant first."
    } catch {
        Add-DoctorCheck "access_gate" "fail" "The exact Cloudflare Access redirect check failed."
    }
} else {
    Add-DoctorCheck "access_gate" "deferred" "Remote Access is not active in the local profile."
}

$statuses = @($checks | ForEach-Object { [string]$_.status })
$overall = if ($statuses -contains "fail") { "fail" } elseif ($statuses -contains "warning") { "warning" } else { "pass" }
[ordered]@{
    schemaVersion = 1
    project = "sing-yin-study-prefect-duty-roster"
    status = $overall
    deploymentMode = $endpoint.Mode
    checks = $checks
} | ConvertTo-Json -Depth 5

if ($overall -eq "fail" -or ($Strict -and $overall -eq "warning")) { exit 1 }
exit 0
