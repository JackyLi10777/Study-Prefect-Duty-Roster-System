"""Operator-facing access controls for private editing and encrypted viewing."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from nicegui import ui

from nicegui_app.access_context import Capability
from nicegui_app.deployment import DeploymentSettings
from nicegui_app.runtime import current_page_context
from nicegui_app.services.public_roster_share import (
    PublicRosterShareMetadata,
    PublicRosterShareService,
    PublicRosterShareSettings,
)
from nicegui_app.ui.i18n import t
from nicegui_app.ui.navigation import navigate_to
from nicegui_app.ui.page_shared import _OPERATION_FAILED, _delete_dialog_after_close, _run_with_progress


_HONG_KONG = ZoneInfo("Asia/Hong_Kong")


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(_HONG_KONG).strftime("%Y-%m-%d %H:%M HKT")


def _external_share_allowed() -> bool:
    return current_page_context().allows(Capability.EXTERNAL_DELIVERY)


def _public_share_service(
    workflow,  # type: ignore[no-untyped-def]
    *,
    settings: PublicRosterShareSettings | None = None,
) -> PublicRosterShareService:
    """Construct the external service only after a server-side capability check."""

    current_page_context().require(Capability.EXTERNAL_DELIVERY)
    resolved_settings = settings or PublicRosterShareSettings.from_environment()
    return PublicRosterShareService(workflow, settings=resolved_settings)


def _render_external_share_restricted() -> None:
    with ui.element("section").classes(
        "sy-surface sy-restricted-state w-full max-w-3xl px-6 py-5"
    ).props("role=status data-testid=guest-public-share-restricted"):
        with ui.row().classes("items-start gap-3 no-wrap"):
            ui.icon("lock").classes("sy-fg-attention text-xl").props("aria-hidden=true")
            with ui.column().classes("gap-1 min-w-0"):
                ui.label(t("access_restricted_title")).classes("font-semibold")
                ui.label(t("access_restricted_body")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )


async def _copy_value(value: str) -> None:
    current_page_context().require(Capability.EXTERNAL_DELIVERY)
    encoded = json.dumps(value, ensure_ascii=False)
    script = f"""
        (async () => {{
            const value = {encoded};
            try {{
                if (!navigator.clipboard?.writeText) throw new Error('clipboard-unavailable');
                await navigator.clipboard.writeText(value);
                return 'copied';
            }} catch (_error) {{
                window.prompt({json.dumps(t('copy_failed_manual'))}, value);
                return 'manual';
            }}
        }})()
    """
    try:
        result = await ui.run_javascript(script, timeout=5.0)
    except Exception:
        ui.notify(t("copy_failed_manual"), type="warning", timeout=5_000)
    else:
        if result == "copied":
            ui.notify(t("public_share_copied"), type="positive")
        else:
            ui.notify(t("copy_manual_prompt"), type="warning", timeout=5_000)


def _show_share_receipt(receipt) -> None:  # type: ignore[no-untyped-def]
    with ui.dialog().props(
        "persistent data-testid=public-share-receipt-dialog"
    ) as dialog, ui.card().classes("sy-surface w-full max-w-2xl p-6"):
        with ui.row().classes("items-start gap-3 no-wrap"):
            ui.icon("link").classes("sy-fg-stable text-2xl").props("aria-hidden=true")
            with ui.column().classes("gap-1 min-w-0"):
                ui.label(t("public_share_created_title")).classes("text-lg font-semibold")
                ui.label(t("public_share_created_body")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
        link_input = ui.input(
            label=t("public_share_link_label"), value=receipt.share_url
        ).props("readonly autocomplete=off data-testid=public-share-url").classes("w-full mt-5")
        ui.label(t("public_share_expiry", value=_format_timestamp(receipt.expires_at))).classes(
            "text-sm text-[var(--sy-muted)]"
        )
        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5 flex-wrap"):
            ui.button(t("close"), icon="close", on_click=dialog.close).props("flat")
            ui.button(
                t("public_share_copy"),
                icon="content_copy",
                on_click=lambda: _copy_value(str(link_input.value or receipt.share_url)),
            ).props("color=primary data-testid=copy-public-share")
    _delete_dialog_after_close(dialog)
    dialog.open()


def _open_create_confirmation(service: PublicRosterShareService, roster_week_id: int) -> None:
    current_page_context().require(Capability.EXTERNAL_DELIVERY)
    share_command_id = f"public-share-create-ui:{uuid4().hex}"
    with ui.dialog().props(
        "data-testid=public-share-confirm-dialog"
    ) as dialog, ui.card().classes("sy-surface w-full max-w-lg p-6"):
        ui.label(t("public_share_confirm_title")).classes("text-lg font-semibold")
        ui.label(t("public_share_confirm_body")).classes(
            "text-sm leading-6 text-[var(--sy-muted)] mt-2"
        )

        async def create_share() -> None:
            current_page_context().require(Capability.EXTERNAL_DELIVERY)
            dialog.close()
            receipt = await _run_with_progress(
                lambda: service.create_share(
                    roster_week_id,
                    command_id=share_command_id,
                ),
                title_key="public_share_progress_title",
                working_key="public_share_progress_working",
                icon="encrypted",
            )
            if receipt is not _OPERATION_FAILED:
                _show_share_receipt(receipt)

        with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5 flex-wrap"):
            ui.button(t("cancel"), icon="close", on_click=dialog.close).props("flat")
            ui.button(
                t("public_share_confirm_action"), icon="link", on_click=create_share
            ).props("color=primary data-testid=confirm-create-public-share")
    dialog.open()


def render_roster_share_action(workflow, roster_week_id: int) -> None:  # type: ignore[no-untyped-def]
    """Render the deliberate share decision beside one published roster."""
    if not _external_share_allowed():
        _render_external_share_restricted()
        return
    settings = PublicRosterShareSettings.from_environment()
    with ui.element("section").classes("sy-surface w-full max-w-3xl px-6 py-5").props(
        "data-testid=published-roster-sharing"
    ):
        with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
            with ui.column().classes("gap-1 max-w-2xl"):
                ui.label(t("public_share_title")).classes("text-lg font-semibold")
                ui.label(t("public_share_intro")).classes(
                    "text-sm leading-6 text-[var(--sy-muted)]"
                )
            ui.button(
                t("access_open_console"),
                icon="admin_panel_settings",
                on_click=lambda: navigate_to("/access-control"),
            ).props("flat")
        if not settings.configured:
            ui.label(t("public_share_not_configured")).classes(
                "text-sm text-[var(--sy-muted)] mt-3"
            )
            return
        service = _public_share_service(workflow, settings=settings)
        ui.button(
            t("public_share_create"),
            icon="link",
            on_click=lambda: _open_create_confirmation(service, roster_week_id),
        ).props("color=primary data-testid=create-public-share").classes("mt-4")


def revoke_withdrawn_roster_shares(workflow, share_ids: tuple[str, ...]) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    """Deliver durable revocation work after a roster withdrawal transaction."""

    if not share_ids:
        return (0, 0)
    current_page_context().require(Capability.EXTERNAL_DELIVERY)
    settings = PublicRosterShareSettings.from_environment()
    service = _public_share_service(workflow, settings=settings)
    completed = 0
    failed = 0
    for share_id in share_ids:
        try:
            service.revoke_share(share_id)
            workflow.complete_external_share_revocation(share_id)
        except Exception as error:  # keep the durable outbox pending for a safe retry
            workflow.fail_external_share_revocation(
                share_id,
                error_code=type(error).__name__,
            )
            failed += 1
        else:
            completed += 1
    return completed, failed


def _render_active_shares(
    area,
    service: PublicRosterShareService,
    shares: list[PublicRosterShareMetadata],
    *,
    roster_week_id: int | None = None,
) -> None:  # type: ignore[no-untyped-def]
    area.clear()
    visible = [item for item in shares if roster_week_id is None or item.roster_week_id == roster_week_id]
    with area:
        if not visible:
            ui.label(t("public_share_active_empty")).classes("text-sm text-[var(--sy-muted)]")
            return
        for share in visible:
            with ui.element("article").classes(
                "sy-surface-subtle w-full px-4 py-4"
            ).props("data-testid=active-public-share"):
                with ui.row().classes("w-full items-start justify-between gap-4 flex-wrap"):
                    with ui.column().classes("gap-1"):
                        ui.label(t("access_permission_label", value=t("access_viewer_title"))).classes(
                            "font-semibold"
                        )
                        ui.label(t("access_week_label", value=share.week_start.isoformat())).classes(
                            "text-sm text-[var(--sy-muted)]"
                        )
                        ui.label(t("public_share_expiry", value=_format_timestamp(share.expires_at))).classes(
                            "text-sm text-[var(--sy-muted)]"
                        )
                        ui.label(t("access_share_id", value=share.share_id[-8:])).classes(
                            "text-xs text-[var(--sy-muted)]"
                        )

                    def confirm_revoke(item: PublicRosterShareMetadata = share) -> None:
                        with ui.dialog() as revoke_dialog, ui.card().classes("sy-surface w-full max-w-md p-6"):
                            ui.label(t("public_share_revoke_confirm_title")).classes("text-lg font-semibold")
                            ui.label(t("public_share_revoke_confirm_body")).classes(
                                "text-sm leading-6 text-[var(--sy-muted)] mt-2"
                            )

                            async def revoke() -> None:
                                current_page_context().require(Capability.EXTERNAL_DELIVERY)
                                revoke_dialog.close()
                                result = await _run_with_progress(
                                    lambda: service.revoke_share(item.share_id),
                                    title_key="public_share_revoke_progress_title",
                                    working_key="public_share_revoke_progress_working",
                                    icon="link_off",
                                )
                                if result is not _OPERATION_FAILED:
                                    ui.notify(t("public_share_revoked"), type="positive")
                                    remaining = [record for record in visible if record.share_id != item.share_id]
                                    _render_active_shares(
                                        area,
                                        service,
                                        remaining,
                                        roster_week_id=roster_week_id,
                                    )

                            with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5"):
                                ui.button(t("cancel"), on_click=revoke_dialog.close).props("flat")
                                ui.button(t("public_share_revoke"), icon="link_off", on_click=revoke).props(
                                    "color=negative data-testid=confirm-revoke-public-share"
                                )
                        revoke_dialog.open()

                    ui.button(
                        t("public_share_revoke"), icon="link_off", on_click=confirm_revoke
                    ).props("outline color=negative")


def render_access_control_console(workflow) -> None:  # type: ignore[no-untyped-def]
    """Render the administrator console for the unified guest/operator website."""
    if not _external_share_allowed():
        _render_external_share_restricted()
        return
    deployment = DeploymentSettings.from_environment()
    settings = PublicRosterShareSettings.from_environment()
    service = _public_share_service(workflow, settings=settings)
    local_url = f"http://127.0.0.1:{deployment.port}"
    canonical_url = settings.base_url if settings.configured else local_url

    ui.label(t("access_control_intro")).classes("text-base leading-7 text-[var(--sy-muted)] max-w-4xl")
    ui.label(t("access_permission_model_title")).classes("text-xl font-semibold mt-2")
    with ui.row().classes("w-full items-stretch gap-5 flex-wrap"):
        with ui.element("section").classes("sy-surface flex-1 min-w-[280px] px-6 py-5").props(
            "data-testid=operator-access-card"
        ):
            ui.label(t("access_operator_title")).classes("text-lg font-semibold")
            ui.label(t("access_operator_body")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-1")
            ui.label(t("access_operator_local")).classes("font-medium mt-4")
            ui.label(canonical_url).classes("text-sm break-all text-[var(--sy-muted)]")
            ui.button(
                t("access_copy_address"), icon="content_copy", on_click=lambda: _copy_value(canonical_url)
            ).props("flat").classes("mt-1")
            ui.label(t("access_operator_remote")).classes("font-medium mt-3")
            ui.label(local_url).classes("text-sm break-all text-[var(--sy-muted)]")
            ui.label(t("access_operator_warp_note")).classes(
                "text-xs leading-5 text-[var(--sy-muted)] mt-3"
            )

        with ui.element("section").classes("sy-surface flex-1 min-w-[280px] px-6 py-5").props(
            "data-testid=viewer-access-card"
        ):
            ui.label(t("access_viewer_title")).classes("text-lg font-semibold")
            ui.label(t("access_viewer_body")).classes("text-sm leading-6 text-[var(--sy-muted)] mt-1")
            if not settings.configured:
                ui.label(t("public_share_not_configured")).classes(
                    "text-sm text-[var(--sy-muted)] mt-4"
                )
            else:
                published = [item for item in workflow.roster_weeks() if item["status"] == "published"]
                if not published:
                    ui.label(t("access_no_published_roster")).classes(
                        "text-sm text-[var(--sy-muted)] mt-4"
                    )
                else:
                    options = {
                        int(item["id"]): f"{item['weekStart']} · v{item['version']}"
                        for item in published
                    }
                    roster_select = ui.select(
                        label=t("access_select_roster"),
                        options=options,
                        value=next(iter(options)),
                    ).classes("w-full mt-4")
                    ui.button(
                        t("public_share_create"),
                        icon="link",
                        on_click=lambda: _open_create_confirmation(service, int(roster_select.value)),
                    ).props("color=primary data-testid=console-create-public-share").classes("mt-3")

    ui.label(t("public_share_active_title")).classes("text-xl font-semibold mt-4")
    management_area = ui.column().classes("w-full gap-3")
    if settings.configured:
        async def load_active() -> None:
            current_page_context().require(Capability.EXTERNAL_DELIVERY)
            result = await _run_with_progress(
                service.list_shares,
                title_key="public_share_manage_progress_title",
                working_key="public_share_manage_progress_working",
                icon="manage_accounts",
            )
            if result is not _OPERATION_FAILED:
                _render_active_shares(management_area, service, list(result))

        ui.button(
            t("access_manage_links"), icon="refresh", on_click=load_active
        ).props("outline color=primary data-testid=load-public-shares")
    else:
        with management_area:
            ui.label(t("public_share_not_configured")).classes("text-sm text-[var(--sy-muted)]")
