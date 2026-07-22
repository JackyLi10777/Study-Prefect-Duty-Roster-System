"""Shared accessible navigation helpers for the NiceGUI workbench."""

from __future__ import annotations

from nicegui import ui

ROUTE_FOCUS_JAVASCRIPT = "sessionStorage.setItem('sy:route-focus', 'main');"


def mark_route_focus() -> None:
    """Ask the destination page to announce its main landmark after navigation."""

    ui.run_javascript(ROUTE_FOCUS_JAVASCRIPT)


def navigate_to(route: str) -> None:
    """Navigate to a shared route while preserving keyboard and AT context."""

    mark_route_focus()
    ui.navigate.to(route)
