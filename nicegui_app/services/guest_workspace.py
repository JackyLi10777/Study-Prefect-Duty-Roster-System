"""Bounded, memory-only workspaces for the unified guest experience.

The service intentionally depends only on the Python standard library.  Guest
state never touches the official database, backups, files, network, AI
providers, background jobs, or analytics.
"""

from __future__ import annotations

import base64
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
import secrets
from threading import RLock
from typing import Any, Callable, Mapping


SNAPSHOT_SCHEMA_VERSION = 1
DEMO_FIXTURE_VERSION = "2026.1"
DEFAULT_TTL_SECONDS = 30 * 60
DEFAULT_MAX_SESSIONS = 24
DEFAULT_MAX_TABS_PER_SESSION = 4
DEFAULT_MAX_PREFECTS = 40
DEFAULT_MAX_WEEKS = 4
DEFAULT_MAX_SNAPSHOT_BYTES = 256 * 1024
DEFAULT_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_COMMANDS_PER_MINUTE = 60


class GuestWorkspaceError(ValueError):
    """Base class for a rejected guest-workspace operation."""


class GuestSnapshotError(GuestWorkspaceError):
    """A client-held snapshot failed integrity, binding, or expiry checks."""


class GuestCapacityError(GuestWorkspaceError):
    """The bounded guest service cannot accept more temporary work."""


class GuestRevisionConflict(GuestWorkspaceError):
    """Another command changed the same temporary workspace first."""


class GuestRateLimitError(GuestWorkspaceError):
    """One guest tab exceeded its short, in-memory command budget."""


def _unix_now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise GuestSnapshotError("snapshot encoding is invalid")
    try:
        return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))
    except (ValueError, TypeError) as error:
        raise GuestSnapshotError("snapshot encoding is invalid") from error


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise GuestWorkspaceError("guest state must contain JSON values only") from error


def _json_copy(value: object) -> Any:
    return json.loads(_canonical_bytes(value).decode("utf-8"))


def demo_fixture() -> dict[str, Any]:
    """Return a fresh fictional, Traditional-Chinese-first demo workspace."""

    assistants = (
        ("demo-ahp-01", "陳樂言"),
        ("demo-ahp-02", "林頌恩"),
        ("demo-ahp-03", "黃善行"),
        ("demo-ahp-04", "李思澄"),
        ("demo-ahp-05", "何頌謙"),
        ("demo-ahp-06", "周恩言"),
    )
    prefects = (
        ("demo-sp-01", "張樂晴"),
        ("demo-sp-02", "郭善恩"),
        ("demo-sp-03", "謝頌賢"),
        ("demo-sp-04", "鄭思朗"),
        ("demo-sp-05", "梁樂謙"),
        ("demo-sp-06", "吳善晴"),
        ("demo-sp-07", "許頌言"),
        ("demo-sp-08", "馬思賢"),
        ("demo-sp-09", "杜樂恩"),
        ("demo-sp-10", "葉善澄"),
        ("demo-sp-11", "馮頌朗"),
        ("demo-sp-12", "羅思言"),
    )
    people = [
        {
            "id": identifier,
            "nameZh": name,
            "role": "assistant_head",
            "form": "F.5",
            "className": f"5{chr(65 + index)}",
            "availableDays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
            "historyWeight": float(index % 3),
            "historyDuties": index % 3,
            "fictional": True,
        }
        for index, (identifier, name) in enumerate(assistants)
    ]
    people.extend(
        {
            "id": identifier,
            "nameZh": name,
            "role": "study_prefect",
            "form": "F.4",
            "className": f"4{chr(65 + (index % 5))}",
            "availableDays": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
            "historyWeight": float(index % 5) / 2,
            "historyDuties": index % 4,
            "fictional": True,
        }
        for index, (identifier, name) in enumerate(prefects)
    )
    return {
        "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
        "fixtureVersion": DEMO_FIXTURE_VERSION,
        "fictional": True,
        "prefects": people,
        "weeks": [],
        "preGenerationLeave": [],
        "fairnessEvents": [],
        "preferences": {
            "language": "zh-HK",
            "theme": "light",
            "musicEnabled": False,
        },
    }


@dataclass(frozen=True)
class GuestSnapshot:
    schema_version: int
    boot_id: str
    session_id: str
    workspace_id: str
    tab_id: str
    revision: int
    issued_at: int
    expires_at: int
    state: dict[str, Any]


class GuestSnapshotCodec:
    """HMAC-seal client-held JSON and bind it to one boot/session/tab."""

    def __init__(
        self,
        secret: bytes | str,
        *,
        boot_id: str | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        clock: Callable[[], int] = _unix_now,
    ) -> None:
        secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        if len(secret_bytes) < 32:
            raise ValueError("guest snapshot secret must be at least 32 bytes")
        if ttl_seconds <= 0 or max_bytes <= 0:
            raise ValueError("guest snapshot limits must be positive")
        self._secret = secret_bytes
        self.boot_id = boot_id or secrets.token_urlsafe(18)
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self._clock = clock

    def seal(
        self,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        revision: int,
        state: Mapping[str, Any],
        expires_at: int | None = None,
        now: int | None = None,
    ) -> str:
        issued_at = self._clock() if now is None else int(now)
        expiry = issued_at + self.ttl_seconds if expires_at is None else int(expires_at)
        if (
            type(revision) is not int
            or revision < 0
            or expiry <= issued_at
            or expiry - issued_at > self.ttl_seconds
        ):
            raise GuestSnapshotError("snapshot revision or expiry is invalid")
        self._require_binding(session_id, workspace_id, tab_id)
        payload = {
            "bootId": self.boot_id,
            "exp": expiry,
            "iat": issued_at,
            "revision": revision,
            "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
            "sid": session_id,
            "state": _json_copy(dict(state)),
            "tabId": tab_id,
            "workspaceId": workspace_id,
        }
        encoded_payload = _b64encode(_canonical_bytes(payload))
        signature = _b64encode(hmac.new(self._secret, encoded_payload.encode("ascii"), hashlib.sha256).digest())
        token = f"{encoded_payload}.{signature}"
        if len(token.encode("utf-8")) > self.max_bytes:
            raise GuestSnapshotError("snapshot exceeds the guest size limit")
        return token

    def open(
        self,
        token: str,
        *,
        expected_session_id: str,
        expected_workspace_id: str,
        expected_tab_id: str,
        minimum_revision: int | None = None,
        now: int | None = None,
    ) -> GuestSnapshot:
        if not isinstance(token, str) or len(token.encode("utf-8")) > self.max_bytes:
            raise GuestSnapshotError("snapshot exceeds the guest size limit")
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
        except ValueError as error:
            raise GuestSnapshotError("snapshot shape is invalid") from error
        try:
            signature_input = encoded_payload.encode("ascii")
        except UnicodeEncodeError as error:
            raise GuestSnapshotError("snapshot encoding is invalid") from error
        expected_signature = hmac.new(self._secret, signature_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_signature, _b64decode(encoded_signature)):
            raise GuestSnapshotError("snapshot signature is invalid")
        try:
            payload = json.loads(_b64decode(encoded_payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GuestSnapshotError("snapshot payload is invalid") from error
        required = {
            "bootId",
            "exp",
            "iat",
            "revision",
            "schemaVersion",
            "sid",
            "state",
            "tabId",
            "workspaceId",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise GuestSnapshotError("snapshot payload shape is invalid")
        if type(payload["schemaVersion"]) is not int or payload["schemaVersion"] != SNAPSHOT_SCHEMA_VERSION:
            raise GuestSnapshotError("snapshot schema is unsupported")
        if payload["bootId"] != self.boot_id:
            raise GuestSnapshotError("snapshot belongs to an earlier application boot")
        if (
            payload["sid"] != expected_session_id
            or payload["workspaceId"] != expected_workspace_id
            or payload["tabId"] != expected_tab_id
        ):
            raise GuestSnapshotError("snapshot identity binding does not match")
        current = self._clock() if now is None else int(now)
        if type(payload["iat"]) is not int or type(payload["exp"]) is not int:
            raise GuestSnapshotError("snapshot timestamps are invalid")
        if payload["iat"] > current + 30 or payload["exp"] <= current:
            raise GuestSnapshotError("snapshot has expired or is not active")
        if payload["exp"] - payload["iat"] > self.ttl_seconds:
            raise GuestSnapshotError("snapshot lifetime exceeds the guest limit")
        revision = payload["revision"]
        if type(revision) is not int or revision < 0:
            raise GuestSnapshotError("snapshot revision is invalid")
        if minimum_revision is not None and revision < minimum_revision:
            raise GuestSnapshotError("snapshot revision is stale")
        if not isinstance(payload["state"], dict):
            raise GuestSnapshotError("snapshot state must be an object")
        return GuestSnapshot(
            schema_version=payload["schemaVersion"],
            boot_id=payload["bootId"],
            session_id=payload["sid"],
            workspace_id=payload["workspaceId"],
            tab_id=payload["tabId"],
            revision=revision,
            issued_at=payload["iat"],
            expires_at=payload["exp"],
            state=_json_copy(payload["state"]),
        )

    @staticmethod
    def _require_binding(session_id: str, workspace_id: str, tab_id: str) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (session_id, workspace_id, tab_id)):
            raise GuestSnapshotError("snapshot identity binding is incomplete")


@dataclass(frozen=True)
class GuestWorkspaceView:
    session_id: str
    workspace_id: str
    tab_id: str
    revision: int
    expires_at: int
    state: dict[str, Any]


@dataclass(frozen=True)
class GuestDownload:
    filename: str
    content: bytes
    media_type: str
    cache_control: str = "no-store, max-age=0"


@dataclass
class _CommandReceipt:
    payload_digest: str
    view: GuestWorkspaceView


@dataclass
class _WorkspaceRecord:
    workspace_id: str
    tab_id: str
    revision: int
    expires_at: int
    state: dict[str, Any]
    commands: dict[str, _CommandReceipt] = field(default_factory=dict)


@dataclass
class _SessionRecord:
    expires_at: int
    workspaces: dict[str, _WorkspaceRecord] = field(default_factory=dict)
    command_times: deque[int] = field(default_factory=deque)


class GuestWorkspaceRegistry:
    """Thread-safe registry with isolated state and strict resource bounds."""

    def __init__(
        self,
        secret: bytes | str,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
        max_tabs_per_session: int = DEFAULT_MAX_TABS_PER_SESSION,
        max_prefects: int = DEFAULT_MAX_PREFECTS,
        max_weeks: int = DEFAULT_MAX_WEEKS,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
        max_commands_per_minute: int = DEFAULT_MAX_COMMANDS_PER_MINUTE,
        clock: Callable[[], int] = _unix_now,
        boot_id: str | None = None,
    ) -> None:
        limits = (
            ttl_seconds,
            max_sessions,
            max_tabs_per_session,
            max_prefects,
            max_weeks,
            max_snapshot_bytes,
            max_download_bytes,
            max_commands_per_minute,
        )
        if any(limit <= 0 for limit in limits):
            raise ValueError("guest workspace limits must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self.max_tabs_per_session = max_tabs_per_session
        self.max_prefects = max_prefects
        self.max_weeks = max_weeks
        self.max_download_bytes = max_download_bytes
        self.max_commands_per_minute = max_commands_per_minute
        self._clock = clock
        self.codec = GuestSnapshotCodec(
            secret,
            boot_id=boot_id,
            ttl_seconds=ttl_seconds,
            max_bytes=max_snapshot_bytes,
            clock=clock,
        )
        # Leave enough room for the signed envelope and base64 expansion so
        # every accepted state is also sealable into the advertised limit.
        self.max_state_bytes = max(1, ((max_snapshot_bytes - 1_024) * 3) // 4)
        self._sessions: dict[str, _SessionRecord] = {}
        self._lock = RLock()

    def create_workspace(
        self,
        *,
        session_id: str,
        tab_id: str,
        workspace_id: str | None = None,
        now: int | None = None,
    ) -> GuestWorkspaceView:
        current = self._now(now)
        self.codec._require_binding(session_id, workspace_id or "pending", tab_id)
        with self._lock:
            self._purge_expired_locked(current)
            session = self._sessions.get(session_id)
            if session is None:
                if len(self._sessions) >= self.max_sessions:
                    raise GuestCapacityError("guest session capacity is full")
                session = _SessionRecord(expires_at=current + self.ttl_seconds)
                self._sessions[session_id] = session
            for record in session.workspaces.values():
                if record.tab_id == tab_id:
                    return self._view(session_id, record)
            if len(session.workspaces) >= self.max_tabs_per_session:
                raise GuestCapacityError("guest tab capacity is full for this session")
            identifier = workspace_id or secrets.token_urlsafe(18)
            if identifier in session.workspaces:
                raise GuestWorkspaceError("workspace_id is already in use")
            record = _WorkspaceRecord(
                workspace_id=identifier,
                tab_id=tab_id,
                revision=0,
                expires_at=session.expires_at,
                state=demo_fixture(),
            )
            self._validate_state(record.state)
            session.workspaces[identifier] = record
            return self._view(session_id, record)

    def get_workspace(
        self,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        now: int | None = None,
    ) -> GuestWorkspaceView:
        current = self._now(now)
        with self._lock:
            record = self._record(session_id, workspace_id, tab_id, current)
            return self._view(session_id, record)

    def initial_view_for_unbound_page(
        self,
        *,
        session_id: str,
        placeholder_id: str,
        now: int | None = None,
    ) -> GuestWorkspaceView:
        """Compose a page before NiceGUI reveals its stable browser-tab ID.

        A single existing workspace is the overwhelmingly common navigation
        case and allows the next route to render the guest's current fictional
        state immediately. With zero or multiple workspaces the safe neutral
        fixture is used until the websocket handshake binds the exact tab.
        This provisional view is never registered and therefore cannot consume
        guest capacity or receive a mutation.
        """

        current = self._now(now)
        with self._lock:
            self._purge_expired_locked(current)
            session = self._sessions.get(session_id)
            if session is not None and len(session.workspaces) == 1:
                record = next(iter(session.workspaces.values()))
                return self._copy_view(self._view(session_id, record))
            return GuestWorkspaceView(
                session_id=session_id,
                workspace_id=placeholder_id,
                tab_id=placeholder_id,
                revision=0,
                expires_at=session.expires_at if session is not None else current + self.ttl_seconds,
                state=demo_fixture(),
            )

    def replace_state(
        self,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        expected_revision: int,
        command_id: str,
        state: Mapping[str, Any],
        now: int | None = None,
    ) -> GuestWorkspaceView:
        if not command_id.strip():
            raise GuestWorkspaceError("command_id must not be empty")
        current = self._now(now)
        copied_state = _json_copy(dict(state))
        self._validate_state(copied_state)
        digest = hashlib.sha256(_canonical_bytes(copied_state)).hexdigest()
        with self._lock:
            record = self._record(session_id, workspace_id, tab_id, current)
            receipt = record.commands.get(command_id)
            if receipt is not None:
                if receipt.payload_digest != digest:
                    raise GuestWorkspaceError("command_id was reused with different content")
                return self._copy_view(receipt.view)
            session = self._sessions[session_id]
            self._consume_command_budget(session, current)
            if record.revision != expected_revision:
                raise GuestRevisionConflict(
                    f"expected revision {expected_revision}, current revision is {record.revision}"
                )
            record.state = copied_state
            record.revision += 1
            view = self._view(session_id, record)
            record.commands[command_id] = _CommandReceipt(digest, view)
            if len(record.commands) > self.max_commands_per_minute * 2:
                oldest = next(iter(record.commands))
                del record.commands[oldest]
            return self._copy_view(view)

    def seal_snapshot(
        self,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        now: int | None = None,
    ) -> str:
        current = self._now(now)
        with self._lock:
            record = self._record(session_id, workspace_id, tab_id, current)
            return self.codec.seal(
                session_id=session_id,
                workspace_id=workspace_id,
                tab_id=tab_id,
                revision=record.revision,
                state=record.state,
                expires_at=record.expires_at,
                now=current,
            )

    def verify_snapshot(
        self,
        token: str,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        now: int | None = None,
    ) -> GuestSnapshot:
        current = self._now(now)
        with self._lock:
            record = self._record(session_id, workspace_id, tab_id, current)
            return self.codec.open(
                token,
                expected_session_id=session_id,
                expected_workspace_id=workspace_id,
                expected_tab_id=tab_id,
                minimum_revision=record.revision,
                now=current,
            )

    def restore_snapshot(
        self,
        token: str,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        now: int | None = None,
    ) -> tuple[GuestWorkspaceView, bool]:
        """Restore a newer signed browser snapshot into its exact live tab.

        The browser token is never authoritative merely because it is newer:
        the HMAC, boot, session, workspace, tab, expiry, schema, state bounds,
        and monotonic revision are all checked before the in-memory record is
        changed.  A stale token can therefore never roll a live tab backwards.
        """

        current = self._now(now)
        snapshot = self.codec.open(
            token,
            expected_session_id=session_id,
            expected_workspace_id=workspace_id,
            expected_tab_id=tab_id,
            now=current,
        )
        self._validate_state(snapshot.state)
        with self._lock:
            record = self._record(session_id, workspace_id, tab_id, current)
            if snapshot.revision < record.revision:
                raise GuestSnapshotError("snapshot revision is stale")
            if snapshot.revision == record.revision:
                if _canonical_bytes(snapshot.state) != _canonical_bytes(record.state):
                    raise GuestSnapshotError("snapshot revision does not match live state")
                return self._copy_view(self._view(session_id, record)), False
            record.state = _json_copy(snapshot.state)
            record.revision = snapshot.revision
            record.commands.clear()
            return self._copy_view(self._view(session_id, record)), True

    def build_demo_download(
        self,
        *,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        file_type: str = "json",
        now: int | None = None,
    ) -> GuestDownload:
        view = self.get_workspace(
            session_id=session_id,
            workspace_id=workspace_id,
            tab_id=tab_id,
            now=now,
        )
        payload = {
            "demo": True,
            "fictional": True,
            "revision": view.revision,
            "workspace": view.workspace_id,
            "data": view.state,
        }
        if file_type == "json":
            content = _canonical_bytes(payload)
            download = GuestDownload(
                filename=f"SYSS_DEMO_roster_r{view.revision}.json",
                content=content,
                media_type="application/json; charset=utf-8",
            )
        elif file_type == "pdf":
            # A bounded placeholder for the later report-rendering adapter.  It
            # is a syntactically recognisable PDF payload and cannot contain
            # official data because its source is this isolated registry.
            summary = (
                f"DEMO - fictional Sing Yin roster workspace {view.workspace_id}, "
                f"revision {view.revision}"
            ).encode("ascii", errors="replace")
            content = b"%PDF-1.4\n% Sing Yin DEMO\n" + summary + b"\n%%EOF\n"
            download = GuestDownload(
                filename=f"SYSS_DEMO_roster_r{view.revision}.pdf",
                content=content,
                media_type="application/pdf",
            )
        else:
            raise GuestWorkspaceError("guest download type is not approved")
        if len(download.content) > self.max_download_bytes:
            raise GuestCapacityError("guest download exceeds the size limit")
        return download

    def cleanup_workspace(self, *, session_id: str, workspace_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            removed = session.workspaces.pop(workspace_id, None) is not None
            if not session.workspaces:
                self._sessions.pop(session_id, None)
            return removed

    def cleanup_session(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def purge_expired(self, *, now: int | None = None) -> int:
        current = self._now(now)
        with self._lock:
            return self._purge_expired_locked(current)

    @property
    def active_session_count(self) -> int:
        with self._lock:
            self._purge_expired_locked(self._clock())
            return len(self._sessions)

    def active_workspace_count(self, session_id: str) -> int:
        with self._lock:
            self._purge_expired_locked(self._clock())
            session = self._sessions.get(session_id)
            return len(session.workspaces) if session else 0

    def _record(
        self,
        session_id: str,
        workspace_id: str,
        tab_id: str,
        current: int,
    ) -> _WorkspaceRecord:
        self._purge_expired_locked(current)
        session = self._sessions.get(session_id)
        record = session.workspaces.get(workspace_id) if session else None
        if record is None or record.tab_id != tab_id:
            raise GuestWorkspaceError("guest workspace is unavailable")
        return record

    def _validate_state(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, dict):
            raise GuestWorkspaceError("guest state must be an object")
        prefects = state.get("prefects", [])
        weeks = state.get("weeks", [])
        if not isinstance(prefects, list) or len(prefects) > self.max_prefects:
            raise GuestCapacityError("guest prefect limit exceeded")
        if not isinstance(weeks, list) or len(weeks) > self.max_weeks:
            raise GuestCapacityError("guest week limit exceeded")
        if len(_canonical_bytes(state)) > self.max_state_bytes:
            raise GuestCapacityError("guest state exceeds the snapshot size limit")

    def _consume_command_budget(self, session: _SessionRecord, current: int) -> None:
        while session.command_times and session.command_times[0] <= current - 60:
            session.command_times.popleft()
        if len(session.command_times) >= self.max_commands_per_minute:
            raise GuestRateLimitError("guest command rate limit exceeded")
        session.command_times.append(current)

    def _purge_expired_locked(self, current: int) -> int:
        expired = [session_id for session_id, session in self._sessions.items() if session.expires_at <= current]
        for session_id in expired:
            del self._sessions[session_id]
        return len(expired)

    @staticmethod
    def _view(session_id: str, record: _WorkspaceRecord) -> GuestWorkspaceView:
        return GuestWorkspaceView(
            session_id=session_id,
            workspace_id=record.workspace_id,
            tab_id=record.tab_id,
            revision=record.revision,
            expires_at=record.expires_at,
            state=deepcopy(record.state),
        )

    @staticmethod
    def _copy_view(view: GuestWorkspaceView) -> GuestWorkspaceView:
        return GuestWorkspaceView(
            session_id=view.session_id,
            workspace_id=view.workspace_id,
            tab_id=view.tab_id,
            revision=view.revision,
            expires_at=view.expires_at,
            state=deepcopy(view.state),
        )

    def _now(self, now: int | None) -> int:
        return self._clock() if now is None else int(now)


__all__ = [
    "DEFAULT_MAX_COMMANDS_PER_MINUTE",
    "DEFAULT_MAX_DOWNLOAD_BYTES",
    "DEFAULT_MAX_PREFECTS",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_SNAPSHOT_BYTES",
    "DEFAULT_MAX_TABS_PER_SESSION",
    "DEFAULT_MAX_WEEKS",
    "DEFAULT_TTL_SECONDS",
    "DEMO_FIXTURE_VERSION",
    "GuestCapacityError",
    "GuestDownload",
    "GuestRateLimitError",
    "GuestRevisionConflict",
    "GuestSnapshot",
    "GuestSnapshotCodec",
    "GuestSnapshotError",
    "GuestWorkspaceError",
    "GuestWorkspaceRegistry",
    "GuestWorkspaceView",
    "SNAPSHOT_SCHEMA_VERSION",
    "demo_fixture",
]
