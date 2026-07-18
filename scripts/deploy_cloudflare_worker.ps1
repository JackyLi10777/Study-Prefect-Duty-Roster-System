[CmdletBinding()]
param(
    [string]$SourceRoot = "D:\code_v3",
    [Parameter(Mandatory = $true)][string]$ReleaseRef,
    [string]$PublicBaseUrl = "https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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
    if ([int]$entrance.StatusCode -ne 200 -or $entrance.Content -notmatch 'Service Weave') {
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

try {
    Write-Step "Validating immutable release source and pinned Worker toolchain"
    $releaseCommit = Assert-ImmutableRelease -Repository $SourceRoot -TagName $ReleaseRef
    $script:NodePath = Find-NodeExecutable
    if (-not (Test-Path -LiteralPath $script:WranglerPath -PathType Leaf)) {
        throw "Pinned Wrangler is not installed in the Worker workspace."
    }
    $package = Get-Content -LiteralPath (Join-Path $script:WorkerRoot "package.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$package.devDependencies.wrangler -cne "4.110.0") {
        throw "Worker deployment requires pinned Wrangler 4.110.0."
    }
    $wranglerVersion = ((Invoke-Wrangler -Arguments @("--version")) | Out-String).Trim()
    if ($wranglerVersion -notmatch '4\.110\.0') {
        throw "The active Wrangler executable is not version 4.110.0."
    }
    $null = New-Item -ItemType Directory -Path $outputDirectory -Force
    Invoke-Wrangler -Arguments @("versions", "upload", "--dry-run", "--strict", "--config", $script:ConfigPath) | Out-Null

    Write-Step "Capturing the current 100 percent production version"
    $before = Get-DeploymentStatus
    $positiveVersions = @($before.versions | Where-Object { [double]$_.percentage -gt 0.001 })
    if ($positiveVersions.Count -ne 1 -or [math]::Abs([double]$positiveVersions[0].percentage - 100.0) -gt 0.001) {
        throw "Production must have exactly one Worker version at 100 percent before release."
    }
    $previousVersionId = [string]$positiveVersions[0].version_id

    Write-Step "Uploading $ReleaseRef as an undeployed Worker version"
    Invoke-Wrangler -OutputFile $uploadOutput -Arguments @(
        "versions", "upload", "--strict", "--config", $script:ConfigPath,
        "--tag", $ReleaseRef, "--message", "Service Weave $ReleaseRef"
    ) | Out-Null
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
}
