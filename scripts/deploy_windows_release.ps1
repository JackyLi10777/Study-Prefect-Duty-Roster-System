[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [string]$HostRoot = "C:\SingYinRoster",
    [Parameter(Mandatory = $true)][string]$ReleaseRef,
    [string]$TaskName = "Sing Yin Roster Host",
    [string]$RuntimeUser = "SingYinRosterSvc",
    [string]$EnvironmentOverlayPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    # Bind the release to the repository that owns this script instead of a
    # mutable machine-specific checkout. Operators may still pass -SourceRoot
    # explicitly when deploying from a separate verified worktree.
    $SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Protect-ReportText([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    $redacted = [regex]::Replace(
        $Text,
        '(?i)\b(Bearer)\s+[A-Za-z0-9._~+/-]+=*',
        '$1 <redacted>'
    )
    $redacted = [regex]::Replace(
        $redacted,
        '(?i)\b(token|secret|password|authorization|cookie)(\s*[:=]\s*|\s+)([^\s,;]+)',
        '$1$2<redacted>'
    )
    return $redacted
}

function Write-DeploymentReport([System.Collections.IDictionary]$Payload) {
    $directory = Split-Path -Parent $script:ReportPath
    if (-not (Test-Path -LiteralPath $directory)) {
        $null = New-Item -ItemType Directory -Path $directory -Force
    }
    $Payload | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $script:ReportPath -Encoding UTF8
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    Push-Location -LiteralPath $WorkingDirectory
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $nativeOutput = @(& $Executable @Arguments 2>&1)
        $nativeExitCode = $LASTEXITCODE
        $lines = @($nativeOutput | ForEach-Object { Protect-ReportText $_.ToString() })
        if ($lines.Count -gt 0) {
            $lines | ForEach-Object { Write-Host $_ }
            Add-Content -LiteralPath $script:NativeLogPath -Encoding UTF8 -Value @(
                ""
                "[$([DateTimeOffset]::UtcNow.ToString('o'))] $Executable"
                $lines
            )
        }
        if ($nativeExitCode -ne 0) {
            throw "$Executable failed with exit code $nativeExitCode. See $script:NativeLogPath."
        }
        return $nativeOutput
    } finally {
        $ErrorActionPreference = $previousPreference
        Pop-Location
    }
}

function Get-GitValue {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $value = @(& git.exe -C $Repository @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed."
    }
    return ($value | Out-String).Trim()
}

function Assert-ImmutableReleaseTag {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$TagName
    )
    $tagReference = "refs/tags/$TagName"
    $tagType = Get-GitValue -Repository $Repository -Arguments @("cat-file", "-t", $tagReference)
    if ($tagType -cne "tag") {
        throw "The release reference must be an annotated immutable Git tag."
    }
    $localTagObject = Get-GitValue -Repository $Repository -Arguments @(
        "rev-parse",
        "$tagReference^{tag}"
    )
    $localCommit = Get-GitValue -Repository $Repository -Arguments @(
        "rev-parse",
        "$tagReference^{commit}"
    )
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $remoteLines = @(
            & git.exe -C $Repository ls-remote --tags origin $tagReference "$tagReference^{}" 2>&1
        )
        $remoteExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($remoteExitCode -ne 0) {
        throw "The release tag could not be verified against origin."
    }
    $escapedReference = [regex]::Escape($tagReference)
    $remoteTagObject = $null
    $remoteCommit = $null
    foreach ($rawLine in $remoteLines) {
        $line = $rawLine.ToString().Trim()
        if ($line -match "^([0-9a-f]{40})\s+$escapedReference$") {
            $remoteTagObject = $Matches[1]
        } elseif ($line -match "^([0-9a-f]{40})\s+$escapedReference\^\{\}$") {
            $remoteCommit = $Matches[1]
        }
    }
    if ($remoteTagObject -cne $localTagObject -or $remoteCommit -cne $localCommit) {
        throw "The local release tag does not match the immutable tag published to origin."
    }
    return $localCommit
}

function Get-CurrentReleaseFingerprint {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Repository
    )
    $code = @'
import json
from nicegui_app.release_evidence import release_source_fingerprint
fingerprint, file_count = release_source_fingerprint()
print(json.dumps({'fingerprint': fingerprint, 'fileCount': file_count}))
'@
    $previousPreference = $ErrorActionPreference
    try {
        Push-Location -LiteralPath $Repository
        $ErrorActionPreference = "Continue"
        $output = @(& $Python -X utf8 -c $code 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
        Pop-Location
    }
    if ($exitCode -ne 0) {
        throw "The release source fingerprint could not be calculated."
    }
    $jsonLine = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace($_.ToString()) })[-1]
    try {
        return ($jsonLine.ToString() | ConvertFrom-Json)
    } catch {
        throw "The release source fingerprint result was not valid JSON."
    }
}

function Read-HostEnvironmentValues([string]$EnvironmentPath) {
    # The shared parser rejects malformed SING_YIN_ entries, duplicate keys,
    # and C0/DEL control characters.  Do not maintain a second, permissive
    # parser in the release boundary.
    return Get-SingYinEnvironmentMap -Path $EnvironmentPath
}

function Import-HostEnvironment([string]$EnvironmentPath) {
    $values = Read-HostEnvironmentValues -EnvironmentPath $EnvironmentPath
    foreach ($name in $values.Keys) {
        [Environment]::SetEnvironmentVariable($name, [string]$values[$name], "Process")
    }
    return $values
}

function Merge-HostEnvironmentValues {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Base,
        [Parameter(Mandatory = $true)][hashtable]$Overlay
    )
    $values = @{}
    foreach ($name in $Base.Keys) {
        $values[[string]$name] = [string]$Base[$name]
    }
    foreach ($name in $Overlay.Keys) {
        $values[[string]$name] = [string]$Overlay[$name]
    }
    return $values
}

function Get-WorkerGatewaySettings {
    param(
        [Parameter(Mandatory = $true)][string]$ConfigurationPath,
        [Parameter(Mandatory = $true)][string]$Python
    )
    if (-not (Test-Path -LiteralPath $ConfigurationPath -PathType Leaf)) {
        throw "The Cloudflare Worker configuration is missing."
    }
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "The verified source Python environment is missing."
    }
    $code = @'
import json
from pathlib import Path
import re
import sys


class BlockCommentError(ValueError):
    pass


class DuplicateKeyError(ValueError):
    pass


def strip_jsonc_line_comments(source: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
            output.append(character)
            index += 1
            continue
        if character == "/" and following == "/":
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue
        if (character == "/" and following == "*") or (character == "*" and following == "/"):
            raise BlockCommentError
        output.append(character)
        index += 1
    return "".join(output)


def remove_jsonc_trailing_commas(source: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    for index, character in enumerate(source):
        if in_string:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            output.append(character)
            continue
        if character == ",":
            following = index + 1
            while following < len(source) and source[following].isspace():
                following += 1
            if following < len(source) and source[following] in "}]":
                continue
        output.append(character)
    return "".join(output)


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def fail(message: str) -> None:
    print(json.dumps({"ok": False, "error": message}, separators=(",", ":")))


try:
    source = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    configuration = json.loads(
        remove_jsonc_trailing_commas(strip_jsonc_line_comments(source)),
        object_pairs_hook=strict_object,
    )
    if not isinstance(configuration, dict):
        raise ValueError("The Cloudflare Worker configuration root must be an object.")
    worker_vars = configuration.get("vars")
    if not isinstance(worker_vars, dict):
        raise ValueError("The Cloudflare Worker configuration must define exactly one top-level vars object.")
    if "ORIGIN_PORT" not in worker_vars or type(worker_vars["ORIGIN_PORT"]) is not int:
        raise ValueError("The Cloudflare Worker top-level vars must define one integer ORIGIN_PORT.")
    origin_port = worker_vars["ORIGIN_PORT"]
    if not 1024 <= origin_port <= 65535:
        raise ValueError("The Cloudflare Worker ORIGIN_PORT must be between 1024 and 65535.")
    if "AUTH_EPOCH" not in worker_vars or type(worker_vars["AUTH_EPOCH"]) is not int:
        raise ValueError("The Cloudflare Worker top-level vars must define one integer AUTH_EPOCH.")
    auth_epoch = worker_vars["AUTH_EPOCH"]
    if auth_epoch < 0 or auth_epoch > 9223372036854775807:
        raise ValueError("The Cloudflare Worker AUTH_EPOCH must be between 0 and 9223372036854775807.")
    origin_principal_kid = worker_vars.get("ORIGIN_PRINCIPAL_KID")
    if not isinstance(origin_principal_kid, str):
        raise ValueError("The Cloudflare Worker top-level vars must define one string ORIGIN_PRINCIPAL_KID.")
    if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", origin_principal_kid) is None:
        raise ValueError("The Cloudflare Worker ORIGIN_PRINCIPAL_KID contains unsupported characters.")
except BlockCommentError:
    fail("The Cloudflare Worker gateway settings do not support block comments.")
except DuplicateKeyError:
    fail("The Cloudflare Worker configuration contains duplicate JSON object keys.")
except json.JSONDecodeError:
    fail("The Cloudflare Worker configuration is not valid JSONC.")
except (OSError, UnicodeError):
    fail("The Cloudflare Worker configuration could not be read safely.")
except ValueError as exc:
    fail(str(exc))
else:
    print(json.dumps({
        "ok": True,
        "originPort": origin_port,
        "authEpoch": auth_epoch,
        "originPrincipalKid": origin_principal_kid,
    }, separators=(",", ":")))
'@
    # Windows PowerShell 5.1 rewrites quotes inside a native-process `-c`
    # argument. Encode the audited parser so Python receives the exact source.
    $encodedCode = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($code))
    $bootstrap = "import base64,sys;code=base64.b64decode(sys.argv.pop(1));exec(code)"
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $Python -X utf8 -c $bootstrap $encodedCode $ConfigurationPath 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne 0 -or $output.Count -ne 1) {
        throw "The Cloudflare Worker configuration parser failed closed."
    }
    try {
        $payload = [string]$output[0] | ConvertFrom-Json -ErrorAction Stop
    } catch {
        throw "The Cloudflare Worker configuration parser returned an invalid result."
    }
    if ($payload.ok -ne $true) {
        throw [string]$payload.error
    }
    return [pscustomobject]@{
        OriginPort = [int]$payload.originPort
        AuthEpoch = [long]$payload.authEpoch
        OriginPrincipalKid = [string]$payload.originPrincipalKid
    }
}

function Assert-UnifiedGuestHostSettings([hashtable]$Values) {
    $required = @(
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET"
    )
    foreach ($name in $required) {
        if (-not $Values.ContainsKey($name) -or [string]::IsNullOrWhiteSpace([string]$Values[$name])) {
            throw "The protected host environment is missing required v1.2 setting $name."
        }
    }
    if ([string]$Values["SING_YIN_UNIFIED_GUEST"] -notmatch '^(0|1|true|false)$') {
        throw "SING_YIN_UNIFIED_GUEST must be 0, 1, true, or false."
    }
    if ([string]$Values["SING_YIN_REQUIRE_GATEWAY_PRINCIPAL"] -notmatch '^(1|true)$') {
        throw "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL must be 1 or true for a controlled release."
    }
    if ([string]$Values["AUTH_EPOCH"] -notmatch '^\d+$') {
        throw "AUTH_EPOCH must be a non-negative integer."
    }
    if ([string]$Values["ORIGIN_PRINCIPAL_KID"] -notmatch '^[A-Za-z0-9._-]{1,64}$') {
        throw "ORIGIN_PRINCIPAL_KID contains unsupported characters."
    }
}

function Assert-WorkerHostGatewayParity {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Values,
        [Parameter(Mandatory = $true)]$WorkerSettings
    )
    Assert-UnifiedGuestHostSettings -Values $Values

    $hostName = if ($Values.ContainsKey("SING_YIN_HOST")) {
        [string]$Values["SING_YIN_HOST"]
    } else {
        "127.0.0.1"
    }
    if ($hostName -notin @("127.0.0.1", "localhost", "::1")) {
        throw "The NiceGUI host must remain loopback-only."
    }
    $rawPort = if ($Values.ContainsKey("SING_YIN_PORT")) {
        [string]$Values["SING_YIN_PORT"]
    } else {
        "8080"
    }
    [int]$hostPort = 0
    if (-not [int]::TryParse($rawPort, [ref]$hostPort) -or $hostPort -lt 1024 -or $hostPort -gt 65535) {
        throw "The NiceGUI port must be between 1024 and 65535."
    }
    if ([int]$WorkerSettings.OriginPort -ne $hostPort) {
        throw (
            "The protected host SING_YIN_PORT ($hostPort) does not match " +
            "the Cloudflare Worker ORIGIN_PORT ($($WorkerSettings.OriginPort)). Update and verify " +
            "both ends in the same immutable release before deployment."
        )
    }

    [long]$hostAuthEpoch = 0
    if (-not [long]::TryParse([string]$Values["AUTH_EPOCH"], [ref]$hostAuthEpoch)) {
        throw "The protected host AUTH_EPOCH exceeds the supported integer range."
    }
    if ([long]$WorkerSettings.AuthEpoch -ne $hostAuthEpoch) {
        throw (
            "The protected host AUTH_EPOCH ($hostAuthEpoch) does not match " +
            "the Cloudflare Worker AUTH_EPOCH ($($WorkerSettings.AuthEpoch)). Update and verify " +
            "both ends in the same immutable release before deployment."
        )
    }

    $hostOriginPrincipalKid = [string]$Values["ORIGIN_PRINCIPAL_KID"]
    if ([string]$WorkerSettings.OriginPrincipalKid -cne $hostOriginPrincipalKid) {
        throw (
            "The protected host ORIGIN_PRINCIPAL_KID ($hostOriginPrincipalKid) does not match " +
            "the Cloudflare Worker ORIGIN_PRINCIPAL_KID ($($WorkerSettings.OriginPrincipalKid)). " +
            "Update and verify both ends in the same immutable release before deployment."
        )
    }

    return [pscustomobject]@{
        Host = $hostName
        HostPort = $hostPort
        WorkerPort = [int]$WorkerSettings.OriginPort
        HostAuthEpoch = $hostAuthEpoch
        WorkerAuthEpoch = [long]$WorkerSettings.AuthEpoch
        HostOriginPrincipalKid = $hostOriginPrincipalKid
        WorkerOriginPrincipalKid = [string]$WorkerSettings.OriginPrincipalKid
        Matches = $true
    }
}

function Read-EnvironmentOverlay([string]$Path) {
    $allowedNames = @(
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET"
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "The environment overlay file is missing."
    }
    $overlayItem = Get-Item -LiteralPath $Path -Force
    if (($overlayItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "The environment overlay must not be a reparse point."
    }
    if ([int64]$overlayItem.Length -gt 65536) {
        throw "The environment overlay exceeds the 64 KiB safety limit."
    }
    $overlayAcl = Get-SingYinAclStatus -Paths @($Path)
    if (
        [int]$overlayAcl.Checked -ne 1 -or
        [int]$overlayAcl.Weak -ne 0 -or
        [int]$overlayAcl.Unprotected -ne 0 -or
        -not [bool]$overlayAcl.Compliant
    ) {
        throw "The environment overlay ACL is too broad or inherits permissions."
    }
    $broadSids = @("S-1-1-0", "S-1-5-11", "S-1-5-32-545")
    $rawAcl = Get-SingYinFileSystemAcl -Path $Path
    $rawRules = $rawAcl.GetAccessRules(
        $true,
        $true,
        [Security.Principal.SecurityIdentifier]
    )
    foreach ($rule in @($rawRules)) {
        if (
            $rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow -and
            $rule.IdentityReference.Value -in $broadSids
        ) {
            throw "The environment overlay grants access to a broad Windows identity."
        }
    }

    $values = @{}
    $lineNumber = 0
    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $lineNumber += 1
        if ([string]::IsNullOrWhiteSpace($rawLine) -or $rawLine.TrimStart().StartsWith("#")) {
            continue
        }
        if ($rawLine -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            throw "The environment overlay contains a malformed entry on line $lineNumber."
        }
        $name = [string]$Matches[1]
        $value = [string]$Matches[2]
        if ($allowedNames -cnotcontains $name) {
            throw "The environment overlay contains an unsupported setting."
        }
        if ($values.ContainsKey($name)) {
            throw "The environment overlay contains a duplicate setting."
        }
        if (
            [string]::IsNullOrWhiteSpace($value) -or
            $value -cne $value.Trim() -or
            $value -match '[\x00\r\n#''"]'
        ) {
            throw "The environment overlay contains an unsafe or empty value."
        }
        if ($name -ceq "SING_YIN_UNIFIED_GUEST" -and $value -notmatch '^(0|1|true|false)$') {
            throw "SING_YIN_UNIFIED_GUEST must be 0, 1, true, or false."
        }
        if (
            $name -ceq "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL" -and
            $value -notmatch '^(1|true)$'
        ) {
            throw "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL must be 1 or true."
        }
        if ($name -ceq "AUTH_EPOCH" -and $value -notmatch '^\d+$') {
            throw "AUTH_EPOCH must be a non-negative integer."
        }
        if ($name -ceq "ORIGIN_PRINCIPAL_KID" -and $value -notmatch '^[A-Za-z0-9._-]{1,64}$') {
            throw "ORIGIN_PRINCIPAL_KID contains unsupported characters."
        }
        $values[$name] = $value
    }
    if ($values.Count -eq 0) {
        throw "The environment overlay does not contain any supported settings."
    }
    return $values
}

function Merge-EnvironmentOverlay {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentPath,
        [Parameter(Mandatory = $true)][hashtable]$Overlay,
        [Parameter(Mandatory = $true)][string]$RuntimeIdentity
    )
    $output = New-Object System.Collections.Generic.List[string]
    $written = New-Object 'System.Collections.Generic.HashSet[string]' (
        [StringComparer]::Ordinal
    )
    foreach ($line in [IO.File]::ReadAllLines($EnvironmentPath, [Text.Encoding]::UTF8)) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=') {
            $name = [string]$Matches[1]
            if ($Overlay.ContainsKey($name)) {
                if ($written.Add($name)) {
                    $output.Add("${name}=$($Overlay[$name])")
                }
                continue
            }
        }
        $output.Add($line)
    }
    foreach ($name in @(
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET"
    )) {
        if ($Overlay.ContainsKey($name) -and $written.Add($name)) {
            $output.Add("${name}=$($Overlay[$name])")
        }
    }

    $temporaryPath = "$EnvironmentPath.release-overlay-$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllBytes($temporaryPath, [byte[]]@())
        Protect-SingYinSensitivePath -Path $temporaryPath -RuntimeUser $RuntimeIdentity
        $content = [string]::Join([Environment]::NewLine, $output.ToArray()) +
            [Environment]::NewLine
        [IO.File]::WriteAllText(
            $temporaryPath,
            $content,
            (New-Object Text.UTF8Encoding($false))
        )
        Move-Item -LiteralPath $temporaryPath -Destination $EnvironmentPath -Force
        Protect-SingYinSensitivePath -Path $EnvironmentPath -RuntimeUser $RuntimeIdentity
    } finally {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    }
}

function Remove-EnvironmentOverlay([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return
    }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        throw "The environment overlay cleanup target must be a file."
    }
    $isReparsePoint = ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    if (-not $isReparsePoint) {
        [IO.File]::WriteAllBytes($Path, [byte[]]@())
    }
    Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
    if (Test-Path -LiteralPath $Path) {
        throw "The one-use environment overlay could not be deleted."
    }
}

function Wait-PortReleased([int]$Port, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Port $Port is still in use after the owned startup task was stopped."
}

function Wait-LoopbackHealth([Parameter(Mandatory = $true)][int]$Port, [int]$TimeoutSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 3
            if (
                $health.application -ceq "sing-yin-roster" -and
                $health.applicationMode -ceq "official" -and
                $health.status -ceq "ok" -and
                $health.database -ceq "ok"
            ) {
                return $health
            }
        } catch {
            # The owned task may still be starting.
        }
        Start-Sleep -Milliseconds 750
    }
    throw "The official origin did not become healthy within $TimeoutSeconds seconds."
}

function Wait-LoopbackReadiness([Parameter(Mandatory = $true)][int]$Port, [int]$TimeoutSeconds = 90) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/readyz" -TimeoutSec 3
            if (
                $ready.status -ceq "ready" -and
                $ready.writeReady -eq $true -and
                $ready.maintenance -eq $false -and
                $ready.recoveryRequired -eq $false -and
                [int]$ready.pendingBackupObligations -eq 0 -and
                $ready.backupRepairFailed -eq $false
            ) {
                return $ready
            }
        } catch {
            # Readiness may remain degraded briefly while startup repair finishes.
        }
        Start-Sleep -Milliseconds 750
    }
    throw "The official origin did not become write-ready within $TimeoutSeconds seconds."
}

function Set-ReleaseEnvironmentValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if ($Name -notmatch '^[A-Z][A-Z0-9_]*$' -or $Value -match '[\x00-\x1F\x7F]') {
        throw "The release environment override is malformed."
    }
    $pattern = '^\s*' + [regex]::Escape($Name) + '\s*='
    $matched = 0
    $output = foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match $pattern) {
            $matched += 1
            if ($matched -gt 1) {
                throw "The protected host environment contains a duplicate $Name setting."
            }
            "$Name=$Value"
        } else {
            $line
        }
    }
    if ($matched -eq 0) { $output = @($output) + "$Name=$Value" }
    $temporaryPath = "$Path.release-$PID-$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        $output | Set-Content -LiteralPath $temporaryPath -Encoding UTF8
        Move-Item -LiteralPath $temporaryPath -Destination $Path -Force
    } finally {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    }
}

function Assert-SafeReleaseBundlePath {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot,
        [Parameter(Mandatory = $true)][string]$CandidatePath
    )

    $root = [IO.Path]::GetFullPath($ReleaseRoot).TrimEnd('\')
    $candidate = [IO.Path]::GetFullPath($CandidatePath).TrimEnd('\')
    $prefix = "$root\"
    if (-not $candidate.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "The release bundle path escaped the controlled release root."
    }
    $leaf = $candidate.Substring($prefix.Length)
    if ([string]::IsNullOrWhiteSpace($leaf) -or $leaf -match '[\\/]' -or $leaf -notmatch '^[A-Za-z0-9._-]+$') {
        throw "The release bundle path is not a single safe child directory."
    }
    return $candidate
}

function New-SingYinReleaseBundle {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$Commit,
        [Parameter(Mandatory = $true)][string]$ReleaseRef,
        [Parameter(Mandatory = $true)][string]$HostRoot,
        [Parameter(Mandatory = $true)][string]$EnvironmentPath,
        [Parameter(Mandatory = $true)][string]$EnvironmentHash,
        [Parameter(Mandatory = $true)][string]$BootstrapPython,
        [Parameter(Mandatory = $true)][string]$RuntimeUser
    )

    $releaseRoot = Join-Path $HostRoot "releases"
    $null = New-Item -ItemType Directory -Path $releaseRoot -Force
    $safeRelease = $ReleaseRef -replace '[^A-Za-z0-9._-]', '-'
    $bundleName = "$safeRelease-$($Commit.Substring(0, 12))-$($EnvironmentHash.Substring(0, 12))"
    $bundlePath = Assert-SafeReleaseBundlePath -ReleaseRoot $releaseRoot -CandidatePath (
        Join-Path $releaseRoot $bundleName
    )
    $markerPath = Join-Path $bundlePath ".sing-yin-release.json"
    if (Test-Path -LiteralPath $bundlePath) {
        if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
            throw "An unverified directory already occupies the immutable release bundle path."
        }
        $marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (
            [string]$marker.releaseRef -cne $ReleaseRef -or
            [string]$marker.commit -cne $Commit -or
            [string]$marker.environmentSha256 -cne $EnvironmentHash -or
            -not (Test-Path -LiteralPath (Join-Path $bundlePath ".venv\Scripts\python.exe") -PathType Leaf)
        ) {
            throw "The existing release bundle does not match the requested immutable release."
        }
        return $bundlePath
    }

    $stagingName = "$bundleName.staging-$PID-$([Guid]::NewGuid().ToString('N'))"
    $stagingPath = Assert-SafeReleaseBundlePath -ReleaseRoot $releaseRoot -CandidatePath (
        Join-Path $releaseRoot $stagingName
    )
    $archivePath = Join-Path ([IO.Path]::GetTempPath()) (
        "sing-yin-release-$PID-$([Guid]::NewGuid().ToString('N')).zip"
    )
    try {
        Invoke-Native -Executable "git.exe" -Arguments @(
            "archive", "--format=zip", "--output", $archivePath, $Commit
        ) -WorkingDirectory $Repository | Out-Null
        $null = New-Item -ItemType Directory -Path $stagingPath -Force
        Expand-Archive -LiteralPath $archivePath -DestinationPath $stagingPath

        $venvPath = Join-Path $stagingPath ".venv"
        Invoke-Native -Executable $BootstrapPython -Arguments @(
            "-m", "venv", $venvPath
        ) -WorkingDirectory $Repository | Out-Null
        $bundlePython = Join-Path $venvPath "Scripts\python.exe"
        Invoke-Native -Executable $bundlePython -Arguments @(
            "-m", "pip", "install", "--require-hashes", "-r",
            (Join-Path $stagingPath "requirements.lock")
        ) -WorkingDirectory $stagingPath | Out-Null

        $bundleEnvironment = Join-Path $stagingPath ".env"
        Copy-Item -LiteralPath $EnvironmentPath -Destination $bundleEnvironment
        Set-ReleaseEnvironmentValue -Path $bundleEnvironment -Name "SING_YIN_APP_MODE" -Value "official"
        Set-ReleaseEnvironmentValue -Path $bundleEnvironment -Name "SING_YIN_DATABASE_PATH" -Value (
            Join-Path $HostRoot "data\runtime\sing-yin-roster.sqlite3"
        )
        Set-ReleaseEnvironmentValue -Path $bundleEnvironment -Name "SING_YIN_BACKUP_DIR" -Value (
            Join-Path $HostRoot "data\backups"
        )
        Set-ReleaseEnvironmentValue -Path $bundleEnvironment -Name "SING_YIN_LOG_DIR" -Value (
            Join-Path $HostRoot "logs"
        )
        Set-ReleaseEnvironmentValue -Path $bundleEnvironment -Name "SING_YIN_SUPPORT_DIR" -Value (
            Join-Path $HostRoot "data\support"
        )
        Protect-SingYinSensitivePath -Path $bundleEnvironment -RuntimeUser $RuntimeUser

        Invoke-Native -Executable $bundlePython -Arguments @(
            "-X", "utf8", "-c", "import nicegui; import nicegui_app.main"
        ) -WorkingDirectory $stagingPath | Out-Null
        Invoke-Native -Executable $bundlePython -Arguments @(
            "-X", "utf8", "scripts\check_deployment_readiness.py",
            "--strict", "--allow-pending-cloudflare-access"
        ) -WorkingDirectory $stagingPath | Out-Null

        $marker = [ordered]@{
            schemaVersion = 1
            releaseRef = $ReleaseRef
            commit = $Commit
            sourceTree = Get-GitValue -Repository $Repository -Arguments @("rev-parse", "$Commit`^{tree}")
            environmentSha256 = $EnvironmentHash
            createdAt = [DateTimeOffset]::UtcNow.ToString("o")
        }
        $marker | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (
            Join-Path $stagingPath ".sing-yin-release.json"
        ) -Encoding UTF8
        Grant-SingYinRuntimeReadAccess -Path $stagingPath -RuntimeUser $RuntimeUser
        Grant-SingYinVenvBasePythonReadAccess -ProjectRoot $stagingPath -RuntimeUser $RuntimeUser
        Move-Item -LiteralPath $stagingPath -Destination $bundlePath
        return $bundlePath
    } catch {
        # Retain a completed bundle only after the atomic directory rename.
        # A private staging directory contains a copied environment file, so
        # remove it on failure after first verifying it is a controlled child.
        $safeStagingPath = Assert-SafeReleaseBundlePath -ReleaseRoot $releaseRoot -CandidatePath $stagingPath
        if (Test-Path -LiteralPath $safeStagingPath) {
            Remove-Item -LiteralPath $safeStagingPath -Recurse -Force
        }
        throw
    } finally {
        if (Test-Path -LiteralPath $archivePath) {
            try {
                Remove-Item -LiteralPath $archivePath -Force -ErrorAction Stop
            } catch {
                Write-Warning "Release archive cleanup failed; remove the bounded temporary file manually: $archivePath"
            }
        }
    }
}

$resolvedOverlayPath = $null
$overlayPathToDelete = $null
$deploymentExitCode = 1
$controlledEnvironmentNames = @()
$processEnvironmentSnapshot = @{}
$processEnvironmentCaptured = $false
try {
    if (-not [string]::IsNullOrWhiteSpace($EnvironmentOverlayPath)) {
        $resolvedOverlayPath = [IO.Path]::GetFullPath($EnvironmentOverlayPath)
        $overlayName = [IO.Path]::GetFileName($resolvedOverlayPath)
        $overlayDirectory = [IO.Path]::GetFullPath(
            (Split-Path -Parent $resolvedOverlayPath)
        ).TrimEnd([IO.Path]::DirectorySeparatorChar)
        $expectedTempDirectory = [IO.Path]::GetFullPath(
            [IO.Path]::GetTempPath()
        ).TrimEnd([IO.Path]::DirectorySeparatorChar)
        if (
            $overlayName -notmatch '^sing-yin-release-overlay-[A-Za-z0-9_-]{8,128}\.env$' -or
            -not [string]::Equals(
                $overlayDirectory,
                $expectedTempDirectory,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "The environment overlay must use the controlled one-use name in the Windows temp directory."
        }
        $prospectiveHostEnvironment = [IO.Path]::GetFullPath(
            (Join-Path ([IO.Path]::GetFullPath($HostRoot)) ".env")
        )
        if (
            [string]::Equals(
                $prospectiveHostEnvironment,
                $resolvedOverlayPath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "The one-use environment overlay must be separate from the protected host environment."
        }
        if (
            -not (Test-Path -LiteralPath $resolvedOverlayPath -PathType Leaf)
        ) {
            throw "The environment overlay file is missing."
        }
        $candidateOverlayItem = Get-Item -LiteralPath $resolvedOverlayPath -Force
        if (($candidateOverlayItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "The environment overlay must not be a reparse point."
        }
    }
    if ($ReleaseRef -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$') {
        throw "ReleaseRef must be a simple immutable release tag name."
    }
    foreach ($requiredRoot in @($SourceRoot, $HostRoot)) {
        if (-not (Test-Path -LiteralPath $requiredRoot -PathType Container)) {
            throw "Required path is missing: $requiredRoot"
        }
    }
    $SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path
    $HostRoot = (Resolve-Path -LiteralPath $HostRoot).Path

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This controlled deployment must run from an elevated Windows session."
    }

    . (Join-Path $SourceRoot "scripts\windows_host_common.ps1")
    $runtimeAccount = Get-SingYinRuntimeAccount -UserName $RuntimeUser

    $safeReleaseName = $ReleaseRef -replace '[^A-Za-z0-9._-]', '-'
    $script:ReportPath = Join-Path $SourceRoot "logs\windows-release-deployment-$safeReleaseName.json"
    $script:NativeLogPath = Join-Path $SourceRoot "logs\windows-release-deployment-$safeReleaseName-native.log"
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $script:ReportPath) -Force
    Set-Content -LiteralPath $script:NativeLogPath -Encoding UTF8 -Value (
        "Sing Yin Roster controlled Windows release deployment native output"
    )

    $requiredChecks = @(
        "repository_hygiene",
        "security_gates",
        "cloudflare_gateway_tests",
        "motion_state_machine_tests",
        "automated_test_suite",
        "python_compile",
        "dependency_integrity",
        "verify_nicegui_ui",
        "verify_runtime_performance",
        "verify_nicegui_write_pipeline",
        "verify_nicegui_mobile",
        "strict_deployment_readiness",
        "verify_unified_guest_ui",
        "verify_nicegui_partial_backup",
        "rc31_theme_control_browser"
    )
    $requiredCheckCount = $requiredChecks.Count
    $startedAt = [DateTimeOffset]::UtcNow
    $releaseCommit = $null
    $previousCommit = $null
    $backupReport = $null
    $taskInitiallyRunning = $false
    $taskInitiallyEnabled = $false
    $taskStopped = $false
    $taskTargetSwitched = $false
    $releaseBundlePath = $null
    $previousTaskAction = $null
    $environmentPath = Join-Path $HostRoot ".env"
    $deploymentPort = 8080
    $environmentBytes = $null
    $environmentAclSddl = $null
    $environmentAclSections = (
        [Security.AccessControl.AccessControlSections]::Access -bor
        [Security.AccessControl.AccessControlSections]::Owner -bor
        [Security.AccessControl.AccessControlSections]::Group
    )
    $environmentHash = $null
    $environmentOverlayApplied = $false
    $controlledEnvironmentNames = @(
        "SING_YIN_UNIFIED_GUEST",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL",
        "ORIGIN_PRINCIPAL_SECRET",
        "ORIGIN_PRINCIPAL_KID",
        "AUTH_EPOCH",
        "SING_YIN_GUEST_SNAPSHOT_SECRET"
    )
    $processEnvironmentSnapshot = @{}
    $processEnvironmentCaptured = $false
    $rollbackAttempted = $false
    $rollbackSucceeded = $false
    $rollbackError = $null
    $preflightGatewayParity = $null
    $postApplyGatewayParity = $null

    try {
    Write-Step "Validating the immutable release and $requiredCheckCount-gate evidence"
    $sourceStatus = Get-GitValue -Repository $SourceRoot -Arguments @(
        "status",
        "--porcelain",
        "--untracked-files=all"
    )
    if (-not [string]::IsNullOrWhiteSpace($sourceStatus)) {
        throw "The source repository is not clean."
    }
    Invoke-Native -Executable "git.exe" -Arguments @(
        "fetch",
        "--prune",
        "--tags",
        "origin"
    ) -WorkingDirectory $SourceRoot | Out-Null
    Invoke-Native -Executable "git.exe" -Arguments @(
        "fetch",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main"
    ) -WorkingDirectory $SourceRoot | Out-Null
    $releaseCommit = Assert-ImmutableReleaseTag -Repository $SourceRoot -TagName $ReleaseRef
    $sourceHead = Get-GitValue -Repository $SourceRoot -Arguments @("rev-parse", "HEAD")
    if ($sourceHead -cne $releaseCommit) {
        throw "The source HEAD does not match the immutable release tag."
    }
    & git.exe -C $SourceRoot merge-base --is-ancestor $releaseCommit origin/main
    if ($LASTEXITCODE -ne 0) {
        throw "$ReleaseRef is not contained in origin/main."
    }

    $sourcePython = Join-Path $SourceRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $sourcePython -PathType Leaf)) {
        throw "The verified source Python environment is missing."
    }
    $releaseReportPath = Join-Path $SourceRoot "logs\release-candidate-report.json"
    $releaseReport = Get-Content -LiteralPath $releaseReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $reportChecks = @($releaseReport.checks)
    $reportRequiredChecks = @($releaseReport.requiredCheckIdentities | ForEach-Object { [string]$_ })
    $passedNames = @(
        $reportChecks |
            Where-Object { $_.status -ceq "pass" } |
            ForEach-Object { [string]$_.name }
    )
    $unexpectedNames = @($passedNames | Where-Object { $_ -notin $requiredChecks })
    $missingNames = @($requiredChecks | Where-Object { $_ -notin $passedNames })
    if (
        [int]$releaseReport.schemaVersion -ne 2 -or
        [string]$releaseReport.sourceCommit -cne $releaseCommit -or
        [string]$releaseReport.sourceTree -cne (Get-GitValue -Repository $SourceRoot -Arguments @("rev-parse", "$releaseCommit`^{tree}")) -or
        [bool]$releaseReport.sourceDirty -or
        [string]$releaseReport.plannedReleaseTag -cne $ReleaseRef -or
        [string]$releaseReport.immutableReleaseReference -cne "refs/tags/$ReleaseRef" -or
        [bool]$releaseReport.humanAcceptanceRequired -ne $true -or
        $null -eq $releaseReport.toolVersions -or
        $reportRequiredChecks.Count -ne $requiredCheckCount -or
        (Compare-Object -ReferenceObject $requiredChecks -DifferenceObject $reportRequiredChecks -SyncWindow 0).Count -ne 0 -or
        $releaseReport.status -cne "pass" -or
        $reportChecks.Count -ne $requiredCheckCount -or
        $passedNames.Count -ne $requiredCheckCount -or
        @($passedNames | Select-Object -Unique).Count -ne $requiredCheckCount -or
        $unexpectedNames.Count -ne 0 -or
        $missingNames.Count -ne 0
    ) {
        throw "The $requiredCheckCount-gate source release report is not a complete pass."
    }
    $currentFingerprint = Get-CurrentReleaseFingerprint -Python $sourcePython -Repository $SourceRoot
    if (
        [string]$releaseReport.sourceFingerprint -cne [string]$currentFingerprint.fingerprint -or
        [int]$releaseReport.sourceFileCount -ne [int]$currentFingerprint.fileCount
    ) {
        throw "The release report fingerprint does not match the immutable release source."
    }

    Write-Step "Inspecting the owned startup task"
    $inspection = Get-SingYinTaskInspection `
        -TaskName $TaskName `
        -ProjectRoot $HostRoot `
        -RuntimeUser $runtimeAccount.Name `
        -AllowReleaseBundle
    if (-not $inspection.Exists -or -not $inspection.Owned) {
        throw "The startup task is missing or is not safely owned by this release host."
    }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    if (@($task.Actions).Count -ne 1) {
        throw "The owned startup task must contain exactly one action."
    }
    if ([string]$task.Principal.LogonType -cne "Password") {
        throw "The owned startup task must use the password-backed service account."
    }
    $previousTaskAction = [pscustomobject]@{
        Execute = [string]$task.Actions[0].Execute
        Arguments = [string]$task.Actions[0].Arguments
        WorkingDirectory = [string]$task.Actions[0].WorkingDirectory
    }
    $taskInitiallyRunning = [string]$task.State -ceq "Running"
    $taskInitiallyEnabled = [bool]$task.Settings.Enabled

    # Fail before reading or consuming a one-use environment overlay. A dirty
    # installed checkout is an attribution problem, not a condition that this
    # deployer may repair implicitly; preserving the overlay lets the operator
    # reconcile the host and retry without recreating sensitive settings.
    $hostStatus = Get-GitValue -Repository $HostRoot -Arguments @(
        "status",
        "--porcelain",
        "--untracked-files=all"
    )
    if (-not [string]::IsNullOrWhiteSpace($hostStatus)) {
        throw "The installed host repository is not clean."
    }
    $previousCommit = Get-GitValue -Repository $HostRoot -Arguments @("rev-parse", "HEAD")

    Write-Step "Preflighting host and Worker gateway identity without changing the host"
    $currentHostEnvironment = Read-HostEnvironmentValues -EnvironmentPath $environmentPath
    $prospectiveHostEnvironment = $currentHostEnvironment
    $environmentOverlay = $null
    if ($null -ne $resolvedOverlayPath) {
        $environmentOverlay = Read-EnvironmentOverlay -Path $resolvedOverlayPath
        $prospectiveHostEnvironment = Merge-HostEnvironmentValues `
            -Base $currentHostEnvironment `
            -Overlay $environmentOverlay
    }
    $workerConfigurationPath = Join-Path $SourceRoot "cloudflare\roster_viewer\wrangler.jsonc"
    $workerGatewaySettings = Get-WorkerGatewaySettings `
        -ConfigurationPath $workerConfigurationPath `
        -Python $sourcePython
    $preflightGatewayParity = Assert-WorkerHostGatewayParity `
        -Values $prospectiveHostEnvironment `
        -WorkerSettings $workerGatewaySettings

    # A one-use overlay is consumed only after the read-only identity preflight
    # passes. A parity failure therefore leaves both the host and the operator's
    # proposed overlay untouched for safe correction.
    $overlayPathToDelete = $resolvedOverlayPath

    Write-Step "Protecting and applying the preflighted host settings"
    # Capture both content and the original security descriptor before the
    # first mutation. A failed protection or overlay step must be able to
    # restore the exact pre-deployment file state, not merely apply the latest
    # preferred ACL policy to already-mutated content.
    $environmentBytes = [IO.File]::ReadAllBytes($environmentPath)
    $environmentAclSddl = (Get-Acl -LiteralPath $environmentPath).GetSecurityDescriptorSddlForm(
        $environmentAclSections
    )
    Protect-SingYinSensitivePath -Path $environmentPath -RuntimeUser $runtimeAccount.Name
    $aclStatus = Get-SingYinAclStatus `
        -Paths @($environmentPath) `
        -RequiredIdentitySid $runtimeAccount.Sid.Value
    if (-not $aclStatus.Compliant) {
        throw "The protected host environment ACL is not compliant."
    }
    if ($null -ne $resolvedOverlayPath) {
        if (
            [string]::Equals(
                [IO.Path]::GetFullPath($environmentPath),
                $resolvedOverlayPath,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "The one-use environment overlay must be separate from the protected host environment."
        }
        Merge-EnvironmentOverlay `
            -EnvironmentPath $environmentPath `
            -Overlay $environmentOverlay `
            -RuntimeIdentity $runtimeAccount.Name
        $environmentOverlayApplied = $true
    }
    $deployedEnvironmentBytes = [IO.File]::ReadAllBytes($environmentPath)
    $environmentHash = (
        [BitConverter]::ToString(
            [Security.Cryptography.SHA256]::Create().ComputeHash($deployedEnvironmentBytes)
        )
    ).Replace("-", "").ToLowerInvariant()
    foreach ($name in $controlledEnvironmentNames) {
        $processEnvironmentSnapshot[$name] = [Environment]::GetEnvironmentVariable(
            $name,
            "Process"
        )
    }
    $processEnvironmentCaptured = $true
    $environmentValues = Import-HostEnvironment -EnvironmentPath $environmentPath
    $postApplyGatewayParity = Assert-WorkerHostGatewayParity `
        -Values $environmentValues `
        -WorkerSettings $workerGatewaySettings
    $configuredEndpoint = Get-SingYinConfiguredEndpoint -EnvironmentPath $environmentPath
    $deploymentPort = [int]$configuredEndpoint.Port
    if ($deploymentPort -ne [int]$postApplyGatewayParity.HostPort) {
        throw "The post-apply endpoint validation disagrees with the gateway parity check."
    }
    $workerOriginPort = [int]$postApplyGatewayParity.WorkerPort
    $hostAuthEpoch = [long]$postApplyGatewayParity.HostAuthEpoch
    $workerAuthEpoch = [long]$postApplyGatewayParity.WorkerAuthEpoch
    $hostOriginPrincipalKid = [string]$postApplyGatewayParity.HostOriginPrincipalKid
    $workerOriginPrincipalKid = [string]$postApplyGatewayParity.WorkerOriginPrincipalKid

    Write-Step "Building and verifying an immutable release bundle before downtime"
    $releaseBundlePath = New-SingYinReleaseBundle `
        -Repository $SourceRoot `
        -Commit $releaseCommit `
        -ReleaseRef $ReleaseRef `
        -HostRoot $HostRoot `
        -EnvironmentPath $environmentPath `
        -EnvironmentHash $environmentHash `
        -BootstrapPython $sourcePython `
        -RuntimeUser $runtimeAccount.Name
    $releaseBundlePath = Assert-SafeReleaseBundlePath `
        -ReleaseRoot (Join-Path $HostRoot "releases") `
        -CandidatePath $releaseBundlePath

    Write-Step "Stopping the owned task and fencing port $deploymentPort"
    if ([string]$task.State -ceq "Running") {
        Stop-ScheduledTask -TaskName $TaskName
    }
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
    $taskStopped = $true
    Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 30

    Write-Step "Creating a fresh verified backup and isolated restore proof"
    $env:SING_YIN_APP_MODE = "official"
    $env:SING_YIN_DATABASE_PATH = Join-Path $HostRoot "data\runtime\sing-yin-roster.sqlite3"
    $env:SING_YIN_BACKUP_DIR = Join-Path $HostRoot "data\backups"
    $env:SING_YIN_LOG_DIR = Join-Path $HostRoot "logs"
    $backupStartedAt = [DateTimeOffset]::UtcNow
    Invoke-Native -Executable $sourcePython -Arguments @(
        "-X",
        "utf8",
        "scripts\verify_formal_backup_restore.py"
    ) -WorkingDirectory $SourceRoot | Out-Null
    $backupReportPath = Join-Path $SourceRoot "logs\formal-backup-restore-report.json"
    $backupReportFile = Get-Item -LiteralPath $backupReportPath -ErrorAction Stop
    if ([DateTimeOffset]$backupReportFile.LastWriteTimeUtc -lt $backupStartedAt.AddSeconds(-2)) {
        throw "The formal backup report was not refreshed by this deployment."
    }
    $backupReport = Get-Content -LiteralPath $backupReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if (
        $backupReport.status -cne "pass" -or
        -not [bool]$backupReport.isolatedRestore -or
        -not [bool]$backupReport.fairnessBalanced -or
        -not [bool]$backupReport.rowCountsMatched -or
        -not [bool]$backupReport.restoreAuditAppended -or
        [string]$backupReport.integrity -cne "ok" -or
        [string]$backupReport.sha256 -notmatch '^[0-9a-f]{64}$'
    ) {
        throw "The fresh backup and isolated restore proof is incomplete."
    }
    $snapshotName = [IO.Path]::GetFileName([string]$backupReport.snapshotFile)
    if ($snapshotName -cne [string]$backupReport.snapshotFile) {
        throw "The formal backup report contains an unsafe snapshot path."
    }
    $snapshotPath = Join-Path $env:SING_YIN_BACKUP_DIR $snapshotName
    $manifestPath = [IO.Path]::ChangeExtension($snapshotPath, ".manifest.json")
    if (
        -not (Test-Path -LiteralPath $snapshotPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $manifestPath -PathType Leaf)
    ) {
        throw "The verified snapshot or checksum manifest is missing."
    }
    $snapshotHash = (Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($snapshotHash -cne ([string]$backupReport.sha256).ToLowerInvariant()) {
        throw "The verified snapshot checksum no longer matches the backup report."
    }

    Write-Step "Atomically switching the owned task to the immutable release bundle"
    $hostPython = Join-Path $releaseBundlePath ".venv\Scripts\python.exe"
    $newTaskAction = New-ScheduledTaskAction `
        -Execute $hostPython `
        -Argument "-X utf8 -m nicegui_app.main" `
        -WorkingDirectory $releaseBundlePath
    Set-ScheduledTask -TaskName $TaskName -Action $newTaskAction | Out-Null
    $taskTargetSwitched = $true
    $currentEnvironmentBytes = [IO.File]::ReadAllBytes($environmentPath)
    $currentEnvironmentHash = (
        [BitConverter]::ToString(
            [Security.Cryptography.SHA256]::Create().ComputeHash($currentEnvironmentBytes)
        )
    ).Replace("-", "").ToLowerInvariant()
    if ($currentEnvironmentHash -cne $environmentHash) {
        throw "The protected host environment changed during the release switch."
    }
    Protect-SingYinSensitivePath -Path $environmentPath -RuntimeUser $runtimeAccount.Name

    $postSwitchInspection = Get-SingYinTaskInspection `
        -TaskName $TaskName `
        -ProjectRoot $releaseBundlePath `
        -RuntimeUser $runtimeAccount.Name
    if (-not $postSwitchInspection.Exists -or -not $postSwitchInspection.Owned) {
        throw "The startup task no longer matches the updated release host."
    }

    Write-Step "Starting the official origin and enforcing health and write-readiness"
    Enable-ScheduledTask -TaskName $TaskName | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    $health = Wait-LoopbackHealth -Port $deploymentPort
    $readiness = Wait-LoopbackReadiness -Port $deploymentPort
    Invoke-Native -Executable $hostPython -Arguments @(
        "-X",
        "utf8",
        "scripts\check_deployment_readiness.py",
        "--strict",
        "--allow-pending-cloudflare-access"
    ) -WorkingDirectory $releaseBundlePath | Out-Null
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop

    Write-DeploymentReport -Payload ([ordered]@{
        schemaVersion = 1
        status = "pass"
        startedAt = $startedAt.ToString("o")
        finishedAt = [DateTimeOffset]::UtcNow.ToString("o")
        releaseRef = $ReleaseRef
        releaseCommit = $releaseCommit
        previousCommit = $previousCommit
        releaseBundle = $releaseBundlePath
        sourceFingerprint = [string]$currentFingerprint.fingerprint
        sourceFileCount = [int]$currentFingerprint.fileCount
        releaseChecksPassed = $requiredCheckCount
        snapshotFile = $snapshotName
        snapshotSha256 = [string]$backupReport.sha256
        isolatedRestore = [bool]$backupReport.isolatedRestore
        fairnessBalanced = [bool]$backupReport.fairnessBalanced
        rowCountsMatched = [bool]$backupReport.rowCountsMatched
        restoreAuditAppended = [bool]$backupReport.restoreAuditAppended
        environmentProtected = $true
        endpoint = [ordered]@{
            host = "127.0.0.1"
            port = $deploymentPort
            workerOriginPort = $workerOriginPort
        }
        gatewayIdentity = [ordered]@{
            hostAuthEpoch = $hostAuthEpoch
            workerAuthEpoch = $workerAuthEpoch
            hostOriginPrincipalKid = $hostOriginPrincipalKid
            workerOriginPrincipalKid = $workerOriginPrincipalKid
            preflightMatched = [bool]$preflightGatewayParity.Matches
            postApplyMatched = [bool]$postApplyGatewayParity.Matches
        }
        environmentOverlayApplied = $environmentOverlayApplied
        taskName = $TaskName
        taskState = [string]$task.State
        taskRuntimeAccount = $runtimeAccount.Name
        health = [ordered]@{
            status = [string]$health.status
            application = [string]$health.application
            applicationMode = [string]$health.applicationMode
            database = [string]$health.database
        }
        readiness = [ordered]@{
            status = [string]$readiness.status
            writeReady = [bool]$readiness.writeReady
            maintenance = [bool]$readiness.maintenance
            recoveryRequired = [bool]$readiness.recoveryRequired
            pendingBackupObligations = [int]$readiness.pendingBackupObligations
            backupRepairFailed = [bool]$readiness.backupRepairFailed
        }
        rollback = [ordered]@{
            attempted = $false
            succeeded = $false
            commit = $null
            error = $null
        }
    })
    Write-Host "`nWindows release deployment passed. Report: $script:ReportPath" -ForegroundColor Green
    $deploymentExitCode = 0
    } catch {
    $failure = Protect-ReportText $_.Exception.Message
    Write-Host "`nDEPLOYMENT FAILED: $failure" -ForegroundColor Red
    if ($taskStopped -or $null -ne $environmentBytes) {
        $rollbackAttempted = $true
        try {
            if ($taskStopped) {
                Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
                # Fail closed: never mutate source or dependencies while the
                # previous process may still own the production port.
                Wait-PortReleased -Port $deploymentPort -TimeoutSeconds 15
                if ($taskTargetSwitched -and $null -ne $previousTaskAction) {
                    Write-Host "Restoring the previous immutable task target ..." -ForegroundColor Yellow
                    $restoreActionParameters = @{
                        Execute = $previousTaskAction.Execute
                        WorkingDirectory = $previousTaskAction.WorkingDirectory
                    }
                    if (-not [string]::IsNullOrWhiteSpace($previousTaskAction.Arguments)) {
                        $restoreActionParameters.Argument = $previousTaskAction.Arguments
                    }
                    $restoreTaskAction = New-ScheduledTaskAction @restoreActionParameters
                    Set-ScheduledTask -TaskName $TaskName -Action $restoreTaskAction | Out-Null
                }
            }
            if ($null -ne $environmentBytes) {
                [IO.File]::WriteAllBytes($environmentPath, $environmentBytes)
                if (-not [string]::IsNullOrWhiteSpace($environmentAclSddl)) {
                    $restoredAcl = Get-Acl -LiteralPath $environmentPath
                    $restoredAcl.SetSecurityDescriptorSddlForm(
                        $environmentAclSddl,
                        $environmentAclSections
                    )
                    Set-Acl -LiteralPath $environmentPath -AclObject $restoredAcl
                }
            }
            if ($taskStopped) {
                if ($taskInitiallyEnabled -or $taskInitiallyRunning) {
                    Enable-ScheduledTask -TaskName $TaskName | Out-Null
                }
                if ($taskInitiallyRunning) {
                    Start-ScheduledTask -TaskName $TaskName
                    $null = Wait-LoopbackHealth -Port $deploymentPort -TimeoutSeconds 90
                }
            }
            $rollbackSucceeded = $true
        } catch {
            $rollbackError = Protect-ReportText $_.Exception.Message
            $failure = "$failure Rollback also needs review."
        }
    }
    Write-DeploymentReport -Payload ([ordered]@{
        schemaVersion = 1
        status = "fail"
        startedAt = $startedAt.ToString("o")
        finishedAt = [DateTimeOffset]::UtcNow.ToString("o")
        releaseRef = $ReleaseRef
        releaseCommit = $releaseCommit
        previousCommit = $previousCommit
        releaseBundle = $releaseBundlePath
        failure = $failure
        nativeLog = [IO.Path]::GetFileName($script:NativeLogPath)
        rollback = [ordered]@{
            attempted = $rollbackAttempted
            succeeded = $rollbackSucceeded
            commit = if ($rollbackSucceeded) { $previousCommit } else { $null }
            taskTarget = if ($rollbackSucceeded -and $null -ne $previousTaskAction) {
                $previousTaskAction.WorkingDirectory
            } else {
                $null
            }
            error = $rollbackError
        }
    })
    $deploymentExitCode = 1
    }
} finally {
    if ($processEnvironmentCaptured) {
        foreach ($name in $controlledEnvironmentNames) {
            [Environment]::SetEnvironmentVariable(
                $name,
                $processEnvironmentSnapshot[$name],
                "Process"
            )
        }
    }
    if ($deploymentExitCode -eq 0) {
        Remove-EnvironmentOverlay -Path $overlayPathToDelete
    }
}
exit $deploymentExitCode
