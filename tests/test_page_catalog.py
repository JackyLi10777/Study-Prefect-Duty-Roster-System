from __future__ import annotations

from nicegui_app.access_context import AccessMode, Capability, CapabilityPolicy
from nicegui_app.config import PROJECT_ROOT
from nicegui_app.ui.page_catalog import (
    PAGE_DEFINITIONS,
    PageKind,
    mobile_navigation_for,
    navigation_groups_for,
    page_definition,
    validate_page_catalog,
)


def test_page_catalog_is_complete_unique_and_translation_independent() -> None:
    assert validate_page_catalog() == []
    assert len({page.route for page in PAGE_DEFINITIONS}) == len(PAGE_DEFINITIONS)
    assert {page.page_kind for page in PAGE_DEFINITIONS} == set(PageKind)
    assert page_definition("/") is not None
    assert page_definition("rosters") == page_definition("/rosters")
    assert page_definition("/not-a-page") is None


def test_admin_guest_and_maintenance_navigation_share_one_ordered_catalog() -> None:
    expected_routes = [page.route for page in PAGE_DEFINITIONS]
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
        assert [page.route for page in mobile_navigation_for(mode)] == [
            "/",
            "/rosters",
            "/prefects",
        ]
    assert navigation_groups_for(AccessMode.PUBLIC) == ()
    assert mobile_navigation_for(AccessMode.PUBLIC) == ()


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
    assert "for page in pages:" in shell
    assert "active_page.is_visible_to(access_mode)" in shell
    assert "page_context.require(active_page.required_capability)" in shell
    assert "title_key = active_page.title_key" in shell
    assert "active_page.page_kind.value" in shell
    assert "active_page.music_context" in shell
    assert 'data-sy-page-kind="{page_kind}"' in shell
    assert "sy-page-kind-{page_kind}" in shell

    route_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes").glob("*.py")
    )
    assert "music_context=" not in route_sources
    assert 'page_shell("dashboard", "/")' not in route_sources
