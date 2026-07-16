from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from urllib.parse import unquote

import pytest
from starlette.requests import Request

from nicegui_app.gateway_identity import (
    ORIGIN_PRINCIPAL_AUDIENCE,
    ORIGIN_PRINCIPAL_HEADER,
    ORIGIN_PRINCIPAL_VERSION,
    origin_request_binding,
    seal_origin_principal_for_test,
)
import nicegui_app.main as main_module
from nicegui_app.main import (
    cleanup_guest_downloads,
    guest_download,
    restore_guest_snapshot,
)
from nicegui_app.services.guest_downloads import (
    GuestDownloadCapacityError,
    GuestDownloadError,
    GuestDownloadRegistry,
    guest_download_registry,
)


SECRET = "guest-download-test-secret-that-is-long-enough"
HOST = "roster.example.test"
SESSION_A = "A" * 22
SESSION_B = "B" * 22


def _principal_request(
    path: str,
    *,
    session_id: str,
    method: str = "GET",
    now: int | None = None,
    body: bytes = b"",
) -> Request:
    current = int(datetime.now(timezone.utc).timestamp()) if now is None else now
    environment = {
        "ORIGIN_PRINCIPAL_SECRET": SECRET,
        "AUTH_EPOCH": "1",
        "ORIGIN_PRINCIPAL_KID": "origin-v1",
    }
    token = seal_origin_principal_for_test(
        {
            "v": ORIGIN_PRINCIPAL_VERSION,
            "aud": ORIGIN_PRINCIPAL_AUDIENCE,
            "mode": "guest",
            "subject": "guest-demo",
            "sid": session_id,
            "iat": current,
            "exp": current + 600,
            "auth_epoch": 1,
            "kid": "origin-v1",
            "request_binding": origin_request_binding(
                method=method,
                public_host=HOST,
                path_and_query=path,
            ),
        },
        environment=environment,
    )
    headers = [
        (b"host", HOST.encode("ascii")),
        (b"x-forwarded-host", HOST.encode("ascii")),
        (ORIGIN_PRINCIPAL_HEADER.encode("ascii"), token.encode("ascii")),
    ]
    if body:
        headers.extend(
            [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": (HOST, 443),
        },
        receive=receive,
    )


def _configure_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORIGIN_PRINCIPAL_SECRET", SECRET)
    monkeypatch.setenv("AUTH_EPOCH", "1")
    monkeypatch.setenv("ORIGIN_PRINCIPAL_KID", "origin-v1")
    monkeypatch.setenv("SING_YIN_REQUIRE_GATEWAY_PRINCIPAL", "1")


def test_registry_is_session_bound_single_use_and_bounded() -> None:
    registry = GuestDownloadRegistry(
        ttl_seconds=30,
        max_download_bytes=16,
        max_downloads=2,
        max_downloads_per_session=1,
    )
    ticket = registry.issue(
        session_id=SESSION_A,
        filename="SYSS_DEMO.json",
        content=b"demo",
        media_type="application/json",
        now=100,
    )

    with pytest.raises(GuestDownloadError):
        registry.consume(token=ticket.token, session_id=SESSION_B, now=101)
    with pytest.raises(GuestDownloadCapacityError):
        registry.issue(
            session_id=SESSION_A,
            filename="another.json",
            content=b"demo",
            media_type="application/json",
            now=101,
        )

    payload = registry.consume(token=ticket.token, session_id=SESSION_A, now=101)
    assert payload.content == b"demo"
    with pytest.raises(GuestDownloadError):
        registry.consume(token=ticket.token, session_id=SESSION_A, now=101)


def test_registry_rejects_expiry_oversize_and_unsafe_filename() -> None:
    registry = GuestDownloadRegistry(ttl_seconds=1, max_download_bytes=4)
    ticket = registry.issue(
        session_id=SESSION_A,
        filename="demo.pdf",
        content=b"%PDF",
        media_type="application/pdf",
        now=100,
    )
    with pytest.raises(GuestDownloadError):
        registry.consume(token=ticket.token, session_id=SESSION_A, now=101)
    with pytest.raises(GuestDownloadCapacityError):
        registry.issue(
            session_id=SESSION_A,
            filename="demo.pdf",
            content=b"12345",
            media_type="application/pdf",
            now=102,
        )
    with pytest.raises(GuestDownloadError):
        registry.issue(
            session_id=SESSION_A,
            filename="../demo.pdf",
            content=b"%PDF",
            media_type="application/pdf",
            now=102,
        )


def test_guest_download_endpoint_is_no_store_session_bound_and_single_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_gateway(monkeypatch)
    registry = guest_download_registry()
    ticket = registry.issue(
        session_id=SESSION_A,
        filename="SYSS_DEMO_服務報告.pdf",
        content=b"%PDF-1.4 demo",
        media_type="application/pdf",
    )
    path = f"/api/guest/download/{ticket.token}"

    wrong_session = guest_download(
        ticket.token,
        _principal_request(path, session_id=SESSION_B),
    )
    assert wrong_session.status_code == 404

    response = guest_download(
        ticket.token,
        _principal_request(path, session_id=SESSION_A),
    )
    assert response.status_code == 200
    assert response.body == b"%PDF-1.4 demo"
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    disposition = response.headers["content-disposition"]
    assert "attachment" in disposition
    assert unquote(disposition.split("filename*=UTF-8''", 1)[1]) == "SYSS_DEMO_服務報告.pdf"

    replay = guest_download(
        ticket.token,
        _principal_request(path, session_id=SESSION_A),
    )
    assert replay.status_code == 404


def test_guest_logout_cleanup_removes_pending_downloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_gateway(monkeypatch)
    registry = guest_download_registry()
    ticket = registry.issue(
        session_id=SESSION_A,
        filename="SYSS_DEMO.json",
        content=b"{}",
        media_type="application/json",
    )
    path = "/api/guest/downloads/cleanup"

    response = cleanup_guest_downloads(
        _principal_request(path, session_id=SESSION_A, method="POST")
    )

    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store, max-age=0"
    with pytest.raises(GuestDownloadError):
        registry.consume(token=ticket.token, session_id=SESSION_A)


def test_guest_snapshot_restore_endpoint_is_bounded_authenticated_and_no_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_gateway(monkeypatch)
    captured: list[dict[str, str]] = []

    def restore(**kwargs):  # type: ignore[no-untyped-def]
        captured.append(kwargs)
        return {
            "accepted": True,
            "restored": False,
            "revision": 3,
            "workspaceId": kwargs["workspace_id"],
            "tabId": kwargs["tab_id"],
            "token": "signed-fresh-token",
        }

    monkeypatch.setattr(main_module, "restore_guest_browser_snapshot", restore)
    payload = {
        "workspaceId": "workspace-a",
        "tabId": "tab-a",
        "nonce": "N" * 32,
        "token": "signed-browser-token",
    }
    body = json.dumps(payload).encode("utf-8")
    path = "/api/guest/snapshot/restore"

    response = asyncio.run(
        restore_guest_snapshot(
            _principal_request(
                path,
                session_id=SESSION_A,
                method="POST",
                body=body,
            )
        )
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, max-age=0"
    assert response.headers["pragma"] == "no-cache"
    assert captured == [
        {
            "session_id": SESSION_A,
            "workspace_id": "workspace-a",
            "tab_id": "tab-a",
            "nonce": "N" * 32,
            "token": "signed-browser-token",
        }
    ]

    malformed = asyncio.run(
        restore_guest_snapshot(
            _principal_request(
                path,
                session_id=SESSION_A,
                method="POST",
                body=b'{"token":"missing binding"}',
            )
        )
    )
    assert malformed.status_code == 404
