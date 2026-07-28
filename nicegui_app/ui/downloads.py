"""Access-aware delivery of generated files."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging

from nicegui import ui

from nicegui_app.access_context import AccessMode, Capability
from nicegui_app.observability import new_request_reference
from nicegui_app.runtime import current_page_context
from nicegui_app.services.guest_downloads import (
    GuestDownloadCapacityError,
    guest_download_registry,
)
from nicegui_app.ui.i18n import t


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GeneratedFile:
    """One generated file with explicit delivery metadata."""

    filename: str
    media_type: str
    content: bytes
    access_mode: AccessMode
    cache_policy: str = "no-store"
    support_reference: str = ""


def single_use_download_script(
    url: str,
    filename: str,
    failure_message: str,
    *,
    expected_media_type: str,
) -> str:
    """Fetch one authenticated file, validate it, and surface delivery errors."""

    return (
        "(async() => {"
        "let objectUrl='';"
        "try {"
        f"const expectedType=String({json.dumps(expected_media_type)}).split(';',1)[0].trim().toLowerCase();"
        f"const response=await fetch({json.dumps(url)},{{credentials:'same-origin',cache:'no-store',headers:{{'Accept':expectedType}}}});"
        "const responseReference=response.headers.get('X-Request-ID')||'';"
        "if(!response.ok){let detail={};try{detail=await response.json();}catch{};"
        "const reference=detail.reference||responseReference;"
        "throw new Error(reference?`REFERENCE:${reference}`:`HTTP:${response.status}`);}"
        "const actualType=String(response.headers.get('Content-Type')||'').split(';',1)[0].trim().toLowerCase();"
        "if(!expectedType||actualType!==expectedType)throw new Error(responseReference?`REFERENCE:${responseReference}`:'MEDIA_TYPE');"
        "const blob=await response.blob();"
        "if(!blob.size)throw new Error('EMPTY');"
        "objectUrl=URL.createObjectURL(blob);"
        "const anchor=document.createElement('a');"
        "anchor.href=objectUrl;"
        f"anchor.download={json.dumps(filename)};"
        "anchor.rel='noopener';anchor.style.display='none';"
        "document.body.appendChild(anchor);anchor.click();anchor.remove();"
        "document.body.dataset.syDownload='completed';"
        "}catch(error){"
        "document.body.dataset.syDownload='failed';"
        "const reference=String(error?.message||'').startsWith('REFERENCE:')?String(error.message).slice(10):'';"
        f"const base={json.dumps(failure_message)};"
        "const message=reference?`${base}\n${reference}`:base;"
        "if(window.Quasar?.Notify?.create){window.Quasar.Notify.create({type:'negative',message,timeout:7000,actions:[{icon:'close',color:'white'}]});}else{window.alert(message);}"
        "}finally{if(objectUrl)window.setTimeout(()=>URL.revokeObjectURL(objectUrl),1000);}"
        "})();"
    )


def deliver_generated_download(
    content: bytes,
    filename: str,
    *,
    media_type: str = "application/octet-stream",
) -> bool:
    """Queue one generated download and report whether delivery could start."""

    context = current_page_context()
    capability = (
        Capability.DEMO_RESULT_DOWNLOAD
        if context.principal.mode is AccessMode.GUEST
        else Capability.REAL_EXPORT
    )
    context.require(capability)
    session_id = context.principal.session_id
    if session_id and context.principal.mode in {AccessMode.GUEST, AccessMode.ADMIN}:
        generated = GeneratedFile(
            filename=filename,
            media_type=media_type,
            content=content,
            access_mode=context.principal.mode,
        )
        try:
            ticket = guest_download_registry().issue(
                access_mode=generated.access_mode,
                session_id=session_id,
                filename=generated.filename,
                content=generated.content,
                media_type=generated.media_type,
            )
        except GuestDownloadCapacityError:
            reference = context.request_reference.strip()
            if not reference.startswith("REQ-"):
                reference = new_request_reference()
            logger.warning(
                "Generated download admission rejected reference=%s mode=%s media_type=%s",
                reference,
                generated.access_mode.value,
                generated.media_type,
            )
            ui.notify(f'{t("download_delivery_failed")}\n{reference}', type="warning")
            return False
        ui.run_javascript(
            single_use_download_script(
                f"/api/generated-download/{ticket.token}",
                generated.filename,
                t("download_delivery_failed"),
                expected_media_type=generated.media_type,
            )
        )
        return True
    ui.download(content, filename, media_type=media_type)
    return True


__all__ = ["GeneratedFile", "deliver_generated_download", "single_use_download_script"]
