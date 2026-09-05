"""Release asset gates: real read-only commands, isolated stale-output controls."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from nicegui_app.release_evidence import RELEASE_SOURCE_FILES
from nicegui_app.release_gates import REQUIRED_CHECK_IDENTITIES
from scripts import verify_release_candidate as verifier


ROOT = Path(__file__).resolve().parents[1]
ASSET_GATES = {
    "generated_design_tokens": "scripts/generate_design_system_tokens.py",
    "generated_service_weave_delivery": "scripts/generate_service_weave_delivery.py",
}


def test_asset_gates_are_required_and_their_checkers_bind_release_source():
    assert set(ASSET_GATES) <= set(REQUIRED_CHECK_IDENTITIES)
    assert {ROOT / script for script in ASSET_GATES.values()} <= set(RELEASE_SOURCE_FILES)


@pytest.mark.parametrize("failed_gate", ASSET_GATES)
def test_runner_records_asset_failure_without_repairing_or_starting_browsers(monkeypatch, tmp_path, failed_gate):
    workspace = tmp_path / "isolated"
    workspace.mkdir()
    report_path = tmp_path / "report.json"
    source = {"sourceFingerprint": "a" * 64, "sourceFileCount": 1,
              "sourceCommit": "b" * 40, "sourceTree": "c" * 40, "sourceDirty": False}
    monkeypatch.setattr(verifier, "REPORT_PATH", report_path)
    monkeypatch.setattr(verifier.tempfile, "mkdtemp", lambda **_: str(workspace))
    monkeypatch.setattr(verifier, "_source_state", lambda **_: dict(source))
    monkeypatch.setattr(verifier, "_planned_release_tag", lambda: "v1.2.0-rc.999")
    monkeypatch.setattr(verifier, "_tool_versions", lambda: {})
    monkeypatch.setattr(verifier, "_deno_motion_command", lambda: ["stub-motion"])
    monkeypatch.setattr(verifier, "_deno_gateway_command", lambda: ["stub-worker"])
    commands = []

    def run(command, **_):
        commands.append(command)
        for script in ASSET_GATES.values():
            if script in command:
                assert command == [sys.executable, "-X", "utf8", script, "--check"]
        return SimpleNamespace(returncode=1 if ASSET_GATES[failed_gate] in command else 0)

    def forbidden(**_):
        raise AssertionError("Browser phase must not begin with unverified generated assets")

    monkeypatch.setattr(verifier.subprocess, "run", run)
    monkeypatch.setattr(verifier, "_run_browser_phase", forbidden)
    monkeypatch.setattr(verifier, "_run_unified_access_phase", forbidden)
    assert verifier.main() == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "fail"
    assert report["checks"][-1]["name"] == failed_gate
    assert report["checks"][-1]["status"] == "fail"
    assert report["postVerificationSource"] == source
    assert workspace.is_dir(), "Retain failures rather than removing their evidence"
    assert ASSET_GATES[failed_gate] in commands[-1]


def _fixture(tmp_path):
    from nicegui_app.ui import design_token_contract as tokens
    from scripts import generate_service_weave_delivery as delivery
    files = {
        *(ROOT / script for script in ASSET_GATES.values()),
        ROOT / "nicegui_app/config.py", Path(tokens.__file__), tokens.SOURCE_PATH, tokens.WORKER_RUNTIME_PATH,
        tokens.THEME_MARKUP_PATH, *tokens.expected_generated_files(),
        *tokens.NICEGUI_CSS_PATH.parent.glob("*.css"),
        delivery.IDENTITY_SOURCE, delivery.SOURCE, delivery.LIGHT_MARK,
        delivery.WHITE_MARK, delivery.OUTPUT, *delivery.WORKER_LANDING_ASSETS.values(),
        *(delivery.WORKER_PUBLIC_ASSET_DIR / name for name in delivery.WORKER_LANDING_ASSETS),
    }
    for path in files:
        destination = tmp_path / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    return {
        "tokens": tokens.NICEGUI_CSS_PATH.relative_to(ROOT),
        "worker_tokens": tokens.WORKER_CONTRACT_PATH.relative_to(ROOT),
        "white_mark": delivery.WHITE_MARK.relative_to(ROOT),
        "module": delivery.OUTPUT.relative_to(ROOT),
        **{name: (delivery.WORKER_PUBLIC_ASSET_DIR / name).relative_to(ROOT)
           for name in delivery.WORKER_LANDING_ASSETS},
    }


def _tree_hash(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("gate,stale", [
    ("generated_design_tokens", None), ("generated_design_tokens", "tokens"),
    ("generated_design_tokens", "worker_tokens"),
    ("generated_service_weave_delivery", None), ("generated_service_weave_delivery", "white_mark"),
    ("generated_service_weave_delivery", "module"),
    ("generated_service_weave_delivery", "service-weave-mark-light-v1.png"),
    ("generated_service_weave_delivery", "service-weave-mark-dark-v1.png"),
])
@pytest.mark.parametrize("defect", ["stale", "missing"])
def test_real_check_commands_reject_stale_outputs_and_never_rewrite_fixture(tmp_path, gate, stale, defect):
    targets = _fixture(tmp_path)
    if stale:
        target = tmp_path / targets[stale]
        if defect == "missing":
            target.unlink()
        else:
            target.write_bytes(b"fictional stale generated output\n")
    before = _tree_hash(tmp_path)
    result = subprocess.run([sys.executable, "-I", "-B", str(tmp_path / ASSET_GATES[gate]), "--check"],
                            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert (result.returncode == 0) == (stale is None), result.stdout + result.stderr
    if stale:
        output = (result.stdout + result.stderr).lower()
        assert "stale" in output or "missing generated file" in output
    assert _tree_hash(tmp_path) == before
