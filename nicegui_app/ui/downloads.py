"""Access-aware delivery of generated files."""

from __future__ import annotations

import json

from nicegui import ui

from nicegui_app.access_context import AccessMode, Capability
from nicegui_app.runtime import current_page_context
from nicegui_app.services.guest_downloads import guest_download_registry


def single_use_download_script(url: str) -> str:
    """Trigger one same-origin download without putting file bytes in browser storage."""

    return (
        "(() => {"
        "const anchor=document.createElement('a');"
        f"anchor.href={json.dumps(url)};"
        "anchor.rel='noopener';"
        "anchor.style.display='none';"
        "document.body.appendChild(anchor);"
        "anchor.click();"
        "anchor.remove();"
        "})();"
    )


def deliver_generated_download(
    content: bytes,
    filename: str,
    *,
    media_type: str = "application/octet-stream",
) -> None:
    """Use a single-use no-store endpoint for guests; preserve normal admin delivery."""

    context = current_page_context()
    if context.principal.mode is AccessMode.GUEST:
        context.require(Capability.DEMO_RESULT_DOWNLOAD)
        session_id = context.principal.session_id
        if not session_id:  # defensive: verified guest principals always carry one
            raise PermissionError("guest download session is unavailable")
        ticket = guest_download_registry().issue(
            session_id=session_id,
            filename=filename,
            content=content,
            media_type=media_type,
        )
        ui.run_javascript(
            single_use_download_script(f"/api/guest/download/{ticket.token}")
        )
        return
    ui.download(content, filename, media_type=media_type)


__all__ = ["deliver_generated_download", "single_use_download_script"]
