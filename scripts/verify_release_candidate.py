"""Run the complete release-candidate evidence suite in disposable local data.

This script never points browser writes at the configured school database. It
creates its own SQLite, backup, and log paths, launches two isolated NiceGUI
servers, and records a non-sensitive result in ``logs/release-candidate-report.json``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from typing import IO
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui_app.config import POLICY_VERSION
from nicegui_app.release_evidence import (
    PROJECT_ID,
    RELEASE_REPORT_SCHEMA_VERSION,
    release_source_fingerprint,
)


REPORT_PATH = PROJECT_ROOT / "logs" / "release-candidate-report.json"
CANONICAL_DATABASE = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
CANONICAL_BACKUPS = (PROJECT_ROOT / "data" / "backups").resolve()
_SERVER_FAILURE_MARKERS = (
    re.compile(r"(?:^|\s)(?:ERROR|CRITICAL)(?:\s|\[)", re.MULTILINE),
    re.compile(r"Traceback \(most recent call last\):"),
    re.compile(r"Task exception was never retrieved", re.IGNORECASE),
)
_WORKER_RUNTIME_TEST = (
    "tests/test_cloudflare_roster_viewer.py::"
    "test_worker_runtime_access_crypto_and_proxy_contracts"
)
REQUIRED_CHECK_IDENTITIES = (
    "repository_hygiene",
    "security_gates",
    "motion_state_machine_tests",
    "cloudflare_gateway_tests",
    "automated_test_suite",
    "python_compile",
    "dependency_integrity",
    "rc31_theme_control_browser",
    "verify_nicegui_ui",
    "verify_runtime_performance",
    "verify_nicegui_write_pipeline",
    "verify_nicegui_mobile",
    "strict_deployment_readiness",
    "verify_unified_guest_ui",
    "verify_nicegui_partial_backup",
)


class ReleaseVerificationError(RuntimeError):
    """Raised when one release gate fails; later gates must not imply success."""


class ReleaseSourceDriftError(ReleaseVerificationError):
    """Raised at the first gate boundary whose source no longer matches the candidate."""


def _git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _planned_release_tag() -> str:
    configured = os.getenv("SING_YIN_RELEASE_TAG", "").strip()
    if configured:
        if not re.fullmatch(r"v1\.2\.0-rc\.\d+", configured):
            raise ReleaseVerificationError("SING_YIN_RELEASE_TAG is not a valid v1.2.0 release-candidate tag.")
        return configured
    existing = _git_value("tag", "--list", "v1.2.0-rc.*").splitlines()
    numbers = [int(match.group(1)) for tag in existing if (match := re.fullmatch(r"v1\.2\.0-rc\.(\d+)", tag))]
    return f"v1.2.0-rc.{max(numbers, default=0) + 1}"


def _tool_versions() -> dict[str, str]:
    def version(command: list[str]) -> str:
        result = subprocess.run(command, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
        return (result.stdout or result.stderr).strip().splitlines()[0]

    return {
        "python": sys.version.split()[0],
        "git": version(["git", "--version"]),
        "pytest": version([sys.executable, "-m", "pytest", "--version"]),
        "deno": version([shutil.which("deno") or "deno", "--version"]),
    }


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def isolated_environment(root: Path, port: int, *, blocked_backup: bool = False) -> dict[str, str]:
    """Build an explicit write-safe environment for one disposable server."""
    database_path = (root / "runtime.sqlite3").resolve()
    backup_path = (root / ("blocked-backup-path" if blocked_backup else "backups")).resolve()
    log_dir = (root / "logs").resolve()
    support_dir = (root / "support").resolve()
    root.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    support_dir.mkdir(parents=True, exist_ok=True)
    if blocked_backup:
        backup_path.write_text("deliberately blocks directory creation", encoding="utf-8")
    else:
        backup_path.mkdir(parents=True, exist_ok=True)
    if database_path == CANONICAL_DATABASE or backup_path == CANONICAL_BACKUPS:
        raise ReleaseVerificationError("Release verification refused a canonical school-data path.")
    return {
        **os.environ,
        "PYTHONUTF8": "1",
        "SING_YIN_E2E_ISOLATED": "1",
        "SING_YIN_E2E_RUN_ID": f"E2E-{uuid4().hex[:12].upper()}",
        "SING_YIN_E2E_ACCESS_MODE": "",
        "SING_YIN_LOCAL_MAINTENANCE": "1",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL": "0",
        "SING_YIN_UNIFIED_GUEST": "0",
        "SING_YIN_APP_MODE": "official",
        "SING_YIN_DATABASE_PATH": str(database_path),
        "SING_YIN_BACKUP_DIR": str(backup_path),
        "SING_YIN_LOG_DIR": str(log_dir),
        "SING_YIN_SUPPORT_DIR": str(support_dir),
        "SING_YIN_DEPLOYMENT_MODE": "local",
        "SING_YIN_HOST": "127.0.0.1",
        "SING_YIN_PORT": str(port),
        "SING_YIN_TEST_URL": f"http://127.0.0.1:{port}",
        "SING_YIN_OPEN_BROWSER": "false",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_ENABLED": "false",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL": "",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN": "",
        "SING_YIN_YOUTUBE_ENABLED": "false",
        "SING_YIN_YOUTUBE_API_KEY": "",
        "SING_YIN_DEEPSEEK_ENABLED": "false",
        "SING_YIN_DEEPSEEK_API_KEY": "",
        "SING_YIN_STORAGE_SECRET": "release-verification-only-secret-0000000000000000",  # pragma: allowlist secret
    }


def _write_report(report: dict[str, object]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REPORT_PATH)


def _source_state(*, refresh_fingerprint: bool) -> dict[str, object]:
    """Capture the exact release inputs and Git state at one integrity boundary."""

    fingerprint, file_count = release_source_fingerprint(refresh=refresh_fingerprint)
    return {
        "sourceFingerprint": fingerprint,
        "sourceFileCount": file_count,
        "sourceCommit": _git_value("rev-parse", "HEAD"),
        "sourceTree": _git_value("rev-parse", "HEAD^{tree}"),
        "sourceDirty": bool(_git_value("status", "--porcelain", "--untracked-files=all")),
    }


def _record_post_verification_source(
    report: dict[str, object],
    initial_source: dict[str, object],
    *,
    require_stable: bool,
) -> None:
    """Bind the report to source that remained unchanged throughout every gate."""

    final_source = _source_state(refresh_fingerprint=True)
    report["postVerificationSource"] = final_source
    _write_report(report)
    if require_stable and final_source != initial_source:
        raise ReleaseSourceDriftError(
            "Release verification changed the source, Git revision, tree, or working tree; "
            "discard generated mutations and rerun from a clean immutable candidate."
        )


def _run_check(
    name: str,
    command: list[str],
    environment: dict[str, str],
    report: dict[str, object],
    *,
    initial_source: dict[str, object] | None = None,
) -> None:
    print(f"\n=== {name} ===", flush=True)
    started = time.monotonic()
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=False)
    duration_ms = round((time.monotonic() - started) * 1000)
    checks = report.setdefault("checks", [])
    assert isinstance(checks, list)
    checks.append({"name": name, "status": "pass" if result.returncode == 0 else "fail", "durationMs": duration_ms})
    _write_report(report)
    if result.returncode != 0:
        raise ReleaseVerificationError(f"{name} failed with exit code {result.returncode}.")
    if initial_source is not None:
        _record_post_verification_source(
            report,
            initial_source,
            require_stable=True,
        )


def _deno_gateway_command() -> list[str]:
    """Return the deterministic Worker contract test command or fail clearly."""
    executable = shutil.which("deno")
    if executable is None:
        raise ReleaseVerificationError(
            "Deno is required for the Cloudflare gateway release tests but is not available on PATH."
        )
    return [executable, "test", "cloudflare/roster_viewer/worker_gateway_test.js"]


def _deno_motion_command() -> list[str]:
    """Return the executable icon-story state-machine test command."""
    executable = shutil.which("deno")
    if executable is None:
        raise ReleaseVerificationError(
            "Deno is required for the motion state-machine release tests but is not available on PATH."
        )
    return [
        executable,
        "test",
        "nicegui_app/assets/motion/sing-yin-icon-story-state_test.js",
    ]


def _start_server(environment: dict[str, str], log_path: Path) -> tuple[subprocess.Popen[str], IO[str]]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    output = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-m", "nicegui_app.launcher"],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=output,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process, output


def _wait_until_ready(
    process: subprocess.Popen[str],
    base_url: str,
    log_path: Path,
    timeout: float = 30.0,
    *,
    require_write_ready: bool = True,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            endpoint = "readyz" if require_write_ready else "healthz"
            with urlopen(f"{base_url}/{endpoint}", timeout=1.0) as response:  # noqa: S310 - fixed localhost URL
                if response.status != 200:
                    time.sleep(0.25)
                    continue
                if not require_write_ready:
                    return
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") == "ready" and payload.get("writeReady") is True:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.25)
    tail = ""
    if log_path.is_file():
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-30:])
    raise ReleaseVerificationError(f"Isolated NiceGUI did not become ready.\n{tail}")


def _stop_server(process: subprocess.Popen[str], output: IO[str]) -> None:
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    finally:
        output.close()


def _assert_server_console_clean(log_path: Path) -> None:
    """Fail closed on server-side exceptions without copying console payload into the report."""
    try:
        output = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise ReleaseVerificationError("Unable to inspect the isolated NiceGUI server console.") from error
    if any(pattern.search(output) for pattern in _SERVER_FAILURE_MARKERS):
        raise ReleaseVerificationError("The isolated NiceGUI server console contains an unexpected failure marker.")


def _run_browser_phase(
    *,
    root: Path,
    blocked_backup: bool,
    scripts: tuple[str, ...],
    report: dict[str, object],
    initial_source: dict[str, object] | None = None,
) -> None:
    port = _free_loopback_port()
    environment = isolated_environment(root, port, blocked_backup=blocked_backup)
    server_log = root / "server-console.log"
    process, output = _start_server(environment, server_log)
    try:
        _wait_until_ready(
            process,
            environment["SING_YIN_TEST_URL"],
            server_log,
            require_write_ready=not blocked_backup,
        )
        for script in scripts:
            _run_check(
                Path(script).stem,
                [sys.executable, "-X", "utf8", script],
                environment,
                report,
                initial_source=initial_source,
            )
        if not blocked_backup:
            _run_check(
                "strict_deployment_readiness",
                [sys.executable, "-X", "utf8", "scripts/check_deployment_readiness.py", "--strict"],
                environment,
                report,
                initial_source=initial_source,
            )
    finally:
        _stop_server(process, output)
    _assert_server_console_clean(server_log)


def _run_unified_access_phase(
    *,
    root: Path,
    report: dict[str, object],
    initial_source: dict[str, object] | None = None,
) -> None:
    """Run the same NiceGUI routes as an isolated operator and guest."""

    admin_port = _free_loopback_port()
    guest_port = _free_loopback_port()
    admin_environment = isolated_environment(root / "admin", admin_port)
    guest_environment = isolated_environment(root / "guest", guest_port)
    for environment in (admin_environment, guest_environment):
        environment["SING_YIN_UNIFIED_GUEST"] = "1"
    guest_environment["SING_YIN_E2E_ACCESS_MODE"] = "guest"
    guest_environment["SING_YIN_ADMIN_TEST_URL"] = admin_environment["SING_YIN_TEST_URL"]
    guest_environment["SING_YIN_GUEST_TEST_URL"] = guest_environment["SING_YIN_TEST_URL"]
    guest_environment["SING_YIN_ADMIN_SUPPORT_DIR"] = admin_environment["SING_YIN_SUPPORT_DIR"]
    guest_environment["SING_YIN_UNIFIED_GUEST_EVIDENCE_DIR"] = str(
        (PROJECT_ROOT / "logs" / "unified-guest-verification").resolve()
    )

    admin_log = root / "admin" / "server-console.log"
    guest_log = root / "guest" / "server-console.log"
    admin_process, admin_output = _start_server(admin_environment, admin_log)
    guest_process, guest_output = _start_server(guest_environment, guest_log)
    try:
        _wait_until_ready(
            admin_process,
            admin_environment["SING_YIN_TEST_URL"],
            admin_log,
        )
        _wait_until_ready(
            guest_process,
            guest_environment["SING_YIN_TEST_URL"],
            guest_log,
        )
        _run_check(
            "verify_unified_guest_ui",
            [sys.executable, "-X", "utf8", "scripts/verify_unified_guest_ui.py"],
            guest_environment,
            report,
            initial_source=initial_source,
        )
    finally:
        _stop_server(guest_process, guest_output)
        _stop_server(admin_process, admin_output)
    _assert_server_console_clean(admin_log)
    _assert_server_console_clean(guest_log)


def main() -> int:
    workspace = Path(tempfile.mkdtemp(prefix="sing-yin-release-candidate-"))
    initial_source = _source_state(refresh_fingerprint=True)
    planned_release_tag = _planned_release_tag()
    report: dict[str, object] = {
        "schemaVersion": RELEASE_REPORT_SCHEMA_VERSION,
        "project": PROJECT_ID,
        "policyVersion": POLICY_VERSION,
        **initial_source,
        "plannedReleaseTag": planned_release_tag,
        "immutableReleaseReference": f"refs/tags/{planned_release_tag}",
        "requiredCheckIdentities": list(REQUIRED_CHECK_IDENTITIES),
        "toolVersions": _tool_versions(),
        "status": "running",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "humanAcceptanceRequired": True,
        "humanAcceptanceGuide": "docs/ACCEPTANCE_EVIDENCE.md",
        "checks": [],
    }
    _write_report(report)
    base_environment = {**os.environ, "PYTHONUTF8": "1"}
    succeeded = False
    try:
        if initial_source["sourceDirty"] is not False:
            raise ReleaseVerificationError(
                "Release verification requires a clean source tree before any gate runs."
            )
        _run_check(
            "repository_hygiene",
            [sys.executable, "-X", "utf8", "scripts/check_repository_hygiene.py"],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "security_gates",
            [sys.executable, "-X", "utf8", "scripts/run_security_checks.py"],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "motion_state_machine_tests",
            _deno_motion_command(),
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "cloudflare_gateway_tests",
            _deno_gateway_command(),
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "automated_test_suite",
            [
                sys.executable,
                "-X",
                "utf8",
                "-m",
                "pytest",
                "-q",
                f"--deselect={_WORKER_RUNTIME_TEST}",
            ],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "python_compile",
            [sys.executable, "-X", "utf8", "-m", "compileall", "-q", "nicegui_app", "packages", "tests", "scripts"],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "dependency_integrity",
            [sys.executable, "-m", "pip", "check"],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_check(
            "rc31_theme_control_browser",
            [sys.executable, "-X", "utf8", "scripts/verify_rc31_theme_controls.py"],
            base_environment,
            report,
            initial_source=initial_source,
        )
        _run_browser_phase(
            root=workspace / "normal",
            blocked_backup=False,
            scripts=(
                "scripts/verify_nicegui_ui.py",
                "scripts/verify_runtime_performance.py",
                "scripts/verify_nicegui_write_pipeline.py",
                "scripts/verify_nicegui_mobile.py",
            ),
            report=report,
            initial_source=initial_source,
        )
        _run_unified_access_phase(
            root=workspace / "unified-access",
            report=report,
            initial_source=initial_source,
        )
        _run_browser_phase(
            root=workspace / "partial-backup",
            blocked_backup=True,
            scripts=("scripts/verify_nicegui_partial_backup.py",),
            report=report,
            initial_source=initial_source,
        )
        _record_post_verification_source(
            report,
            initial_source,
            require_stable=True,
        )
        report["status"] = "pass"
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        _write_report(report)
        succeeded = True
        print(f"\nRelease-candidate verification passed. Report: {REPORT_PATH}", flush=True)
        return 0
    except Exception as error:  # noqa: BLE001 - CLI boundary must leave a failed evidence report
        if not isinstance(error, ReleaseSourceDriftError):
            try:
                _record_post_verification_source(
                    report,
                    initial_source,
                    require_stable=False,
                )
            except Exception:  # noqa: BLE001 - preserve the original gate failure
                pass
        report["status"] = "fail"
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        report["failure"] = str(error)
        _write_report(report)
        print(f"\nRELEASE VERIFICATION FAILED: {error}", file=sys.stderr, flush=True)
        print(f"Isolated evidence retained at: {workspace}", file=sys.stderr, flush=True)
        return 1
    finally:
        if succeeded:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
