"""Behavioral checks for idle polling, revocation and browser lifecycle races."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from nicegui_app.access_context import AccessMode
from nicegui_app.ui import shell


@pytest.mark.parametrize("mode", [AccessMode.ADMIN, AccessMode.GUEST])
@pytest.mark.parametrize(
    "scenario",
    [
        "hidden", "visibility", "expiry", "revoked", "broadcast", "failure",
        "late-response", "late-json", "reinstall", "hidden-response",
        "expiry-pending", "logout-retry", "network-error",
    ],
)
def test_auth_monitor_browser_lifecycle(
    monkeypatch: pytest.MonkeyPatch, mode: AccessMode, scenario: str,
) -> None:
    node = shutil.which("node")
    assert node is not None, "Node.js is required by the repository's verification environment"
    scripts: list[str] = []
    monkeypatch.setattr(shell.ui, "run_javascript", scripts.append)
    shell._install_auth_status_monitor(
        mode, datetime.fromtimestamp(1800003600, tz=timezone.utc),
    )
    assert len(scripts) == 1
    result = subprocess.run(
        [node, str(Path(__file__).with_name("auth_status_runtime.cjs"))],
        input=json.dumps({"script": scripts[0], "scenario": scenario, "mode": mode.value}),
        text=True, encoding="utf-8", capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"scenario": scenario, "mode": mode.value, "status": "pass"}
