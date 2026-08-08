from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nicegui_app.access_context import (
    AccessMode,
    Capability,
    CapabilityDeniedError,
    CapabilityPolicy,
    GUEST_ALLOWED_CAPABILITIES,
    GUEST_DENIED_CAPABILITIES,
    PageContext,
    Principal,
    PrincipalExpiredError,
)


def test_guest_capability_matrix_is_exact_and_deny_by_default() -> None:
    assert CapabilityPolicy.capabilities_for(AccessMode.GUEST) == GUEST_ALLOWED_CAPABILITIES
    assert GUEST_ALLOWED_CAPABILITIES == {
        Capability.DEMO_DATA_READ,
        Capability.DEMO_STATE_MODIFY,
        Capability.DEMO_RESULT_DOWNLOAD,
        Capability.SESSION_PREFERENCES_MODIFY,
    }
    assert GUEST_DENIED_CAPABILITIES == frozenset(set(Capability) - set(GUEST_ALLOWED_CAPABILITIES))
    assert CapabilityPolicy.capabilities_for(AccessMode.PUBLIC) == frozenset(
        {Capability.SUPPORT_REPORT_SUBMIT}
    )

    for capability in GUEST_ALLOWED_CAPABILITIES:
        assert CapabilityPolicy.allows(AccessMode.GUEST, capability)
    for capability in GUEST_DENIED_CAPABILITIES:
        assert not CapabilityPolicy.allows(AccessMode.GUEST, capability)
        with pytest.raises(CapabilityDeniedError):
            CapabilityPolicy.require(AccessMode.GUEST, capability)


def test_admin_and_maintenance_are_explicitly_granted_known_capabilities() -> None:
    for mode in (AccessMode.ADMIN, AccessMode.LOCAL_MAINTENANCE):
        assert CapabilityPolicy.capabilities_for(mode) == frozenset(Capability)


def test_page_context_rechecks_expiry_and_capability_at_execution_time() -> None:
    now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    principal = Principal(
        mode=AccessMode.GUEST,
        subject="guest:hashed-subject",
        session_id="session-1",
        expires_at=now + timedelta(minutes=30),
        auth_epoch=3,
        key_id="guest-v1",
    )
    context = PageContext.create(
        principal,
        workspace=object(),
        preference_store=object(),
        request_reference="REQ-123",
    )

    context.require(Capability.DEMO_STATE_MODIFY, now=now)
    with pytest.raises(CapabilityDeniedError):
        context.require(Capability.PERSISTENT_WRITE, now=now)
    with pytest.raises(PrincipalExpiredError):
        context.require(Capability.DEMO_DATA_READ, now=now + timedelta(minutes=30))
    with pytest.raises(ValueError, match="must match"):
        PageContext(
            principal=principal,
            capabilities=frozenset(Capability),
            request_reference="FORGED",
        )


def test_verified_session_modes_require_session_identity_and_guest_expiry() -> None:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    with pytest.raises(ValueError, match="session_id"):
        Principal(mode=AccessMode.ADMIN, subject="admin", expires_at=expiry)
    with pytest.raises(ValueError, match="expiry"):
        Principal(mode=AccessMode.GUEST, subject="guest", session_id="sid")
    with pytest.raises(ValueError, match="timezone-aware"):
        Principal(
            mode=AccessMode.GUEST,
            subject="guest",
            session_id="sid",
            expires_at=datetime(2026, 7, 17, 12, 0),
        )
