from __future__ import annotations

from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.page_catalog import page_definition
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from tests.ui_source import combined_page_source


def test_access_console_explains_one_site_with_authenticated_editing() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "access_control.py").read_text(encoding="utf-8")
    routes = combined_page_source()

    access_page = page_definition("/access-control")
    assert access_page is not None
    assert (access_page.title_key, access_page.icon) == (
        "access_control",
        "admin_panel_settings",
    )
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
    gateway = (PROJECT_ROOT / "nicegui_app" / "gateway_identity.py").read_text(encoding="utf-8")

    assert "current_page_context()" in shell
    assert "x-sing-yin-origin-principal" in gateway
    assert "x-sing-yin-access-email" not in shell
    assert "data-testid=administrator-mode" in shell
    assert "data-testid=administrator-logout" in shell
    assert "fetch('/auth/logout'" in shell
    assert "data-testid=guest-mode" in shell


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


def test_published_adjustment_immediately_processes_stale_viewer_revocation() -> None:
    weekly = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes" / "weekly.py").read_text(encoding="utf-8")

    adjustment = weekly.split("async def apply_adjustment() -> None:", 1)[1].split(
        'ui.label(t("adjustment_step_reason"))',
        1,
    )[0]
    assert "result.share_ids_to_revoke" in adjustment
    assert "revoke_roster_shares" in adjustment
    assert "adjustment_receipt_share_revoked" in adjustment
    assert "adjustment_receipt_share_pending" in adjustment
    assert "do not retry the adjustment" in MESSAGES["adjustment_share_pending"][EN]
    assert "不要重複提交調整" in MESSAGES["adjustment_share_pending"][ZH_HK]


def test_access_console_can_retry_durable_stale_viewer_revocations() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "ui" / "access_control.py").read_text(encoding="utf-8")

    assert "workflow.pending_external_share_revocations()" in source
    assert "revoke_roster_shares(workflow, share_ids)" in source
    assert "data-testid=pending-public-share-revocations" in source
    assert "data-testid=retry-pending-public-share-revocations" in source
    assert "do not resubmit the roster change" in MESSAGES["public_share_pending_body"][EN]
    assert "不要重複提交值班變更" in MESSAGES["public_share_pending_body"][ZH_HK]


def test_live_viewer_verifier_uses_only_a_temporary_fictional_workflow() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py").read_text(encoding="utf-8")

    assert "tempfile.mkdtemp" in source
    assert 'database_path=temporary_root / "fictional.sqlite3"' in source
    assert "CANONICAL_DATABASE_PATH" not in source
    assert "receipt.share_url" in source
    assert "service.revoke_share" in source


def test_live_viewer_verifier_covers_the_release_entry_contract() -> None:
    source = (PROJECT_ROOT / "scripts" / "verify_public_roster_viewer.py").read_text(encoding="utf-8")

    for helper in (
        "_assert_page_identity",
        "_assert_guest_landing",
        "_assert_public_support",
        "_assert_public_support_network_fallback",
        "_assert_theme_selection",
        "_assert_manual_verse_refresh",
        "_assert_reduced_motion",
        "_assert_read_only_roster",
        "_assert_document_fits_viewport",
    ):
        assert helper in source
    assert 'EXPLICIT_THEME_STATES: Final = ("light", "dark")' in source
    assert 'page.get_by_test_id("public-theme-control")' in source
    assert 'viewport={"width": 1440, "height": 1000}' in source
    assert "_new_mobile_context(" in source
    assert "width=390" in source
    assert "height=844" in source
    assert "width=320" in source
    assert "height=760" in source
    assert 'reduced_motion="reduce"' in source
    assert 'page.locator("#refreshLandingVerse").click()' in source
    assert 'page.locator("#shareSite")' in source
    assert "sing-yin-roster-viewer-theme-v1" in source
    assert 'r"INC-\\d{8}-[A-F0-9]{8}"' in source
    assert 'r"FB-[A-F0-9]{16}"' in source
    assert "import re" in source
    assert 'route.abort("connectionfailed")' in source
    assert '"不包含任何值班表"' in source
    assert 'login_box["height"] < 48' in source
    assert "document.documentElement.scrollWidth" in source
    assert "editable_controls.count() != 0" in source
    assert "console_errors or page_errors" in source
