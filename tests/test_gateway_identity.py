from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

import pytest

from nicegui_app.access_context import AccessMode
from nicegui_app.gateway_identity import (
    ORIGIN_PRINCIPAL_AUDIENCE,
    OriginPrincipalError,
    origin_request_binding,
    principal_from_request,
    seal_origin_principal_for_test,
    verify_origin_principal,
)


ENV = {
    "ORIGIN_PRINCIPAL_SECRET": "origin-principal-test-secret-at-least-32-bytes",
    "ORIGIN_PRINCIPAL_KID": "origin-v2",
    "AUTH_EPOCH": "4",
}


def _payload(*, mode: str = "guest", now: int = 10_000) -> dict[str, object]:
    return {
        "v": 1,
        "aud": ORIGIN_PRINCIPAL_AUDIENCE,
        "mode": mode,
        "subject": "guest" if mode == "guest" else "admin@example.test",
        "sid": "abcdefghijklmnopqrstuv",
        "iat": now,
        "exp": now + (1_800 if mode == "guest" else 28_800),
        "auth_epoch": 4,
        "kid": "origin-v2",
        "request_binding": origin_request_binding(
            method="GET",
            public_host="roster.example.test",
            path_and_query="/rosters?week=1",
        ),
    }


def test_origin_principal_is_hmac_verified_request_bound_and_session_lived() -> None:
    payload = _payload()
    token = seal_origin_principal_for_test(payload, environment=ENV)
    principal = verify_origin_principal(
        token,
        expected_binding=str(payload["request_binding"]),
        environment=ENV,
        now=10_000,
    )
    assert principal.mode is AccessMode.GUEST
    assert principal.session_id == "abcdefghijklmnopqrstuv"
    assert int(principal.expires_at.astimezone(timezone.utc).timestamp()) == 11_800

    with pytest.raises(OriginPrincipalError, match="bound"):
        verify_origin_principal(
            token,
            expected_binding=origin_request_binding(
                method="POST",
                public_host="roster.example.test",
                path_and_query="/rosters?week=1",
            ),
            environment=ENV,
            now=10_000,
        )


def test_origin_principal_accepts_only_a_signed_explicit_theme_handoff() -> None:
    payload = {**_payload(), "theme": "dark"}
    principal = verify_origin_principal(
        seal_origin_principal_for_test(payload, environment=ENV),
        expected_binding=str(payload["request_binding"]),
        environment=ENV,
        now=10_000,
    )
    assert principal.theme_handoff == "dark"

    for invalid in ("system", "sepia", "", 1, None):
        rejected = {**_payload(), "theme": invalid}
        with pytest.raises(OriginPrincipalError):
            verify_origin_principal(
                seal_origin_principal_for_test(rejected, environment=ENV),
                expected_binding=str(rejected["request_binding"]),
                environment=ENV,
                now=10_000,
            )


def test_origin_principal_rejects_tamper_stale_epoch_key_and_overlong_session() -> None:
    payload = _payload()
    token = seal_origin_principal_for_test(payload, environment=ENV)
    with pytest.raises(OriginPrincipalError, match="signature"):
        verify_origin_principal(
            token[:-1] + ("A" if token[-1] != "A" else "B"),
            expected_binding=str(payload["request_binding"]),
            environment=ENV,
            now=10_000,
        )
    with pytest.raises(OriginPrincipalError, match="stale"):
        verify_origin_principal(
            token,
            expected_binding=str(payload["request_binding"]),
            environment={**ENV, "AUTH_EPOCH": "5"},
            now=10_000,
        )
    with pytest.raises(OriginPrincipalError, match="stale"):
        verify_origin_principal(
            token,
            expected_binding=str(payload["request_binding"]),
            environment={**ENV, "ORIGIN_PRINCIPAL_KID": "rotated"},
            now=10_000,
        )
    with pytest.raises(OriginPrincipalError, match="stale"):
        verify_origin_principal(
            token,
            expected_binding=str(payload["request_binding"]),
            environment=ENV,
            now=10_061,
        )

    overlong = _payload()
    overlong["exp"] = 10_000 + 1_801
    with pytest.raises(OriginPrincipalError, match="stale"):
        verify_origin_principal(
            seal_origin_principal_for_test(overlong, environment=ENV),
            expected_binding=str(overlong["request_binding"]),
            environment=ENV,
            now=10_000,
        )


@dataclass
class _URL:
    netloc: str
    path: str
    query: str


@dataclass
class _Request:
    method: str
    headers: dict[str, str]
    url: _URL


def test_request_resolution_uses_forwarded_public_host_and_explicit_local_mode() -> None:
    payload = _payload()
    token = seal_origin_principal_for_test(payload, environment=ENV)
    request = _Request(
        method="GET",
        headers={
            "x-forwarded-host": "roster.example.test",
            "x-sing-yin-origin-principal": token,
        },
        url=_URL(netloc="127.0.0.1:8080", path="/rosters", query="week=1"),
    )
    assert principal_from_request(request, environment=ENV, now=10_000).mode is AccessMode.GUEST
    with pytest.raises(OriginPrincipalError, match="explicit local-maintenance"):
        principal_from_request(None, environment=ENV)
    assert principal_from_request(
        None,
        environment={**ENV, "SING_YIN_LOCAL_MAINTENANCE": "1"},
    ).mode is AccessMode.LOCAL_MAINTENANCE
    with pytest.raises(OriginPrincipalError, match="required"):
        principal_from_request(
            None,
            environment={**ENV, "SING_YIN_REQUIRE_GATEWAY_PRINCIPAL": "1"},
        )


def test_isolated_e2e_guest_override_requires_all_three_guards() -> None:
    environment = {
        "SING_YIN_E2E_ISOLATED": "1",
        "SING_YIN_E2E_RUN_ID": "E2E-ABCDEF123456",
        "SING_YIN_E2E_ACCESS_MODE": "guest",
        "AUTH_EPOCH": "1",
        "ORIGIN_PRINCIPAL_KID": "origin-v1",
    }

    principal = principal_from_request(None, environment=environment, now=1_700_000_000)

    assert principal.mode is AccessMode.GUEST
    assert principal.subject == "guest-e2e:E2E-ABCDEF123456"
    assert principal.session_id
    assert principal.expires_at is not None

    for key, value in (
        ("SING_YIN_E2E_ISOLATED", "0"),
        ("SING_YIN_E2E_RUN_ID", "invalid"),
        ("SING_YIN_E2E_ACCESS_MODE", "admin"),
    ):
        rejected = {**environment, key: value}
        with pytest.raises(OriginPrincipalError, match="explicit local-maintenance"):
            principal_from_request(None, environment=rejected)


def test_python_accepts_the_worker_cross_language_principal_vector() -> None:
    environment = {
        "ORIGIN_PRINCIPAL_SECRET": "test-only-origin-principal-secret-with-more-than-32-characters",
        "AUTH_EPOCH": "7",
        "ORIGIN_PRINCIPAL_KID": "test-origin-v7",
    }
    binding = "IA6owyScWUXkk2hYMBvAgo2d9EdLSxS3Jwil1BFlIrQ"
    token = (
        "eyJ2IjoxLCJhdWQiOiJzaW5nLXlpbi1yb3N0ZXItb3JpZ2luIiwibW9kZSI6Imd1ZXN0Iiwic3ViamVjdCI6"
        "Imd1ZXN0Iiwic2lkIjoiQkFRRUJBUUVCQVFFQkFRRUJBUUVCQSIsImlhdCI6MjAwMDAwMDAwMCwiZXhwIjoy"
        "MDAwMDAxODAwLCJhdXRoX2Vwb2NoIjo3LCJraWQiOiJ0ZXN0LW9yaWdpbi12NyIsInJlcXVlc3RfYmluZGlu"
        "ZyI6IklBNm93eVNjV1VYa2syaFlNQnZBZ28yZDlFZExTeFMzSndpbDFCRmxJclEifQ."
        "2TQ5sfwCOuoBII4Ytf8FJLCuYV-8Eo7ki3-FPmJWv04"
    )
    principal = verify_origin_principal(
        token,
        expected_binding=binding,
        environment=environment,
        now=2_000_000_000,
    )
    assert principal.mode is AccessMode.GUEST
    assert principal.session_id == "BAQEBAQEBAQEBAQEBAQEBA"
