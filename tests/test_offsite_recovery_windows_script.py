from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "export_offsite_recovery.ps1"


def test_windows_export_fails_closed_on_storage_and_encryption_boundaries() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "& $python -B -X utf8 $recoveryTool export-and-drill" in source

    assert "Assert-SingYinAdministrator" in source
    assert "Get-Partition" in source
    assert "Get-Disk" in source
    assert 'BusType -notin @("USB", "SD")' in source
    assert ".IsBoot" in source
    assert ".IsSystem" in source
    assert "Get-BitLockerVolume" in source
    assert 'ProtectionStatus -ne "On"' in source
    assert 'VolumeStatus -ne "FullyEncrypted"' in source
    assert "bitlocker_external" in source
    assert "export-and-drill" in source
    assert 'Join-Path $PSScriptRoot "windows_host_common.ps1"' in source
    assert "$actualScriptRoot.Equals($expectedScriptRoot" in source
    assert source.count("Get-SingYinApprovedOffsiteVolume -Drive $DestinationDrive") == 2
    assert "$targetAfterDrill.EvidenceSha256.Equals($target.EvidenceSha256" in source


def test_windows_export_does_not_offer_host_bound_or_unverified_fallbacks() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert "dpapi" not in source
    assert "convertfrom-securestring" not in source
    assert "cipher.exe" not in source
    assert "allowinternal" not in source
    assert "allownetwork" not in source
