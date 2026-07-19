"""Shared route hierarchy and workflow navigation components."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nicegui import ui


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One stable destination in a multi-page operator workflow."""

    label: str
    route: str
    icon: str
    state: str = "available"


def render_route_trail(items: Iterable[tuple[str, str | None]], *, label: str) -> None:
    """Render an accessible, explicit route trail without relying on browser history."""

    trail = list(items)
    with ui.element("nav").classes("sy-route-trail w-full").props(f'aria-label="{label}"'):
        for index, (label, route) in enumerate(trail):
            if index:
                ui.icon("chevron_right").classes("sy-route-trail-separator").props("aria-hidden=true")
            if route:
                ui.link(label, route).classes("sy-route-trail-link")
            else:
                ui.label(label).classes("sy-route-trail-current").props("aria-current=page")


def render_back_action(label: str, route: str, *, test_id: str) -> None:
    """Render a predictable return action to the owning page."""

    ui.button(label, icon="arrow_back", on_click=lambda: ui.navigate.to(route)).props(
        f"flat no-caps data-testid={test_id}"
    ).classes("sy-back-action")


def render_workflow_navigation(
    steps: Iterable[WorkflowStep],
    *,
    current_index: int,
    label: str,
) -> None:
    """Show the operator's current location and safe next destinations."""

    with ui.element("nav").classes("sy-workflow-navigation w-full").props(f'aria-label="{label}"'):
        for index, step in enumerate(steps, start=1):
            is_current = index == current_index
            classes = "sy-workflow-navigation-step"
            if is_current:
                classes += " is-current"
            if step.state == "locked":
                classes += " is-locked"
            state_props = []
            if is_current:
                state_props.append("aria-current=step")
            if step.state == "locked":
                state_props.append("disable")
            with ui.button(on_click=lambda route=step.route: ui.navigate.to(route)).props(
                f"flat no-caps {' '.join(state_props)}"
            ).classes(classes):
                ui.label(f"{index:02d}").classes("sy-workflow-navigation-index")
                ui.icon(step.icon).classes("sy-workflow-navigation-icon").props("aria-hidden=true")
                ui.label(step.label).classes("sy-workflow-navigation-label")
