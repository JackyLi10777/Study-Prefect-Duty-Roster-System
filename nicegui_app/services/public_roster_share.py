"""Encrypted, read-only publication of one approved weekly roster.

This module is an application/adapter boundary.  It deliberately consumes the
stable ``RosterWorkflow`` read API and sends only an encrypted, presentation-
ready snapshot to the public viewer.  Prefect identifiers, roles, leave data,
fairness data, audit records, and other operational state never cross this
boundary.
"""

from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
import re
import secrets
from time import monotonic, sleep
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from nicegui_app.access_context import AccessMode, Capability, CapabilityPolicy
from nicegui_app.services.workflow_types import WorkflowError
from nicegui_app.services.roster_presentation import (
    RosterPresentationError,
    build_roster_presentation,
)


SNAPSHOT_SCHEMA_VERSION = "sing-yin-public-roster-v1"
_AAD_PREFIX = "sing-yin-roster-share-v1:"
_HONG_KONG = ZoneInfo("Asia/Hong_Kong")
_SHARE_ID = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_CONTENT_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_MAX_RESPONSE_BYTES = 1_000_000
_VISIBILITY_POLL_SECONDS = 2.0

class PublicRosterShareError(WorkflowError):
    """A safe operator-facing failure at the public-sharing boundary."""


@dataclass(frozen=True)
class PublicRosterShareSettings:
    enabled: bool
    base_url: str
    admin_token: str
    timeout_seconds: float = 10.0
    visibility_timeout_seconds: float = 75.0

    @classmethod
    def from_environment(cls) -> "PublicRosterShareSettings":
        enabled = os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        raw_timeout = os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_TIMEOUT_SECONDS", "10").strip()
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError:
            timeout_seconds = 10.0
        raw_visibility_timeout = os.getenv(
            "SING_YIN_PUBLIC_ROSTER_VIEWER_VISIBILITY_TIMEOUT_SECONDS",
            "75",
        ).strip()
        try:
            visibility_timeout_seconds = float(raw_visibility_timeout)
        except ValueError:
            visibility_timeout_seconds = 75.0
        return cls(
            enabled=enabled,
            base_url=os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL", "").strip().rstrip("/"),
            admin_token=os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN", "").strip(),
            timeout_seconds=timeout_seconds,
            visibility_timeout_seconds=visibility_timeout_seconds,
        )

    @property
    def configured(self) -> bool:
        parsed = urlparse(self.base_url)
        return (
            self.enabled
            and parsed.scheme == "https"
            and bool(parsed.hostname)
            and len(self.admin_token) >= 32
            and 1 <= self.timeout_seconds <= 30
            and 5 <= self.visibility_timeout_seconds <= 120
        )

    def require_configured(self) -> None:
        if not self.enabled:
            raise PublicRosterShareError("Public roster viewing is not enabled on this computer.")
        if not self.configured:
            raise PublicRosterShareError("Public roster viewing needs administrator configuration before use.")


@dataclass(frozen=True)
class PublicRosterShareReceipt:
    share_id: str
    share_url: str
    week_start: date
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class PublicRosterShareMetadata:
    share_id: str
    roster_week_id: int | None
    week_start: date
    created_at: datetime
    expires_at: datetime


class PublicRosterShareGateway(Protocol):
    def create(self, payload: Mapping[str, object]) -> Mapping[str, object] | None: ...

    def list(self) -> Sequence[Mapping[str, object]]: ...

    def revoke(self, share_id: str) -> None: ...


class CloudflarePublicRosterShareGateway:
    """Authenticated HTTP adapter for the Cloudflare Worker/KV outer layer."""

    def __init__(
        self,
        settings: PublicRosterShareSettings,
        *,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = sleep,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.settings = settings
        self._opener = opener
        self._sleep = sleeper
        self._clock = clock

    def create(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        share_id = str(payload.get("shareId") or "")
        _require_share_id(share_id)
        result = self._request_json("POST", "/api/admin/shares", payload)
        exact_digest: str | None = None
        try:
            returned_digest = result.get("contentDigest")
            if returned_digest is not None:
                exact_digest = str(returned_digest)
                if not _CONTENT_DIGEST.fullmatch(exact_digest):
                    exact_digest = None
                    raise PublicRosterShareError(
                        "The public roster viewer returned invalid share metadata."
                    )
            returned_share_id = result.get("shareId")
            if returned_share_id is not None and returned_share_id != share_id:
                raise PublicRosterShareError(
                    "The public roster viewer returned invalid share metadata."
                )
            if result.get("createdAt") is not None:
                try:
                    _parse_datetime(result["createdAt"])
                except (TypeError, ValueError) as error:
                    raise PublicRosterShareError(
                        "The public roster viewer returned invalid share metadata."
                    ) from error
            if self._wait_until_visible(share_id, payload):
                return result
        except PublicRosterShareError:
            self._request_best_effort_withdrawal(share_id, exact_digest)
            raise

        withdrawal_requested = self._request_best_effort_withdrawal(share_id, exact_digest)
        if withdrawal_requested:
            raise PublicRosterShareError(
                "The encrypted roster link did not become readable in time. "
                "No decryption key was issued, and a withdrawal request was sent. "
                "Check the access console before trying again."
            )
        raise PublicRosterShareError(
            "The encrypted roster link did not become readable in time, and no decryption key was issued. "
            "Check the access console and revoke it before trying again."
        )

    def _request_best_effort_withdrawal(
        self,
        share_id: str,
        content_digest: str | None,
    ) -> bool:
        path = f"/api/admin/shares/{share_id}"
        if content_digest is not None and _CONTENT_DIGEST.fullmatch(content_digest):
            path = f"{path}?contentDigest={content_digest}"
        try:
            self._request_json("DELETE", path)
        except PublicRosterShareError:
            return False
        return True

    def list(self) -> Sequence[Mapping[str, object]]:
        result = self._request_json("GET", "/api/admin/shares")
        shares = result.get("shares") if isinstance(result, dict) else None
        if not isinstance(shares, list) or not all(isinstance(item, dict) for item in shares):
            raise PublicRosterShareError("The public roster viewer returned an invalid share list.")
        return shares

    def revoke(self, share_id: str) -> None:
        _require_share_id(share_id)
        self._request_json("DELETE", f"/api/admin/shares/{share_id}")

    def _wait_until_visible(
        self,
        share_id: str,
        expected: Mapping[str, object],
    ) -> bool:
        deadline = self._clock() + self.settings.visibility_timeout_seconds
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                return False
            visible = self._request_public_share(
                share_id,
                timeout_seconds=min(self.settings.timeout_seconds, remaining),
            )
            if visible is not None:
                try:
                    same_expiry = _parse_datetime(visible.get("expiresAt")) == _parse_datetime(
                        expected.get("expiresAt")
                    )
                except (TypeError, ValueError, PublicRosterShareError):
                    same_expiry = False
                if (
                    visible.get("schemaVersion") != SNAPSHOT_SCHEMA_VERSION
                    or visible.get("ciphertext") != expected.get("ciphertext")
                    or visible.get("nonce") != expected.get("nonce")
                    or not same_expiry
                ):
                    raise PublicRosterShareError(
                        "The public roster viewer returned an unexpected encrypted share."
                    )
                return True
            remaining = deadline - self._clock()
            if remaining > 0:
                self._sleep(min(_VISIBILITY_POLL_SECONDS, remaining))

    def _request_public_share(
        self,
        share_id: str,
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object] | None:
        self.settings.require_configured()
        endpoint = self._validated_endpoint("/api/view")
        body = json.dumps(
            {"shareId": share_id},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Sing-Yin-Roster/1.0",
            },
        )
        try:
            with self._opener(request, timeout=timeout_seconds) as response:  # nosec B310
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            if error.code == 404 or error.code == 429 or 500 <= error.code <= 599:
                return None
            if error.code in {401, 403}:
                raise PublicRosterShareError(
                    "The public roster viewer is not accepting public share checks."
                ) from error
            raise PublicRosterShareError("The public roster viewer is temporarily unavailable.") from error
        except (TimeoutError, URLError, OSError):
            return None
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise PublicRosterShareError("The public roster viewer returned an unexpectedly large response.")
        try:
            parsed_payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PublicRosterShareError("The public roster viewer returned an invalid response.") from error
        if not isinstance(parsed_payload, dict):
            raise PublicRosterShareError("The public roster viewer returned an invalid response.")
        return parsed_payload

    def _validated_endpoint(self, path: str) -> str:
        endpoint = urljoin(f"{self.settings.base_url}/", path.lstrip("/"))
        parsed = urlparse(endpoint)
        base = urlparse(self.settings.base_url)
        if parsed.scheme != "https" or parsed.netloc != base.netloc:
            raise PublicRosterShareError("The public roster viewer address is invalid.")
        return endpoint

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        self.settings.require_configured()
        endpoint = self._validated_endpoint(path)
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.settings.admin_token}",
                "Content-Type": "application/json",
                "User-Agent": "Sing-Yin-Roster/1.0",
            },
        )
        attempts = 2 if method == "POST" and body is not None else 1
        raw = b""
        for attempt in range(attempts):
            try:
                # The origin is administrator-configured, HTTPS-only, and checked above.
                # A create request may be replayed once with the exact same encrypted body.
                # The Worker treats that replay as idempotent, covering a committed write
                # whose HTTP response was lost in transit.
                with self._opener(request, timeout=self.settings.timeout_seconds) as response:  # nosec B310
                    raw = response.read(_MAX_RESPONSE_BYTES + 1)
                break
            except HTTPError as error:
                if error.code in {401, 403}:
                    raise PublicRosterShareError(
                        "The public roster viewer rejected its administrator credential."
                    ) from error
                raise PublicRosterShareError("The public roster viewer is temporarily unavailable.") from error
            except (TimeoutError, URLError, OSError) as error:
                if attempt + 1 < attempts:
                    continue
                raise PublicRosterShareError(
                    "The public roster viewer could not be reached. Try again later."
                ) from error
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise PublicRosterShareError("The public roster viewer returned an unexpectedly large response.")
        if not raw:
            return {}
        try:
            parsed_payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PublicRosterShareError("The public roster viewer returned an invalid response.") from error
        if not isinstance(parsed_payload, dict):
            raise PublicRosterShareError("The public roster viewer returned an invalid response.")
        return parsed_payload


class PublicRosterShareService:
    """Build, encrypt, publish, list, and revoke minimum-data roster shares."""

    def __init__(
        self,
        workflow: Any,
        *,
        settings: PublicRosterShareSettings | None = None,
        gateway: PublicRosterShareGateway | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.workflow = workflow
        self.settings = settings or PublicRosterShareSettings.from_environment()
        self.gateway = gateway or CloudflarePublicRosterShareGateway(self.settings)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def create_share(
        self,
        roster_week_id: int,
        *,
        expires_at: datetime | None = None,
        command_id: str | None = None,
    ) -> PublicRosterShareReceipt:
        self._require_external_delivery()
        self.settings.require_configured()
        snapshot = self._build_snapshot(roster_week_id)
        now = _as_utc(self._now())
        week_start = date.fromisoformat(str(snapshot["weekStart"]))
        roster_version = int(snapshot["version"])
        normalized_expiry = _as_utc(expires_at) if expires_at else _default_expiry(week_start, now)
        if normalized_expiry <= now + timedelta(minutes=1):
            raise PublicRosterShareError("The public roster link expiry must be in the future.")
        if normalized_expiry > now + timedelta(days=31):
            raise PublicRosterShareError("Public roster links may remain active for at most 31 days.")

        share_id = secrets.token_urlsafe(18)
        key = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        aad = f"{_AAD_PREFIX}{share_id}".encode("utf-8")
        plaintext = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        content_digest = hashlib.sha256(plaintext).hexdigest()
        normalized_expiry_text = _iso_z(normalized_expiry.replace(microsecond=0))
        operation_id = command_id
        if operation_id is None:
            operation_id = self.workflow.retryable_external_share_command(
                roster_week_id=roster_week_id,
                roster_version=roster_version,
                content_digest=content_digest,
                expires_at=normalized_expiry_text,
            )
        operation_id = operation_id or f"public-share:{secrets.token_hex(16)}"
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
        created_at = now.replace(microsecond=0)
        normalized_expiry = normalized_expiry.replace(microsecond=0)
        delivery_payload = {
            "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
            "shareId": share_id,
            "weekStart": week_start.isoformat(),
            "createdAt": _iso_z(created_at),
            "expiresAt": normalized_expiry_text,
            "nonce": _base64url(nonce),
            "ciphertext": _base64url(ciphertext),
        }
        receipt_metadata = {
            "shareId": share_id,
            "weekStart": week_start.isoformat(),
            "createdAt": _iso_z(created_at),
            "expiresAt": normalized_expiry_text,
        }
        queued = self.workflow.queue_external_share(
            command_id=operation_id,
            roster_week_id=roster_week_id,
            roster_version=roster_version,
            content_digest=content_digest,
            share_id=share_id,
            delivery_payload=delivery_payload,
            share_key=_base64url(key),
            receipt_metadata=receipt_metadata,
        )
        if queued.get("outboxStatus") == "delivered":
            raise PublicRosterShareError(
                "This public-share request was already delivered. "
                "Its decryption key is no longer stored; revoke it or create a new link."
            )
        delivery = self.workflow.begin_external_share_delivery(command_id=operation_id)
        if delivery.get("outboxStatus") == "delivered":
            raise PublicRosterShareError(
                "This public-share request was already delivered. "
                "Its decryption key is no longer stored; revoke it or create a new link."
            )
        persisted_payload = delivery.get("deliveryPayload")
        persisted_receipt = delivery.get("receipt")
        persisted_key = str(delivery.get("shareKey") or "")
        if (
            not isinstance(persisted_payload, dict)
            or not isinstance(persisted_receipt, dict)
            or not persisted_key
        ):
            self.workflow.fail_external_share_delivery(
                command_id=operation_id,
                error_code="invalid_persisted_envelope",
            )
            raise PublicRosterShareError("The queued public-share delivery envelope is invalid.")

        try:
            gateway_receipt = self.gateway.create(persisted_payload)
        except Exception as error:
            self.workflow.fail_external_share_delivery(
                command_id=operation_id,
                error_code=type(error).__name__,
            )
            raise
        if gateway_receipt and gateway_receipt.get("createdAt") is not None:
            try:
                created_at = _parse_datetime(gateway_receipt["createdAt"])
            except (TypeError, ValueError) as error:
                self.workflow.fail_external_share_delivery(
                    command_id=operation_id,
                    error_code="invalid_gateway_receipt",
                )
                raise PublicRosterShareError("The public roster viewer returned invalid share metadata.") from error
        share_id = str(persisted_receipt["shareId"])
        week_start = date.fromisoformat(str(persisted_receipt["weekStart"]))
        normalized_expiry = _parse_datetime(persisted_receipt["expiresAt"])
        share_url = f"{self.settings.base_url}/view#{share_id}.{persisted_key}"
        self.workflow.complete_external_share_delivery(
            command_id=operation_id,
            delivered_receipt={
                "shareId": share_id,
                "shareUrl": share_url,
                "weekStart": week_start.isoformat(),
                "createdAt": _iso_z(created_at),
                "expiresAt": _iso_z(normalized_expiry),
            },
        )
        return PublicRosterShareReceipt(
            share_id,
            share_url,
            week_start,
            created_at,
            normalized_expiry,
        )

    def list_shares(self) -> list[PublicRosterShareMetadata]:
        self._require_external_delivery()
        self.settings.require_configured()
        local_weeks = {
            _coerce_date(item.get("weekStart")): int(item["id"])
            for item in self.workflow.roster_weeks()
            if isinstance(item, Mapping) and item.get("id") is not None and item.get("weekStart") is not None
        }
        shares: list[PublicRosterShareMetadata] = []
        for item in self.gateway.list():
            try:
                share_id = str(item["shareId"])
                _require_share_id(share_id)
                week_start = _coerce_date(item["weekStart"])
                created_at = _parse_datetime(item["createdAt"])
                expires_at = _parse_datetime(item["expiresAt"])
            except (KeyError, TypeError, ValueError) as error:
                raise PublicRosterShareError("The public roster viewer returned invalid share metadata.") from error
            shares.append(
                PublicRosterShareMetadata(
                    share_id=share_id,
                    roster_week_id=local_weeks.get(week_start),
                    week_start=week_start,
                    created_at=created_at,
                    expires_at=expires_at,
                )
            )
        return sorted(shares, key=lambda item: item.created_at, reverse=True)

    def revoke_share(self, share_id: str) -> None:
        self._require_external_delivery()
        self.settings.require_configured()
        _require_share_id(share_id)
        self.gateway.revoke(share_id)

    def _require_external_delivery(self) -> None:
        """Reject guest/public adapters even when a caller bypasses the UI."""

        raw_mode = getattr(self.workflow, "access_mode", None)
        if raw_mode is None:
            # Direct RosterWorkflow use is reserved for trusted local scripts
            # and tests. Browser requests are always wrapped in a verified
            # PageContextWorkflowAdapter.
            return
        try:
            mode = raw_mode if isinstance(raw_mode, AccessMode) else AccessMode(str(raw_mode))
        except ValueError as error:
            raise PublicRosterShareError("The public-share access mode is invalid.") from error
        CapabilityPolicy.require(mode, Capability.EXTERNAL_DELIVERY)

    def _build_snapshot(self, roster_week_id: int) -> dict[str, object]:
        week, assignments = self.workflow.roster_schedule_snapshot(roster_week_id)
        if str(week.get("status")) != "published":
            raise PublicRosterShareError("Only a published roster can receive a public view link.")
        try:
            public_matrix = build_roster_presentation(
                week,
                assignments,
                editable=False,
                strict=True,
            ).to_public_dict()
        except RosterPresentationError as error:
            raise PublicRosterShareError(str(error)) from error
        return {
            "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
            "schoolNameZh": "聖言中學",
            "schoolNameEn": "Sing Yin Secondary School",
            "titleZh": "導學風紀值班表",
            "titleEn": "Study Prefect Duty Roster",
            **public_matrix,
        }


def _default_expiry(week_start: date, now: datetime) -> datetime:
    end_of_roster_week = datetime.combine(week_start + timedelta(days=6), time(23, 59, 59), tzinfo=_HONG_KONG)
    expiry = end_of_roster_week.astimezone(timezone.utc)
    return expiry if expiry > now + timedelta(minutes=1) else now + timedelta(hours=24)


def _as_utc(value: datetime | None) -> datetime:
    if value is None or value.tzinfo is None or value.utcoffset() is None:
        raise PublicRosterShareError("Public roster link times must include a time zone.")
    return value.astimezone(timezone.utc)


def _parse_datetime(value: object) -> datetime:
    candidate = str(value).replace("Z", "+00:00")
    return _as_utc(datetime.fromisoformat(candidate))


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _require_share_id(value: str) -> None:
    if not _SHARE_ID.fullmatch(value):
        raise PublicRosterShareError("The public roster share identifier is invalid.")


def _base64url(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _iso_z(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
