[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [Parameter(Mandatory = $true)][string]$ReleaseRef,
    [string]$PublicBaseUrl = "https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/",
    [string]$SecretOverlayPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "worker_deployment_helpers.ps1")

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    # Use the immutable checkout containing this script by default. An
    # explicit -SourceRoot remains available for a separately verified
    # release worktree.
    $SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Protect-Text([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    $redacted = [regex]::Replace(
        $Text,
        '(?i)\b(Bearer)\s+[A-Za-z0-9._~+/-]+=*',
        '$1 <redacted>'
    )
    return [regex]::Replace(
        $redacted,
        '(?i)\b(token|secret|password|authorization|cookie)(\s*[:=]\s*|\s+)([^\s,;]+)',
        '$1$2<redacted>'
    )
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
        $output = @(& $Executable @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
        Pop-Location
    }
    $safeOutput = @($output | ForEach-Object { Protect-Text $_.ToString() })
    if ($safeOutput.Count -gt 0) {
        $safeOutput | ForEach-Object { Write-Host $_ }
    }
    if ($exitCode -ne 0) {
        throw "$Executable failed with exit code $exitCode."
    }
    return $output
}

function Get-GitValue {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    $output = @(Invoke-Native -Executable "git.exe" -Arguments (@("-C", $Repository) + $Arguments) -WorkingDirectory $Repository)
    return ($output | Out-String).Trim()
}

function Get-CurrentReleaseFingerprint {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string]$Repository
    )
    $code = @'
import json
from nicegui_app.release_evidence import release_source_fingerprint
fingerprint, file_count = release_source_fingerprint(refresh=True)
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
        throw "The Worker release source fingerprint could not be calculated."
    }
    $jsonLine = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace($_.ToString()) })[-1]
    try {
        return ($jsonLine.ToString() | ConvertFrom-Json)
    } catch {
        throw "The Worker release source fingerprint result was not valid JSON."
    }
}

function Test-RequiredBooleanProperty {
    param(
        [AllowNull()][object]$InputObject,
        [Parameter(Mandatory = $true)][string]$Name
    )
    if ($null -eq $InputObject) {
        return $false
    }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $false
    }
    return ($property.Value -is [bool])
}

function Assert-ImmutableRelease {
    param(
        [Parameter(Mandatory = $true)][string]$Repository,
        [Parameter(Mandatory = $true)][string]$TagName
    )
    $status = Get-GitValue -Repository $Repository -Arguments @("status", "--porcelain", "--untracked-files=all")
    if (-not [string]::IsNullOrWhiteSpace($status)) {
        throw "The release source must be clean."
    }
    Invoke-Native -Executable "git.exe" -Arguments @("fetch", "--prune", "--tags", "origin") -WorkingDirectory $Repository | Out-Null
    Invoke-Native -Executable "git.exe" -Arguments @("fetch", "origin", "+refs/heads/main:refs/remotes/origin/main") -WorkingDirectory $Repository | Out-Null

    $tagRef = "refs/tags/$TagName"
    if ((Get-GitValue -Repository $Repository -Arguments @("cat-file", "-t", $tagRef)) -cne "tag") {
        throw "ReleaseRef must be an annotated Git tag."
    }
    $tagObject = Get-GitValue -Repository $Repository -Arguments @("rev-parse", "$tagRef^{tag}")
    $tagCommit = Get-GitValue -Repository $Repository -Arguments @("rev-parse", "$tagRef^{commit}")
    $headCommit = Get-GitValue -Repository $Repository -Arguments @("rev-parse", "HEAD")
    if ($headCommit -cne $tagCommit) {
        throw "Source HEAD does not match the release tag."
    }
    $remoteLines = @(Invoke-Native -Executable "git.exe" -Arguments @("ls-remote", "--tags", "origin", $tagRef, "$tagRef^{}") -WorkingDirectory $Repository)
    $remoteTagObject = $null
    $remoteCommit = $null
    foreach ($rawLine in $remoteLines) {
        $line = $rawLine.ToString().Trim()
        if ($line -match "^([0-9a-f]{40})\s+$([regex]::Escape($tagRef))$") {
            $remoteTagObject = $Matches[1]
        } elseif ($line -match "^([0-9a-f]{40})\s+$([regex]::Escape($tagRef))\^\{\}$") {
            $remoteCommit = $Matches[1]
        }
    }
    if ($remoteTagObject -cne $tagObject -or $remoteCommit -cne $tagCommit) {
        throw "The local tag does not match the tag published to origin."
    }
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & git.exe -C $Repository merge-base --is-ancestor $tagCommit origin/main 2>$null
        $ancestorExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($ancestorExit -ne 0) {
        throw "$TagName is not contained in origin/main."
    }
    return $tagCommit
}

function Find-NodeExecutable {
    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($env:SING_YIN_NODE)) {
        $candidates.Add($env:SING_YIN_NODE)
    }
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -ne $nodeCommand) { $candidates.Add($nodeCommand.Source) }
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if ($null -ne $nodeCommand) { $candidates.Add($nodeCommand.Source) }
    $known = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    $candidates.Add($known)
    $legacyRoot = Join-Path $env:LOCALAPPDATA "OpenAI\Codex\runtimes\cua_node"
    if (Test-Path -LiteralPath $legacyRoot) {
        Get-ChildItem -LiteralPath $legacyRoot -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { $candidates.Add((Join-Path $_.FullName "bin\node.exe")) }
    }
    foreach ($candidate in @($candidates | Select-Object -Unique)) {
        if ([string]::IsNullOrWhiteSpace($candidate) -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        $versionText = (& $candidate --version 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $versionText -match '^v(\d+)\.') {
            if ([int]$Matches[1] -ge 22) { return (Resolve-Path -LiteralPath $candidate).Path }
        }
    }
    throw "Node.js 22 or newer was not found."
}

function Invoke-Wrangler {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$OutputFile = ""
    )
    $previousOutputPath = $env:WRANGLER_OUTPUT_FILE_PATH
    try {
        if ([string]::IsNullOrWhiteSpace($OutputFile)) {
            Remove-Item Env:WRANGLER_OUTPUT_FILE_PATH -ErrorAction SilentlyContinue
        } else {
            $env:WRANGLER_OUTPUT_FILE_PATH = $OutputFile
        }
        return @(Invoke-Native -Executable $script:NodePath -Arguments (@($script:WranglerPath) + $Arguments) -WorkingDirectory $script:WorkerRoot)
    } finally {
        if ($null -eq $previousOutputPath) {
            Remove-Item Env:WRANGLER_OUTPUT_FILE_PATH -ErrorAction SilentlyContinue
        } else {
            $env:WRANGLER_OUTPUT_FILE_PATH = $previousOutputPath
        }
    }
}

function Get-WranglerSemanticVersion([string]$Output) {
    $matches = [regex]::Matches(
        $Output,
        '(?<![0-9A-Za-z.+-])(?<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))(?![0-9A-Za-z.+-])'
    )
    if ($matches.Count -ne 1) {
        return $null
    }
    return $matches[0].Groups["version"].Value
}

function Read-WranglerEvent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Type
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Wrangler did not create its structured output file."
    }
    $events = @()
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $events += ($line | ConvertFrom-Json) } catch { }
    }
    $match = @($events | Where-Object { $_.type -ceq $Type } | Select-Object -Last 1)
    if ($match.Count -ne 1) {
        throw "Wrangler did not report the expected $Type event."
    }
    return $match[0]
}

function Assert-RequiredWorkerSecrets {
    param([string[]]$AdditionalNames = @())
    $configurationSource = Get-Content -LiteralPath $script:ConfigPath -Raw -Encoding UTF8
    $requiredBlock = [regex]::Match(
        $configurationSource,
        '"secrets"\s*:\s*\{\s*"required"\s*:\s*\[(?<items>[^\]]*)\]',
        [Text.RegularExpressions.RegexOptions]::Singleline
    )
    if (-not $requiredBlock.Success) {
        throw "Worker configuration does not declare required secrets."
    }
    $requiredNames = @(
        [regex]::Matches($requiredBlock.Groups["items"].Value, '"(?<name>[A-Z][A-Z0-9_]*)"') |
            ForEach-Object { $_.Groups["name"].Value } |
            Select-Object -Unique
    )
    if ($requiredNames.Count -eq 0) {
        throw "Worker configuration declares an empty required-secret set."
    }
    $raw = @(Invoke-Wrangler -Arguments @("secret", "list", "--format", "json", "--config", $script:ConfigPath))
    $configuredNames = @(
        @(ConvertFrom-WorkerSecretInventory -Json ($raw | Out-String)) + @($AdditionalNames) |
            Select-Object -Unique
    )
    $missing = @($requiredNames | Where-Object { $_ -notin $configuredNames })
    if ($missing.Count -gt 0) {
        throw "Worker secret inventory is incomplete: $($missing -join ', ')."
    }
}

function Assert-AdminIdentityAllowlistValue([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value.Length -gt 8192) {
        throw "ADMIN_IDENTITY_ALLOWLIST must be a bounded JSON object."
    }
    try { $configuration = $Value | ConvertFrom-Json } catch {
        throw "ADMIN_IDENTITY_ALLOWLIST must be valid JSON."
    }
    $properties = @($configuration.PSObject.Properties)
    if (
        $null -eq $configuration -or
        $configuration -is [System.Array] -or
        $properties.Count -ne 1 -or
        $properties[0].Name -cne "emails" -or
        $configuration.emails -isnot [System.Array] -or
        $configuration.emails.Count -lt 1 -or
        $configuration.emails.Count -gt 32
    ) {
        throw "ADMIN_IDENTITY_ALLOWLIST must contain only an emails array with 1 to 32 entries."
    }
    $seen = @{}
    foreach ($rawEmail in @($configuration.emails)) {
        if ($rawEmail -isnot [string]) {
            throw "ADMIN_IDENTITY_ALLOWLIST entries must be strings."
        }
        $email = [string]$rawEmail
        if (
            $email.Length -gt 320 -or
            $email -cne $email.Trim() -or
            $email -cne $email.ToLowerInvariant() -or
            $email -notmatch '^[^@\s]+@[^@\s]+$' -or
            $seen.ContainsKey($email)
        ) {
            throw "ADMIN_IDENTITY_ALLOWLIST contains an invalid or duplicate email entry."
        }
        $seen[$email] = $true
    }
}

function Remove-SecretOverlay([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) { return }
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) { throw "The Worker secret overlay cleanup target must be a file." }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
        [IO.File]::WriteAllBytes($item.FullName, [byte[]]@())
    }
    Remove-Item -LiteralPath $item.FullName -Force -ErrorAction Stop
    if (Test-Path -LiteralPath $item.FullName) {
        throw "The one-use Worker secret overlay could not be deleted."
    }
}

function Get-DeploymentStatus {
    $raw = @(Invoke-Wrangler -Arguments @("deployments", "status", "--json", "--config", $script:ConfigPath))
    try { return (($raw | Out-String) | ConvertFrom-Json) } catch {
        throw "Wrangler deployment status was not valid JSON."
    }
}

function Assert-Traffic {
    param(
        [Parameter(Mandatory = $true)]$Status,
        [Parameter(Mandatory = $true)][hashtable]$Expected
    )
    $actual = @{}
    foreach ($entry in @($Status.versions)) {
        $actual[[string]$entry.version_id] = [double]$entry.percentage
    }
    foreach ($versionId in $Expected.Keys) {
        if (-not $actual.ContainsKey($versionId)) {
            throw "Deployment status omitted expected version $versionId."
        }
        if ([math]::Abs($actual[$versionId] - [double]$Expected[$versionId]) -gt 0.001) {
            throw "Version $versionId has unexpected traffic."
        }
    }
    $unexpectedPositive = @($actual.Keys | Where-Object {
        -not $Expected.ContainsKey($_) -and [double]$actual[$_] -gt 0.001
    })
    if ($unexpectedPositive.Count -gt 0) {
        throw "Unexpected Worker versions are receiving production traffic."
    }
}

function Invoke-SmokeChecks {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl,
        [string]$VersionId = ""
    )
    $base = ([uri]$BaseUrl).AbsoluteUri.TrimEnd('/')
    $headers = @{ Accept = "application/json, text/html;q=0.9" }
    if (-not [string]::IsNullOrWhiteSpace($VersionId)) {
        $headers["Cloudflare-Workers-Version-Overrides"] = "$($script:WorkerName)=`"$VersionId`""
    }
    $health = Invoke-RestMethod -Uri "$base/healthz" -Headers $headers -Method Get -TimeoutSec 20
    if ($health.status -cne "ok" -or $health.application -cne "sing-yin-roster-gateway") {
        throw "The Worker health response is not the expected gateway."
    }
    $entrance = Invoke-WebRequest -UseBasicParsing -Uri "$base/" -Headers $headers -Method Get -TimeoutSec 20
    if (
        [int]$entrance.StatusCode -ne 200 -or
        $entrance.Content -notmatch 'data-guest-bootstrap=' -or
        $entrance.Content -notmatch 'Study Prefect Duty Roster'
    ) {
        throw "The public entrance smoke check failed."
    }
    $viewer = Invoke-WebRequest -UseBasicParsing -Uri "$base/view" -Headers $headers -Method Get -TimeoutSec 20
    if ([int]$viewer.StatusCode -ne 200 -or $viewer.Content -notmatch 'viewer') {
        throw "The public viewer shell smoke check failed."
    }
    return [ordered]@{ health = 200; entrance = 200; viewer = 200 }
}

function Write-Report([System.Collections.IDictionary]$Payload) {
    $directory = Split-Path -Parent $script:ReportPath
    if (-not (Test-Path -LiteralPath $directory)) {
        $null = New-Item -ItemType Directory -Path $directory -Force
    }
    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $script:ReportPath -Encoding UTF8
}

$script:WorkerRoot = Join-Path (Resolve-Path -LiteralPath $SourceRoot).Path "cloudflare\roster_viewer"
$script:ConfigPath = Join-Path $script:WorkerRoot "wrangler.jsonc"
$script:WranglerPath = Join-Path $script:WorkerRoot "node_modules\wrangler\bin\wrangler.js"
$script:WorkerName = "sing-yin-roster-viewer"
$safeReleaseName = $ReleaseRef -replace '[^A-Za-z0-9._-]', '-'
$script:ReportPath = Join-Path $SourceRoot "logs\cloudflare-worker-deployment-$safeReleaseName.json"
$outputDirectory = Join-Path $env:TEMP "sing-yin-worker-deploy-$([guid]::NewGuid().ToString('N'))"
$uploadOutput = Join-Path $outputDirectory "upload.ndjson"
$stageOutput = Join-Path $outputDirectory "stage.ndjson"
$promoteOutput = Join-Path $outputDirectory "promote.ndjson"
$startedAt = [DateTimeOffset]::UtcNow
$releaseCommit = $null
$previousVersionId = $null
$newVersionId = $null
$staged = $false
$rollbackRequired = $false
$promoted = $false
$rollbackCompleted = $false
$stagedSmoke = $null
$liveSmoke = $null
$resolvedSecretOverlayPath = $null
$secretOverlayPathToDelete = $null
$secretOverlayNames = @()
$secretUploadArguments = @()

try {
    if (-not [string]::IsNullOrWhiteSpace($SecretOverlayPath)) {
        $resolvedSecretOverlayPath = [IO.Path]::GetFullPath($SecretOverlayPath)
        $overlayName = [IO.Path]::GetFileName($resolvedSecretOverlayPath)
        $overlayDirectory = [IO.Path]::GetFullPath(
            (Split-Path -Parent $resolvedSecretOverlayPath)
        ).TrimEnd([IO.Path]::DirectorySeparatorChar)
        $expectedTempDirectory = [IO.Path]::GetFullPath(
            [IO.Path]::GetTempPath()
        ).TrimEnd([IO.Path]::DirectorySeparatorChar)
        if (
            $overlayName -notmatch '^sing-yin-worker-secrets-[A-Za-z0-9_-]{8,128}\.json$' -or
            -not [string]::Equals(
                $overlayDirectory,
                $expectedTempDirectory,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "The Worker secret overlay must use the controlled one-use name in the Windows temp directory."
        }
        if (-not (Test-Path -LiteralPath $resolvedSecretOverlayPath -PathType Leaf)) {
            throw "The Worker secret overlay file is missing."
        }
        $overlayItem = Get-Item -LiteralPath $resolvedSecretOverlayPath -Force
        if (($overlayItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "The Worker secret overlay must not be a reparse point."
        }
        # Register cleanup as soon as the path itself is proven safe. Parsing or
        # semantic validation must never strand a one-use file containing secrets.
        $secretOverlayPathToDelete = $resolvedSecretOverlayPath
        try { $overlay = Get-Content -LiteralPath $resolvedSecretOverlayPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch {
            throw "The Worker secret overlay is not valid JSON."
        }
        $secretOverlayNames = @($overlay.PSObject.Properties | ForEach-Object { [string]$_.Name })
        if (
            $secretOverlayNames.Count -eq 0 -or
            $secretOverlayNames.Count -gt 32 -or
            @($secretOverlayNames | Where-Object { $_ -notmatch '^[A-Z][A-Z0-9_]{1,127}$' }).Count -gt 0
        ) {
            throw "The Worker secret overlay contains invalid secret names."
        }
        foreach ($property in @($overlay.PSObject.Properties)) {
            if ($property.Value -isnot [string] -or [string]::IsNullOrWhiteSpace($property.Value)) {
                throw "Every Worker secret overlay value must be a non-empty string."
            }
        }
        $allowlistProperty = @($overlay.PSObject.Properties | Where-Object { $_.Name -ceq "ADMIN_IDENTITY_ALLOWLIST" })
        if ($allowlistProperty.Count -eq 1) {
            Assert-AdminIdentityAllowlistValue -Value ([string]$allowlistProperty[0].Value)
        }
        $secretUploadArguments = @("--secrets-file", $resolvedSecretOverlayPath)
    }
    Write-Step "Validating immutable release source and pinned Worker toolchain"
    $releaseCommit = Assert-ImmutableRelease -Repository $SourceRoot -TagName $ReleaseRef
    $releaseReportPath = Join-Path $SourceRoot "logs\release-candidate-report.json"
    if (-not (Test-Path -LiteralPath $releaseReportPath -PathType Leaf)) {
        throw "The source-bound release report is missing."
    }
    $releaseTree = Get-GitValue -Repository $SourceRoot -Arguments @("rev-parse", "$releaseCommit`^{tree}")
    $sourcePython = Join-Path $SourceRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $sourcePython -PathType Leaf)) {
        throw "The verified source Python environment is missing."
    }
    $currentFingerprint = Get-CurrentReleaseFingerprint -Python $sourcePython -Repository $SourceRoot
    . (Join-Path $SourceRoot "scripts\release_gate_contract.ps1")
    $gateEvidence = Assert-ReleaseGateEvidence -Python $sourcePython -Repository $SourceRoot -ReportPath $releaseReportPath
    $releaseReport = $gateEvidence.report
    $postVerificationSource = $releaseReport.postVerificationSource
    $releaseSourceDirtyIsBoolean = Test-RequiredBooleanProperty `
        -InputObject $releaseReport `
        -Name "sourceDirty"
    $postSourceDirtyIsBoolean = Test-RequiredBooleanProperty `
        -InputObject $postVerificationSource `
        -Name "sourceDirty"
    $reportChecks = @($releaseReport.checks)
    $reportRequiredIdentities = @($releaseReport.requiredCheckIdentities)
    $reportCheckNames = @($reportChecks | ForEach-Object { [string]$_.name })
    $reportCheckStatuses = @($reportChecks | ForEach-Object { [string]$_.status })
    $reportIdentityDifferences = @(
        Compare-Object `
            -ReferenceObject @($reportRequiredIdentities | Sort-Object) `
            -DifferenceObject @($reportCheckNames | Sort-Object)
    )
    if (
        [int]$releaseReport.schemaVersion -ne $gateEvidence.reportSchemaVersion -or
        [string]$releaseReport.status -cne "pass" -or
        [string]$releaseReport.sourceCommit -cne $releaseCommit -or
        [string]$releaseReport.sourceTree -cne $releaseTree -or
        -not $releaseSourceDirtyIsBoolean -or
        [bool]$releaseReport.sourceDirty -or
        [string]$releaseReport.plannedReleaseTag -cne $ReleaseRef -or
        [string]$releaseReport.immutableReleaseReference -cne "refs/tags/$ReleaseRef" -or
        [bool]$releaseReport.humanAcceptanceRequired -ne $true -or
        $null -eq $postVerificationSource -or
        [string]$postVerificationSource.sourceFingerprint -cne [string]$releaseReport.sourceFingerprint -or
        [int]$postVerificationSource.sourceFileCount -ne [int]$releaseReport.sourceFileCount -or
        [string]$postVerificationSource.sourceCommit -cne [string]$releaseReport.sourceCommit -or
        [string]$postVerificationSource.sourceTree -cne [string]$releaseReport.sourceTree -or
        -not $postSourceDirtyIsBoolean -or
        [bool]$postVerificationSource.sourceDirty -or
        [string]$releaseReport.sourceFingerprint -cne [string]$currentFingerprint.fingerprint -or
        [int]$releaseReport.sourceFileCount -ne [int]$currentFingerprint.fileCount -or
        $reportRequiredIdentities.Count -eq 0 -or
        $reportChecks.Count -ne $reportRequiredIdentities.Count -or
        $reportIdentityDifferences.Count -ne 0 -or
        @($reportCheckStatuses | Where-Object { $_ -cne "pass" }).Count -ne 0
    ) {
        throw "The source-bound release report does not match the immutable Worker release."
    }
    $script:NodePath = Find-NodeExecutable
    if (-not (Test-Path -LiteralPath $script:WranglerPath -PathType Leaf)) {
        throw "Pinned Wrangler is not installed in the Worker workspace."
    }
    $package = Get-Content -LiteralPath (Join-Path $script:WorkerRoot "package.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$package.devDependencies.wrangler -cne "4.116.0") {
        throw "Worker deployment requires pinned Wrangler 4.116.0."
    }
    $wranglerVersion = ((Invoke-Wrangler -Arguments @("--version")) | Out-String).Trim()
    $activeWranglerVersion = Get-WranglerSemanticVersion -Output $wranglerVersion
    if ($activeWranglerVersion -cne "4.116.0") {
        throw "The active Wrangler executable is not version 4.116.0."
    }
    $null = New-Item -ItemType Directory -Path $outputDirectory -Force
    $dryRunArguments = @("versions", "upload", "--dry-run", "--strict", "--config", $script:ConfigPath) + $secretUploadArguments
    Invoke-Wrangler -Arguments $dryRunArguments | Out-Null
    Assert-RequiredWorkerSecrets -AdditionalNames $secretOverlayNames

    Write-Step "Capturing the current 100 percent production version"
    $before = Get-DeploymentStatus
    $positiveVersions = @($before.versions | Where-Object { [double]$_.percentage -gt 0.001 })
    if ($positiveVersions.Count -ne 1 -or [math]::Abs([double]$positiveVersions[0].percentage - 100.0) -gt 0.001) {
        throw "Production must have exactly one Worker version at 100 percent before release."
    }
    $previousVersionId = [string]$positiveVersions[0].version_id

    Write-Step "Uploading $ReleaseRef as an undeployed Worker version"
    $uploadArguments = @(
        "versions", "upload", "--strict", "--config", $script:ConfigPath,
        "--tag", $ReleaseRef, "--message", "Service Weave $ReleaseRef"
    ) + $secretUploadArguments
    Invoke-Wrangler -OutputFile $uploadOutput -Arguments $uploadArguments | Out-Null
    $uploadEvent = Read-WranglerEvent -Path $uploadOutput -Type "version-upload"
    $newVersionId = [string]$uploadEvent.version_id
    if ($newVersionId -notmatch '^[0-9a-f-]{36}$' -or $newVersionId -ceq $previousVersionId) {
        throw "Wrangler returned an invalid new Worker version ID."
    }

    Write-Step "Staging the new Worker at zero percent traffic"
    # From this point onward a remote deployment mutation may have occurred even
    # if Wrangler loses its response, so every failure must restore the captured
    # production version.
    $rollbackRequired = $true
    Invoke-Wrangler -OutputFile $stageOutput -Arguments @(
        "versions", "deploy", "$previousVersionId@100%", "$newVersionId@0%",
        "--config", $script:ConfigPath, "--message", "Stage $ReleaseRef at zero percent", "--yes"
    ) | Out-Null
    $null = Read-WranglerEvent -Path $stageOutput -Type "version-deploy"
    $staged = $true
    $stageStatus = Get-DeploymentStatus
    Assert-Traffic -Status $stageStatus -Expected @{ $previousVersionId = 100.0; $newVersionId = 0.0 }

    Write-Step "Smoke-testing only the staged Worker version"
    $stagedSmoke = Invoke-SmokeChecks -BaseUrl $PublicBaseUrl -VersionId $newVersionId

    Write-Step "Promoting the verified Worker version to 100 percent"
    Invoke-Wrangler -OutputFile $promoteOutput -Arguments @(
        "versions", "deploy", "$newVersionId@100%", "--config", $script:ConfigPath,
        "--message", "Promote $ReleaseRef after version override smoke checks", "--yes"
    ) | Out-Null
    $null = Read-WranglerEvent -Path $promoteOutput -Type "version-deploy"
    $promoteStatus = Get-DeploymentStatus
    Assert-Traffic -Status $promoteStatus -Expected @{ $newVersionId = 100.0 }
    $promoted = $true

    Write-Step "Verifying the live canonical site"
    $liveSmoke = Invoke-SmokeChecks -BaseUrl $PublicBaseUrl
    # A successful report is only truthful after the one-use secret file has
    # been securely emptied and removed. Cleanup failure follows the same
    # rollback path as any other deployment failure.
    Remove-SecretOverlay -Path $secretOverlayPathToDelete
    $secretOverlayPathToDelete = $null
    Write-Report -Payload ([ordered]@{
        status = "pass"
        releaseRef = $ReleaseRef
        releaseCommit = $releaseCommit
        worker = $script:WorkerName
        previousVersionId = $previousVersionId
        newVersionId = $newVersionId
        stagedAtZeroPercent = $staged
        promotedToOneHundredPercent = $promoted
        stagedSmoke = $stagedSmoke
        liveSmoke = $liveSmoke
        rollbackCompleted = $false
        startedAt = $startedAt.ToString("o")
        completedAt = [DateTimeOffset]::UtcNow.ToString("o")
    })
    Write-Host "`nCloudflare Worker deployment completed: $newVersionId" -ForegroundColor Green
    Write-Host "Report: $script:ReportPath"
} catch {
    $failure = Protect-Text $_.Exception.Message
    if ($rollbackRequired -and -not [string]::IsNullOrWhiteSpace($previousVersionId)) {
        try {
            Write-Step "Rolling production back to the exact previous Worker version"
            Invoke-Wrangler -Arguments @(
                "rollback", $previousVersionId, "--config", $script:ConfigPath,
                "--message", "Automatic rollback after failed $ReleaseRef", "--yes"
            ) | Out-Null
            $rollbackStatus = Get-DeploymentStatus
            Assert-Traffic -Status $rollbackStatus -Expected @{ $previousVersionId = 100.0 }
            $rollbackCompleted = $true
        } catch {
            $failure = "$failure Rollback also failed: $(Protect-Text $_.Exception.Message)"
        }
    }
    Write-Report -Payload ([ordered]@{
        status = "fail"
        releaseRef = $ReleaseRef
        releaseCommit = $releaseCommit
        worker = $script:WorkerName
        previousVersionId = $previousVersionId
        newVersionId = $newVersionId
        stagedAtZeroPercent = $staged
        promotedToOneHundredPercent = $promoted
        rollbackCompleted = $rollbackCompleted
        error = $failure
        startedAt = $startedAt.ToString("o")
        completedAt = [DateTimeOffset]::UtcNow.ToString("o")
    })
    throw $failure
} finally {
    if (Test-Path -LiteralPath $outputDirectory) {
        Remove-Item -LiteralPath $outputDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-SecretOverlay -Path $secretOverlayPathToDelete
}
