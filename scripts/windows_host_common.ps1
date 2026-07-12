[CmdletBinding()]
param()

Set-StrictMode -Version Latest

$script:SingYinTaskOwnerMarker = "owner=sing-yin-roster-v1"

function Find-SingYinCloudflared {
    $command = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($path in @(
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
    )) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return (Resolve-Path -LiteralPath $path).Path
        }
    }
    return $null
}

function Get-SingYinEnvironmentMap {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "The Sing Yin environment file is missing."
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -notmatch '^\s*(?<name>SING_YIN_[A-Z0-9_]+)\s*=\s*(?<value>.*)$') { continue }
        $values[$Matches.name] = $Matches.value.Trim()
    }
    return $values
}

function Get-SingYinConfiguredEndpoint {
    param([Parameter(Mandatory = $true)][string]$EnvironmentPath)

    $values = Get-SingYinEnvironmentMap -Path $EnvironmentPath
    $hostName = if ($values.ContainsKey("SING_YIN_HOST")) { [string]$values["SING_YIN_HOST"] } else { "127.0.0.1" }
    if ($hostName -notin @("127.0.0.1", "localhost", "::1")) {
        throw "The NiceGUI host must remain loopback-only."
    }
    $rawPort = if ($values.ContainsKey("SING_YIN_PORT")) { [string]$values["SING_YIN_PORT"] } else { "8080" }
    $port = 0
    if (-not [int]::TryParse($rawPort, [ref]$port) -or $port -lt 1024 -or $port -gt 65535) {
        throw "The NiceGUI port must be between 1024 and 65535."
    }
    $mode = if ($values.ContainsKey("SING_YIN_DEPLOYMENT_MODE")) {
        ([string]$values["SING_YIN_DEPLOYMENT_MODE"]).ToLowerInvariant()
    } else {
        "local"
    }
    if ($mode -notin @("local", "server")) { throw "The deployment mode must be local or server." }
    return [pscustomobject]@{ Host = $hostName; Port = $port; Mode = $mode; Values = $values }
}

function Test-SingYinAccessRedirect {
    param(
        [Parameter(Mandatory = $true)][string]$Location,
        [Parameter(Mandatory = $true)][string]$TeamDomain
    )

    $expectedHost = $TeamDomain.Trim().ToLowerInvariant().TrimEnd('.')
    if ($expectedHost -notmatch '^[a-z0-9.-]+\.cloudflareaccess\.com$') { return $false }
    try { $uri = [Uri]$Location } catch { return $false }
    if (-not $uri.IsAbsoluteUri -or $uri.Scheme -cne "https") { return $false }
    if ($uri.DnsSafeHost.ToLowerInvariant().TrimEnd('.') -cne $expectedHost) { return $false }
    return $uri.AbsolutePath.StartsWith("/cdn-cgi/access/", [StringComparison]::OrdinalIgnoreCase)
}

function Get-SingYinTaskInspection {
    param(
        [Parameter(Mandatory = $true)][string]$TaskName,
        [Parameter(Mandatory = $true)][string]$ProjectRoot
    )

    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        return [pscustomobject]@{ Exists = $false; Owned = $false; State = "missing" }
    }
    $expectedRoot = [IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
    $expectedPython = [IO.Path]::GetFullPath((Join-Path $expectedRoot ".venv\Scripts\python.exe"))
    $matchingAction = @($task.Actions) | Where-Object {
        try {
            [IO.Path]::GetFullPath([string]$_.Execute) -ieq $expectedPython -and
            [IO.Path]::GetFullPath([string]$_.WorkingDirectory).TrimEnd('\') -ieq $expectedRoot -and
            ([string]$_.Arguments).Trim() -ceq "-X utf8 -m nicegui_app.main"
        } catch { $false }
    } | Select-Object -First 1
    $description = [string]$task.Description
    $owned = [bool]$matchingAction -and $description.Contains($script:SingYinTaskOwnerMarker)
    return [pscustomobject]@{ Exists = $true; Owned = $owned; State = [string]$task.State }
}

function Protect-SingYinSensitivePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $item = Get-Item -LiteralPath $Path -Force
    $acl = Get-Acl -LiteralPath $item.FullName
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleAll($rule) }

    $inheritance = if ($item.PSIsContainer) {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit
    } else {
        [Security.AccessControl.InheritanceFlags]::None
    }
    $propagation = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $identities = @(
        [Security.Principal.WindowsIdentity]::GetCurrent().User,
        [Security.Principal.SecurityIdentifier]::new("S-1-5-18"),
        [Security.Principal.SecurityIdentifier]::new("S-1-5-32-544")
    )
    foreach ($identity in $identities) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $identity,
            [Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance,
            $propagation,
            $allow
        )
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $item.FullName -AclObject $acl
}

function Get-SingYinAclStatus {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    $broadSids = @("S-1-1-0", "S-1-5-11", "S-1-5-32-545")
    $writeMask =
        [Security.AccessControl.FileSystemRights]::Write -bor
        [Security.AccessControl.FileSystemRights]::Modify -bor
        [Security.AccessControl.FileSystemRights]::FullControl -bor
        [Security.AccessControl.FileSystemRights]::CreateFiles -bor
        [Security.AccessControl.FileSystemRights]::WriteData
    $checked = 0
    $weak = 0
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $checked += 1
        $acl = Get-Acl -LiteralPath $path
        foreach ($rule in @($acl.Access)) {
            if ($rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow) { continue }
            try { $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value } catch { continue }
            if ($sid -in $broadSids -and (([int64]$rule.FileSystemRights -band [int64]$writeMask) -ne 0)) {
                $weak += 1
                break
            }
        }
    }
    return [pscustomobject]@{ Checked = $checked; Weak = $weak; Compliant = ($checked -gt 0 -and $weak -eq 0) }
}
