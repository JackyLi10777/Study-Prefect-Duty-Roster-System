"""Fictional gate evidence; never invoke a deployment script or live service."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from nicegui_app import release_gates as gates
from nicegui_app.release_evidence import RELEASE_SOURCE_FILES, load_release_evidence
from scripts import verify_release_candidate as verifier
from tests.test_release_evidence import _report

ROOT = Path(__file__).resolve().parents[1]


def _mutate(payload, defect):
    if defect == "self-reduced":
        payload["requiredCheckIdentities"] = payload["requiredCheckIdentities"][:1]
        payload["checks"] = payload["checks"][:1]
    elif defect == "same-reorder":
        payload["requiredCheckIdentities"].reverse()
        payload["checks"].reverse()
    elif defect == "duplicate":
        payload["checks"][-1] = copy.deepcopy(payload["checks"][0])
    elif defect == "extra":
        payload["checks"].append({"name": "extra", "status": "pass", "durationMs": 1})
    elif defect == "missing":
        payload["checks"].pop()
    elif defect == "missing-manifest":
        del payload["gateManifest"]
    elif defect == "wrong-manifest":
        payload["gateManifest"]["fingerprint"] = "0" * 64
    elif defect == "boolean-version":
        payload["gateManifest"]["version"] = True
    elif defect == "old-schema":
        payload["schemaVersion"] = 3
    elif defect == "missing-timing":
        del payload["checks"][0]["durationMs"]
    elif defect == "boolean-timing":
        payload["checks"][0]["durationMs"] = True
    elif defect == "negative-timing":
        payload["checks"][0]["durationMs"] = -1
    elif defect == "failed":
        payload["checks"][0]["status"] = "fail"
    elif defect == "malformed-identities":
        payload["requiredCheckIdentities"] = [{"not": "a string"}]
    elif defect is not None:
        raise AssertionError(defect)
    return payload


DEFECTS = ("self-reduced", "same-reorder", "duplicate", "extra", "missing", "missing-manifest",
           "wrong-manifest", "boolean-version", "old-schema", "missing-timing", "boolean-timing",
           "negative-timing", "failed", "malformed-identities")


@pytest.mark.parametrize("defect", (None, *DEFECTS))
def test_all_python_consumers_agree_on_source_owned_contract(tmp_path, defect):
    payload = _mutate(_report(fingerprint="current"), defect)
    path = tmp_path / "fictional.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert (load_release_evidence(path, current_fingerprint="current").state == "pass") == (defect is None)
    if defect is None:
        gates.validate_completed_gates(payload)
        verifier._assert_completed_checks(payload)
    else:
        with pytest.raises(ValueError):
            gates.validate_completed_gates(payload)
        with pytest.raises(verifier.ReleaseVerificationError):
            verifier._assert_completed_checks(payload)


@pytest.mark.parametrize("raw", ['{"same":1,"same":2}', '{"nested":{"x":1,"x":2}}',
                                  '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', "[" * 2000])
def test_report_json_does_not_silently_discard_ambiguous_evidence(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        gates.read_strict_json(path)
    assert load_release_evidence(path, current_fingerprint="current").state == "unreadable"


@pytest.mark.parametrize("field,value", [("schemaVersion", True), ("schemaVersion", 2),
    ("reportSchemaVersion", 3), ("reportSchemaVersion", 4.0), ("requiredChecks", []),
    ("requiredChecks", ["same", "same"]), ("requiredChecks", ["Valid"]),
    ("requiredChecks", [True]), ("requiredChecks", "one")])
def test_invalid_source_manifest_is_rejected(tmp_path, field, value):
    manifest = gates.load_gate_manifest()
    manifest[field] = value
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        gates.load_gate_manifest(path)


def test_manifest_and_both_deployment_consumers_invalidate_runtime_fingerprint():
    required = {ROOT / "scripts" / name for name in ("release-gates.json", "release_gate_contract.ps1",
                 "deploy_windows_release.ps1", "deploy_cloudflare_worker.ps1")}
    assert required <= set(RELEASE_SOURCE_FILES)
    assert verifier.REQUIRED_CHECK_IDENTITIES is gates.REQUIRED_CHECK_IDENTITIES


def test_deployment_consumes_the_exact_report_validated_by_the_bridge(tmp_path):
    payload = _report(fingerprint="current")
    path = tmp_path / "report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "nicegui_app.release_gates", "--report", str(path)],
                            cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    assert json.loads(result.stdout).get("report") == payload
    for name in ("deploy_windows_release.ps1", "deploy_cloudflare_worker.ps1"):
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "$releaseReport = $gateEvidence.report" in source
        assert "Get-Content -LiteralPath $releaseReportPath" not in source


@pytest.mark.parametrize("corrupt_returned_snapshot", [False, True])
def test_windows_powershell_bridge_uses_same_validator_without_deploying(tmp_path, corrupt_returned_snapshot):
    shell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell is unavailable")
    fixture = tmp_path / "fictional source with spaces"
    package = fixture / "nicegui_app"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(ROOT / "nicegui_app/release_gates.py", package / "release_gates.py")
    (fixture / "scripts").mkdir()
    shutil.copy2(gates.GATE_MANIFEST_PATH, fixture / "scripts/release-gates.json")
    cases = []
    for index, defect in enumerate((None, *DEFECTS)):
        path = fixture / f"report-{index}.json"
        path.write_text(json.dumps(_mutate(_report(fingerprint="current"), defect)), encoding="utf-8")
        cases.append({"path": str(path), "valid": defect is None})
    # Duplicate keys can be lost by ConvertFrom-Json; the bridge reads raw JSON
    # in Python, even if its deployment caller already parsed the same file.
    duplicate = fixture / "duplicate-json.json"
    raw = json.dumps(_report(fingerprint="current"))
    duplicate.write_text('{"schemaVersion":3,' + raw[1:], encoding="utf-8")
    cases.append({"path": str(duplicate), "valid": False})
    cases_path = fixture / "cases.json"
    cases_path.write_text(json.dumps(cases), encoding="utf-8")
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    script = f"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. {quote(ROOT / 'scripts/release_gate_contract.ps1')}
$cases = Get-Content -LiteralPath {quote(cases_path)} -Raw | ConvertFrom-Json
foreach ($case in $cases) {{
    $validated = $false
    try {{
        $gate = Assert-ReleaseGateEvidence -Python {quote(sys.executable)} -Repository {quote(fixture)} -ReportPath $case.path
        $validated = $true
    }} catch {{ $validated = $false }}
    if ($validated -ne $case.valid) {{ throw 'Consumer mismatch' }}
    if ($validated) {{
        if ($gate.requiredChecks.Count -ne {len(gates.REQUIRED_CHECK_IDENTITIES)}) {{ throw 'Checklist mismatch' }}
        # A later report replacement must not replace the validated snapshot.
        Set-Content -LiteralPath $case.path -Value '{{"sourceCommit":"changed"}}'
        {"$gate.report.sourceCommit = 'corrupted-returned-snapshot'" if corrupt_returned_snapshot else ""}
        # Assertions stay outside the expected rejection catch. The corruption
        # control proves a broken snapshot assertion really fails this harness.
        if ($gate.report.sourceCommit -cne {quote('a' * 40)}) {{ throw 'Snapshot changed' }}
    }}
}}
Write-Output 'PASS pure evidence bridge'
"""
    result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                            capture_output=True, text=True, timeout=60)
    if corrupt_returned_snapshot:
        assert result.returncode != 0
        assert "Snapshot changed" in result.stderr
        assert "PASS pure evidence bridge" not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert "PASS pure evidence bridge" in result.stdout
