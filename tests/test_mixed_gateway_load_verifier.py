from __future__ import annotations

import base64
import hashlib
import hmac
import json
from ipaddress import IPv4Address
from pathlib import Path
import shutil
import subprocess
import sys

from cryptography import x509
import pytest

from scripts import verify_mixed_gateway_load as verifier


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_mixed_load_child_environment_drops_parent_credentials(monkeypatch) -> None:
    monkeypatch.setenv("PATH", "mixed-load-path")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "must-not-cross-the-process-boundary")
    monkeypatch.setenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN", "must-not-be-inherited")

    environment = verifier._base_process_environment()

    assert environment["PATH"] == "mixed-load-path"
    assert "CLOUDFLARE_API_TOKEN" not in environment
    assert "SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN" not in environment


def test_mixed_load_origin_environment_is_disposable_and_fail_closed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "must-not-cross-the-process-boundary")
    certificate_path = tmp_path / "localhost-ca.pem"
    environment = verifier._isolated_origin_environment(
        tmp_path / "origin",
        port=18765,
        gateway_url="https://localhost:18766",
        certificate_path=certificate_path,
        admin_token="a" * 42,
        origin_principal_secret="b" * 42,
    )

    database_path = Path(environment["SING_YIN_DATABASE_PATH"]).resolve()
    backup_path = Path(environment["SING_YIN_BACKUP_DIR"]).resolve()
    assert database_path.is_relative_to(tmp_path.resolve())
    assert backup_path.is_relative_to(tmp_path.resolve())
    assert database_path != verifier.CANONICAL_DATABASE
    assert backup_path != verifier.CANONICAL_BACKUPS
    assert environment["SING_YIN_HOST"] == "127.0.0.1"
    assert environment["SING_YIN_REQUIRE_GATEWAY_PRINCIPAL"] == "1"
    assert environment["SING_YIN_UNIFIED_GUEST"] == "1"
    assert environment["SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL"] == "https://localhost:18766"
    assert environment["SING_YIN_YOUTUBE_ENABLED"] == "false"
    assert environment["SING_YIN_DEEPSEEK_ENABLED"] == "false"
    assert "CLOUDFLARE_API_TOKEN" not in environment


def test_mixed_load_certificate_covers_only_localhost(tmp_path: Path) -> None:
    certificate_path, key_path = verifier._generate_local_certificate(tmp_path)
    certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
    names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value

    assert names.get_values_for_type(x509.DNSName) == ["localhost"]
    assert names.get_values_for_type(x509.IPAddress) == [IPv4Address("127.0.0.1")]
    assert key_path.is_file()


def test_admin_session_fixture_matches_worker_hmac_contract() -> None:
    secret = "session-secret-with-at-least-thirty-two-characters"
    token = verifier._admin_session_token(secret, now=1_800_000_000)
    payload_segment, signature_segment = token.split(".")
    payload = json.loads(_decode_base64url(payload_segment))
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()

    assert payload["v"] == 2
    assert payload["email"] == verifier.ADMIN_EMAIL
    assert payload["iat"] == 1_800_000_000
    assert payload["exp"] == 1_800_003_600
    assert payload["epoch"] == verifier.AUTH_EPOCH
    assert hmac.compare_digest(_decode_base64url(signature_segment), expected)


def test_local_workerd_launcher_fails_closed_without_explicit_arguments() -> None:
    node = shutil.which("node")
    assert node is not None

    result = subprocess.run(
        [node, str(verifier.WORKER_RUNTIME_ENTRY)],
        cwd=verifier.PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=20,
    )

    assert result.returncode == 1
    assert "required mixed-load runtime argument" in result.stderr.lower()
    assert "cloudflare.com" not in result.stderr.lower()


def test_missing_worker_dependency_still_writes_failure_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    report_path = tmp_path / "verification.json"
    monkeypatch.setattr(verifier, "REPORT_PATH", report_path)
    monkeypatch.setattr(verifier, "MINIFLARE_PACKAGE", tmp_path / "missing-package.json")
    monkeypatch.setattr(verifier.tempfile, "mkdtemp", lambda **_kwargs: str(workspace))
    monkeypatch.setattr(sys, "argv", [str(verifier.__file__), "--smoke-only"])

    exit_code = verifier.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["status"] == "fail"
    assert report["scope"]["productionTouched"] is False
    assert "dependencies are missing" in report["failure"]
    assert workspace.is_dir()


def test_cli_refuses_a_load_that_would_only_measure_edge_rate_limiting(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [str(verifier.__file__), "--guests", "11", "--waves", "2"],
    )

    with pytest.raises(SystemExit) as error:
        verifier._arguments()

    assert error.value.code == 2


@pytest.mark.parametrize(
    ("url", "tls"),
    [
        ("file:///tmp/report.json", False),
        ("https://example.com:443/healthz", True),
        ("http://127.0.0.1:80/healthz", False),
        ("http://user@127.0.0.1:18765/healthz", False),
        ("http://127.0.0.1:18765/healthz#fragment", False),
        ("http://127.0.0.1:18765/healthz", True),
    ],
)
def test_json_probe_rejects_every_non_loopback_or_mismatched_url(url: str, tls: bool) -> None:
    with pytest.raises(verifier.MixedGatewayLoadError):
        verifier._validate_loopback_url(url, tls=tls)


def test_json_probe_accepts_only_the_expected_loopback_protocol() -> None:
    verifier._validate_loopback_url("http://127.0.0.1:18765/readyz", tls=False)
    verifier._validate_loopback_url("https://localhost:18766/healthz?probe=1", tls=True)
