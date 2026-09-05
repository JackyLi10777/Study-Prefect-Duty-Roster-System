"""Safe client-side native sharing for generated roster files.

The file bytes never leave the browser through this module unless the user
explicitly chooses a target in the operating system share sheet.  The returned
handler is designed to run directly from a NiceGUI button click so transient
user activation is preserved for Web Share Level 2.
"""

from __future__ import annotations

import base64
import json


MAX_NATIVE_SHARE_BYTES = 5 * 1024 * 1024
ALLOWED_NATIVE_SHARE_MEDIA_TYPES = frozenset({"application/pdf", "image/png"})
_FILE_SIGNATURES = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
}
_LEASE_START_GUARD_JS = """
            if (metadata.leaseToken !== null) {
                const button = event?.currentTarget;
                if (!button || button.__syShareUsed || !Number.isFinite(metadata.leaseExpiresAt) ||
                    performance.now() >= metadata.leaseExpiresAt) {
                    report('expired');
                    return;
                }
                button.__syShareUsed = true;
                button.disabled = true;
            }
"""


def can_offer_native_file_share(content: bytes, *, media_type: str) -> bool:
    """Return whether a generated file is safe to embed in a share handler."""

    return (
        media_type in ALLOWED_NATIVE_SHARE_MEDIA_TYPES
        and bool(content)
        and len(content) <= MAX_NATIVE_SHARE_BYTES
        and content.startswith(_FILE_SIGNATURES[media_type])
    )


def build_native_file_share_js(
    *,
    content: bytes,
    filename: str,
    media_type: str,
    title: str,
    text: str,
    result_token: str | None = None,
    lease_token: str | None = None,
    lease_expires_at: float | None = None,
) -> str:
    """Build a direct-click Web Share Level 2 handler for one generated file.

    All translated metadata is JSON encoded and file bytes are base64 encoded;
    caller-controlled values are therefore never interpolated as JavaScript.
    Only the deliberately narrow roster-export MIME allowlist is accepted.
    """

    if not can_offer_native_file_share(content, media_type=media_type):
        raise ValueError("File is empty, too large, or has an unsupported media type.")

    metadata = json.dumps(
        {
            "filename": filename,
            "mediaType": media_type,
            "title": title,
            "text": text,
            "resultToken": result_token,
            "leaseToken": lease_token,
            "leaseExpiresAt": lease_expires_at,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    metadata = (
        metadata.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    encoded = json.dumps(base64.b64encode(content).decode("ascii"))
    return f"""async event => {{
        const metadata = {metadata};
        const report = status => emit({{status,
            ...(metadata.resultToken === null ? {{}} : {{token: metadata.resultToken}}),
            ...(metadata.leaseToken === null ? {{}} : {{lease: metadata.leaseToken}})}});
        try {{
            {_LEASE_START_GUARD_JS}
            const binary = atob({encoded});
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {{
                bytes[index] = binary.charCodeAt(index);
            }}
            const file = new File([bytes], metadata.filename, {{type: metadata.mediaType}});
            if (typeof navigator.share !== 'function' ||
                typeof navigator.canShare !== 'function' ||
                !navigator.canShare({{files: [file]}})) {{
                report('unsupported');
                return;
            }}
            if (metadata.leaseToken !== null) report('started');
            await navigator.share({{files: [file], title: metadata.title, text: metadata.text}});
            report('shared');
        }} catch (error) {{
            report(error && error.name === 'AbortError' ? 'cancelled' : 'failed');
        }}
    }}"""


def build_native_file_share_from_data_url_js(
    *,
    preview_selector: str,
    filename: str | None = None,
    filename_selector: str | None = None,
    media_type: str,
    title: str,
    text: str,
    result_token_selector: str | None = None,
    lease_token: str | None = None,
    lease_expires_at: float | None = None,
) -> str:
    """Build a compact direct-click share handler backed by an existing preview.

    Runtime-generated previews already contain the file once as a bounded data
    URL. Repeating the same base64 payload in a Vue event handler makes the
    browser compile and retain another large JavaScript source on every dialog
    lifecycle. This variant reads the current preview synchronously inside the
    click handler, so Web Share still starts from the user's activation while
    the file bytes have one browser owner which disappears with the preview.
    """

    if media_type not in ALLOWED_NATIVE_SHARE_MEDIA_TYPES:
        raise ValueError("File has an unsupported media type.")
    if not preview_selector.strip():
        raise ValueError("Preview selector must not be empty.")
    if bool(filename) == bool(filename_selector):
        raise ValueError("Provide exactly one filename or filename selector.")

    metadata = json.dumps(
        {
            "previewSelector": preview_selector,
            "filename": filename,
            "filenameSelector": filename_selector,
            "mediaType": media_type,
            "title": title,
            "text": text,
            "maxBytes": MAX_NATIVE_SHARE_BYTES,
            "resultTokenSelector": result_token_selector,
            "leaseToken": lease_token,
            "leaseExpiresAt": lease_expires_at,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    metadata = (
        metadata.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    signatures = json.dumps(
        {
            media_type: list(signature)
            for media_type, signature in _FILE_SIGNATURES.items()
        },
        separators=(",", ":"),
    )
    return f"""async event => {{
        const metadata = {metadata};
        const signatures = {signatures};
        let resultToken = null;
        const report = status => emit({{status,
            ...(resultToken === null ? {{}} : {{token: resultToken}}),
            ...(metadata.leaseToken === null ? {{}} : {{lease: metadata.leaseToken}})}});
        try {{
            // Capture the generation before sharing; the reusable preview may change while awaiting the OS.
            resultToken = metadata.resultTokenSelector
                ? document.querySelector(metadata.resultTokenSelector)?.getAttribute('data-share-token') ?? null
                : null;
            {_LEASE_START_GUARD_JS}
            const preview = document.querySelector(metadata.previewSelector);
            const image = preview?.matches('img') ? preview : preview?.querySelector('img');
            const prefix = `data:${{metadata.mediaType}};base64,`;
            const source = image?.getAttribute('src') || '';
            if (!source.startsWith(prefix)) {{
                report('failed');
                return;
            }}
            const binary = atob(source.slice(prefix.length));
            if (!binary.length || binary.length > metadata.maxBytes) {{
                report('failed');
                return;
            }}
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {{
                bytes[index] = binary.charCodeAt(index);
            }}
            const signature = signatures[metadata.mediaType];
            if (!signature || !signature.every((value, index) => bytes[index] === value)) {{
                report('failed');
                return;
            }}
            const filenameNode = metadata.filenameSelector
                ? document.querySelector(metadata.filenameSelector)
                : null;
            const resolvedFilename = metadata.filename || filenameNode?.textContent?.trim() || '';
            if (!resolvedFilename) {{
                report('failed');
                return;
            }}
            const file = new File([bytes], resolvedFilename, {{type: metadata.mediaType}});
            if (typeof navigator.share !== 'function' ||
                typeof navigator.canShare !== 'function' ||
                !navigator.canShare({{files: [file]}})) {{
                report('unsupported');
                return;
            }}
            if (metadata.leaseToken !== null) report('started');
            await navigator.share({{files: [file], title: metadata.title, text: metadata.text}});
            report('shared');
        }} catch (error) {{
            report(error && error.name === 'AbortError' ? 'cancelled' : 'failed');
        }}
    }}"""


__all__ = (
    "ALLOWED_NATIVE_SHARE_MEDIA_TYPES",
    "MAX_NATIVE_SHARE_BYTES",
    "build_native_file_share_from_data_url_js",
    "build_native_file_share_js",
    "can_offer_native_file_share",
)
