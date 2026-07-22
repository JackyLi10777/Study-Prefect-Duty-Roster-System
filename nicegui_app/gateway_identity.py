"""Verification of the Cloudflare gateway's short-lived origin principal."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import re
from typing import Any, Mapping, Protocol

from nicegui_app.access_context import AccessMode, Principal


ORIGIN_PRINCIPAL_HEADER = "x-sing-yin-origin-principal"
ORIGIN_PRINCIPAL_AUDIENCE = "sing-yin-roster-origin"
ORIGIN_PRINCIPAL_VERSION = 1
ORIGIN_PRINCIPAL_MAX_BYTES = 4_096
ORIGIN_PRINCIPAL_FRESHNESS_SECONDS = 60
GUEST_SESSION_MAX_SECONDS = 30 * 60
ADMIN_SESSION_MAX_SECONDS = 8 * 60 * 60
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{22}$")
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_E2E_RUN_ID_PATTERN = re.compile(r"^E2E-[A-F0-9]{12}$")


class OriginPrincipalError(PermissionError):
    """A principal is missing, malformed, stale, revoked, or forged."""


class _RequestURL(Protocol):
    netloc: str
    path: str
    query: str


class OriginRequest(Protocol):
    method: str
    headers: Mapping[str, str]
    url: _RequestURL


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))
    except (ValueError, TypeError) as error:
        raise OriginPrincipalError("origin principal encoding is invalid") from error


def _required_secret(environment: Mapping[str, str]) -> bytes:
    secret = environment.get("ORIGIN_PRINCIPAL_SECRET", "")
    if not isinstance(secret, str) or secret != secret.strip() or not 32 <= len(secret) <= 512:
        raise OriginPrincipalError("origin principal secret is not configured safely")
    return secret.encode("utf-8")


def configured_auth_epoch(environment: Mapping[str, str]) -> int:
    raw = environment.get("AUTH_EPOCH", "1")
    if not isinstance(raw, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", raw):
        raise OriginPrincipalError("auth epoch is invalid")
    epoch = int(raw)
    if not 1 <= epoch <= 2_147_483_647:
        raise OriginPrincipalError("auth epoch is invalid")
    return epoch


def configured_key_id(environment: Mapping[str, str]) -> str:
    key_id = environment.get("ORIGIN_PRINCIPAL_KID", "origin-v1")
    if not isinstance(key_id, str) or key_id != key_id.strip() or not _KEY_ID_PATTERN.fullmatch(key_id):
        raise OriginPrincipalError("origin principal key id is invalid")
    return key_id


def origin_request_binding(*, method: str, public_host: str, path_and_query: str) -> str:
    material = "\n".join((method.upper(), public_host.lower(), path_and_query))
    return _b64encode(hashlib.sha256(material.encode("utf-8")).digest())


def request_binding_for(request: OriginRequest) -> str:
    public_host = request.headers.get("x-forwarded-host", "") or request.url.netloc
    path_and_query = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return origin_request_binding(
        method=request.method,
        public_host=public_host,
        path_and_query=path_and_query,
    )


def verify_origin_principal(
    token: str,
    *,
    expected_binding: str,
    environment: Mapping[str, str] | None = None,
    now: int | None = None,
) -> Principal:
    env = os.environ if environment is None else environment
    if not isinstance(token, str) or not 32 <= len(token.encode("utf-8")) <= ORIGIN_PRINCIPAL_MAX_BYTES:
        raise OriginPrincipalError("origin principal is malformed")
    parts = token.split(".")
    if len(parts) != 2 or not all(parts):
        raise OriginPrincipalError("origin principal is malformed")
    payload_segment, signature_segment = parts
    try:
        signature = _b64decode(signature_segment)
        payload_bytes = _b64decode(payload_segment)
    except OriginPrincipalError:
        raise
    if len(signature) != 32 or not 2 <= len(payload_bytes) <= 2_048:
        raise OriginPrincipalError("origin principal is malformed")
    expected_signature = hmac.new(
        _required_secret(env),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_signature, signature):
        raise OriginPrincipalError("origin principal signature is invalid")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OriginPrincipalError("origin principal payload is invalid") from error
    required = {
        "v",
        "aud",
        "mode",
        "subject",
        "sid",
        "iat",
        "exp",
        "auth_epoch",
        "kid",
        "request_binding",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise OriginPrincipalError("origin principal payload shape is invalid")
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else int(now)
    mode_value = payload["mode"]
    try:
        mode = AccessMode(mode_value)
    except (TypeError, ValueError) as error:
        raise OriginPrincipalError("origin principal mode is invalid") from error
    if mode not in {AccessMode.ADMIN, AccessMode.GUEST}:
        raise OriginPrincipalError("origin principal mode is invalid")
    maximum_session = GUEST_SESSION_MAX_SECONDS if mode is AccessMode.GUEST else ADMIN_SESSION_MAX_SECONDS
    if (
        payload["v"] != ORIGIN_PRINCIPAL_VERSION
        or payload["aud"] != ORIGIN_PRINCIPAL_AUDIENCE
        or not isinstance(payload["subject"], str)
        or not payload["subject"]
        or len(payload["subject"]) > 320
        or not isinstance(payload["sid"], str)
        or not _SESSION_ID_PATTERN.fullmatch(payload["sid"])
        or type(payload["iat"]) is not int
        or type(payload["exp"]) is not int
        or payload["iat"] > current + ORIGIN_PRINCIPAL_FRESHNESS_SECONDS
        or payload["iat"] < current - ORIGIN_PRINCIPAL_FRESHNESS_SECONDS
        or payload["exp"] <= current
        or payload["exp"] <= payload["iat"]
        or payload["exp"] - payload["iat"] > maximum_session
        or payload["auth_epoch"] != configured_auth_epoch(env)
        or payload["kid"] != configured_key_id(env)
        or not hmac.compare_digest(str(payload["request_binding"]), expected_binding)
    ):
        raise OriginPrincipalError("origin principal is stale, revoked, or bound to another request")
    return Principal(
        mode=mode,
        subject=payload["subject"],
        session_id=payload["sid"],
        expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
        auth_epoch=payload["auth_epoch"],
        key_id=payload["kid"],
    )


def principal_from_request(
    request: OriginRequest | None,
    *,
    environment: Mapping[str, str] | None = None,
    now: int | None = None,
) -> Principal:
    """Resolve a signed remote principal or an explicitly local principal."""

    env = os.environ if environment is None else environment
    token = request.headers.get(ORIGIN_PRINCIPAL_HEADER, "") if request is not None else ""
    if token:
        return verify_origin_principal(
            token,
            expected_binding=request_binding_for(request),
            environment=env,
            now=now,
        )
    e2e_mode = env.get("SING_YIN_E2E_ACCESS_MODE", "").strip().lower()
    e2e_run_id = env.get("SING_YIN_E2E_RUN_ID", "").strip()
    if (
        env.get("SING_YIN_E2E_ISOLATED") == "1"
        and _E2E_RUN_ID_PATTERN.fullmatch(e2e_run_id)
        and e2e_mode == AccessMode.GUEST.value
    ):
        current = int(datetime.now(timezone.utc).timestamp()) if now is None else int(now)
        session_id = _b64encode(
            hashlib.sha256(f"{e2e_run_id}\0guest".encode("utf-8")).digest()
        )[:22]
        return Principal(
            mode=AccessMode.GUEST,
            subject=f"guest-e2e:{e2e_run_id}",
            session_id=session_id,
            expires_at=datetime.fromtimestamp(current + GUEST_SESSION_MAX_SECONDS, timezone.utc),
            auth_epoch=configured_auth_epoch(env),
            key_id=configured_key_id(env),
        )
    require_gateway = env.get("SING_YIN_REQUIRE_GATEWAY_PRINCIPAL", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if require_gateway:
        raise OriginPrincipalError("a verified gateway principal is required")
    local_maintenance = env.get("SING_YIN_LOCAL_MAINTENANCE", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not local_maintenance:
        raise OriginPrincipalError(
            "an explicit local-maintenance mode or verified gateway principal is required"
        )
    return Principal(mode=AccessMode.LOCAL_MAINTENANCE, subject="local-console")


def seal_origin_principal_for_test(
    payload: Mapping[str, Any],
    *,
    environment: Mapping[str, str],
) -> str:
    """Build a deterministic test token without weakening production parsing."""

    payload_segment = _b64encode(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signature = hmac.new(
        _required_secret(environment),
        payload_segment.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_segment}.{_b64encode(signature)}"


__all__ = [
    "ADMIN_SESSION_MAX_SECONDS",
    "GUEST_SESSION_MAX_SECONDS",
    "ORIGIN_PRINCIPAL_AUDIENCE",
    "ORIGIN_PRINCIPAL_HEADER",
    "ORIGIN_PRINCIPAL_VERSION",
    "OriginPrincipalError",
    "configured_auth_epoch",
    "configured_key_id",
    "origin_request_binding",
    "principal_from_request",
    "request_binding_for",
    "seal_origin_principal_for_test",
    "verify_origin_principal",
]
