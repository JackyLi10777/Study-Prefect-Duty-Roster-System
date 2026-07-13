from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from tests.ui_source import combined_page_source


def test_access_console_explains_one_site_with_authenticated_editing() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "access_control.py").read_text(encoding="utf-8")
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    routes = combined_page_source()

    assert '("/access-control", "access_control", "admin_panel_settings")' in shell
    assert '@ui.page("/access-control")' in routes
    assert "data-testid=operator-access-card" in source
    assert "data-testid=viewer-access-card" in source
    assert "PublicRosterShareService" in source
    assert "SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN" not in source
    assert "same website" in MESSAGES["access_operator_body"][EN]
    assert "同一個網站" in MESSAGES["access_operator_body"][ZH_HK]
    assert "Cloudflare Access" in MESSAGES["access_operator_body"][EN]


def test_authenticated_gateway_identity_adds_admin_state_and_logout() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")

    assert 'request.headers.get("x-sing-yin-access-email"' in shell
    assert "data-testid=administrator-mode" in shell
    assert "data-testid=administrator-logout" in shell
    assert 'ui.navigate.to("/logout")' in shell


def test_public_share_ui_requires_confirmation_and_shows_keyed_link_once() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "access_control.py").read_text(encoding="utf-8")

    for test_id in (
        "public-share-confirm-dialog",
        "confirm-create-public-share",
        "public-share-receipt-dialog",
        "public-share-url",
        "confirm-revoke-public-share",
    ):
        assert test_id in source
    assert "service.create_share" in source
    assert "service.revoke_share" in source
    assert "navigator.clipboard.writeText" in source


def test_public_share_action_is_available_only_inside_published_roster_branch() -> None:
    weekly = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py").read_text(encoding="utf-8")
    published_branch = weekly.split('if week["status"] == "draft":', 3)[-1]

    assert "render_roster_share_action(workflow, roster_week_id)" in published_branch


def test_live_viewer_verifier_uses_only_a_temporary_fictional_workflow() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py").read_text(encoding="utf-8")

    assert "tempfile.mkdtemp" in source
    assert 'database_path=temporary_root / "fictional.sqlite3"' in source
    assert "CANONICAL_DATABASE_PATH" not in source
    assert "receipt.share_url" in source
    assert "service.revoke_share" in source
