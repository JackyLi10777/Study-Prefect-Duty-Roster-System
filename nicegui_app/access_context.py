"""Verified access identity and deny-by-default capability contracts.

This module deliberately contains no NiceGUI or persistence imports.  It is the
small, reusable boundary which page handlers and services can both enforce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class AccessMode(str, Enum):
    """How one request is allowed to interact with the application."""

    PUBLIC = "public"
    ADMIN = "admin"
    GUEST = "guest"
    LOCAL_MAINTENANCE = "local_maintenance"


class Capability(str, Enum):
    """Stable, translation-independent permissions used at every boundary."""

    DEMO_DATA_READ = "demo_data.read"
    DEMO_STATE_MODIFY = "demo_state.modify"
    DEMO_RESULT_DOWNLOAD = "demo_result.download"
    SESSION_PREFERENCES_MODIFY = "session_preferences.modify"

    AI_USE = "ai.use"
    DATA_IMPORT = "data.import"
    FILE_UPLOAD = "file.upload"
    CLIPBOARD_INGEST = "clipboard.ingest"
    EXTERNAL_INTEGRATION = "external_integration.use"
    SYNC = "sync.execute"
    PERSISTENT_WRITE = "persistent.write"
    BACKGROUND_JOB = "background_job.schedule"
    EXTERNAL_DELIVERY = "external_delivery.execute"
    EXPENSIVE_PROCESSING = "expensive_processing.execute"
    REAL_EXPORT = "real_export.download"


GUEST_ALLOWED_CAPABILITIES = frozenset(
    {
        Capability.DEMO_DATA_READ,
        Capability.DEMO_STATE_MODIFY,
        Capability.DEMO_RESULT_DOWNLOAD,
        Capability.SESSION_PREFERENCES_MODIFY,
    }
)
GUEST_DENIED_CAPABILITIES = frozenset(set(Capability) - set(GUEST_ALLOWED_CAPABILITIES))


class CapabilityDeniedError(PermissionError):
    """Raised when a verified principal does not have a required capability."""

    def __init__(self, mode: AccessMode, capability: Capability) -> None:
        self.mode = mode
        self.capability = capability
        super().__init__(f"{mode.value} is not allowed to use {capability.value}")


class PrincipalExpiredError(PermissionError):
    """Raised when a formerly valid session may no longer perform work."""


class CapabilityPolicy:
    """Explicit capability matrix.

    Missing modes and missing capabilities are denied.  Public traffic receives
    no application capability.  Administrative and local-maintenance
    principals are still subject to domain policy after this access check.
    """

    _CAPABILITIES_BY_MODE: dict[AccessMode, frozenset[Capability]] = {
        AccessMode.PUBLIC: frozenset(),
        AccessMode.GUEST: GUEST_ALLOWED_CAPABILITIES,
        AccessMode.ADMIN: frozenset(Capability),
        AccessMode.LOCAL_MAINTENANCE: frozenset(Capability),
    }

    @classmethod
    def capabilities_for(cls, mode: AccessMode) -> frozenset[Capability]:
        return cls._CAPABILITIES_BY_MODE.get(mode, frozenset())

    @classmethod
    def allows(cls, mode: AccessMode, capability: Capability) -> bool:
        return capability in cls.capabilities_for(mode)

    @classmethod
    def require(cls, mode: AccessMode, capability: Capability) -> None:
        if not cls.allows(mode, capability):
            raise CapabilityDeniedError(mode, capability)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Principal:
    """Origin-verified identity passed into one application interaction."""

    mode: AccessMode
    subject: str
    session_id: str | None = None
    expires_at: datetime | None = None
    auth_epoch: int = 0
    key_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.subject, str) or not self.subject.strip():
            raise ValueError("principal subject must not be empty")
        if self.auth_epoch < 0:
            raise ValueError("auth_epoch must be non-negative")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.mode in {AccessMode.ADMIN, AccessMode.GUEST} and (
            not isinstance(self.session_id, str) or not self.session_id.strip()
        ):
            raise ValueError(f"{self.mode.value} principal requires a session_id")
        if self.mode is AccessMode.GUEST and self.expires_at is None:
            raise ValueError("guest principal requires an expiry")

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return self.expires_at is not None and (now or _utc_now()) >= self.expires_at

    def require_active(self, *, now: datetime | None = None) -> None:
        if self.is_expired(now=now):
            raise PrincipalExpiredError(f"{self.mode.value} session has expired")


@dataclass(frozen=True)
class PageContext:
    """Verified identity plus the adapters used by one rendered page."""

    principal: Principal
    capabilities: frozenset[Capability]
    workspace: Any = None
    preference_store: Any = None
    request_reference: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        expected = CapabilityPolicy.capabilities_for(self.principal.mode)
        if self.capabilities != expected:
            raise ValueError("page context capabilities must match the verified access mode")

    @classmethod
    def create(
        cls,
        principal: Principal,
        *,
        workspace: Any = None,
        preference_store: Any = None,
        request_reference: str = "",
        metadata: dict[str, str] | None = None,
    ) -> "PageContext":
        return cls(
            principal=principal,
            capabilities=CapabilityPolicy.capabilities_for(principal.mode),
            workspace=workspace,
            preference_store=preference_store,
            request_reference=request_reference,
            metadata=dict(metadata or {}),
        )

    def allows(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def require(
        self,
        capability: Capability,
        *,
        now: datetime | None = None,
    ) -> None:
        self.principal.require_active(now=now)
        if capability not in self.capabilities or not CapabilityPolicy.allows(
            self.principal.mode,
            capability,
        ):
            raise CapabilityDeniedError(self.principal.mode, capability)

    def require_all(
        self,
        capabilities: Iterable[Capability],
        *,
        now: datetime | None = None,
    ) -> None:
        self.principal.require_active(now=now)
        for capability in capabilities:
            if capability not in self.capabilities:
                raise CapabilityDeniedError(self.principal.mode, capability)


__all__ = [
    "AccessMode",
    "Capability",
    "CapabilityDeniedError",
    "CapabilityPolicy",
    "GUEST_ALLOWED_CAPABILITIES",
    "GUEST_DENIED_CAPABILITIES",
    "PageContext",
    "Principal",
    "PrincipalExpiredError",
]
