from __future__ import annotations

from nicegui_app.access_context import AccessMode, Capability, CapabilityPolicy
from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.page_catalog import (
    NAVIGATION_GROUP_ORDER,
    PAGE_DEFINITIONS,
    PORTAL_GROUP,
    PageKind,
    mobile_navigation_for,
    navigation_groups_for,
    page_definition,
    portal_pages_for,
    validate_page_catalog,
)
from nicegui_app.ui.theme import ATMOSPHERE_THEME_PAIRS


def test_page_catalog_is_complete_unique_and_translation_independent() -> None:
    assert validate_page_catalog() == []
    assert len({page.route for page in PAGE_DEFINITIONS}) == len(PAGE_DEFINITIONS)
    assert {page.page_kind for page in PAGE_DEFINITIONS} == set(PageKind)
    assert page_definition("/") is not None
    assert page_definition("rosters") == page_definition("/rosters")
    assert page_definition("/not-a-page") is None


def test_admin_guest_and_maintenance_navigation_share_one_ordered_catalog() -> None:
    assert NAVIGATION_GROUP_ORDER == (
        "nav_getting_started",
        "nav_weekly_operations",
        "nav_people_fairness",
        "nav_handover_governance",
        "nav_administration",
        "nav_contextual_help",
    )
    expected_routes = [
        page.route
        for group in NAVIGATION_GROUP_ORDER
        for page in PAGE_DEFINITIONS
        if page.navigation_group == group
    ]
    expected_portals = [
        page.route for page in PAGE_DEFINITIONS if page.navigation_group == PORTAL_GROUP
    ]
    for mode in (
        AccessMode.ADMIN,
        AccessMode.GUEST,
        AccessMode.LOCAL_MAINTENANCE,
    ):
        grouped_routes = [
            page.route
            for _group, pages in navigation_groups_for(mode)
            for page in pages
        ]
        assert grouped_routes == expected_routes
        assert [page.route for page in portal_pages_for(mode)] == expected_portals
        assert [page.route for page in mobile_navigation_for(mode)] == [
            "/",
            "/rosters",
            "/prefects",
        ]
    assert navigation_groups_for(AccessMode.PUBLIC) == ()
    assert mobile_navigation_for(AccessMode.PUBLIC) == ()
    assert portal_pages_for(AccessMode.PUBLIC) == ()


def test_every_visible_page_capability_is_granted_server_side() -> None:
    for page in PAGE_DEFINITIONS:
        if page.required_capability is None:
            continue
        assert isinstance(page.required_capability, Capability)
        for mode in page.visible_access_modes:
            assert CapabilityPolicy.allows(mode, page.required_capability)


def test_desktop_and_mobile_shell_read_the_page_catalog() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(
        encoding="utf-8"
    )
    assert "navigation_groups_for(access_mode)" in shell
    assert "mobile_navigation_for(access_mode)" in shell
    assert "portal_pages_for(access_mode)" in shell
    assert "for page in pages:" in shell
    assert "active_page.is_visible_to(access_mode)" in shell
    assert "page_context.require(active_page.required_capability)" in shell
    assert "title_key = active_page.title_key" in shell
    assert "active_page.page_kind.value" in shell
    assert "active_page.music_context" in shell
    assert "active_page.atmosphere_slot" in shell
    assert 'active_page.atmosphere_presentation == "shell"' in shell
    assert '"sy-page-atmosphere"' in shell
    assert "--sy-page-atmosphere-image: var(--sy-image-" in shell
    assert 'data-sy-page-kind="{page_kind}"' in shell
    assert "sy-page-kind-{page_kind}" in shell

    route_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes").glob("*.py")
    )
    assert "music_context=" not in route_sources
    assert 'page_shell("dashboard", "/")' not in route_sources


def test_every_page_has_one_registered_atmosphere_and_one_presentation_mode() -> None:
    expected = {
        "/": ("weekly-pulse", "embedded"),
        "/rosters": ("weekly-operations", "shell"),
        "/prefects": ("people-fairness", "shell"),
        "/handover": ("handover", "embedded"),
        "/access-control": ("administration-recovery", "shell"),
        "/settings": ("administration-recovery", "shell"),
        "/platform": ("platform", "embedded"),
        "/system-architecture": ("architecture", "embedded"),
        "/engineering": ("engineering", "embedded"),
        "/getting-started": ("onboarding", "embedded"),
        "/guide": ("guide", "embedded"),
        "/devotional": ("devotional", "embedded"),
        "/support": ("support-lifeline", "shell"),
    }

    assert {
        page.route: (page.atmosphere_slot, page.atmosphere_presentation)
        for page in PAGE_DEFINITIONS
    } == expected
    assert all(page.atmosphere_slot in ATMOSPHERE_THEME_PAIRS for page in PAGE_DEFINITIONS)


def test_shell_atmosphere_is_a_noninteractive_band_after_page_context() -> None:
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(
        encoding="utf-8"
    )
    narrative = (
        PROJECT_ROOT
        / "nicegui_app"
        / "assets"
        / "css"
        / "sing-yin-narrative-v1.css"
    ).read_text(encoding="utf-8")

    context_index = shell.index('classes("sy-page-context")')
    atmosphere_index = shell.index('"sy-page-atmosphere"')
    content_index = shell.index("        yield", atmosphere_index)
    assert context_index < atmosphere_index < content_index
    assert "aria-hidden=true" in shell[atmosphere_index:content_index]
    assert "pointer-events: none" in narrative.split(
        ".sy-page-atmosphere::before", 1
    )[1].split("}", 1)[0]
    atmosphere_rules = narrative.split("/* ---------- Brand lockup", 1)[0]
    for sensitive_selector in (
        ".q-table",
        ".q-field",
        ".q-dialog",
        ".sy-roster-mobile-prefect",
        ".sy-fairness",
    ):
        assert sensitive_selector not in atmosphere_rules
