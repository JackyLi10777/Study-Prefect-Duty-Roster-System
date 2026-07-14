"""Client-side delivery helpers for a locally generated roster PDF.

The PDF is prepared by Python, but ``navigator.share`` must run directly from
the user's second button press so the browser still has transient activation.
No PDF bytes are uploaded to a third-party service by this module.
"""

from __future__ import annotations

import base64
import json


MAX_NATIVE_SHARE_BYTES = 5 * 1024 * 1024


def can_offer_native_pdf_share(content: bytes) -> bool:
    """Keep the client-side share payload bounded while download stays available."""
    return bool(content) and len(content) <= MAX_NATIVE_SHARE_BYTES


def build_native_pdf_share_js(*, content: bytes, filename: str, title: str, text: str) -> str:
    """Return a direct click handler for Web Share Level 2 file delivery.

    Metadata is JSON encoded and the bytes are base64 encoded so neither a
    translated label nor a filename can escape into executable JavaScript.
    Callers must use this as NiceGUI's ``js_handler`` rather than invoking it
    after a Python round trip.
    """
    if not can_offer_native_pdf_share(content):
        raise ValueError("PDF is empty or too large for the native-share bridge.")

    payload = json.dumps(
        {"filename": filename, "title": title, "text": text},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    encoded = json.dumps(base64.b64encode(content).decode("ascii"))
    return f"""async () => {{
        const metadata = {payload};
        try {{
            const binary = atob({encoded});
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {{
                bytes[index] = binary.charCodeAt(index);
            }}
            const file = new File([bytes], metadata.filename, {{type: 'application/pdf'}});
            if (typeof navigator.share !== 'function' ||
                typeof navigator.canShare !== 'function' ||
                !navigator.canShare({{files: [file]}})) {{
                emit({{status: 'unsupported'}});
                return;
            }}
            await navigator.share({{files: [file], title: metadata.title, text: metadata.text}});
            emit({{status: 'shared'}});
        }} catch (error) {{
            emit({{status: error && error.name === 'AbortError' ? 'cancelled' : 'failed'}});
        }}
    }}"""
