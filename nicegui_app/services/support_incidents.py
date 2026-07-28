"""Local-first, privacy-bounded incident bundles and safe inbox inspection.

Incident input is always untrusted.  This module never executes attachments,
opens URLs, interprets report instructions, or writes to roster persistence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from threading import RLock
from typing import Any, Iterable, Mapping, Sequence
from uuid import uuid4
import zipfile
from io import BytesIO
import warnings
import zlib

from PIL import Image, UnidentifiedImageError

from nicegui_app.config import support_directory


INCIDENT_SCHEMA_VERSION = 1
INCIDENT_ID_PATTERN = re.compile(r"^INC-\d{8}-[A-F0-9]{8}$")
OP_REFERENCE_PATTERN = re.compile(r"^OP-[A-F0-9]{8}$")
REQ_REFERENCE_PATTERN = re.compile(r"^REQ-[A-F0-9]{8}$")
ALLOWED_SOURCES = frozenset({"admin_ui", "browser_export", "synthetic_test", "inbox_import"})
ALLOWED_ACTOR_MODES = frozenset({"admin", "guest", "public", "local_maintenance", "synthetic"})
ALLOWED_LIFECYCLE_STATES = frozenset(
    {
        "new",
        "validated",
        "triaged",
        "reproduced",
        "fixed",
        "verified",
        "released",
        "closed",
        "needs_information",
        "duplicate",
        "rejected",
        "quarantined",
        "deferred",
    }
)
ALLOWED_ROUTE_CATEGORIES = frozenset(
    {
        "dashboard",
        "rosters",
        "roster_workflow",
        "prefects",
        "handover",
        "settings",
        "access_control",
        "platform",
        "engineering",
        "system_architecture",
        "getting_started",
        "guide",
        "devotional",
        "viewer",
        "login",
        "other",
    }
)
ALLOWED_WORKFLOW_ACTIONS = frozenset(
    {
        "page_view",
        "generate_draft",
        "edit_draft",
        "publish_roster",
        "export_pdf",
        "leave_declaration",
        "leave_adjustment",
        "prefect_import",
        "prefect_edit",
        "backup",
        "restore",
        "authentication",
        "guest_session",
        "music",
        "other",
    }
)
MAX_NARRATIVE_CHARACTERS = 4_000
MAX_REPRODUCTION_STEPS = 12
MAX_REPRODUCTION_STEP_CHARACTERS = 500
MAX_REFERENCES = 16
MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_BYTES = 512 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_STATUS_BYTES = 256 * 1024
MAX_STATUS_RECORDS = 512
STALE_STAGING_HOURS = 24
QUARANTINE_RETENTION_DAYS = 30
RESOLVED_RETENTION_DAYS = 180
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_DIMENSION = 4_096
MAX_PNG_PIXELS = 16_000_000
MAX_PNG_CHUNKS = 2_048
MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "incident_id",
        "created_at_utc",
        "source",
        "actor_mode",
        "application_version",
        "source_fingerprint",
        "environment",
        "application_mode",
        "route_category",
        "workflow_action",
        "error_fingerprint",
        "operation_references",
        "request_references",
        "attachment_manifest",
        "redaction_summary",
        "integrity_hashes",
        "lifecycle_status",
    }
)

_TEXT_ATTACHMENT_TYPES = frozenset({"text/plain", "application/json"})
_ATTACHMENT_SUFFIX_BY_MEDIA_TYPE = {
    "text/plain": ".txt",
    "application/json": ".json",
    "image/png": ".png",
}
_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "private_key",
        re.compile(r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----", re.I | re.S),
        "[REDACTED PRIVATE KEY]",
    ),
    ("bearer", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer [REDACTED]"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "[REDACTED JWT]"),
    (
        "credential",
        re.compile(r"(?i)\b(password|passwd|secret|token|api[_ -]?key|authorization|cookie)\b\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED]",
    ),
    ("email", re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"), "[REDACTED EMAIL]"),
    ("windows_user_path", re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\r\n]+"), r"C:\\Users\\[REDACTED]"),
    ("url_query", re.compile(r"(?i)(https?://[^\s?#]+)\?[^\s#]*"), r"\1?[REDACTED_QUERY]"),
)


class SupportIncidentError(RuntimeError):
    """Base class for safe support-pipeline failures."""


class IncidentValidationError(SupportIncidentError):
    """The untrusted incident input does not satisfy the v1 contract."""


class SupportStorageError(SupportIncidentError):
    """The local support store cannot complete an atomic operation."""


class IncidentNotFoundError(SupportIncidentError):
    """The requested incident does not exist in the safe inbox."""


def _validate_png_container(payload: bytes) -> None:
    """Reject truncated, corrupt, and polyglot PNG containers before decoding."""

    if not payload.startswith(PNG_SIGNATURE):
        raise IncidentValidationError("PNG signature is invalid")
    offset = len(PNG_SIGNATURE)
    chunks = 0
    saw_header = False
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise IncidentValidationError("PNG container is truncated")
        length = int.from_bytes(payload[offset : offset + 4], "big")
        chunk_type = payload[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(payload):
            raise IncidentValidationError("PNG chunk is truncated")
        data = payload[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(payload[offset + 8 + length : end], "big")
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
            raise IncidentValidationError("PNG chunk checksum is invalid")
        chunks += 1
        if chunks > MAX_PNG_CHUNKS:
            raise IncidentValidationError("PNG contains too many chunks")
        if chunks == 1:
            if chunk_type != b"IHDR" or length != 13:
                raise IncidentValidationError("PNG header is invalid")
            saw_header = True
        if chunk_type == b"IEND":
            if length != 0 or end != len(payload):
                raise IncidentValidationError("PNG has trailing or invalid content")
            if not saw_header:
                raise IncidentValidationError("PNG header is missing")
            return
        offset = end
    raise IncidentValidationError("PNG end marker is missing")


def _sanitize_png(payload: bytes) -> bytes:
    """Decode and re-encode a bounded PNG without ancillary metadata."""

    _validate_png_container(payload)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as source:
                if source.format != "PNG":
                    raise IncidentValidationError("attachment is not a PNG image")
                width, height = source.size
                if (
                    width <= 0
                    or height <= 0
                    or width > MAX_PNG_DIMENSION
                    or height > MAX_PNG_DIMENSION
                    or width * height > MAX_PNG_PIXELS
                ):
                    raise IncidentValidationError("PNG dimensions exceed the safe limit")
                source.load()
                has_alpha = source.mode in {"RGBA", "LA"} or "transparency" in source.info
                clean = source.convert("RGBA" if has_alpha else "RGB")
                output = BytesIO()
                clean.save(output, format="PNG", optimize=True, compress_level=9)
    except IncidentValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise IncidentValidationError("PNG could not be safely decoded") from error
    sanitized = output.getvalue()
    if len(sanitized) > MAX_ATTACHMENT_BYTES:
        raise IncidentValidationError("sanitized PNG exceeds the per-file limit")
    _validate_png_container(sanitized)
    return sanitized


@dataclass(frozen=True)
class AttachmentInput:
    filename: str
    media_type: str
    content: bytes
    consent_at_utc: str


@dataclass(frozen=True)
class IncidentReportInput:
    source: str
    actor_mode: str
    route_category: str
    workflow_action: str
    expected_behavior: str
    actual_behavior: str
    reproduction_steps: tuple[str, ...] = ()
    impact: str = ""
    frequency: str = ""
    last_known_good: str = ""
    operation_references: tuple[str, ...] = ()
    request_references: tuple[str, ...] = ()
    safe_error_type: str = ""
    safe_code_locations: tuple[str, ...] = ()
    safe_breadcrumbs: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class IncidentBundleSummary:
    incident_id: str
    lifecycle_status: str
    application_version: str
    route_category: str
    workflow_action: str
    error_fingerprint: str
    occurrence_count: int = 1
    integrity_valid: bool = True
    redaction_count: int = 0


@dataclass(frozen=True)
class InboxLimits:
    root_bytes: int = 50 * 1024 * 1024
    incidents_per_day: int = 20
    incident_count: int = 200
    minimum_free_bytes: int = 20 * 1024 * 1024

    @classmethod
    def from_environment(cls) -> "InboxLimits":
        def bounded(name: str, default: int, low: int, high: int) -> int:
            try:
                value = int(os.getenv(name, str(default)).strip())
            except ValueError:
                return default
            return max(low, min(high, value))

        return cls(
            root_bytes=bounded("SING_YIN_SUPPORT_MAX_BYTES", cls.root_bytes, 2 * 1024 * 1024, 1024 * 1024 * 1024),
            incidents_per_day=bounded("SING_YIN_SUPPORT_DAILY_LIMIT", cls.incidents_per_day, 1, 500),
            incident_count=bounded("SING_YIN_SUPPORT_INCIDENT_LIMIT", cls.incident_count, 1, 10_000),
            minimum_free_bytes=bounded("SING_YIN_SUPPORT_MIN_FREE_BYTES", cls.minimum_free_bytes, 1024 * 1024, 10 * 1024 * 1024 * 1024),
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        raise IncidentValidationError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_incident_id(now: datetime | None = None) -> str:
    timestamp = (now or _utc_now()).astimezone(timezone.utc)
    return f"INC-{timestamp:%Y%m%d}-{uuid4().hex[:8].upper()}"


def _sanitize_text(value: object, *, maximum: int, redactions: Counter[str]) -> str:
    if not isinstance(value, str):
        raise IncidentValidationError("text fields must be strings")
    if "\x00" in value:
        raise IncidentValidationError("NUL is not allowed in incident text")
    cleaned = value.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _CONTROL_PATTERN.sub("", cleaned)
    for category, pattern, replacement in _REDACTION_PATTERNS:
        cleaned, count = pattern.subn(replacement, cleaned)
        if count:
            redactions[category] += count
    if len(cleaned) > maximum:
        raise IncidentValidationError(f"text field exceeds {maximum} characters")
    return cleaned.strip()


def sanitize_untrusted_text(value: str, *, maximum: int = MAX_NARRATIVE_CHARACTERS) -> tuple[str, dict[str, int]]:
    redactions: Counter[str] = Counter()
    return _sanitize_text(value, maximum=maximum, redactions=redactions), dict(sorted(redactions.items()))


def _safe_reference_list(values: Sequence[str], pattern: re.Pattern[str], label: str) -> tuple[str, ...]:
    if len(values) > MAX_REFERENCES:
        raise IncidentValidationError(f"too many {label} references")
    result: list[str] = []
    for value in values:
        normalized = str(value).strip().upper()
        if not pattern.fullmatch(normalized):
            raise IncidentValidationError(f"invalid {label} reference")
        if normalized not in result:
            result.append(normalized)
    return tuple(result)


def _safe_slug(value: str, *, fallback: str = "unknown") -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.:-]+", "_", str(value).strip())[:96]
    return normalized or fallback


def _fingerprint(*parts: str) -> str:
    payload = "\0".join(_safe_slug(part) for part in parts).encode("utf-8")
    return sha256(payload).hexdigest()[:24]


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _jsonl_bytes(values: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(dict(value), ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        for value in values
    )


def _sha256(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return path.is_symlink() or bool(attributes & reparse_flag)


def _assert_plain_directory(path: Path) -> None:
    if not path.is_dir() or _is_reparse_point(path):
        raise SupportStorageError("support storage contains an unsafe directory boundary")


def _safe_relative_file(bundle: Path, relative: str) -> Path:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise IncidentValidationError("unsafe bundle path")
    target = bundle.joinpath(*candidate.parts)
    resolved_bundle = bundle.resolve()
    try:
        target.resolve().relative_to(resolved_bundle)
    except (OSError, ValueError) as error:
        raise IncidentValidationError("bundle path escapes its incident directory") from error
    return target


class SupportInbox:
    """Write and inspect incident bundles without touching roster persistence."""

    _write_lock = RLock()
    _DIRECTORIES = ("inbox", "quarantined", "triaged", "resolved", "exported", "staging")

    def __init__(self, root: Path | None = None, *, limits: InboxLimits | None = None) -> None:
        self.root = Path(root if root is not None else support_directory()).expanduser()
        self.limits = limits or InboxLimits.from_environment()

    def initialize(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            _assert_plain_directory(self.root)
            for name in self._DIRECTORIES:
                directory = self.root / name
                directory.mkdir(exist_ok=True)
                _assert_plain_directory(directory)
        except SupportIncidentError:
            raise
        except OSError as error:
            raise SupportStorageError("support storage is unavailable") from error

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    def _incident_directories(self) -> list[Path]:
        directories: list[Path] = []
        for bucket in ("inbox", "triaged", "resolved"):
            container = self.root / bucket
            if not container.is_dir() or _is_reparse_point(container):
                continue
            for item in container.iterdir():
                if item.is_dir() and INCIDENT_ID_PATTERN.fullmatch(item.name) and not _is_reparse_point(item):
                    directories.append(item)
        return directories

    def _preflight(self, *, estimated_bytes: int, now: datetime) -> None:
        existing = self._incident_directories()
        if len(existing) >= self.limits.incident_count:
            raise SupportStorageError("support inbox incident limit reached")
        day_prefix = f"INC-{now.astimezone(timezone.utc):%Y%m%d}-"
        if sum(item.name.startswith(day_prefix) for item in existing) >= self.limits.incidents_per_day:
            raise SupportStorageError("support inbox daily limit reached")
        root_size = 0
        for item in existing:
            for candidate in item.rglob("*"):
                if candidate.is_file() and not _is_reparse_point(candidate):
                    try:
                        root_size += candidate.stat().st_size
                    except OSError as error:
                        raise SupportStorageError("support inbox size cannot be verified") from error
        if root_size + estimated_bytes > self.limits.root_bytes:
            raise SupportStorageError("support inbox storage quota reached")
        try:
            free_bytes = shutil.disk_usage(self.root).free
        except OSError as error:
            raise SupportStorageError("support storage capacity cannot be verified") from error
        if free_bytes < self.limits.minimum_free_bytes + estimated_bytes:
            raise SupportStorageError("support storage does not have enough free space")

    def _write_file(self, path: Path, payload: bytes) -> None:
        if len(payload) > MAX_BUNDLE_BYTES:
            raise IncidentValidationError("incident file exceeds bundle limit")
        try:
            with path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as error:
            raise SupportStorageError("incident bundle could not be written atomically") from error

    def _prepare_attachment(
        self,
        item: AttachmentInput,
        index: int,
        redactions: Counter[str],
    ) -> tuple[str, bytes, dict[str, Any]]:
        media_type = item.media_type.strip().lower().split(";", 1)[0]
        suffix = _ATTACHMENT_SUFFIX_BY_MEDIA_TYPE.get(media_type)
        if suffix is None:
            raise IncidentValidationError("attachment type is not allowed")
        if not isinstance(item.content, bytes) or len(item.content) > MAX_ATTACHMENT_BYTES:
            raise IncidentValidationError("attachment exceeds the per-file limit")
        safe_name = f"attachment-{index:02d}{suffix}"
        if media_type == "image/png":
            payload = _sanitize_png(item.content)
        else:
            try:
                decoded = item.content.decode("utf-8")
            except UnicodeDecodeError as error:
                raise IncidentValidationError("text attachments must be UTF-8") from error
            if media_type == "application/json":
                try:
                    parsed = json.loads(decoded)
                except json.JSONDecodeError as error:
                    raise IncidentValidationError("JSON attachment is invalid") from error

                def scrub(value: Any) -> Any:
                    if isinstance(value, str):
                        return _sanitize_text(value, maximum=MAX_NARRATIVE_CHARACTERS, redactions=redactions)
                    if isinstance(value, list):
                        return [scrub(child) for child in value[:200]]
                    if isinstance(value, dict):
                        if len(value) > 200:
                            raise IncidentValidationError("JSON attachment has too many keys")
                        return {
                            _safe_slug(str(key), fallback="field")[:80]: scrub(child)
                            for key, child in value.items()
                        }
                    if value is None or isinstance(value, (bool, int, float)):
                        return value
                    raise IncidentValidationError("JSON attachment contains an unsupported value")

                payload = _json_bytes(scrub(parsed))
            else:
                cleaned = _sanitize_text(decoded, maximum=MAX_ATTACHMENT_BYTES, redactions=redactions)
                payload = (cleaned + "\n").encode("utf-8")
        if len(payload) > MAX_ATTACHMENT_BYTES:
            raise IncidentValidationError("sanitized attachment exceeds the per-file limit")
        consent = _sanitize_text(item.consent_at_utc, maximum=64, redactions=redactions)
        return safe_name, payload, {
            "safe_filename": safe_name,
            "media_type": media_type,
            "size": len(payload),
            "sha256": _sha256(payload),
            "consent_at_utc": consent,
        }

    def create_incident(
        self,
        report: IncidentReportInput,
        *,
        application_version: str,
        source_fingerprint: str,
        application_mode: str,
        environment: Mapping[str, Any] | None = None,
        health_summary: Mapping[str, Any] | None = None,
        events: Sequence[Mapping[str, Any]] = (),
        attachments: Sequence[AttachmentInput] = (),
        now: datetime | None = None,
    ) -> IncidentBundleSummary:
        if report.source not in ALLOWED_SOURCES or report.actor_mode not in ALLOWED_ACTOR_MODES:
            raise IncidentValidationError("invalid incident source or actor mode")
        if report.route_category not in ALLOWED_ROUTE_CATEGORIES:
            raise IncidentValidationError("route category is not allowlisted")
        if report.workflow_action not in ALLOWED_WORKFLOW_ACTIONS:
            raise IncidentValidationError("workflow action is not allowlisted")
        if len(report.reproduction_steps) > MAX_REPRODUCTION_STEPS:
            raise IncidentValidationError("too many reproduction steps")
        if len(attachments) > MAX_ATTACHMENTS:
            raise IncidentValidationError("too many attachments")

        redactions: Counter[str] = Counter()
        cleaned = {
            "expected_behavior": _sanitize_text(report.expected_behavior, maximum=MAX_NARRATIVE_CHARACTERS, redactions=redactions),
            "actual_behavior": _sanitize_text(report.actual_behavior, maximum=MAX_NARRATIVE_CHARACTERS, redactions=redactions),
            "reproduction_steps": [
                _sanitize_text(step, maximum=MAX_REPRODUCTION_STEP_CHARACTERS, redactions=redactions)
                for step in report.reproduction_steps
            ],
            "impact": _sanitize_text(report.impact, maximum=MAX_NARRATIVE_CHARACTERS, redactions=redactions),
            "frequency": _sanitize_text(report.frequency, maximum=500, redactions=redactions),
            "last_known_good": _sanitize_text(report.last_known_good, maximum=1_000, redactions=redactions),
        }
        operation_references = _safe_reference_list(report.operation_references, OP_REFERENCE_PATTERN, "operation")
        request_references = _safe_reference_list(report.request_references, REQ_REFERENCE_PATTERN, "request")
        safe_error_type = _safe_slug(report.safe_error_type, fallback="unknown")
        safe_locations = tuple(_safe_slug(item) for item in report.safe_code_locations[:16])
        version = _safe_slug(application_version)
        fingerprint = _safe_slug(source_fingerprint)
        error_fingerprint = _fingerprint(
            safe_error_type,
            ",".join(safe_locations),
            report.route_category,
            report.workflow_action,
            version,
        )
        created_at = now or _utc_now()
        created_at_utc = _rfc3339(created_at)
        incident_id = new_incident_id(created_at)

        attachment_payloads: list[tuple[str, bytes]] = []
        attachment_manifest: list[dict[str, Any]] = []
        total_attachment_bytes = 0
        for index, item in enumerate(attachments, start=1):
            safe_name, payload, metadata = self._prepare_attachment(item, index, redactions)
            total_attachment_bytes += len(payload)
            if total_attachment_bytes > MAX_TOTAL_ATTACHMENT_BYTES:
                raise IncidentValidationError("total attachment limit exceeded")
            attachment_payloads.append((safe_name, payload))
            attachment_manifest.append(metadata)

        safe_environment: dict[str, Any] = {}
        for key, value in dict(environment or {}).items():
            safe_key = _safe_slug(str(key), fallback="field")[:64]
            if isinstance(value, bool) or value is None:
                safe_environment[safe_key] = value
            elif isinstance(value, int):
                safe_environment[safe_key] = value
            elif isinstance(value, str):
                safe_environment[safe_key] = _sanitize_text(value, maximum=256, redactions=redactions)
        safe_health: dict[str, Any] = {}
        for key, value in dict(health_summary or {}).items():
            if isinstance(value, (bool, int)) or value is None:
                safe_health[_safe_slug(str(key), fallback="metric")[:64]] = value
            elif isinstance(value, str) and value in {"ok", "degraded", "unavailable", "unknown"}:
                safe_health[_safe_slug(str(key), fallback="metric")[:64]] = value
        environment_payload = _json_bytes({"environment": safe_environment, "health_summary": safe_health})

        safe_events: list[dict[str, Any]] = []
        for event in events[:64]:
            safe_events.append(
                {
                    "timestamp_utc": _sanitize_text(str(event.get("timestamp_utc", "")), maximum=64, redactions=redactions),
                    "category": _safe_slug(str(event.get("category", "unknown"))),
                    "outcome": _safe_slug(str(event.get("outcome", "unknown"))),
                }
            )
        events_payload = _jsonl_bytes(safe_events)
        status_record = {
            "timestamp_utc": created_at_utc,
            "status": "new",
            "actor": "system",
            "note_code": "incident_created",
        }
        status_payload = _jsonl_bytes((status_record,))

        def report_section(title: str, value: str) -> str:
            return f"## {title}\n\n{html.escape(value) if value else 'Not provided'}\n"

        report_markdown = (
            f"# Incident {incident_id}\n\n"
            f"Created: {created_at_utc}\n\n"
            + report_section("Expected behavior", cleaned["expected_behavior"])
            + report_section("Actual behavior", cleaned["actual_behavior"])
            + "## Reproduction steps\n\n"
            + ("\n".join(f"{index}. {html.escape(step)}" for index, step in enumerate(cleaned["reproduction_steps"], 1)) or "Not provided")
            + "\n\n"
            + report_section("Impact", cleaned["impact"])
            + report_section("Frequency", cleaned["frequency"])
            + report_section("Last known good", cleaned["last_known_good"])
        )
        report_payload = report_markdown.encode("utf-8")
        file_payloads: dict[str, bytes] = {
            "report.md": report_payload,
            "environment.json": environment_payload,
            "evidence/events.jsonl": events_payload,
            "status.jsonl": status_payload,
        }
        for safe_name, payload in attachment_payloads:
            file_payloads[f"attachments/{safe_name}"] = payload
        integrity_hashes = {
            relative: _sha256(payload)
            for relative, payload in file_payloads.items()
            if relative != "status.jsonl"
        }
        manifest = {
            "schema_version": INCIDENT_SCHEMA_VERSION,
            "incident_id": incident_id,
            "created_at_utc": created_at_utc,
            "source": report.source,
            "actor_mode": report.actor_mode,
            "application_version": version,
            "source_fingerprint": fingerprint,
            "environment": "environment.json",
            "application_mode": _safe_slug(application_mode),
            "route_category": report.route_category,
            "workflow_action": report.workflow_action,
            "error_fingerprint": error_fingerprint,
            "operation_references": list(operation_references),
            "request_references": list(request_references),
            "attachment_manifest": attachment_manifest,
            "redaction_summary": dict(sorted(redactions.items())),
            "integrity_hashes": integrity_hashes,
            "lifecycle_status": "new",
        }
        manifest_payload = _json_bytes(manifest)
        estimated_size = len(manifest_payload) + sum(map(len, file_payloads.values()))
        if estimated_size > MAX_BUNDLE_BYTES:
            raise IncidentValidationError("incident bundle exceeds the total size limit")

        with self._write_lock:
            self.initialize()
            self._preflight(estimated_bytes=estimated_size, now=created_at)
            staging = self.root / "staging" / f".{incident_id}-{uuid4().hex}"
            destination = self.inbox / incident_id
            try:
                staging.mkdir(exist_ok=False)
                (staging / "evidence").mkdir()
                (staging / "attachments").mkdir()
                for relative, payload in file_payloads.items():
                    self._write_file(_safe_relative_file(staging, relative), payload)
                self._write_file(staging / "manifest.json", manifest_payload)
                self._validate_bundle_path(staging, expected_incident_id=incident_id)
                if destination.exists():
                    raise SupportStorageError("incident identifier collision")
                os.replace(staging, destination)
            except SupportIncidentError:
                shutil.rmtree(staging, ignore_errors=True)
                raise
            except OSError as error:
                shutil.rmtree(staging, ignore_errors=True)
                raise SupportStorageError("incident bundle could not be committed") from error
        return IncidentBundleSummary(
            incident_id=incident_id,
            lifecycle_status="new",
            application_version=version,
            route_category=report.route_category,
            workflow_action=report.workflow_action,
            error_fingerprint=error_fingerprint,
            redaction_count=sum(redactions.values()),
        )

    def _find_incident(self, incident_id: str) -> Path:
        if not INCIDENT_ID_PATTERN.fullmatch(incident_id):
            raise IncidentValidationError("invalid incident identifier")
        self.initialize()
        for bucket in ("inbox", "triaged", "resolved", "quarantined"):
            candidate = self.root / bucket / incident_id
            if candidate.is_dir() and not _is_reparse_point(candidate):
                return candidate
        raise IncidentNotFoundError("incident was not found")

    def _validate_bundle_path(self, bundle: Path, *, expected_incident_id: str | None = None) -> IncidentBundleSummary:
        _assert_plain_directory(bundle)
        manifest_path = bundle / "manifest.json"
        if not manifest_path.is_file() or _is_reparse_point(manifest_path):
            raise IncidentValidationError("incident manifest is missing or unsafe")
        if manifest_path.stat().st_size > 256 * 1024:
            raise IncidentValidationError("incident manifest is too large")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IncidentValidationError("incident manifest is unreadable") from error
        if not isinstance(manifest, dict) or frozenset(manifest) != MANIFEST_KEYS:
            raise IncidentValidationError("incident manifest schema is invalid")
        incident_id = manifest.get("incident_id")
        if not isinstance(incident_id, str) or not INCIDENT_ID_PATTERN.fullmatch(incident_id):
            raise IncidentValidationError("incident manifest identifier is invalid")
        if expected_incident_id and incident_id != expected_incident_id:
            raise IncidentValidationError("incident directory and manifest identifiers differ")
        if manifest.get("schema_version") != INCIDENT_SCHEMA_VERSION:
            raise IncidentValidationError("unsupported incident schema")
        if manifest.get("source") not in ALLOWED_SOURCES or manifest.get("actor_mode") not in ALLOWED_ACTOR_MODES:
            raise IncidentValidationError("incident source or actor is invalid")
        if manifest.get("route_category") not in ALLOWED_ROUTE_CATEGORIES:
            raise IncidentValidationError("incident route category is invalid")
        if manifest.get("workflow_action") not in ALLOWED_WORKFLOW_ACTIONS:
            raise IncidentValidationError("incident workflow action is invalid")
        if manifest.get("lifecycle_status") not in ALLOWED_LIFECYCLE_STATES:
            raise IncidentValidationError("incident lifecycle status is invalid")
        for field_name in ("application_version", "source_fingerprint", "application_mode", "error_fingerprint"):
            value = manifest.get(field_name)
            if not isinstance(value, str) or not value or len(value) > 128:
                raise IncidentValidationError(f"incident {field_name} is invalid")
        for field_name, pattern in (
            ("operation_references", OP_REFERENCE_PATTERN),
            ("request_references", REQ_REFERENCE_PATTERN),
        ):
            references = manifest.get(field_name)
            if not isinstance(references, list) or len(references) > MAX_REFERENCES:
                raise IncidentValidationError(f"incident {field_name} is invalid")
            if any(not isinstance(value, str) or not pattern.fullmatch(value) for value in references):
                raise IncidentValidationError(f"incident {field_name} is invalid")
        hashes = manifest.get("integrity_hashes")
        if not isinstance(hashes, dict) or len(hashes) > 16:
            raise IncidentValidationError("incident integrity index is invalid")
        total_size = manifest_path.stat().st_size
        for relative, expected_hash in hashes.items():
            if not isinstance(relative, str) or not re.fullmatch(r"[a-f0-9]{64}", str(expected_hash)):
                raise IncidentValidationError("incident integrity entry is invalid")
            target = _safe_relative_file(bundle, relative)
            if not target.is_file() or _is_reparse_point(target):
                raise IncidentValidationError("incident evidence is missing or unsafe")
            payload = target.read_bytes()
            total_size += len(payload)
            if _sha256(payload) != expected_hash:
                raise IncidentValidationError("incident evidence hash mismatch")
        attachment_manifest = manifest.get("attachment_manifest")
        if not isinstance(attachment_manifest, list) or len(attachment_manifest) > MAX_ATTACHMENTS:
            raise IncidentValidationError("incident attachment manifest is invalid")
        indexed_attachments: set[str] = set()
        for entry in attachment_manifest:
            if not isinstance(entry, dict) or set(entry) != {
                "safe_filename",
                "media_type",
                "size",
                "sha256",
                "consent_at_utc",
            }:
                raise IncidentValidationError("incident attachment entry is invalid")
            safe_name = entry.get("safe_filename")
            media_type = entry.get("media_type")
            if (
                not isinstance(safe_name, str)
                or not re.fullmatch(r"attachment-\d{2}\.(txt|json|png)", safe_name)
                or media_type not in _ATTACHMENT_SUFFIX_BY_MEDIA_TYPE
                or safe_name in indexed_attachments
            ):
                raise IncidentValidationError("incident attachment identity is invalid")
            relative = f"attachments/{safe_name}"
            target = _safe_relative_file(bundle, relative)
            if relative not in hashes or not target.is_file() or _is_reparse_point(target):
                raise IncidentValidationError("incident attachment is missing or unindexed")
            payload = target.read_bytes()
            if (
                entry.get("size") != len(payload)
                or entry.get("sha256") != _sha256(payload)
                or hashes[relative] != entry.get("sha256")
            ):
                raise IncidentValidationError("incident attachment metadata does not match its payload")
            indexed_attachments.add(safe_name)
        attachment_dir = bundle / "attachments"
        evidence_dir = bundle / "evidence"
        try:
            _assert_plain_directory(attachment_dir)
            _assert_plain_directory(evidence_dir)
            root_entries = {item.name for item in bundle.iterdir()}
            evidence_entries = {item.name for item in evidence_dir.iterdir()}
            attachment_entries = tuple(attachment_dir.iterdir())
        except (OSError, SupportStorageError) as error:
            raise IncidentValidationError("incident bundle layout is unreadable or unsafe") from error
        if root_entries != {
            "attachments",
            "environment.json",
            "evidence",
            "manifest.json",
            "report.md",
            "status.jsonl",
        }:
            raise IncidentValidationError("incident contains an unindexed root entry")
        if evidence_entries != {"events.jsonl"}:
            raise IncidentValidationError("incident contains unindexed evidence")
        if any(not item.is_file() or _is_reparse_point(item) for item in attachment_entries):
            raise IncidentValidationError("incident contains an unsafe attachment entry")
        actual_attachments = {item.name for item in attachment_entries}
        if actual_attachments != indexed_attachments:
            raise IncidentValidationError("incident contains an unindexed attachment")
        expected_hashes = {
            "report.md",
            "environment.json",
            "evidence/events.jsonl",
            *(f"attachments/{name}" for name in indexed_attachments),
        }
        if set(hashes) != expected_hashes:
            raise IncidentValidationError("incident integrity index does not match its file set")
        if total_size > MAX_BUNDLE_BYTES:
            raise IncidentValidationError("incident bundle is oversized")
        redactions = manifest.get("redaction_summary")
        redaction_count = sum(value for value in redactions.values() if isinstance(value, int)) if isinstance(redactions, dict) else 0
        lifecycle_status = self._read_lifecycle_status(
            bundle,
            default=str(manifest["lifecycle_status"]),
        )
        return IncidentBundleSummary(
            incident_id=incident_id,
            lifecycle_status=lifecycle_status,
            application_version=str(manifest["application_version"]),
            route_category=str(manifest["route_category"]),
            workflow_action=str(manifest["workflow_action"]),
            error_fingerprint=str(manifest["error_fingerprint"]),
            integrity_valid=True,
            redaction_count=redaction_count,
        )

    def _read_lifecycle_status(self, bundle: Path, *, default: str) -> str:
        status_path = bundle / "status.jsonl"
        if not status_path.is_file() or _is_reparse_point(status_path):
            raise IncidentValidationError("incident lifecycle record is missing or unsafe")
        try:
            if status_path.stat().st_size > MAX_STATUS_BYTES:
                raise IncidentValidationError("incident lifecycle record is too large")
            records = status_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise IncidentValidationError("incident lifecycle record is unreadable") from error
        if not records or len(records) > MAX_STATUS_RECORDS:
            raise IncidentValidationError("incident lifecycle record count is invalid")
        effective = default
        for line in records:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise IncidentValidationError("incident lifecycle record is invalid") from error
            if not isinstance(record, dict) or set(record) != {
                "timestamp_utc",
                "status",
                "actor",
                "note_code",
            }:
                raise IncidentValidationError("incident lifecycle schema is invalid")
            if record.get("status") not in ALLOWED_LIFECYCLE_STATES:
                raise IncidentValidationError("incident lifecycle state is invalid")
            for field_name in ("timestamp_utc", "actor", "note_code"):
                value = record.get(field_name)
                if not isinstance(value, str) or not value or len(value) > 128:
                    raise IncidentValidationError("incident lifecycle metadata is invalid")
            effective = str(record["status"])
        return effective

    def validate_bundle(self, incident_id: str) -> IncidentBundleSummary:
        return self._validate_bundle_path(self._find_incident(incident_id), expected_incident_id=incident_id)

    def list_incidents(self) -> tuple[IncidentBundleSummary, ...]:
        self.initialize()
        grouped: dict[tuple[str, str, str], IncidentBundleSummary] = {}
        for path in self._incident_directories():
            try:
                summary = self._validate_bundle_path(path, expected_incident_id=path.name)
            except SupportIncidentError:
                continue
            key = (summary.error_fingerprint, summary.route_category, summary.workflow_action)
            previous = grouped.get(key)
            grouped[key] = summary if previous is None else IncidentBundleSummary(
                **{**asdict(previous), "occurrence_count": previous.occurrence_count + 1}
            )
        return tuple(sorted(grouped.values(), key=lambda item: item.incident_id, reverse=True))

    def quarantine(self, incident_id: str, *, reason_code: str = "validation_failed") -> Path:
        with self._write_lock:
            source = self._find_incident(incident_id)
            destination = self.root / "quarantined" / incident_id
            if source.parent.name == "quarantined":
                return source
            if destination.exists():
                raise SupportStorageError("quarantine destination already exists")
            os.replace(source, destination)
            quarantine_record = {
                "timestamp_utc": _rfc3339(_utc_now()),
                "status": "quarantined",
                "actor": "inspector",
                "note_code": _safe_slug(reason_code),
            }
            try:
                with (destination / "status.jsonl").open("ab") as handle:
                    handle.write(_jsonl_bytes((quarantine_record,)))
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as error:
                raise SupportStorageError("quarantine status could not be recorded") from error
            return destination

    def append_status(self, incident_id: str, *, status_value: str, note_code: str, actor: str = "operator") -> None:
        if status_value not in ALLOWED_LIFECYCLE_STATES:
            raise IncidentValidationError("invalid lifecycle status")
        note = _safe_slug(note_code)
        safe_actor = _safe_slug(actor)
        with self._write_lock:
            bundle = self._find_incident(incident_id)
            self._validate_bundle_path(bundle, expected_incident_id=incident_id)
            record = {
                "timestamp_utc": _rfc3339(_utc_now()),
                "status": status_value,
                "actor": safe_actor,
                "note_code": note,
            }
            try:
                with (bundle / "status.jsonl").open("ab") as handle:
                    handle.write(_jsonl_bytes((record,)))
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as error:
                raise SupportStorageError("incident lifecycle could not be updated") from error
            target_bucket = (
                "resolved"
                if status_value in {"fixed", "verified", "released", "closed", "duplicate", "rejected"}
                else "triaged"
                if status_value in {"validated", "triaged", "reproduced", "needs_information", "deferred"}
                else bundle.parent.name
            )
            if target_bucket != bundle.parent.name:
                destination = self.root / target_bucket / incident_id
                if destination.exists():
                    raise SupportStorageError("incident lifecycle destination already exists")
                try:
                    os.replace(bundle, destination)
                except OSError as error:
                    raise SupportStorageError("incident lifecycle could not be committed") from error

    def cleanup_expired(self, *, now: datetime | None = None) -> dict[str, int]:
        """Remove only stale staging and explicitly bounded non-active records."""

        current = now or _utc_now()
        current_timestamp = current.timestamp()
        removed = {"staging": 0, "quarantined": 0, "resolved": 0}
        rules = (
            ("staging", STALE_STAGING_HOURS * 60 * 60),
            ("quarantined", QUARANTINE_RETENTION_DAYS * 24 * 60 * 60),
            ("resolved", RESOLVED_RETENTION_DAYS * 24 * 60 * 60),
        )
        with self._write_lock:
            try:
                self.initialize()
            except (SupportIncidentError, OSError):
                return removed
            for bucket, maximum_age in rules:
                container = self.root / bucket
                try:
                    candidates = tuple(container.iterdir())
                except OSError:
                    continue
                for candidate in candidates:
                    if not candidate.is_dir() or _is_reparse_point(candidate):
                        continue
                    try:
                        age = current_timestamp - candidate.stat().st_mtime
                    except OSError:
                        continue
                    if age < maximum_age:
                        continue
                    if bucket == "resolved":
                        try:
                            summary = self._validate_bundle_path(
                                candidate,
                                expected_incident_id=candidate.name,
                            )
                        except SupportIncidentError:
                            continue
                        if summary.lifecycle_status not in {
                            "released",
                            "closed",
                            "duplicate",
                            "rejected",
                        }:
                            continue
                    try:
                        shutil.rmtree(candidate, ignore_errors=False)
                    except OSError:
                        continue
                    removed[bucket] += 1
        return removed

    def export_bundle_bytes(self, incident_id: str) -> bytes:
        bundle = self._find_incident(incident_id)
        self._validate_bundle_path(bundle, expected_incident_id=incident_id)
        output = BytesIO()
        with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(bundle.rglob("*")):
                if not path.is_file() or _is_reparse_point(path):
                    continue
                relative = path.relative_to(bundle).as_posix()
                if ".." in PurePosixPath(relative).parts:
                    raise IncidentValidationError("unsafe export path")
                archive.writestr(relative, path.read_bytes())
        payload = output.getvalue()
        if len(payload) > MAX_BUNDLE_BYTES:
            raise SupportStorageError("incident export exceeds the safe size limit")
        return payload


__all__ = [
    "ALLOWED_ACTOR_MODES",
    "ALLOWED_LIFECYCLE_STATES",
    "ALLOWED_ROUTE_CATEGORIES",
    "ALLOWED_SOURCES",
    "ALLOWED_WORKFLOW_ACTIONS",
    "AttachmentInput",
    "InboxLimits",
    "IncidentBundleSummary",
    "IncidentNotFoundError",
    "IncidentReportInput",
    "IncidentValidationError",
    "SupportInbox",
    "SupportIncidentError",
    "SupportStorageError",
    "new_incident_id",
    "sanitize_untrusted_text",
]
