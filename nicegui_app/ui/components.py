"""Public, semantic NiceGUI components shared by every access mode.

The application deliberately keeps NiceGUI and Quasar as its only frontend
runtime.  This module translates mature component-library principles into a
small Python API: every control exposes a complete state, semantic colour is
chosen by purpose, and Admin/Guest pages render the same DOM skeleton.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import contextmanager
from itertools import count
import json
from typing import Iterator, Literal, TypeVar

from nicegui import ui

from nicegui_app.ui.html_safety import attr, text
from nicegui_app.ui.i18n import t
from nicegui_app.ui.reference_navigation import (
    ReferenceDestination,
    ReferenceItem,
    render_page_toc,
    render_reference_pager,
)


ActionVariant = Literal["primary", "secondary", "quiet", "attention", "danger"]
StatusTone = Literal["action", "stable", "attention", "danger", "neutral"]
WorkflowState = Literal["active", "done", "pending"]
_Control = TypeVar("_Control")
_FIELD_SEQUENCE = count(1)


def action(
    text: str,
    *,
    icon: str | None = None,
    on_click: Callable[..., object] | None = None,
    variant: ActionVariant = "primary",
    busy: bool = False,
    disabled: bool = False,
    test_id: str | None = None,
    classes: str = "",
):
    """Render one action with complete hover, busy and disabled semantics."""

    props = {
        "primary": "color=primary",
        "secondary": "outline color=primary",
        "quiet": "flat",
        "attention": "outline",
        "danger": "color=negative",
    }[variant]
    if busy:
        props += " loading disable aria-busy=true"
    elif disabled:
        props += " disable aria-disabled=true"
    if test_id:
        props += f" data-testid={test_id}"
    button = ui.button(text, icon=icon, on_click=on_click).props(props).classes(
        f"sy-action sy-action--{variant} {classes}".strip()
    )
    return button


def field(
    *,
    label: str,
    control_factory: Callable[[], _Control],
    description: str | None = None,
    optional: bool = False,
    error: str | None = None,
    read_only: bool = False,
    test_id: str | None = None,
) -> _Control:
    """Render a labelled field with persistent help/error and focus metadata."""

    sequence = next(_FIELD_SEQUENCE)
    label_id = f"sy-field-label-{sequence}"
    description_id = f"sy-field-description-{sequence}"
    error_id = f"sy-field-error-{sequence}"
    wrapper_props = ["role=group", f"aria-labelledby={label_id}"]
    if error:
        wrapper_props.append("data-invalid=true")
    if read_only:
        wrapper_props.append("data-readonly=true")
    if test_id:
        wrapper_props.append(f"data-testid={test_id}")

    with ui.element("div").classes("sy-field w-full").props(" ".join(wrapper_props)):
        with ui.row().classes("sy-field-heading w-full items-baseline gap-2"):
            ui.label(label).classes("sy-field-label").props(f"id={label_id}")
            if optional:
                ui.label(t("optional")).classes("sy-field-optional")
        control = control_factory()
        described_by: list[str] = []
        if description:
            ui.label(description).classes("sy-field-description").props(f"id={description_id}")
            described_by.append(description_id)
        if error:
            ui.label(error).classes("sy-field-error").props(f"id={error_id} role=alert aria-live=polite")
            described_by.append(error_id)
        control_props = [f"aria-labelledby={label_id}"]
        if described_by:
            control_props.append(f"aria-describedby={' '.join(described_by)}")
        if error:
            control_props.append("aria-invalid=true")
        if read_only:
            control_props.append("readonly aria-readonly=true")
        control.props(" ".join(control_props))
    return control


def status(text: str, tone: StatusTone = "neutral", *, props: str = ""):
    """Render a status whose text/icon remain meaningful without colour."""

    icon = {
        "action": "arrow_forward",
        "stable": "check_circle",
        "attention": "error_outline",
        "danger": "report",
        "neutral": "info",
    }[tone]
    badge = ui.badge(color=None).classes(f"sy-status-badge sy-tone-{tone}")
    badge.props(f'role=status aria-label="{attr(text)}" {props}'.strip())
    with badge:
        ui.icon(icon).classes("sy-status-badge-icon").props("aria-hidden=true")
        ui.label(text).classes("sy-status-badge-label")
    return badge


@contextmanager
def dialog(
    *,
    title: str,
    description: str,
    consequence: str | None = None,
    persistent: bool = False,
    test_id: str | None = None,
) -> Iterator[object]:
    """Create an accessible dialog shell and yield its action/body region."""

    props = "persistent" if persistent else ""
    if test_id:
        props += f" data-testid={test_id}"
    with ui.dialog().props(props.strip()) as element, ui.card().classes("sy-dialog w-full max-w-lg p-6"):
        ui.label(title).classes("sy-dialog-title").props("role=heading aria-level=2")
        ui.label(description).classes("sy-dialog-description")
        if consequence:
            with ui.element("aside").classes("sy-dialog-consequence").props("role=note"):
                ui.icon("info").props("aria-hidden=true")
                ui.label(consequence)
        with ui.element("div").classes("sy-dialog-content w-full"):
            yield element


def empty_state(
    *,
    title: str,
    body: str,
    icon: str,
    action_text: str | None = None,
    on_action: Callable[..., object] | None = None,
    action_variant: ActionVariant = "secondary",
    action_test_id: str | None = None,
    illustrated: bool = False,
    test_id: str | None = None,
) -> None:
    """Render an empty result with one clear, safe next step."""

    variant = " sy-empty-state--illustrated" if illustrated else ""
    props = f'role=status aria-live=polite aria-label="{attr(title)}"'
    if test_id:
        props += f" data-testid={test_id}"
    with ui.element("section").classes(f"sy-empty-state{variant} w-full").props(props):
        ui.icon(icon).classes("sy-empty-state-icon").props("aria-hidden=true")
        with ui.column().classes("items-center gap-1 max-w-lg"):
            ui.label(title).classes("sy-empty-state-title")
            ui.label(body).classes("sy-empty-state-copy")
        if action_text and on_action:
            action(
                action_text,
                icon="arrow_forward",
                on_click=on_action,
                variant=action_variant,
                test_id=action_test_id,
                classes="mt-2",
            )


def restricted_state(
    *,
    title: str,
    body: str,
    action_text: str | None = None,
    on_action: Callable[..., object] | None = None,
    test_id: str | None = None,
) -> None:
    """Explain an unavailable capability without pretending it is broken."""

    with ui.element("section").classes("sy-restricted-state w-full").props(
        f'role=status aria-live=polite aria-label="{attr(title)}"'
        + (f" data-testid={test_id}" if test_id else "")
    ):
        status(t("restricted"), "attention")
        ui.label(title).classes("sy-restricted-state-title")
        ui.label(body).classes("sy-restricted-state-copy")
        if action_text and on_action:
            action(action_text, icon="arrow_forward", on_click=on_action, variant="secondary")


def progress_state(
    *,
    title: str,
    status_text: str,
    value: float | None = None,
    test_id: str | None = None,
) -> None:
    """Render honest progress; indeterminate work never invents a percentage."""

    props = "role=status aria-live=polite aria-busy=true"
    if test_id:
        props += f" data-testid={test_id}"
    with ui.element("section").classes("sy-progress-state w-full").props(props):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.spinner(size="sm", color="primary")
            with ui.column().classes("gap-0 min-w-0"):
                ui.label(title).classes("sy-progress-state-title")
                ui.label(status_text).classes("sy-progress-state-copy")
        if value is None:
            ui.linear_progress().props("indeterminate color=primary").classes("w-full")
        else:
            ui.linear_progress(value=max(0.0, min(1.0, value)), color="primary").classes("w-full")


def responsive_table(
    *,
    rows: list[dict[str, object]],
    columns: list[dict[str, object]],
    row_key: str,
    classes: str = "",
    test_id: str | None = None,
) -> None:
    """Use one data model for ordered desktop and labelled phone views."""

    props = f"data-testid={test_id}" if test_id else ""
    with ui.element("div").classes(f"sy-responsive-table w-full {classes}".strip()).props(props):
        ui.table(rows=rows, columns=columns, row_key=row_key).classes(
            "sy-table sy-responsive-table-desktop w-full"
        )
        ui.table(rows=rows, columns=columns, row_key=row_key).props("grid hide-header").classes(
            "sy-table sy-responsive-table-mobile w-full"
        )


def workflow_step(
    *,
    number: int,
    title: str,
    detail: str,
    state: WorkflowState,
    state_text: str,
    icon: str,
    action_text: str | None = None,
    on_action: Callable[..., object] | None = None,
) -> None:
    """Render one ordered stage with explicit state and optional action."""

    with ui.element("li").classes(f"sy-flow-step sy-flow-step--{state}"):
        with ui.row().classes("w-full items-start justify-between gap-3"):
            ui.label(f"{number:02d}").classes("sy-flow-index")
            ui.icon(icon).classes("sy-flow-symbol").props("aria-hidden=true")
            status(state_text, {"active": "action", "done": "stable"}.get(state, "neutral"))
        ui.label(title).classes("sy-flow-title mt-5")
        ui.label(detail).classes("sy-flow-copy mt-2")
        if action_text and on_action:
            action(
                action_text,
                icon="arrow_forward",
                on_click=on_action,
                variant="primary" if state == "active" else "secondary",
                classes="sy-flow-action mt-5",
            )
        elif state == "pending":
            ui.label(t("flow_unavailable")).classes("sy-flow-disabled mt-5")


def editorial_heading(
    *,
    title: str,
    copy: str,
    kicker: str | None = None,
    anchor_id: str | None = None,
) -> None:
    """Render the shared editorial heading used by story and evidence pages."""

    with ui.column().classes("sy-architecture-section-heading gap-1"):
        if kicker:
            ui.label(kicker).classes("sy-architecture-section-kicker")
        title_element = ui.html(text(title), tag="h2").classes("sy-architecture-section-title")
        if anchor_id:
            title_element.props(f"id={attr(anchor_id)}")
        ui.label(copy).classes("sy-architecture-section-copy")


def page_toc(items: Sequence[ReferenceItem]) -> None:
    """Public alias for the shared page-local contents navigation."""

    render_page_toc(items)


def reference_pager(
    *,
    previous: ReferenceDestination | None = None,
    next_: ReferenceDestination | None = None,
) -> None:
    """Public alias for explicit reference-page reading continuity."""

    render_reference_pager(previous=previous, next_=next_)


def code_sample(
    *,
    code: str,
    label: str,
    language: str = "text",
    test_id: str | None = None,
) -> None:
    """Render a read-only command/code sample with accessible copy feedback."""

    props = f'aria-label="{attr(label)}"'
    if test_id:
        props += f" data-testid={test_id}"
    payload = json.dumps(code)
    with ui.element("figure").classes("sy-code-sample w-full").props(props):
        with ui.row().classes("sy-code-sample-header w-full items-center justify-between gap-3"):
            ui.label(label).classes("sy-code-sample-label")
            copy_button = action(
                t("copy"),
                icon="content_copy",
                variant="quiet",
                test_id=f"{test_id}-copy" if test_id else None,
            )
        ui.html(
            f'<pre><code class="language-{attr(language)}">{text(code)}</code></pre>'
        ).classes("sy-code-sample-body")

        async def copy_to_clipboard() -> None:
            await ui.run_javascript(f"navigator.clipboard.writeText({payload})")
            copy_button.props("data-sy-feedback=success")
            ui.notify(t("copied"), type="positive", timeout=2_000)

        copy_button.on("click", copy_to_clipboard)


__all__ = (
    "ActionVariant",
    "StatusTone",
    "WorkflowState",
    "action",
    "code_sample",
    "dialog",
    "editorial_heading",
    "empty_state",
    "field",
    "page_toc",
    "progress_state",
    "reference_pager",
    "responsive_table",
    "restricted_state",
    "status",
    "workflow_step",
)
