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
import json
import os
import re
import secrets
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from roster_policy import (
    DUTY_SERVICE_TIME_WINDOWS,
    DutyPost,
    SchoolDay,
    is_chinese_display_name,
    is_room_open,
)

from nicegui_app.services.workflow_types import WorkflowError


SNAPSHOT_SCHEMA_VERSION = "sing-yin-public-roster-v1"
_AAD_PREFIX = "sing-yin-roster-share-v1:"
_HONG_KONG = ZoneInfo("Asia/Hong_Kong")
_SHARE_ID = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_MAX_RESPONSE_BYTES = 1_000_000

_DAYS: tuple[SchoolDay, ...] = (
    SchoolDay.MONDAY,
    SchoolDay.TUESDAY,
    SchoolDay.WEDNESDAY,
    SchoolDay.THURSDAY,
    SchoolDay.FRIDAY,
)
_DAY_LABELS: Mapping[SchoolDay, tuple[str, str]] = {
    SchoolDay.MONDAY: ("星期一", "Monday"),
    SchoolDay.TUESDAY: ("星期二", "Tuesday"),
    SchoolDay.WEDNESDAY: ("星期三", "Wednesday"),
    SchoolDay.THURSDAY: ("星期四", "Thursday"),
    SchoolDay.FRIDAY: ("星期五", "Friday"),
}
_POST_LABELS: Mapping[DutyPost, tuple[str, str]] = {
    DutyPost.ASSIST_IN_CHARGE: ("助理首席導學風紀當值", "Assist. in charge"),
    DutyPost.ROOM_302: ("302 室（溫習室）", "Room 302 (Study Room)"),
    DutyPost.ROOM_303: ("303 室（功課輔導）", "Room 303 (HW Completion)"),
    DutyPost.ROOM_202: ("202 室（中一溫習小組）", "Room 202 (F1 Study Group)"),
}
_ROW_LAYOUT: tuple[tuple[DutyPost, int], ...] = (
    (DutyPost.ASSIST_IN_CHARGE, 1),
    (DutyPost.ROOM_302, 1),
    (DutyPost.ROOM_303, 1),
    (DutyPost.ROOM_303, 2),
    (DutyPost.ROOM_202, 1),
    (DutyPost.ROOM_202, 2),
)


class PublicRosterShareError(WorkflowError):
    """A safe operator-facing failure at the public-sharing boundary."""


@dataclass(frozen=True)
class PublicRosterShareSettings:
    enabled: bool
    base_url: str
    admin_token: str
    timeout_seconds: float = 10.0

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
        return cls(
            enabled=enabled,
            base_url=os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_BASE_URL", "").strip().rstrip("/"),
            admin_token=os.getenv("SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN", "").strip(),
            timeout_seconds=timeout_seconds,
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
    ) -> None:
        self.settings = settings
        self._opener = opener

    def create(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        return self._request_json("POST", "/api/admin/shares", payload)

    def list(self) -> Sequence[Mapping[str, object]]:
        result = self._request_json("GET", "/api/admin/shares")
        shares = result.get("shares") if isinstance(result, dict) else None
        if not isinstance(shares, list) or not all(isinstance(item, dict) for item in shares):
            raise PublicRosterShareError("The public roster viewer returned an invalid share list.")
        return shares

    def revoke(self, share_id: str) -> None:
        _require_share_id(share_id)
        self._request_json("DELETE", f"/api/admin/shares/{share_id}")

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        self.settings.require_configured()
        endpoint = urljoin(f"{self.settings.base_url}/", path.lstrip("/"))
        parsed = urlparse(endpoint)
        base = urlparse(self.settings.base_url)
        if parsed.scheme != "https" or parsed.netloc != base.netloc:
            raise PublicRosterShareError("The public roster viewer address is invalid.")
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
        try:
            # The origin is administrator-configured, HTTPS-only, and checked above.
            with self._opener(request, timeout=self.settings.timeout_seconds) as response:  # nosec B310
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            if error.code in {401, 403}:
                raise PublicRosterShareError("The public roster viewer rejected its administrator credential.") from error
            raise PublicRosterShareError("The public roster viewer is temporarily unavailable.") from error
        except (TimeoutError, URLError, OSError) as error:
            raise PublicRosterShareError("The public roster viewer could not be reached. Try again later.") from error
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
    ) -> PublicRosterShareReceipt:
        self.settings.require_configured()
        snapshot = self._build_snapshot(roster_week_id)
        now = _as_utc(self._now())
        week_start = date.fromisoformat(str(snapshot["weekStart"]))
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
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
        created_at = now.replace(microsecond=0)
        normalized_expiry = normalized_expiry.replace(microsecond=0)
        gateway_receipt = self.gateway.create(
            {
                "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
                "shareId": share_id,
                "weekStart": week_start.isoformat(),
                "createdAt": _iso_z(created_at),
                "expiresAt": _iso_z(normalized_expiry),
                "nonce": _base64url(nonce),
                "ciphertext": _base64url(ciphertext),
            }
        )
        if gateway_receipt and gateway_receipt.get("createdAt") is not None:
            try:
                created_at = _parse_datetime(gateway_receipt["createdAt"])
            except (TypeError, ValueError) as error:
                raise PublicRosterShareError("The public roster viewer returned invalid share metadata.") from error
        share_url = f"{self.settings.base_url}/view#{share_id}.{_base64url(key)}"
        return PublicRosterShareReceipt(share_id, share_url, week_start, created_at, normalized_expiry)

    def list_shares(self) -> list[PublicRosterShareMetadata]:
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
        self.settings.require_configured()
        _require_share_id(share_id)
        self.gateway.revoke(share_id)

    def _build_snapshot(self, roster_week_id: int) -> dict[str, object]:
        week = self.workflow.roster_week(roster_week_id)
        if str(week.get("status")) != "published":
            raise PublicRosterShareError("Only a published roster can receive a public view link.")
        week_start = _coerce_date(week.get("weekStart"))
        assignments = self.workflow.assignments(roster_week_id)
        assignment_index: dict[tuple[str, str, int], Mapping[str, object]] = {}
        for item in assignments:
            if not isinstance(item, Mapping):
                raise PublicRosterShareError("The published roster contains an invalid assignment.")
            try:
                key = (str(item["day"]), str(item["postCode"]), int(item["slotIndex"]))
            except (KeyError, TypeError, ValueError) as error:
                raise PublicRosterShareError("The published roster contains an invalid assignment.") from error
            if key in assignment_index:
                raise PublicRosterShareError("The published roster contains a duplicate duty slot.")
            assignment_index[key] = item

        day_items = [
            {
                "code": day.name,
                "date": (week_start + timedelta(days=int(day))).isoformat(),
                "labelZh": _DAY_LABELS[day][0],
                "labelEn": _DAY_LABELS[day][1],
            }
            for day in _DAYS
        ]
        rows: list[dict[str, object]] = []
        for post, slot_index in _ROW_LAYOUT:
            start_time, end_time = DUTY_SERVICE_TIME_WINDOWS[post]
            cells: list[dict[str, str]] = []
            for day in _DAYS:
                if not is_room_open(post, day):
                    cells.append({"status": "closed"})
                    continue
                assignment = assignment_index.get((day.name, post.name, slot_index))
                if assignment is None:
                    raise PublicRosterShareError("The published roster is missing a required duty slot.")
                assignment_status = str(assignment.get("status"))
                if assignment_status == "vacant":
                    cells.append({"status": "vacant"})
                    continue
                if assignment_status not in {"active", "replaced"}:
                    raise PublicRosterShareError("The published roster contains an invalid assignment status.")
                name_zh = str(assignment.get("prefectName") or "").strip()
                if not is_chinese_display_name(name_zh):
                    raise PublicRosterShareError("Every name in a public roster must be a valid Chinese display name.")
                cells.append({"status": "assigned", "nameZh": name_zh})
            rows.append(
                {
                    "postCode": post.name,
                    "slotIndex": slot_index,
                    "labelZh": _POST_LABELS[post][0],
                    "labelEn": _POST_LABELS[post][1],
                    "dutyTime": {"start": start_time, "end": end_time},
                    "cells": cells,
                }
            )
        return {
            "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
            "schoolNameZh": "聖言中學",
            "schoolNameEn": "Sing Yin Secondary School",
            "titleZh": "導學風紀值班表",
            "titleEn": "Study Prefect Duty Roster",
            "weekStart": week_start.isoformat(),
            "version": int(week.get("version") or 1),
            "days": day_items,
            "rows": rows,
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
