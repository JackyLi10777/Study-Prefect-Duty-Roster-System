"""Local-first deployment settings and non-sensitive readiness evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import re
import secrets
import socket
import time
from typing import Literal

from starlette.middleware.trustedhost import TrustedHostMiddleware

from nicegui_app.config import DEFAULT_BACKUP_DIR, DEFAULT_DATABASE_PATH, POLICY_VERSION, PROJECT_ROOT
from nicegui_app.application_mode import current_application_mode
from nicegui_app.persistence.database import database_readiness


LOCAL_HOSTS = {"127.0.0.1", "localhost"}
DEVELOPMENT_STORAGE_SECRETS = {
    "",
    "local-sing-yin-development-secret",
    "replace-with-a-long-random-local-secret",
}
MANAGED_STORAGE_SECRET_PATH = PROJECT_ROOT / "data" / "runtime" / ".nicegui-storage-secret"
_MINIMUM_STORAGE_SECRET_LENGTH = 32
_MANAGED_SECRET_CREATE_RETRIES = 20
_MANAGED_SECRET_RETRY_SECONDS = 0.01
_PUBLIC_HOSTNAME_PATTERN = re.compile(
    r"(?=^.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)


def _enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DeploymentSettings:
    """Fail-closed network settings for the current and future host."""

    mode: Literal["local", "server"]
    host: str
    port: int
    remote_access_enabled: bool
    cloudflare_access_audience: str
    cloudflare_team_domain: str
    public_hostname: str = ""
    protect_with_access: bool = False
    private_warp_enabled: bool = False
    private_hostname: str = ""

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_environment(cls) -> "DeploymentSettings":
        raw_mode = os.getenv("SING_YIN_DEPLOYMENT_MODE", "local").strip().lower()
        if raw_mode not in {"local", "server"}:
            raise RuntimeError("SING_YIN_DEPLOYMENT_MODE must be 'local' or 'server'.")
        raw_port = os.getenv("SING_YIN_PORT", "8080").strip()
        try:
            port = int(raw_port)
        except ValueError as error:
            raise RuntimeError("SING_YIN_PORT must be a number between 1024 and 65535.") from error
        settings = cls(
            mode=raw_mode,  # type: ignore[arg-type]
            host=os.getenv("SING_YIN_HOST", "127.0.0.1").strip(),
            port=port,
            remote_access_enabled=_enabled("SING_YIN_REMOTE_ACCESS_ENABLED"),
            cloudflare_access_audience=os.getenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "").strip(),
            cloudflare_team_domain=os.getenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "").strip(),
            public_hostname=os.getenv("SING_YIN_PUBLIC_HOSTNAME", "").strip().lower().rstrip("."),
            protect_with_access=_enabled("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS"),
            private_warp_enabled=_enabled("SING_YIN_CLOUDFLARE_PRIVATE_WARP"),
            private_hostname=os.getenv("SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME", "").strip().lower().rstrip("."),
        )
        return settings

    @property
    def is_loopback(self) -> bool:
        return self.host.lower() in LOCAL_HOSTS

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        hosts = {"127.0.0.1", "localhost", "::1", "[::1]"}
        if self.mode == "server" and self.public_hostname:
            hosts.add(self.public_hostname)
        if self.mode == "server" and self.private_warp_enabled and self.private_hostname:
            hosts.add(self.private_hostname)
        return tuple(sorted(hosts))

    @property
    def remote_access_method(self) -> Literal["disabled", "public_access", "private_warp"]:
        if self.mode == "local" or not self.remote_access_enabled:
            return "disabled"
        return "private_warp" if self.private_warp_enabled else "public_access"

    def validate(self) -> None:
        if not 1024 <= self.port <= 65535:
            raise RuntimeError("SING_YIN_PORT must be between 1024 and 65535.")
        if self.host.lower() in {"::1", "[::1]"}:
            raise RuntimeError(
                "SING_YIN_HOST=::1 is unsupported by the installed TrustedHostMiddleware; use 127.0.0.1."
            )
        if not self.is_loopback:
            raise RuntimeError(
                "NiceGUI refuses non-loopback hosts. A future Cloudflare Tunnel must connect to 127.0.0.1."
            )
        if self.mode == "local":
            if self.remote_access_enabled:
                raise RuntimeError("Remote access cannot be enabled while SING_YIN_DEPLOYMENT_MODE=local.")
            return
        if not self.remote_access_enabled:
            raise RuntimeError("Server mode requires SING_YIN_REMOTE_ACCESS_ENABLED=true.")
        if self.private_warp_enabled:
            if self.protect_with_access or self.public_hostname or self.cloudflare_access_audience:
                raise RuntimeError(
                    "Private WARP mode cannot be combined with public-hostname Cloudflare Access settings."
                )
            team_domain = self.cloudflare_team_domain.lower().rstrip(".")
            if not _PUBLIC_HOSTNAME_PATTERN.fullmatch(team_domain) or not team_domain.endswith(".cloudflareaccess.com"):
                raise RuntimeError("Private WARP mode requires a valid Cloudflare Access team domain.")
            if not _PUBLIC_HOSTNAME_PATTERN.fullmatch(self.private_hostname):
                raise RuntimeError(
                    "Private WARP mode requires one valid SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME."
                )
            return
        if not self.protect_with_access:
            raise RuntimeError("Server mode requires Cloudflare Tunnel Protect with Access to be explicitly enabled.")
        if not self.cloudflare_access_audience or not self.cloudflare_team_domain:
            raise RuntimeError("Server mode requires complete Cloudflare Access audience and team-domain settings.")
        team_domain = self.cloudflare_team_domain.lower().rstrip(".")
        if not _PUBLIC_HOSTNAME_PATTERN.fullmatch(team_domain) or not team_domain.endswith(".cloudflareaccess.com"):
            raise RuntimeError("Server mode requires a valid Cloudflare Access team domain.")
        if not _PUBLIC_HOSTNAME_PATTERN.fullmatch(self.public_hostname):
            raise RuntimeError("Server mode requires one valid SING_YIN_PUBLIC_HOSTNAME without a scheme or path.")


@dataclass(frozen=True)
class ReadinessCheck:
    code: str
    status: Literal["pass", "warning", "deferred", "fail"]
    message: str


def install_trusted_host_protection(application: object, settings: DeploymentSettings) -> None:
    """Reject DNS-rebinding and unexpected proxy Host headers before route handling."""
    if getattr(application, "_sing_yin_trusted_hosts_installed", False):
        return
    add_middleware = getattr(application, "add_middleware", None)
    if not callable(add_middleware):
        raise TypeError("The application does not support HTTP middleware.")
    add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts), www_redirect=False)
    setattr(application, "_sing_yin_trusted_hosts_installed", True)


def _valid_storage_secret(value: str) -> bool:
    return len(value) >= _MINIMUM_STORAGE_SECRET_LENGTH and value not in DEVELOPMENT_STORAGE_SECRETS


def _read_managed_storage_secret(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError("The managed local storage secret could not be read safely.") from error
    if not _valid_storage_secret(value):
        raise RuntimeError(
            "The managed local storage secret is invalid. Remove data/runtime/.nicegui-storage-secret and restart locally."
        )
    return value


def _read_managed_storage_secret_after_concurrent_create(path: Path) -> str:
    """Allow an exclusive creator to finish its tiny write/fsync window."""
    for attempt in range(_MANAGED_SECRET_CREATE_RETRIES + 1):
        try:
            return _read_managed_storage_secret(path)
        except RuntimeError:
            if attempt >= _MANAGED_SECRET_CREATE_RETRIES:
                raise
            time.sleep(_MANAGED_SECRET_RETRY_SECONDS)
    raise RuntimeError("The managed local storage secret could not be read safely.")  # pragma: no cover


def _create_managed_storage_secret(path: Path) -> str:
    """Create one persistent local secret without overwriting a concurrent writer."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RuntimeError("The managed local storage-secret directory could not be created.") from error
    value = secrets.token_urlsafe(48)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        # Another local process may have won the create race but not yet
        # completed its tiny fsync. Never overwrite it; wait for a valid value.
        return _read_managed_storage_secret_after_concurrent_create(path)
    except OSError as error:
        raise RuntimeError("The managed local storage secret could not be created safely.") from error

    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return value
    except OSError as error:
        path.unlink(missing_ok=True)
        raise RuntimeError("The managed local storage secret could not be persisted safely.") from error


def resolve_storage_secret(
    settings: DeploymentSettings,
    *,
    managed_path: Path = MANAGED_STORAGE_SECRET_PATH,
) -> str:
    """Return an explicit secret or create a persistent secret for localhost only."""
    configured = os.getenv("SING_YIN_STORAGE_SECRET", "").strip()
    if _valid_storage_secret(configured):
        return configured
    if settings.mode == "server":
        raise RuntimeError("Server mode requires a unique SING_YIN_STORAGE_SECRET of at least 32 characters.")
    if managed_path.exists():
        return _read_managed_storage_secret_after_concurrent_create(managed_path)
    return _create_managed_storage_secret(managed_path)


def storage_secret_readiness(
    settings: DeploymentSettings,
    *,
    managed_path: Path = MANAGED_STORAGE_SECRET_PATH,
) -> tuple[Literal["configured", "managed", "missing", "invalid"], str]:
    """Inspect storage-secret readiness without creating or revealing a secret."""
    configured = os.getenv("SING_YIN_STORAGE_SECRET", "").strip()
    if _valid_storage_secret(configured):
        return "configured", "A non-default storage secret is configured."
    if settings.mode == "server":
        return "invalid", "Server mode requires a unique environment storage secret of at least 32 characters."
    if not managed_path.is_file():
        return "missing", "The managed localhost storage secret will be created on the next application start."
    try:
        _read_managed_storage_secret(managed_path)
    except RuntimeError:
        return "invalid", "The managed localhost storage secret is unreadable or invalid."
    return "managed", "A persistent, non-default localhost storage secret is managed on this computer."


def database_integrity(database_path: Path = DEFAULT_DATABASE_PATH) -> str:
    """Return payload-free readiness for SQLite bytes, schema, and migrations."""
    return database_readiness(database_path)


def health_snapshot(database_path: Path = DEFAULT_DATABASE_PATH) -> dict[str, str]:
    database = database_integrity(database_path)
    return {
        "status": "ok" if database == "ok" else "degraded",
        "application": "sing-yin-roster",
        "applicationMode": current_application_mode().mode,
        "policyVersion": POLICY_VERSION,
        "database": database,
    }


def verified_backup_evidence(
    database_path: Path = DEFAULT_DATABASE_PATH,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
) -> tuple[str, int, int]:
    """Return current managed-snapshot trust without creating or modifying data.

    The readiness report must use the same manifest, checksum, SQLite integrity,
    and schema contract as Settings and managed restore. A filename alone is not
    recovery evidence.
    """
    from nicegui_app.services.roster_workflow import RosterWorkflow

    try:
        inventory = RosterWorkflow(database_path=database_path, backup_dir=backup_dir).backup_inventory()
    except OSError:
        return "unavailable", 0, 0
    checked = int(inventory["checkedCount"])
    verified = int(inventory["verifiedCount"])
    if checked == 0:
        return "missing", checked, verified
    if verified > 0:
        return "verified", checked, verified
    return "invalid", checked, verified


def build_readiness_report(
    settings: DeploymentSettings,
    *,
    database_path: Path = DEFAULT_DATABASE_PATH,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    managed_secret_path: Path = MANAGED_STORAGE_SECRET_PATH,
) -> list[ReadinessCheck]:
    """Describe readiness without installing software, opening ports, or exposing data."""
    checks: list[ReadinessCheck] = []
    checks.append(
        ReadinessCheck(
            "network_bind",
            "pass" if settings.is_loopback else "fail",
            "NiceGUI is restricted to loopback; a future same-host Tunnel does not expose the origin port."
            if settings.mode == "server"
            else "NiceGUI is restricted to this computer.",
        )
    )
    secret_state, secret_message = storage_secret_readiness(settings, managed_path=managed_secret_path)
    checks.append(
        ReadinessCheck(
            "storage_secret",
            "pass" if secret_state in {"configured", "managed"} else "fail" if secret_state == "invalid" else "warning",  # pragma: allowlist secret
            secret_message,
        )
    )
    integrity = database_integrity(database_path)
    integrity_status = "pass" if integrity == "ok" else ("warning" if integrity == "missing" else "fail")
    checks.append(
        ReadinessCheck(
            "database_integrity",
            integrity_status,
            (
                "SQLite integrity, schema contract, and migration head passed."
                if integrity == "ok"
                else f"SQLite readiness is {integrity}; repair or migrate it before service."
            ),
        )
    )
    backup_state, checked_backups, verified_backups = verified_backup_evidence(database_path, backup_dir)
    if backup_state == "verified":
        backup_status: Literal["pass", "warning", "deferred", "fail"] = "pass"
        backup_message = (
            f"{verified_backups} of the {checked_backups} most recent local snapshots passed manifest, checksum, "
            "SQLite integrity, and schema verification."
        )
    elif backup_state == "missing":
        backup_status = "warning"
        backup_message = "No local SQLite snapshot was found yet."
    elif backup_state == "invalid":
        backup_status = "fail"
        backup_message = (
            f"{checked_backups} local snapshot(s) were checked, but none passed manifest, checksum, SQLite integrity, "
            "and schema verification."
        )
    else:
        backup_status = "fail"
        backup_message = "The managed backup directory could not be inspected safely."
    checks.append(
        ReadinessCheck(
            "verified_backup",
            backup_status,
            backup_message,
        )
    )
    checks.append(
        ReadinessCheck(
            "cloudflare_access",
            "deferred" if settings.mode == "local" else "warning",
            "Cloudflare remote access is inactive; complete the documented account, Access, and live identity checks before activation."
            if settings.mode == "local"
            else (
                "Private WARP, team domain, and private hostname are declared; live enrolled-device verification is still required."
                if settings.private_warp_enabled
                else "Protect with Access, audience, team domain, and public hostname are declared; live identity and bypass verification is still required."
            ),
        )
    )
    try:
        socket.getaddrinfo(settings.host, settings.port)
        endpoint_status: Literal["pass", "warning"] = "pass"
    except socket.gaierror:
        endpoint_status = "warning"
    checks.append(ReadinessCheck("endpoint", endpoint_status, f"Configured endpoint is {settings.host}:{settings.port}."))
    return checks


def readiness_payload(settings: DeploymentSettings) -> dict[str, object]:
    checks = build_readiness_report(settings)
    return {
        "project": PROJECT_ROOT.name,
        "deploymentMode": settings.mode,
        "checks": [asdict(check) for check in checks],
    }
