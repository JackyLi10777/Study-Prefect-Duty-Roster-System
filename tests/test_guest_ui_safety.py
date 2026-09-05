from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from nicegui_app.access_context import (
    AccessMode,
    CapabilityDeniedError,
    PageContext,
    Principal,
)
from nicegui_app.services.music_library import (
    BUILTIN_TRACKS,
    MusicLibrary,
    MusicTrack,
    builtin_tracks_for_context,
)
from nicegui_app.services.guest_downloads import (
    GuestDownloadCapacityError,
    GuestDownloadTicket,
)
from nicegui_app.ui import access_control, downloads, music


def _guest_context() -> PageContext:
    return PageContext.create(
        Principal(
            mode=AccessMode.GUEST,
            subject="guest-demo",
            session_id="guest-session",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
    )


def test_guest_share_capability_fails_before_external_service_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructed = 0

    def forbidden_constructor(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal constructed
        constructed += 1
        raise AssertionError("external share service must not be constructed")

    monkeypatch.setattr(access_control, "current_page_context", _guest_context)
    monkeypatch.setattr(access_control, "PublicRosterShareService", forbidden_constructor)

    with pytest.raises(CapabilityDeniedError):
        access_control._public_share_service(object(), settings=object())  # type: ignore[arg-type]

    assert constructed == 0


def test_guest_playlist_uses_bundled_tracks_without_opening_custom_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundled = MusicTrack(
        id="demo-bundled",
        filename="bundled.m4a",
        title="Bundled",
        artist="Fixture",
        duration="",
        contexts=("dashboard",),
    )

    def forbidden_library():  # type: ignore[no-untyped-def]
        raise AssertionError("guest playlist must not open MusicLibrary")

    monkeypatch.setattr(music, "MusicLibrary", forbidden_library)
    monkeypatch.setattr(
        music,
        "builtin_tracks_for_context",
        lambda context, *, profile: [bundled],
    )

    assert music._tracks_for_page(
        "dashboard",
        profile="quiet",
        guest_mode=True,
    ) == [bundled]


def test_bundled_track_lookup_never_reads_custom_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = next(track for track in BUILTIN_TRACKS if "dashboard" in track.contexts)
    asset = tmp_path / selected.filename
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"fixture")
    monkeypatch.setattr(
        MusicLibrary,
        "_state",
        lambda self: (_ for _ in ()).throw(AssertionError("custom manifest opened")),
    )

    tracks = builtin_tracks_for_context("dashboard", root=tmp_path)

    assert selected in tracks


def test_shared_shell_revalidates_identity_and_clears_guest_tab_state() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "ui"
        / "shell.py"
    ).read_text(encoding="utf-8")

    assert "fetch('/auth/status'" in source
    assert "cache: 'no-store'" in source
    assert "status.authenticated !== true" in source
    assert "status.mode !== expectedMode" in source
    assert "sessionStorage.clear()" in source
    assert "sing-yin-guest-session-v1" in source
    assert "/api/guest/downloads/cleanup" in source
    assert "window.setTimeout(check, 45_000)" in source
    assert "scheduleExpiry(principalExpiresAt)" in source
    assert "window.addEventListener('pageshow', onPageShow)" in source
    assert "if (event.persisted) check()" in source
    assert "_install_auth_status_monitor(access_mode, page_context.principal.expires_at)" in source


def test_guest_published_roster_renders_restricted_share_state() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "ui"
        / "access_control.py"
    ).read_text(encoding="utf-8")

    assert "data-testid=guest-public-share-restricted" in source
    assert "if not _external_share_allowed():" in source
    assert "current_page_context().require(Capability.EXTERNAL_DELIVERY)" in source
    copy_body = source.split("async def _copy_value", 1)[1].split(
        "def _show_share_receipt", 1
    )[0]
    assert "require(Capability.EXTERNAL_DELIVERY)" in copy_body
    assert "navigator.clipboard?.writeText" in copy_body
    assert "window.prompt" in copy_body
    assert "copy_failed_manual" in copy_body


def test_guest_generated_file_uses_single_use_server_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scripts: list[str] = []
    direct_downloads: list[object] = []
    issued: list[dict[str, object]] = []

    class FakeRegistry:
        def issue(self, **kwargs):  # type: ignore[no-untyped-def]
            issued.append(kwargs)
            return GuestDownloadTicket(token="A" * 43, expires_at=1_800_000_000)

    monkeypatch.setattr(downloads, "current_page_context", _guest_context)
    monkeypatch.setattr(downloads, "guest_download_registry", FakeRegistry)
    monkeypatch.setattr(downloads.ui, "run_javascript", scripts.append)
    monkeypatch.setattr(
        downloads.ui,
        "download",
        lambda *args, **kwargs: direct_downloads.append((args, kwargs)),
    )

    delivered = downloads.deliver_generated_download(
        b"fictional-demo",
        "SYSS_DEMO_report.json",
        media_type="application/json",
    )

    assert delivered is True
    assert direct_downloads == []
    assert issued == [
        {
            "access_mode": AccessMode.GUEST,
            "session_id": "guest-session",
            "filename": "SYSS_DEMO_report.json",
            "content": b"fictional-demo",
            "media_type": "application/json",
        }
    ]
    assert len(scripts) == 1
    assert "/api/generated-download/" + ("A" * 43) in scripts[0]
    assert "response.blob()" in scripts[0]
    assert "response.headers.get('Content-Type')" in scripts[0]
    assert "actualType!==expectedType" in scripts[0]
    assert "application/json" in scripts[0]
    assert scripts[0].index("actualType!==expectedType") < scripts[0].index("response.blob()")
    assert "fetch(" in scripts[0]
    assert "credentials:'same-origin'" in scripts[0]
    assert "URL.revokeObjectURL" in scripts[0]


def test_generated_file_capacity_failure_is_reported_to_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notifications: list[tuple[object, object]] = []

    class FullRegistry:
        def issue(self, **_kwargs):  # type: ignore[no-untyped-def]
            raise GuestDownloadCapacityError("capacity exhausted")

    monkeypatch.setattr(downloads, "current_page_context", _guest_context)
    monkeypatch.setattr(downloads, "guest_download_registry", FullRegistry)
    monkeypatch.setattr(
        downloads.ui,
        "notify",
        lambda message, **kwargs: notifications.append((message, kwargs.get("type"))),
    )
    monkeypatch.setattr(downloads, "new_request_reference", lambda: "REQ-CAPACITY")

    delivered = downloads.deliver_generated_download(
        b"fictional-demo",
        "SYSS_DEMO_report.json",
        media_type="application/json",
    )

    assert delivered is False
    assert notifications and notifications[-1][1] == "warning"
    assert "REQ-CAPACITY" in str(notifications[-1][0])


def test_generated_file_callers_do_not_report_success_after_delivery_failure() -> None:
    root = Path(__file__).resolve().parents[1] / "nicegui_app" / "ui"
    source_contracts = {
        root / "page_shared.py": (
            "if not deliver_generated_download(",
            'ui.notify(t("pdf_ready"), type="positive")',
        ),
        root / "page_routes" / "people.py": (
            "if not deliver_generated_download(",
            'ui.notify(t("summary_export_ready"), type="positive")',
        ),
        root / "page_routes" / "stewardship.py": (
            "if not deliver_generated_download(",
            "handover_package_dialog.close()",
        ),
    }

    for source_path, (guard, success_action) in source_contracts.items():
        source = source_path.read_text(encoding="utf-8")
        guard_offset = source.index(guard)
        success_offset = source.index(success_action, guard_offset)
        guarded_region = source[guard_offset:success_offset]
        assert "return" in guarded_region, source_path
