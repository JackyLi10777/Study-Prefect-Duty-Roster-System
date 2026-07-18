"""Small, reusable navigation helpers for operator and trust reference pages."""

from __future__ import annotations

from collections.abc import Sequence

from nicegui import ui

from nicegui_app.ui.i18n import t


ReferenceItem = tuple[str, str]
ReferenceDestination = tuple[str, str]


def render_page_toc(items: Sequence[ReferenceItem]) -> None:
    """Render a compact page-local contents list without creating another sidebar."""

    with ui.element("nav").classes("sy-reference-toc w-full").props(
        f'aria-label="{t("reference_on_this_page")}" data-testid=reference-toc'
    ):
        ui.label(t("reference_on_this_page")).classes("sy-reference-toc-title")
        with ui.element("div").classes("sy-reference-toc-links"):
            for anchor, label_key in items:
                ui.link(t(label_key), f"#{anchor}").classes("sy-reference-toc-link").props(
                    f"data-sy-toc-target={anchor}"
                )


def render_reference_pager(
    *,
    previous: ReferenceDestination | None = None,
    next_: ReferenceDestination | None = None,
) -> None:
    """Keep reading order explicit within one operator or trust lane."""

    if previous is None and next_ is None:
        return
    with ui.element("nav").classes("sy-reference-pager w-full").props(
        f'aria-label="{t("reference_continue_reading")}" data-testid=reference-pager'
    ):
        if previous is not None:
            route, label_key = previous
            with ui.link(target=route).classes("sy-reference-pager-link sy-reference-pager-link--previous"):
                ui.label(t("reference_previous")).classes("sy-reference-pager-kicker")
                ui.label(t(label_key)).classes("sy-reference-pager-label")
        else:
            ui.element("span").classes("sy-reference-pager-spacer").props("aria-hidden=true")
        if next_ is not None:
            route, label_key = next_
            with ui.link(target=route).classes("sy-reference-pager-link sy-reference-pager-link--next"):
                ui.label(t("reference_next")).classes("sy-reference-pager-kicker")
                ui.label(t(label_key)).classes("sy-reference-pager-label")
