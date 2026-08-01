[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z]:\\?$')]
    [string]$DestinationDrive,
    [string]$HostRoot = "C:\SingYinRoster",
    [string]$TaskName = "Sing Yin Roster Host",
    [string]$RuntimeUser = "SingYinRosterSvc"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-SingYinApprovedOffsiteVolume {
    param([Parameter(Mandatory = $true)][string]$Drive)

    $driveLetter = $Drive.Substring(0, 1).ToUpperInvariant()
    $partition = Get-Partition -DriveLetter $driveLetter -ErrorAction Stop
    $disk = $partition | Get-Disk -ErrorAction Stop
    if (@($disk).Count -ne 1) {
        throw "The destination must resolve to exactly one physical disk."
    }
    if ([bool]$disk.IsBoot -or [bool]$disk.IsSystem) {
        throw "The Windows boot or system disk cannot be an off-site recovery target."
    }
    if ([string]$disk.BusType -notin @("USB", "SD")) {
        throw "The recovery target must be an externally removable USB or SD disk."
    }

    $mountPoint = "$driveLetter`:"
    $bitLocker = Get-BitLockerVolume -MountPoint $mountPoint -ErrorAction Stop
    if (@($bitLocker).Count -ne 1) {
        throw "The destination must resolve to exactly one BitLocker volume."
    }
    if ([string]$bitLocker.ProtectionStatus -ne "On") {
        throw "BitLocker protection must be enabled on the external recovery volume."
    }
    if ([string]$bitLocker.VolumeStatus -ne "FullyEncrypted") {
        throw "The external recovery volume must be fully encrypted before export."
    }
    if ([string]$bitLocker.LockStatus -ne "Unlocked") {
        throw "Unlock the approved BitLocker recovery volume before export."
    }

    $volume = Get-Volume -DriveLetter $driveLetter -ErrorAction Stop
    if ([string]$volume.FileSystem -ne "NTFS") {
        throw "The approved recovery volume must use NTFS."
    }
    if ([string]::IsNullOrWhiteSpace([string]$volume.UniqueId)) {
        throw "Windows did not expose a stable identity for the recovery volume."
    }
    if ([long]$volume.SizeRemaining -lt 536870912) {
        throw "The approved recovery volume has less than 512 MiB free."
    }

    $evidenceMaterial = (
        [string]$volume.UniqueId + "|" +
        [string]$disk.Number + "|" +
        [string]$disk.BusType + "|" +
        [string]$bitLocker.EncryptionMethod
    )
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $evidenceHash = ([BitConverter]::ToString(
            $hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($evidenceMaterial))
        )).Replace("-", "").ToLowerInvariant()
    } finally {
        $hasher.Dispose()
    }

    return [pscustomobject]@{
        Root = "$driveLetter`:\"
        EvidenceSha256 = $evidenceHash
        EncryptionMethod = [string]$bitLocker.EncryptionMethod
    }
}

$HostRoot = (Resolve-Path -LiteralPath $HostRoot -ErrorAction Stop).Path
. (Join-Path $PSScriptRoot "windows_host_common.ps1")

Assert-SingYinAdministrator -Operation "Sing Yin off-site recovery export"
$taskInspection = Get-SingYinTaskInspection `
    -TaskName $TaskName `
    -ProjectRoot $HostRoot `
    -RuntimeUser $RuntimeUser `
    -AllowReleaseBundle
if (-not $taskInspection.Exists -or -not $taskInspection.Owned) {
    throw "The owned Sing Yin production task could not be verified."
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$actions = @($task.Actions)
if ($actions.Count -ne 1) {
    throw "The production task must have exactly one verified action."
}
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $HostRoot "releases")).TrimEnd('\')
$runtimeRoot = [IO.Path]::GetFullPath([string]$actions[0].WorkingDirectory).TrimEnd('\')
if (-not $runtimeRoot.StartsWith("$releaseRoot\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "The production task is not running from an immutable release bundle."
}
$expectedScriptRoot = [IO.Path]::GetFullPath((Join-Path $runtimeRoot "scripts")).TrimEnd('\')
$actualScriptRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
if (-not $actualScriptRoot.Equals($expectedScriptRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Run the off-site recovery wrapper from the active immutable release bundle."
}

$python = Join-Path $runtimeRoot ".venv\Scripts\python.exe"
$recoveryTool = Join-Path $runtimeRoot "scripts\offsite_recovery.py"
$releaseMarker = Join-Path $runtimeRoot ".sing-yin-release.json"
foreach ($requiredFile in @($python, $recoveryTool, $releaseMarker)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "The active immutable release does not contain the required off-site recovery capability."
    }
}

$target = Get-SingYinApprovedOffsiteVolume -Drive $DestinationDrive
$destinationRoot = Join-Path $target.Root "SingYinRosterRecoveryMedia"
$databasePath = Join-Path $HostRoot "data\runtime\sing-yin-roster.sqlite3"
$backupDir = Join-Path $HostRoot "data\backups"
$reportPath = Join-Path $HostRoot "logs\offsite-recovery-latest.json"
if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw "The official database is unavailable."
}
if (-not (Test-Path -LiteralPath $backupDir -PathType Container)) {
    throw "The managed backup directory is unavailable."
}
$null = New-Item -ItemType Directory -Path $destinationRoot -Force
$destinationItem = Get-Item -LiteralPath $destinationRoot -Force
if (($destinationItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw "The off-site destination must not be a reparse point."
}
$resolvedDestination = [IO.Path]::GetFullPath($destinationItem.FullName)
$approvedPrefix = [IO.Path]::GetFullPath($target.Root)
if (-not $resolvedDestination.StartsWith($approvedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "The off-site destination escaped the approved external volume."
}

& $python -B -X utf8 $recoveryTool export-and-drill `
    --database-path $databasePath `
    --backup-dir $backupDir `
    --destination-root $destinationRoot `
    --release-marker $releaseMarker `
    --target-kind bitlocker_external `
    --target-evidence-sha256 $target.EvidenceSha256 `
    --target-encryption-method $target.EncryptionMethod `
    --report $reportPath
if ($LASTEXITCODE -ne 0) {
    throw "The off-site export or isolated restore drill failed. Review the protected report locally."
}

$targetAfterDrill = Get-SingYinApprovedOffsiteVolume -Drive $DestinationDrive
if (
    -not $targetAfterDrill.Root.Equals($target.Root, [StringComparison]::OrdinalIgnoreCase) -or
    -not $targetAfterDrill.EvidenceSha256.Equals($target.EvidenceSha256, [StringComparison]::Ordinal) -or
    -not $targetAfterDrill.EncryptionMethod.Equals($target.EncryptionMethod, [StringComparison]::Ordinal)
) {
    throw "The approved external recovery volume changed during export or drill."
}

$report = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (
    [string]$report.status -ne "pass" -or
    [string]$report.export.bundleName -notmatch '^SYSS_Offsite_[A-Za-z0-9_]+$' -or
    [string]$report.drill.status -ne "pass" -or
    -not [bool]$report.drill.rowCountsMatched -or
    -not [bool]$report.drill.fairnessBalanced -or
    -not [bool]$report.drill.restoreAuditAppended
) {
    throw "The off-site recovery report did not retain the complete pass contract."
}
$expectedBundle = Join-Path (Join-Path $destinationRoot "SingYinRosterRecovery") ([string]$report.export.bundleName)
if (-not (Test-Path -LiteralPath $expectedBundle -PathType Container)) {
    throw "The verified off-site bundle is no longer present on the approved external volume."
}

Write-Host "Off-site recovery export and isolated restore drill passed."
Write-Host "Bundle: $($report.export.bundleName)"
Write-Host "RPO at export: $($report.export.rpoSecondsAtExport) seconds"
Write-Host "Measured isolated RTO: $($report.drill.rtoSeconds) seconds"
Write-Host "Safely eject the encrypted volume and place it with the approved school custodian."
