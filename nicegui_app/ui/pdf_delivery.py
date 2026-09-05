"""Backward-compatible PDF wrappers around the generated-file share bridge."""

from __future__ import annotations

from nicegui_app.ui.native_file_share import (
    MAX_NATIVE_SHARE_BYTES,
    build_native_file_share_js,
    can_offer_native_file_share,
)

def can_offer_native_pdf_share(content: bytes) -> bool:
    """Keep the client-side share payload bounded while download stays available."""
    return can_offer_native_file_share(content, media_type="application/pdf")


def build_native_pdf_share_js(*, content: bytes, filename: str, title: str, text: str) -> str:
    """Return a direct click handler for Web Share Level 2 file delivery.

    Metadata is JSON encoded and the bytes are base64 encoded so neither a
    translated label nor a filename can escape into executable JavaScript.
    Callers must use this as NiceGUI's ``js_handler`` rather than invoking it
    after a Python round trip.
    """
    return build_native_file_share_js(
        content=content,
        filename=filename,
        media_type="application/pdf",
        title=title,
        text=text,
    )


__all__ = (
    "MAX_NATIVE_SHARE_BYTES",
    "build_native_pdf_share_js",
    "can_offer_native_pdf_share",
)
