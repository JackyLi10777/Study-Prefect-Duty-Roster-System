"""Shared product-brand primitives.

The Service Weave mark identifies the software product. The official school
crest keeps its separate role in school attribution and formal documents.
"""

from __future__ import annotations

from nicegui import ui

from nicegui_app.ui.html_safety import attr
from nicegui_app.ui.i18n import current_locale
from nicegui_app.ui.product_identity import PRODUCT_IDENTITY


_SERVICE_WEAVE_MARKS = (
    (
        "light",
        PRODUCT_IDENTITY.product_asset(
            PRODUCT_IDENTITY.delivery["navigationLightVariant"]
        ).public_url,
    ),
    (
        "dark",
        PRODUCT_IDENTITY.product_asset(
            PRODUCT_IDENTITY.delivery["navigationDarkVariant"]
        ).public_url,
    ),
)


def render_service_weave_mark(*, context: str = "navigation", test_id: str | None = None) -> None:
    """Render one semantic mark whose paired artwork follows the active theme."""

    if context not in {"navigation", "display"}:
        raise ValueError(f"Unsupported Service Weave mark context: {context}")
    test_attribute = f" data-testid={test_id}" if test_id else ""
    accessible_name = PRODUCT_IDENTITY.accessible_name(
        "productMark", current_locale()
    )
    with ui.element("span").classes(f"sy-product-mark sy-product-mark--{context}").props(
        f'role=img aria-label="{attr(accessible_name)}"{test_attribute}'
    ):
        for appearance, source in _SERVICE_WEAVE_MARKS:
            if source is None:  # protected by the identity contract
                raise RuntimeError(f"Missing public URL for {appearance} product mark")
            ui.element("img").classes(
                f"sy-product-mark-image sy-product-mark-image--{appearance}"
            ).props(
                f'src="{attr(source)}" alt="" aria-hidden=true width=256 height=256 '
                'loading=eager decoding=async draggable=false'
            )


__all__ = ("PRODUCT_IDENTITY", "render_service_weave_mark")
