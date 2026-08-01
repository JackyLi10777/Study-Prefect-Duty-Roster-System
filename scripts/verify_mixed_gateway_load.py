"""Exercise mixed Admin and Guest traffic through local workerd and NiceGUI.

This verifier is deliberately local-only. It runs the real Worker module in
Miniflare's local workerd runtime, proxies it through a fail-closed loopback
service binding, and starts one disposable NiceGUI origin backed by fictional
data. It never accepts a caller-supplied URL, canonical database, Cloudflare
account binding, deployment command, or production secret.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import sqlite3
import ssl
# Child commands use fixed local executables, validated argv, and no shell.
import subprocess  # nosec B404
import sys
import tempfile
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from nicegui_app.config import PREFECT_SEED_PATH, PROJECT_ROOT
from nicegui_app.services.guest_workspace import DEFAULT_MAX_SESSIONS
from nicegui_app.services.roster_workflow import RosterWorkflow
from scripts.verify_unified_guest_ui import logical_database_fingerprint


WORKER_ROOT = PROJECT_ROOT / "cloudflare" / "roster_viewer"
WORKER_ENTRY = WORKER_ROOT / "worker.js"
WORKER_RUNTIME_ENTRY = WORKER_ROOT / "scripts" / "run_mixed_gateway_workerd.mjs"
MINIFLARE_PACKAGE = WORKER_ROOT / "node_modules" / "miniflare" / "package.json"
ORIGIN_PROXY_ENTRY = PROJECT_ROOT / "scripts" / "fixtures" / "cloudflare_loopback_origin_proxy.js"
CANONICAL_DATABASE = (PROJECT_ROOT / "data" / "runtime" / "sing-yin-roster.sqlite3").resolve()
CANONICAL_BACKUPS = (PROJECT_ROOT / "data" / "backups").resolve()
REPORT_PATH = PROJECT_ROOT / "logs" / "mixed-gateway-load" / "verification.json"

ADMIN_EMAIL = "mixed-load-admin@example.invalid"
ADMIN_COOKIE_NAME = "__Host-SingYinAdminSession"
GUEST_COOKIE_NAME = "__Host-SingYinGuestSession"
AUTH_EPOCH = 1
ORIGIN_PRINCIPAL_KID = "mixed-load-origin-v1"
DEFAULT_GUESTS = 10
DEFAULT_WAVES = 2
GUEST_STARTS_PER_MINUTE = 20
MAX_RESIDUAL_GROWTH_BYTES = 32 * 1024 * 1024
MAX_BASELINE_GROWTH_BYTES = 128 * 1024 * 1024
_SERVER_FAILURE_MARKERS = (
    re.compile(r"Traceback \(most recent call last\)"),
    re.compile(r"database is locked", re.IGNORECASE),
    re.compile(r"500 Internal Server Error", re.IGNORECASE),
    re.compile(r"unhandled(?:rejection| exception)", re.IGNORECASE),
)
_WORKER_RUNTIME_FAILURE_MARKERS = (
    re.compile(r"\[ERROR\]"),
    re.compile(r"Uncaught "),
    re.compile(r"workerd.*fatal", re.IGNORECASE),
)
_PROCESS_ENVIRONMENT_ALLOWLIST = frozenset(
    {
        "APPDATA",
        "COMSPEC",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LANG",
        "LC_ALL",
        "LOCALAPPDATA",
        "NUMBER_OF_PROCESSORS",
        "PATH",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)


class MixedGatewayLoadError(RuntimeError):
    """The isolated mixed-load acceptance boundary failed."""


def _base_process_environment() -> dict[str, str]:
    """Retain only OS process essentials; never inherit account credentials."""

    return {
        name: value
        for name, value in os.environ.items()
        if name.upper() in _PROCESS_ENVIRONMENT_ALLOWLIST
    }


def _required_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise MixedGatewayLoadError(f"Required local executable {name!r} is unavailable.")
    return str(Path(resolved).resolve())


@dataclass
class BrowserSession:
    role: str
    context: Any
    page: Any
    websocket_urls: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    server_errors: list[str] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_commit() -> str:
    # Executable and arguments are fixed by this verifier.
    result = subprocess.run(
        [_required_executable("git"), "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603
    return result.stdout.strip()


def _source_dirty() -> bool:
    # Executable and arguments are fixed by this verifier.
    result = subprocess.run(
        [_required_executable("git"), "status", "--porcelain", "--untracked-files=all"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )  # nosec B603
    return bool(result.stdout.strip())


def _working_set_bytes(process_id: int) -> int:
    if os.name != "nt":
        status_path = Path(f"/proc/{process_id}/status")
        if not status_path.is_file():
            raise MixedGatewayLoadError("Unable to measure the isolated origin working set.")
        match = re.search(r"^VmRSS:\s+(\d+)\s+kB$", status_path.read_text(), re.MULTILINE)
        if not match:
            raise MixedGatewayLoadError("Unable to parse the isolated origin working set.")
        return int(match.group(1)) * 1024
    # process_id is an integer returned by Popen, not caller input.
    result = subprocess.run(
        [
            _required_executable("powershell.exe"),
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-Process -Id {process_id} -ErrorAction Stop).WorkingSet64",
        ],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603
    try:
        value = int(result.stdout.strip())
    except ValueError as error:
        raise MixedGatewayLoadError("Unable to measure the isolated origin working set.") from error
    if result.returncode != 0 or value <= 0:
        raise MixedGatewayLoadError("Unable to measure the isolated origin working set.")
    return value


def _percentile_95(values: list[float]) -> float:
    if not values:
        raise MixedGatewayLoadError("No latency samples were recorded.")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))
    return round(ordered[index], 2)


def _generate_local_certificate(root: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    certificate_path = root / "localhost-ca.pem"
    key_path = root / "localhost-key.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return certificate_path, key_path


def _isolated_origin_environment(
    root: Path,
    *,
    port: int,
    gateway_url: str,
    certificate_path: Path,
    admin_token: str,
    origin_principal_secret: str,
) -> dict[str, str]:
    database_path = (root / "runtime.sqlite3").resolve()
    backup_dir = (root / "backups").resolve()
    log_dir = (root / "logs").resolve()
    support_dir = (root / "support").resolve()
    for directory in (backup_dir, log_dir, support_dir):
        directory.mkdir(parents=True, exist_ok=True)
    if database_path == CANONICAL_DATABASE or backup_dir == CANONICAL_BACKUPS:
        raise MixedGatewayLoadError("Mixed-load verification refused a canonical data path.")
    return {
        **_base_process_environment(),
        "PYTHONUTF8": "1",
        "SSL_CERT_FILE": str(certificate_path),
        "SING_YIN_E2E_ISOLATED": "1",
        "SING_YIN_E2E_RUN_ID": f"E2E-{secrets.token_hex(6).upper()}",
        "SING_YIN_E2E_ACCESS_MODE": "",
        "SING_YIN_LOCAL_MAINTENANCE": "0",
        "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL": "1",
        "SING_YIN_UNIFIED_GUEST": "1",
        "SING_YIN_APP_MODE": "official",
        "SING_YIN_DATABASE_PATH": str(database_path),
        "SING_YIN_BACKUP_DIR": str(backup_dir),
        "SING_YIN_LOG_DIR": str(log_dir),
        "SING_YIN_SUPPORT_DIR": str(support_dir),
        "SING_YIN_DEPLOYMENT_MODE": "local",
        "SING_YIN_HOST": "127.0.0.1",
        "SING_YIN_PORT": str(port),
        "SING_YIN_TEST_URL": f"http://127.0.0.1:{port}",
        "SING_YIN_OPEN_BROWSER": "false",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_ENABLED": "true",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL": gateway_url,
        "SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN": admin_token,
        "SING_YIN_PUBLIC_ROSTER_VIEWER_TIMEOUT_SECONDS": "10",
        "SING_YIN_PUBLIC_ROSTER_VIEWER_VISIBILITY_TIMEOUT_SECONDS": "15",
        "SING_YIN_YOUTUBE_ENABLED": "false",
        "SING_YIN_YOUTUBE_API_KEY": "",
        "SING_YIN_DEEPSEEK_ENABLED": "false",
        "SING_YIN_DEEPSEEK_API_KEY": "",
        "SING_YIN_STORAGE_SECRET": secrets.token_urlsafe(36),
        "ORIGIN_PRINCIPAL_SECRET": origin_principal_secret,
        "ORIGIN_PRINCIPAL_KID": ORIGIN_PRINCIPAL_KID,
        "AUTH_EPOCH": str(AUTH_EPOCH),
    }


def _seed_disposable_database(environment: dict[str, str]) -> tuple[Path, Path]:
    database_path = Path(environment["SING_YIN_DATABASE_PATH"]).resolve()
    backup_dir = Path(environment["SING_YIN_BACKUP_DIR"]).resolve()
    workflow = RosterWorkflow(
        database_path=database_path,
        backup_dir=backup_dir,
        seed_path=PREFECT_SEED_PATH,
    )
    workflow.bootstrap()
    if len(workflow.prefects()) < 20:
        raise MixedGatewayLoadError("The fictional load fixture did not initialize completely.")
    return database_path, backup_dir


def _start_process(command: list[str], *, environment: dict[str, str], log_path: Path) -> tuple[subprocess.Popen[str], Any]:
    if not command or not Path(command[0]).is_absolute():
        raise MixedGatewayLoadError("Child process executable must be an absolute local path.")
    if any("\x00" in argument or "\r" in argument or "\n" in argument for argument in command):
        raise MixedGatewayLoadError("Child process arguments contain a forbidden control character.")
    output = log_path.open("w", encoding="utf-8")
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        # argv is validated, the executable is absolute, and shell remains disabled.
        process = subprocess.Popen(  # nosec B603
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creation_flags,
        )
    except Exception:
        output.close()
        raise
    return process, output


def _stop_process(process: subprocess.Popen[str], output: Any) -> None:
    try:
        if process.poll() is None:
            if os.name == "nt":
                taskkill = shutil.which("taskkill.exe")
                if taskkill is None:
                    process.terminate()
                else:
                    # taskkill is absolute and the PID comes directly from Popen.
                    subprocess.run(  # nosec B603
                        [str(Path(taskkill).resolve()), "/PID", str(process.pid), "/T", "/F"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
            else:
                process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                if os.name != "nt":
                    process.kill()
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=5)
    finally:
        output.close()


def _validate_loopback_url(url: str, *, tls: bool) -> None:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as error:
        raise MixedGatewayLoadError("Local verification URL is malformed.") from error
    expected_scheme = "https" if tls else "http"
    if (
        parsed.scheme != expected_scheme
        or parsed.hostname not in {"localhost", "127.0.0.1"}
        or port is None
        or port < 1024
        or port > 65535
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    ):
        raise MixedGatewayLoadError("Verification requests are restricted to an explicit loopback origin.")


def _json_request(url: str, *, certificate_path: Path | None = None, method: str = "GET") -> tuple[int, dict[str, Any]]:
    _validate_loopback_url(url, tls=certificate_path is not None)
    context = ssl.create_default_context(cafile=str(certificate_path)) if certificate_path else None
    request = Request(url, method=method, headers={"Accept": "application/json"})
    try:
        # _validate_loopback_url rejects non-local schemes and destinations.
        with urlopen(request, timeout=2.0, context=context) as response:  # nosec B310
            raw = response.read(512 * 1024)
            return response.status, json.loads(raw.decode("utf-8"))
    except HTTPError as error:
        raw = error.read(512 * 1024)
        with suppress(json.JSONDecodeError, UnicodeDecodeError):
            return error.code, json.loads(raw.decode("utf-8"))
        return error.code, {}


def _wait_for_json(
    process: subprocess.Popen[str],
    url: str,
    *,
    certificate_path: Path | None = None,
    expected_status: str,
    timeout_seconds: float = 45.0,
    log_path: Path,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline and process.poll() is None:
        try:
            status, payload = _json_request(url, certificate_path=certificate_path)
            if status == 200 and payload.get("status") == expected_status:
                return payload
        except (URLError, TimeoutError, ssl.SSLError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    tail = ""
    if log_path.is_file():
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:])
    raise MixedGatewayLoadError(f"Local service did not become ready at {url}.\n{tail}")


def _admin_session_token(secret: str, *, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    payload = {
        "v": 2,
        "email": ADMIN_EMAIL,
        "iat": issued_at,
        "exp": issued_at + 60 * 60,
        "epoch": AUTH_EPOCH,
        "nonce": _base64url(secrets.token_bytes(16)),
    }
    payload_segment = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_segment}.{_base64url(signature)}"


async def _wait_for_app(session: BrowserSession, gateway_url: str, route: str) -> None:
    started = time.perf_counter()
    response = await session.page.goto(
        f"{gateway_url}{route}",
        wait_until="domcontentloaded",
        timeout=30_000,
    )
    if response is None or response.status != 200:
        raise MixedGatewayLoadError(f"{session.role} route {route} did not return HTTP 200.")
    await session.page.wait_for_selector("main#main-content", timeout=20_000)
    await session.page.wait_for_selector(".sy-header-title", timeout=15_000)
    await session.page.wait_for_function(
        "() => sessionStorage.getItem('__nicegui_tab_closed') !== 'true'",
        timeout=15_000,
    )
    await session.page.wait_for_timeout(180)
    mode = await session.page.locator("main#main-content").get_attribute("data-sy-mode")
    if mode != session.role:
        raise MixedGatewayLoadError(
            f"Expected {session.role} through the gateway but NiceGUI rendered {mode or 'no mode'}."
        )
    session.latencies_ms.append((time.perf_counter() - started) * 1000)


def _install_page_observers(session: BrowserSession) -> None:
    session.page.on(
        "websocket",
        lambda websocket: session.websocket_urls.append(websocket.url),
    )
    session.page.on(
        "console",
        lambda message: session.console_errors.append(message.text)
        if message.type == "error"
        else None,
    )
    session.page.on("pageerror", lambda error: session.page_errors.append(str(error)))
    session.page.on(
        "response",
        lambda response: session.server_errors.append(f"{response.status} {response.url}")
        if response.status >= 500
        else None,
    )


async def _open_admin_session(browser: Any, gateway_url: str, token: str) -> BrowserSession:
    context = await browser.new_context(ignore_https_errors=True, accept_downloads=True)
    await context.add_cookies(
        [
            {
                "name": ADMIN_COOKIE_NAME,
                "value": token,
                "url": gateway_url,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
    )
    page = await context.new_page()
    session = BrowserSession("admin", context, page)
    _install_page_observers(session)
    await _wait_for_app(session, gateway_url, "/")
    return session


async def _open_guest_session(browser: Any, gateway_url: str) -> BrowserSession:
    context = await browser.new_context(ignore_https_errors=True, accept_downloads=True)
    response = await context.request.post(
        f"{gateway_url}/auth/guest/start",
        headers={
            "Accept": "application/json",
            "Origin": gateway_url,
            "Sec-Fetch-Site": "same-origin",
        },
    )
    if response.status != 201:
        raise MixedGatewayLoadError(f"Guest session start returned HTTP {response.status}.")
    payload = await response.json()
    if payload.get("authenticated") is not True or payload.get("mode") != "guest":
        raise MixedGatewayLoadError("Guest session start returned the wrong gateway mode.")
    page = await context.new_page()
    session = BrowserSession("guest", context, page)
    _install_page_observers(session)
    await _wait_for_app(session, gateway_url, "/")
    return session


async def _close_sessions(sessions: list[BrowserSession]) -> None:
    await asyncio.gather(*(session.context.close() for session in sessions), return_exceptions=True)


async def _download_first_roster_pdf(page: Any) -> tuple[int, str]:
    await page.get_by_role(
        "button",
        name=re.compile(r"下載列印版 PDF|Download print-ready PDF"),
    ).click()
    await page.get_by_role(
        "button",
        name=re.compile(r"準備中文週表 PDF|Prepare Chinese schedule PDF"),
    ).click()
    ready = page.get_by_test_id("pdf-delivery-ready")
    await ready.wait_for(state="visible", timeout=30_000)
    async with page.expect_download(timeout=30_000) as pending:
        await ready.get_by_test_id("download-prepared-pdf").click()
    download = await pending.value
    path = await download.path()
    if path is None:
        raise MixedGatewayLoadError("The roster PDF download did not create a local artifact.")
    artifact = Path(path)
    size = artifact.stat().st_size
    digest = _sha256(artifact)
    await page.get_by_role("button", name=re.compile(r"取消|Cancel")).last.click()
    if size < 1_000:
        raise MixedGatewayLoadError("The roster PDF download is unexpectedly small.")
    return size, digest


async def _guest_isolation_workflow(
    writer: BrowserSession,
    observer: BrowserSession,
    gateway_url: str,
) -> dict[str, Any]:
    await _wait_for_app(writer, gateway_url, "/rosters")
    started = time.perf_counter()
    await writer.page.get_by_role(
        "button",
        name=re.compile(r"生成並儲存草稿|Generate and save draft"),
    ).click()
    await writer.page.wait_for_url(re.compile(r".*/rosters/[0-9]+$"), timeout=30_000)
    await writer.page.wait_for_selector("main#main-content", timeout=20_000)
    roster_id = int(writer.page.url.rstrip("/").rsplit("/", 1)[-1])
    await writer.page.get_by_role(
        "button",
        name=re.compile(r"發布週表|Publish roster"),
    ).click()
    await writer.page.get_by_role(
        "button",
        name=re.compile(r"確認發布並入帳|Publish and post to ledger"),
    ).click()
    await writer.page.get_by_role(
        "button",
        name=re.compile(r"處理請假調整|Handle leave adjustment"),
    ).first.wait_for(state="visible", timeout=30_000)
    operation_ms = (time.perf_counter() - started) * 1000
    pdf_size, pdf_digest = await _download_first_roster_pdf(writer.page)

    await _wait_for_app(observer, gateway_url, "/")
    observer_history = await observer.page.locator(
        "[data-testid='dashboard-history'] .sy-dashboard-history-item"
    ).count()
    if observer_history != 0:
        raise MixedGatewayLoadError("A second Guest session observed another Guest's roster history.")
    await _wait_for_app(observer, gateway_url, "/access-control")
    await observer.page.get_by_test_id("guest-restricted-state").first.wait_for(
        state="visible", timeout=15_000
    )
    if (
        await observer.page.get_by_test_id("operator-access-card").count()
        or await observer.page.get_by_test_id("viewer-access-card").count()
    ):
        raise MixedGatewayLoadError("Guest access-control route exposed administrator delivery controls.")
    return {
        "rosterId": roster_id,
        "operationMs": round(operation_ms, 2),
        "observerHistoryCount": observer_history,
        "download": {"bytes": pdf_size, "sha256": pdf_digest},
        "externalDeliveryDenied": True,
    }


async def _route_cycle(session: BrowserSession, gateway_url: str, routes: tuple[str, ...]) -> list[float]:
    before = len(session.latencies_ms)
    for route in routes:
        await _wait_for_app(session, gateway_url, route)
    return session.latencies_ms[before:]


async def _admin_write_workflow(session: BrowserSession, gateway_url: str) -> dict[str, Any]:
    await _wait_for_app(session, gateway_url, "/rosters")
    started = time.perf_counter()
    await session.page.get_by_role(
        "button",
        name=re.compile(r"生成並儲存草稿|Generate and save draft"),
    ).click()
    await session.page.wait_for_url(re.compile(r".*/rosters/[0-9]+$"), timeout=30_000)
    await session.page.wait_for_selector("main#main-content", timeout=20_000)
    roster_id = int(session.page.url.rstrip("/").rsplit("/", 1)[-1])
    await session.page.get_by_role(
        "button",
        name=re.compile(r"發布週表|Publish roster"),
    ).click()
    await session.page.get_by_role(
        "button",
        name=re.compile(r"確認發布並入帳|Publish and post to ledger"),
    ).click()
    await session.page.get_by_role(
        "button",
        name=re.compile(r"處理請假調整|Handle leave adjustment"),
    ).first.wait_for(state="visible", timeout=30_000)
    write_ms = (time.perf_counter() - started) * 1000
    pdf_size, pdf_digest = await _download_first_roster_pdf(session.page)

    await _wait_for_app(session, gateway_url, "/access-control")
    await session.page.get_by_test_id("console-create-public-share").click()
    await session.page.get_by_test_id("public-share-confirm-dialog").wait_for(state="visible", timeout=10_000)
    share_started = time.perf_counter()
    await session.page.get_by_test_id("confirm-create-public-share").click()
    receipt = session.page.get_by_test_id("public-share-receipt-dialog")
    await receipt.wait_for(state="visible", timeout=30_000)
    share_url = await session.page.get_by_test_id("public-share-url").input_value()
    share_ms = (time.perf_counter() - share_started) * 1000
    parsed_share = urlparse(share_url)
    share_id = parsed_share.fragment.split(".", 1)[0]
    if parsed_share.scheme != "https" or parsed_share.netloc != urlparse(gateway_url).netloc or not share_id:
        raise MixedGatewayLoadError("The local Worker returned an invalid public-share receipt.")
    return {
        "rosterId": roster_id,
        "writeMs": round(write_ms, 2),
        "download": {"bytes": pdf_size, "sha256": pdf_digest},
        "shareMs": round(share_ms, 2),
        "shareId": share_id,
        "shareUrl": share_url,
    }


async def _verify_public_share(browser: Any, share_url: str) -> None:
    context = await browser.new_context(ignore_https_errors=True)
    page = await context.new_page()
    try:
        await page.goto(share_url, wait_until="domcontentloaded", timeout=30_000)
        await page.locator("#rosterState").wait_for(state="visible", timeout=30_000)
        if await page.locator("#guestState").is_visible():
            raise MixedGatewayLoadError("The encrypted viewer did not render the shared roster.")
    finally:
        await context.close()


async def _browser_wave(
    browser: Any,
    *,
    gateway_url: str,
    guests: int,
) -> list[BrowserSession]:
    sessions = await asyncio.gather(
        *(_open_guest_session(browser, gateway_url) for _ in range(guests))
    )
    cookies = []
    for session in sessions:
        matching = [cookie for cookie in await session.context.cookies() if cookie["name"] == GUEST_COOKIE_NAME]
        if len(matching) != 1:
            raise MixedGatewayLoadError("A Guest browser context did not retain exactly one gateway session.")
        cookies.append(matching[0]["value"])
    if len(set(cookies)) != len(cookies):
        raise MixedGatewayLoadError("Independent Guest browser contexts received a duplicate session token.")
    return list(sessions)


def _wait_for_guest_sessions(origin_url: str, expected: int, timeout_seconds: float = 35.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            status, latest = _json_request(f"{origin_url}/readyz")
            if status == 200 and latest.get("guestSessions") == expected:
                return latest
        except (URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    raise MixedGatewayLoadError(
        f"Guest session cleanup did not converge to {expected}; last count={latest.get('guestSessions')}."
    )


def _assert_browser_clean(sessions: list[BrowserSession]) -> None:
    missing_websockets = [index for index, session in enumerate(sessions) if not session.websocket_urls]
    server_errors = [error for session in sessions for error in session.server_errors]
    page_errors = [error for session in sessions for error in session.page_errors]
    console_errors = [error for session in sessions for error in session.console_errors]
    if missing_websockets:
        raise MixedGatewayLoadError(f"Browser sessions never opened a Worker-proxied WebSocket: {missing_websockets}.")
    if server_errors:
        raise MixedGatewayLoadError(f"Browser traffic observed server errors: {server_errors[:5]}.")
    if page_errors:
        raise MixedGatewayLoadError(f"Browser pages raised unhandled errors: {page_errors[:5]}.")
    if console_errors:
        raise MixedGatewayLoadError(f"Browser consoles raised errors: {console_errors[:5]}.")


def _assert_log_clean(path: Path, markers: tuple[re.Pattern[str], ...], label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if any(marker.search(text) for marker in markers):
        raise MixedGatewayLoadError(f"The isolated {label} log contains a failure marker.")


def _outbox_summary(database_path: Path) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT status, attempts FROM external_share_outbox ORDER BY id"
        ).fetchall()
    if len(rows) != 1 or rows[0][0] != "delivered" or int(rows[0][1]) < 1:
        raise MixedGatewayLoadError("The external-share outbox did not reach one delivered terminal state.")
    return {"records": len(rows), "delivered": 1, "attempts": int(rows[0][1])}


async def _run_browser_load(
    *,
    gateway_url: str,
    origin_url: str,
    admin_token: str,
    origin_process: subprocess.Popen[str],
    database_path: Path,
    backup_dir: Path,
    guests: int,
    waves: int,
    smoke_only: bool,
) -> dict[str, Any]:
    from playwright.async_api import async_playwright

    all_sessions: list[BrowserSession] = []
    residual_samples: list[int] = []
    navigation_samples: list[float] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        admin_sessions: list[BrowserSession] = []
        try:
            admin_sessions = list(
                await asyncio.gather(
                    _open_admin_session(browser, gateway_url, admin_token),
                    _open_admin_session(browser, gateway_url, admin_token),
                )
            )
            all_sessions.extend(admin_sessions)
            baseline_working_set = _working_set_bytes(origin_process.pid)
            fingerprint_before_guest, _ = logical_database_fingerprint(database_path)
            backups_before = len(list(backup_dir.glob("*.sqlite3")))
            guest_evidence: dict[str, Any] = {}
            admin_evidence: dict[str, Any] = {}

            for wave_index in range(waves):
                guest_sessions = await _browser_wave(browser, gateway_url=gateway_url, guests=guests)
                all_sessions.extend(guest_sessions)
                _wait_for_guest_sessions(origin_url, guests)
                if wave_index == 0 and not smoke_only:
                    guest_evidence = await _guest_isolation_workflow(
                        guest_sessions[0], guest_sessions[1], gateway_url
                    )
                    fingerprint_after_guest, _ = logical_database_fingerprint(database_path)
                    if fingerprint_after_guest != fingerprint_before_guest:
                        raise MixedGatewayLoadError("Guest activity changed the disposable official SQLite database.")

                    read_tasks = [
                        _route_cycle(admin_sessions[1], gateway_url, ("/prefects", "/audit", "/settings"))
                    ]
                    read_tasks.extend(
                        _route_cycle(
                            session,
                            gateway_url,
                            (("/prefects", "/audit") if index % 2 == 0 else ("/settings", "/support")),
                        )
                        for index, session in enumerate(guest_sessions[2:])
                    )
                    mixed_results = await asyncio.gather(
                        _admin_write_workflow(admin_sessions[0], gateway_url),
                        *read_tasks,
                    )
                    admin_evidence = dict(mixed_results[0])
                    await _verify_public_share(browser, str(admin_evidence.pop("shareUrl")))
                    admin_evidence["viewerDecrypted"] = True
                else:
                    await asyncio.gather(
                        *(
                            _route_cycle(
                                session,
                                gateway_url,
                                (("/prefects", "/audit") if index % 2 == 0 else ("/settings", "/support")),
                            )
                            for index, session in enumerate(guest_sessions)
                        )
                    )
                _assert_browser_clean(guest_sessions)
                await _close_sessions(guest_sessions)
                _wait_for_guest_sessions(origin_url, 0)
                await asyncio.sleep(0.5)
                residual_samples.append(_working_set_bytes(origin_process.pid))

            _assert_browser_clean(admin_sessions)
            navigation_samples.extend(
                latency
                for session in all_sessions
                for latency in session.latencies_ms
            )
            if len(residual_samples) >= 2 and residual_samples[-1] > residual_samples[-2] + MAX_RESIDUAL_GROWTH_BYTES:
                raise MixedGatewayLoadError("Origin working-set growth continued after the second Guest cleanup wave.")
            if residual_samples and residual_samples[-1] > baseline_working_set + MAX_BASELINE_GROWTH_BYTES:
                raise MixedGatewayLoadError("Origin working set did not return within the bounded cleanup budget.")
            backups_after = len(list(backup_dir.glob("*.sqlite3")))
            if not smoke_only and backups_after <= backups_before:
                raise MixedGatewayLoadError("The serialized Admin write did not create recovery evidence.")
            return {
                "guest": guest_evidence,
                "admin": admin_evidence,
                "capacity": {
                    "simultaneousGuestSessions": guests,
                    "configuredGuestSessionLimit": DEFAULT_MAX_SESSIONS,
                    "waves": waves,
                    "adminSessions": len(admin_sessions),
                },
                "latency": {
                    "samples": len(navigation_samples),
                    "navigationP95Ms": _percentile_95(navigation_samples),
                    "navigationMaxMs": round(max(navigation_samples), 2),
                },
                "memory": {
                    "baselineBytes": baseline_working_set,
                    "postCleanupBytes": residual_samples,
                    "maxResidualWaveGrowthBytes": MAX_RESIDUAL_GROWTH_BYTES,
                    "maxBaselineGrowthBytes": MAX_BASELINE_GROWTH_BYTES,
                },
                "backups": {"before": backups_before, "after": backups_after},
                "webSocketsObserved": sum(bool(session.websocket_urls) for session in all_sessions),
            }
        finally:
            await _close_sessions(admin_sessions)
            await browser.close()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guests", type=int, default=DEFAULT_GUESTS)
    parser.add_argument("--waves", type=int, default=DEFAULT_WAVES)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--retain", action="store_true")
    arguments = parser.parse_args()
    if not 2 <= arguments.guests <= min(DEFAULT_MAX_SESSIONS, GUEST_STARTS_PER_MINUTE):
        parser.error(
            "--guests must be between 2 and the edge guest-start budget "
            f"({GUEST_STARTS_PER_MINUTE})"
        )
    if not 1 <= arguments.waves <= 3:
        parser.error("--waves must be between 1 and 3")
    if arguments.guests * arguments.waves > GUEST_STARTS_PER_MINUTE:
        parser.error(
            "--guests multiplied by --waves must stay within the production "
            f"guest-start budget ({GUEST_STARTS_PER_MINUTE} per minute)"
        )
    return arguments


def main() -> int:
    arguments = _arguments()
    workspace = Path(tempfile.mkdtemp(prefix="sing-yin-mixed-gateway-load-"))
    origin_root = workspace / "origin"
    worker_root = workspace / "worker"
    origin_log = origin_root / "origin-console.log"
    worker_log = worker_root / "workerd-console.log"
    origin_process: subprocess.Popen[str] | None = None
    origin_output: Any | None = None
    worker_process: subprocess.Popen[str] | None = None
    worker_output: Any | None = None
    success = False
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "kind": "local-workerd-mixed-gateway-load",
        "status": "running",
        "sourceCommit": "unavailable",
        "sourceDirty": True,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "productionTouched": False,
            "data": "fictional-disposable",
            "workerRuntime": "local-workerd-via-miniflare",
            "cloudflareNetwork": False,
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        required_files = (WORKER_ENTRY, WORKER_RUNTIME_ENTRY, MINIFLARE_PACKAGE, ORIGIN_PROXY_ENTRY)
        if not all(path.is_file() for path in required_files):
            raise MixedGatewayLoadError(
                "Local Worker dependencies are missing. "
                "Run pnpm install --frozen-lockfile in cloudflare/roster_viewer."
            )
        report["sourceCommit"] = _source_commit()
        report["sourceDirty"] = _source_dirty()
        origin_root.mkdir(parents=True)
        worker_root.mkdir(parents=True)
        origin_port = _free_loopback_port()
        gateway_port = _free_loopback_port()
        inspector_port = _free_loopback_port()
        gateway_url = f"https://localhost:{gateway_port}"
        origin_url = f"http://127.0.0.1:{origin_port}"
        certificate_path, key_path = _generate_local_certificate(worker_root)
        admin_token = secrets.token_urlsafe(42)
        admin_session_secret = secrets.token_urlsafe(42)
        guest_session_secret = secrets.token_urlsafe(42)
        origin_principal_secret = secrets.token_urlsafe(42)
        environment = _isolated_origin_environment(
            origin_root,
            port=origin_port,
            gateway_url=gateway_url,
            certificate_path=certificate_path,
            admin_token=admin_token,
            origin_principal_secret=origin_principal_secret,
        )
        database_path, backup_dir = _seed_disposable_database(environment)
        before_fingerprint, before_counts = logical_database_fingerprint(database_path)
        origin_process, origin_output = _start_process(
            [str(Path(sys.executable).resolve()), "-X", "utf8", "-m", "nicegui_app.main"],
            environment=environment,
            log_path=origin_log,
        )
        _wait_for_json(
            origin_process,
            f"{origin_url}/readyz",
            expected_status="ready",
            log_path=origin_log,
        )
        worker_command = [
            _required_executable("node"),
            str(WORKER_RUNTIME_ENTRY),
            "--port",
            str(gateway_port),
            "--inspector-port",
            str(inspector_port),
            "--origin-port",
            str(origin_port),
            "--https-key",
            str(key_path),
            "--https-cert",
            str(certificate_path),
            "--persist",
            str(worker_root / "state"),
        ]
        worker_environment = {
            **_base_process_environment(),
            "NO_COLOR": "1",
            "SING_YIN_LOAD_ADMIN_BEARER_TOKEN": admin_token,
            "SING_YIN_LOAD_ADMIN_SESSION_SECRET": admin_session_secret,
            "SING_YIN_LOAD_GUEST_SESSION_SECRET": guest_session_secret,
            "SING_YIN_LOAD_ORIGIN_PRINCIPAL_SECRET": origin_principal_secret,
        }
        worker_process, worker_output = _start_process(
            worker_command,
            environment=worker_environment,
            log_path=worker_log,
        )
        gateway_health = _wait_for_json(
            worker_process,
            f"{gateway_url}/healthz",
            certificate_path=certificate_path,
            expected_status="ok",
            log_path=worker_log,
            timeout_seconds=60.0,
        )
        session_token = _admin_session_token(admin_session_secret)
        browser_evidence = asyncio.run(
            _run_browser_load(
                gateway_url=gateway_url,
                origin_url=origin_url,
                admin_token=session_token,
                origin_process=origin_process,
                database_path=database_path,
                backup_dir=backup_dir,
                guests=arguments.guests,
                waves=arguments.waves,
                smoke_only=arguments.smoke_only,
            )
        )
        after_fingerprint, after_counts = logical_database_fingerprint(database_path)
        workflow = RosterWorkflow(database_path=database_path, backup_dir=backup_dir, seed_path=None)
        workflow.bootstrap()
        fairness = workflow.reconcile_fairness()
        if not fairness.balanced:
            raise MixedGatewayLoadError("The official fairness ledger did not reconcile after mixed load.")
        if not arguments.smoke_only and after_fingerprint == before_fingerprint:
            raise MixedGatewayLoadError("The Admin workflow did not durably change the disposable database.")
        outbox = {} if arguments.smoke_only else _outbox_summary(database_path)
        _assert_log_clean(origin_log, _SERVER_FAILURE_MARKERS, "origin")
        _assert_log_clean(worker_log, _WORKER_RUNTIME_FAILURE_MARKERS, "workerd")
        report.update(
            {
                "status": "smoke" if arguments.smoke_only else "pass",
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "gateway": {
                    "status": gateway_health.get("status"),
                    "application": gateway_health.get("application"),
                    "capabilities": gateway_health.get("capabilities", []),
                },
                "browser": browser_evidence,
                "database": {
                    "tableCount": len(after_counts),
                    "fixtureRowCount": sum(before_counts.values()),
                    "changedOnlyAfterAdmin": not arguments.smoke_only,
                    "fairnessBalanced": True,
                },
                "outbox": outbox,
                "stopConditions": {
                    "crossSessionLeak": False,
                    "unhandledLockOr5xx": False,
                    "fairnessMismatch": False,
                    "guestDatabaseWrite": False,
                    "cleanupMemoryBudgetExceeded": False,
                },
            }
        )
        success = True
        return 0
    except Exception as error:  # noqa: BLE001 - CLI boundary must preserve failure evidence
        report.update(
            {
                "status": "fail",
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "failure": str(error),
            }
        )
        print(f"MIXED GATEWAY LOAD FAILED: {error}", file=sys.stderr, flush=True)
        print(f"Isolated evidence retained at: {workspace}", file=sys.stderr, flush=True)
        return 1
    finally:
        if worker_process is not None and worker_output is not None:
            _stop_process(worker_process, worker_output)
        if origin_process is not None and origin_output is not None:
            _stop_process(origin_process, origin_output)
        temporary_report = REPORT_PATH.with_suffix(".tmp")
        temporary_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_report.replace(REPORT_PATH)
        if success and not arguments.retain:
            shutil.rmtree(workspace, ignore_errors=True)
        elif success:
            print(f"Retained isolated evidence: {workspace}", flush=True)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
