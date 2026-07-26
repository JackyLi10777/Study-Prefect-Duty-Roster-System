from __future__ import annotations

import json
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "collect_host_security_summary.ps1"


def test_host_security_collector_is_privacy_bounded_by_contract() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden_output in (
        '"username"',
        '"hostname"',
        '"ipAddress"',
        '"commandLine"',
        '"eventXml"',
    ):
        assert forbidden_output not in source
    assert "Get-MpComputerStatus" in source
    assert "Get-NetFirewallProfile" in source
    assert "Sing Yin Roster Host" in source


def test_host_security_collector_emits_data_free_json() -> None:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ExpectedSourceFingerprint",
            "a" * 64,
            "-ObservedSourceFingerprint",
            "a" * 64,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schemaVersion"] == 1
    assert payload["evidenceClass"] == "privacy_bounded_host_security_summary"
    assert payload["release"]["fingerprintMatch"] is True
    serialized = json.dumps(payload).lower()
    assert "c:\\users\\" not in serialized
    assert "student" not in serialized.replace("student_data", "")
