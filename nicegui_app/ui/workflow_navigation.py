"""Shared route hierarchy and workflow navigation components."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from nicegui import ui

from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.navigation import ROUTE_FOCUS_JAVASCRIPT, navigate_to


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
    with ui.element("nav").classes("sy-route-trail w-full").props(f'aria-label="{attr(label)}"'):
        for index, (label, route) in enumerate(trail):
            if index:
                ui.icon("chevron_right").classes("sy-route-trail-separator").props("aria-hidden=true")
            if route:
                ui.link(label, route).on(
                    "click",
                    js_handler=f"() => {{{ROUTE_FOCUS_JAVASCRIPT}}}",
                ).classes("sy-route-trail-link")
            else:
                ui.label(label).classes("sy-route-trail-current").props("aria-current=page")


def render_back_action(label: str, route: str, *, test_id: str) -> None:
    """Render a predictable return action to the owning page."""

    ui.button(label, icon="arrow_back", on_click=lambda: navigate_to(route)).props(
        f"flat no-caps data-testid={test_id}"
    ).classes("sy-back-action")


def render_workflow_navigation(
    steps: Iterable[WorkflowStep],
    *,
    current_index: int,
    label: str,
) -> None:
    """Show the operator's current location and safe next destinations."""

    workflow_steps = tuple(steps)
    if not workflow_steps:
        raise ValueError("Workflow navigation requires at least one step.")
    if current_index < 1 or current_index > len(workflow_steps):
        raise ValueError("Workflow navigation current_index is outside the available steps.")
    invalid_states = {step.state for step in workflow_steps} - {"available", "locked"}
    if invalid_states:
        raise ValueError("Workflow navigation contains an unsupported step state.")

    position = current_index / len(workflow_steps) * 100
    with (
        ui.element("nav")
        .classes("sy-workflow-navigation sy-workflow-navigation--operational-rhythm w-full")
        .props(f'aria-label="{attr(label)}" data-design-direction="B-A-C"')
        .style(f"--sy-workflow-position: {position:.2f}%")
    ):
        for index, step in enumerate(workflow_steps, start=1):
            is_current = index == current_index
            semantic_state = "current" if is_current else step.state
            classes = "sy-workflow-navigation-step"
            if is_current:
                classes += " is-current"
            if step.state == "locked":
                classes += " is-locked"
            if is_current:
                classes += " sy-workflow-navigation-content"
                control = ui.element("div").props("aria-current=step")
            else:
                state_props = "disable aria-disabled=true" if step.state == "locked" else ""
                control = ui.button(on_click=lambda route=step.route: navigate_to(route)).props(
                    f"flat no-caps {state_props}"
                )
            with control.classes(classes).props(f"data-state={semantic_state}"):
                ui.label(f"{index:02d}").classes("sy-workflow-navigation-index")
                ui.icon(step.icon).classes("sy-workflow-navigation-icon").props("aria-hidden=true")
                ui.label(step.label).classes("sy-workflow-navigation-label")
