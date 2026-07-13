from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nicegui_app.deployment import (
    DeploymentSettings,
    build_readiness_report,
    health_snapshot,
    install_trusted_host_protection,
    resolve_storage_secret,
    storage_secret_readiness,
)
from nicegui_app.services.roster_workflow import RosterWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_deployment_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SING_YIN_DEPLOYMENT_MODE",
        "SING_YIN_HOST",
        "SING_YIN_PORT",
        "SING_YIN_REMOTE_ACCESS_ENABLED",
        "SING_YIN_CLOUDFLARE_ACCESS_AUD",
        "SING_YIN_CLOUDFLARE_TEAM_DOMAIN",
        "SING_YIN_PUBLIC_HOSTNAME",
        "SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS",
        "SING_YIN_CLOUDFLARE_PRIVATE_WARP",
        "SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = DeploymentSettings.from_environment()
    assert settings.mode == "local"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8080
    assert settings.is_loopback is True


def test_local_deployment_refuses_external_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "local")
    monkeypatch.setenv("SING_YIN_HOST", "0.0.0.0")
    with pytest.raises(RuntimeError, match="refuses non-loopback"):
        DeploymentSettings.from_environment()


def test_future_server_mode_fails_closed_until_access_is_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.delenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", raising=False)
    monkeypatch.delenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", raising=False)
    with pytest.raises(RuntimeError, match="complete Cloudflare Access"):
        DeploymentSettings.from_environment()


def test_future_server_mode_never_allows_a_direct_origin_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "0.0.0.0")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "audience")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "roster.example.edu.hk")

    with pytest.raises(RuntimeError, match="Tunnel must connect to 127.0.0.1"):
        DeploymentSettings.from_environment()


def test_future_server_mode_requires_protect_with_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "false")

    with pytest.raises(RuntimeError, match="Protect with Access"):
        DeploymentSettings.from_environment()


def test_future_server_mode_requires_a_valid_public_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "audience")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "https://roster.example.edu.hk/path")

    with pytest.raises(RuntimeError, match="valid SING_YIN_PUBLIC_HOSTNAME"):
        DeploymentSettings.from_environment()


def test_future_server_mode_requires_a_valid_cloudflare_team_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "audience")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "not-cloudflare.example.com")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "roster.example.edu.hk")

    with pytest.raises(RuntimeError, match="valid Cloudflare Access team domain"):
        DeploymentSettings.from_environment()


def test_direct_deployment_settings_construction_cannot_bypass_validation() -> None:
    with pytest.raises(RuntimeError, match="refuses non-loopback"):
        DeploymentSettings("local", "0.0.0.0", 8080, False, "", "")


def test_future_server_mode_is_loopback_only_and_host_allowlisted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "audience")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "roster.example.edu.hk")

    settings = DeploymentSettings.from_environment()

    assert settings.is_loopback is True
    assert settings.public_hostname == "roster.example.edu.hk"
    assert "roster.example.edu.hk" in settings.allowed_hosts


def test_private_warp_server_mode_is_loopback_only_and_host_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_WARP", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME", "roster.singyin.internal")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.delenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", raising=False)
    monkeypatch.delenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", raising=False)
    monkeypatch.delenv("SING_YIN_PUBLIC_HOSTNAME", raising=False)

    settings = DeploymentSettings.from_environment()

    assert settings.is_loopback is True
    assert settings.remote_access_method == "private_warp"
    assert settings.private_hostname == "roster.singyin.internal"
    assert "roster.singyin.internal" in settings.allowed_hosts


def test_private_warp_mode_refuses_public_access_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_WARP", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME", "roster.singyin.internal")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "roster.example.edu.hk")

    with pytest.raises(RuntimeError, match="cannot be combined"):
        DeploymentSettings.from_environment()


def test_private_warp_readiness_requires_live_device_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_WARP", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME", "roster.singyin.internal")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_STORAGE_SECRET", "server-secret-longer-than-thirty-two-characters")
    settings = DeploymentSettings.from_environment()

    checks = build_readiness_report(
        settings,
        database_path=tmp_path / "missing.sqlite3",
        backup_dir=tmp_path / "backups",
    )

    access_check = next(check for check in checks if check.code == "cloudflare_access")
    assert access_check.status == "warning"
    assert "live enrolled-device verification" in access_check.message


def test_future_server_readiness_cannot_impersonate_live_access_acceptance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SING_YIN_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("SING_YIN_HOST", "127.0.0.1")
    monkeypatch.setenv("SING_YIN_REMOTE_ACCESS_ENABLED", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_PROTECT_WITH_ACCESS", "true")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_ACCESS_AUD", "audience")
    monkeypatch.setenv("SING_YIN_CLOUDFLARE_TEAM_DOMAIN", "school.cloudflareaccess.com")
    monkeypatch.setenv("SING_YIN_PUBLIC_HOSTNAME", "roster.example.edu.hk")
    monkeypatch.setenv("SING_YIN_STORAGE_SECRET", "server-secret-longer-than-thirty-two-characters")
    settings = DeploymentSettings.from_environment()

    checks = build_readiness_report(
        settings,
        database_path=tmp_path / "missing.sqlite3",
        backup_dir=tmp_path / "backups",
    )

    assert next(check for check in checks if check.code == "network_bind").status == "pass"
    access_check = next(check for check in checks if check.code == "cloudflare_access")
    assert access_check.status == "warning"
    assert "live identity and bypass verification is still required" in access_check.message


def test_trusted_host_protection_rejects_unexpected_hosts() -> None:
    application = FastAPI()
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")
    install_trusted_host_protection(application, settings)

    @application.get("/")
    def home() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(application, base_url="http://localhost") as client:
        assert client.get("/").status_code == 200
        assert client.get("/", headers={"host": "unexpected.example"}).status_code == 400


def test_health_and_readiness_use_read_only_database_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "runtime.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY)")
    monkeypatch.setenv("SING_YIN_STORAGE_SECRET", "a-local-secret-longer-than-thirty-two-characters")
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    health = health_snapshot(database)
    checks = build_readiness_report(settings, database_path=database, backup_dir=tmp_path / "backups")

    assert health == {
        "status": "ok",
        "application": "sing-yin-roster",
        "applicationMode": "official",
        "policyVersion": health["policyVersion"],
        "database": "ok",
    }
    assert next(check for check in checks if check.code == "database_integrity").status == "pass"
    assert next(check for check in checks if check.code == "cloudflare_access").status == "deferred"


def test_readiness_rejects_a_sqlite_filename_without_managed_verification(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "untrusted.sqlite3").write_bytes(b"not a managed SQLite snapshot")
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    checks = build_readiness_report(settings, database_path=tmp_path / "live.sqlite3", backup_dir=backup_dir)
    backup_check = next(check for check in checks if check.code == "verified_backup")

    assert backup_check.status == "fail"
    assert "none passed manifest" in backup_check.message


def test_readiness_accepts_a_snapshot_only_after_full_managed_verification(tmp_path: Path) -> None:
    database = tmp_path / "live.sqlite3"
    backup_dir = tmp_path / "backups"
    workflow = RosterWorkflow(database_path=database, backup_dir=backup_dir)
    workflow.bootstrap()
    workflow.create_verified_backup()
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    checks = build_readiness_report(settings, database_path=database, backup_dir=backup_dir)
    backup_check = next(check for check in checks if check.code == "verified_backup")

    assert backup_check.status == "pass"
    assert "passed manifest, checksum" in backup_check.message


def test_readiness_script_runs_directly_from_project_root(tmp_path: Path) -> None:
    environment = {
        "SING_YIN_DEPLOYMENT_MODE": "local",
        "SING_YIN_HOST": "127.0.0.1",
        "SING_YIN_DATABASE_PATH": str(tmp_path / "missing.sqlite3"),
        "SING_YIN_BACKUP_DIR": str(tmp_path / "backups"),
    }
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "scripts/check_deployment_readiness.py"],
        cwd=PROJECT_ROOT,
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"deploymentMode": "local"' in result.stdout
    assert '"code": "database_integrity"' in result.stdout


def test_local_storage_secret_is_generated_once_and_persists(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SING_YIN_STORAGE_SECRET", raising=False)
    secret_path = tmp_path / "runtime" / ".nicegui-storage-secret"
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    first = resolve_storage_secret(settings, managed_path=secret_path)
    second = resolve_storage_secret(settings, managed_path=secret_path)

    assert first == second
    assert len(first) >= 64
    assert secret_path.read_text(encoding="utf-8").strip() == first


def test_explicit_storage_secret_takes_priority_without_creating_managed_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    configured = "explicit-school-controlled-secret-value-000000000000"
    monkeypatch.setenv("SING_YIN_STORAGE_SECRET", configured)
    secret_path = tmp_path / ".nicegui-storage-secret"
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    assert resolve_storage_secret(settings, managed_path=secret_path) == configured
    assert not secret_path.exists()


def test_managed_storage_secret_creation_is_safe_under_local_concurrency(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SING_YIN_STORAGE_SECRET", raising=False)
    secret_path = tmp_path / "runtime" / ".nicegui-storage-secret"
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda _index: resolve_storage_secret(settings, managed_path=secret_path), range(24)))

    assert len(set(values)) == 1
    assert secret_path.read_text(encoding="utf-8").strip() == values[0]


def test_corrupt_managed_storage_secret_fails_closed_without_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SING_YIN_STORAGE_SECRET", raising=False)
    secret_path = tmp_path / ".nicegui-storage-secret"
    secret_path.write_text("too-short", encoding="utf-8")
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    with pytest.raises(RuntimeError, match="managed local storage secret is invalid"):
        resolve_storage_secret(settings, managed_path=secret_path)

    assert secret_path.read_text(encoding="utf-8") == "too-short"


def test_server_mode_requires_explicit_storage_secret_even_if_managed_file_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("SING_YIN_STORAGE_SECRET", raising=False)
    secret_path = tmp_path / ".nicegui-storage-secret"
    secret_path.write_text("managed-local-secret-that-is-long-enough-0000000000", encoding="utf-8")
    settings = DeploymentSettings(
        "server",
        "127.0.0.1",
        8080,
        True,
        "audience",
        "school.cloudflareaccess.com",
        "roster.example.edu.hk",
        True,
    )

    with pytest.raises(RuntimeError, match="Server mode requires a unique SING_YIN_STORAGE_SECRET"):
        resolve_storage_secret(settings, managed_path=secret_path)


def test_storage_secret_readiness_is_read_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SING_YIN_STORAGE_SECRET", raising=False)
    secret_path = tmp_path / "runtime" / ".nicegui-storage-secret"
    settings = DeploymentSettings("local", "127.0.0.1", 8080, False, "", "")

    assert storage_secret_readiness(settings, managed_path=secret_path)[0] == "missing"
    assert not secret_path.exists()
    resolve_storage_secret(settings, managed_path=secret_path)
    assert storage_secret_readiness(settings, managed_path=secret_path)[0] == "managed"

    checks = build_readiness_report(
        settings,
        database_path=tmp_path / "missing.sqlite3",
        backup_dir=tmp_path / "backups",
        managed_secret_path=secret_path,
    )
    secret_check = next(check for check in checks if check.code == "storage_secret")
    assert secret_check.status == "pass"
    assert "managed on this computer" in secret_check.message
