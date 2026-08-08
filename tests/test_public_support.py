from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from starlette.requests import Request

from nicegui_app.access_context import AccessMode
from nicegui_app.gateway_identity import (
    ORIGIN_PRINCIPAL_AUDIENCE,
    ORIGIN_PRINCIPAL_HEADER,
    ORIGIN_PRINCIPAL_VERSION,
    origin_request_binding,
    seal_origin_principal_for_test,
)
import nicegui_app.main as main_module
from nicegui_app.services import public_support
from nicegui_app.services.support_incidents import (
    InboxLimits,
    IncidentValidationError,
    SupportInbox,
)


_ORIGIN_ENVIRONMENT = {
    "ORIGIN_PRINCIPAL_SECRET": "public-support-test-secret-that-is-long-enough",
    "AUTH_EPOCH": "1",
    "ORIGIN_PRINCIPAL_KID": "origin-v1",
}
_ORIGIN_HOST = "roster.example.test"


def _public_request(chunks: tuple[bytes, ...], *, declared_length: int | None = None) -> Request:
    now = int(datetime.now(timezone.utc).timestamp())
    path = "/api/support/incidents"
    token = seal_origin_principal_for_test(
        {
            "v": ORIGIN_PRINCIPAL_VERSION,
            "aud": ORIGIN_PRINCIPAL_AUDIENCE,
            "mode": AccessMode.PUBLIC.value,
            "subject": "public-support",
            "sid": "P" * 22,
            "iat": now,
            "exp": now + 60,
            "auth_epoch": 1,
            "kid": "origin-v1",
            "request_binding": origin_request_binding(
                method="POST",
                public_host=_ORIGIN_HOST,
                path_and_query=path,
            ),
        },
        environment=_ORIGIN_ENVIRONMENT,
    )
    headers = [
        (b"host", _ORIGIN_HOST.encode("ascii")),
        (b"x-forwarded-host", _ORIGIN_HOST.encode("ascii")),
        (b"content-type", b"application/json"),
        (ORIGIN_PRINCIPAL_HEADER.encode("ascii"), token.encode("ascii")),
    ]
    if declared_length is not None:
        headers.append((b"content-length", str(declared_length).encode("ascii")))
    pending = list(chunks)

    async def receive() -> dict[str, object]:
        chunk = pending.pop(0) if pending else b""
        return {"type": "http.request", "body": chunk, "more_body": bool(pending)}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": (_ORIGIN_HOST, 443),
        },
        receive=receive,
    )


def _configure_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _ORIGIN_ENVIRONMENT.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SING_YIN_REQUIRE_GATEWAY_PRINCIPAL", "1")


def _payload() -> dict[str, str]:
    return {
        "source": "public_entrance",
        "category": "access",
        "expected_behavior": "登入頁應跟隨深色模式",
        "actual_behavior": "support page stayed light; user@example.test",
        "reproduction_steps": "1. Select dark mode\n2. Open the support page",
        "impact": "Cannot read comfortably",
    }


def _inbox(root: Path) -> SupportInbox:
    return SupportInbox(
        root,
        limits=InboxLimits(
            root_bytes=4 * 1024 * 1024,
            incidents_per_day=20,
            incident_count=40,
            minimum_free_bytes=1024 * 1024,
        ),
    )


def test_public_report_is_text_only_redacted_and_traceable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(public_support, "release_source_fingerprint", lambda: ("f" * 64, 313))
    monkeypatch.setattr(
        public_support,
        "current_application_mode",
        lambda: type("Mode", (), {"mode": "production"})(),
    )
    monkeypatch.setenv("SING_YIN_RELEASE_VERSION", "v1.2.0-test")
    inbox = _inbox(tmp_path / "support")

    submission = public_support.create_public_support_incident(
        _payload(),
        request_reference="REQ-1234ABCD",
        inbox=inbox,
    )

    summary = inbox.validate_bundle(submission.incident_id)
    bundle = inbox.inbox / submission.incident_id
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    report = (bundle / "report.md").read_text(encoding="utf-8")
    assert summary.incident_id == submission.incident_id
    assert manifest["source"] == "public_ui"
    assert manifest["actor_mode"] == "public"
    assert manifest["request_references"] == ["REQ-1234ABCD"]
    assert manifest["attachment_manifest"] == []
    assert "user@example.test" not in report
    assert "[REDACTED EMAIL]" in report


@pytest.mark.parametrize(
    "mutation",
    (
        lambda payload: payload.pop("impact"),
        lambda payload: payload.__setitem__("unexpected", "value"),
        lambda payload: payload.__setitem__("source", "admin"),
        lambda payload: payload.__setitem__("expected_behavior", ""),
        lambda payload: payload.__setitem__("reproduction_steps", ""),
        lambda payload: payload.__setitem__("actual_behavior", "x" * 1_201),
    ),
)
def test_public_report_rejects_non_exact_or_unbounded_payloads(mutation) -> None:  # type: ignore[no-untyped-def]
    payload = _payload()
    mutation(payload)

    with pytest.raises(IncidentValidationError):
        public_support.report_from_public_payload(payload)


def test_public_viewer_other_reports_are_classified_as_viewer() -> None:
    payload = _payload()
    payload.update(source="public_viewer", category="other")

    report = public_support.report_from_public_payload(payload)

    assert report.route_category == "viewer"
    assert report.workflow_action == "page_view"


def test_public_support_endpoint_accepts_only_the_signed_bounded_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_origin(monkeypatch)
    captured: list[object] = []

    def create(payload: object, *, request_reference: str = "") -> public_support.PublicSupportSubmission:
        captured.append((payload, request_reference))
        return public_support.PublicSupportSubmission("INC-20260808-1234ABCD")

    monkeypatch.setattr(main_module, "create_public_support_incident", create)
    body = json.dumps(_payload(), ensure_ascii=False).encode("utf-8")

    response = asyncio.run(main_module.submit_public_support_incident(_public_request((body,))))

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "status": "saved",
        "incidentId": "INC-20260808-1234ABCD",
    }
    assert captured and captured[0][0] == _payload()


def test_public_support_endpoint_rejects_chunked_overflow_before_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_origin(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "create_public_support_incident",
        lambda *_args, **_kwargs: pytest.fail("oversized report reached storage"),
    )

    response = asyncio.run(
        main_module.submit_public_support_incident(
            _public_request((b"a" * 10_000, b"b" * 6_385))
        )
    )

    assert response.status_code == 413
    assert json.loads(response.body)["error"] == "request_too_large"


def test_public_report_stream_stops_at_the_memory_boundary() -> None:
    async def chunks():
        yield b"a" * 10_000
        yield b"b" * 6_384

    body = asyncio.run(public_support.read_bounded_public_support_body(chunks()))

    assert len(body) == public_support.PUBLIC_SUPPORT_MAX_BODY_BYTES


def test_public_report_stream_rejects_chunked_overflow() -> None:
    consumed = 0

    async def chunks():
        nonlocal consumed
        for chunk in (b"a" * 10_000, b"b" * 6_385, b"must-not-be-read"):
            consumed += 1
            yield chunk

    with pytest.raises(public_support.PublicSupportRequestTooLarge):
        asyncio.run(public_support.read_bounded_public_support_body(chunks()))

    assert consumed == 2
