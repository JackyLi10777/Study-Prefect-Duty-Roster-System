"""Page-owned restore consent; durable verification remains in the workflow."""

from pathlib import Path
import re

from nicegui import ui

from nicegui_app.services.workflow_types import WorkflowError
from nicegui_app.ui.components import dialog as semantic_dialog
from nicegui_app.ui.i18n import t
from nicegui_app.ui.page_shared import _OPERATION_FAILED, _run_with_progress


class RestoreControls:
    """One retained confirmation with immutable per-submission intent."""

    def __init__(self, workflow, options: dict[str, str], *, guest: bool) -> None:
        self.workflow, self.options, self.guest = workflow, dict(options), guest
        self.reviewed: tuple[str, str | int] | None = None
        self.request = 0
        self.busy = False
        self.reviewing = False
        self.selector = ui.select(label=t("select_backup"), options=self.options, value=None).classes(
            "w-full mt-4 text-base"
        ).props("data-testid=restore-backup-choice clearable")
        self.selector.on_value_change(lambda _: self.selection_changed())
        self.ready = ui.button(t("restore_review_action"), icon="fact_check", on_click=self.review_selected).props(
            "outline data-testid=restore-ready-action"
        ).classes("sy-button-attention mt-4 min-h-[44px]")
        self.failure = ui.label(t("restore_failed_review_again")).classes("text-sm mt-3").props(
            "role=status data-testid=restore-failure-receipt"
        )
        self.failure.set_visibility(False)
        self.receipt = ui.label("").classes("text-sm mt-3").props("role=status data-testid=restore-success-receipt")
        self.receipt.set_visibility(False)
        self.reload = ui.button(t("reload_and_review"), icon="refresh", on_click=ui.navigate.reload).props(
            "outline data-testid=restore-reload-action"
        ).classes("mt-3 min-h-[44px]")
        self.reload.set_visibility(False)
        with semantic_dialog(
            title=t("confirm_restore"),
            description=t("restore_demo_warning" if guest else "restore_warning"),
            presentation="alert", test_id="restore-confirm-dialog",
        ) as self.dialog:
            self.summary = ui.label("").classes("text-sm whitespace-pre-wrap break-all w-full").props(
                "data-testid=restore-reviewed-summary"
            )
            self.phrase = ui.input(label=t("restore_type_confirmation", phrase=t("restore_confirmation_phrase"))).props(
                "autocomplete=off data-testid=restore-confirmation-text"
            ).classes("w-full text-base mt-4")
            self.phrase.on_value_change(lambda _: self.sync())
            with ui.row().classes("sy-mobile-actions w-full justify-end gap-3 mt-5 flex-wrap"):
                ui.button(t("cancel"), icon="close", on_click=self.cancel).props("flat data-testid=restore-cancel-action")
                self.confirm = ui.button(t("confirm_restore"), icon="restore", on_click=self.submit).props(
                    "color=negative data-testid=confirm-restore-action"
                ).classes("min-h-[44px]")
        self.dialog.on_value_change(lambda event: self.clear_consent() if not event.value else None)
        # Quasar retains its focus trap during the leave transition. Return focus
        # after hide, not just when the server changes the dialog value.
        self.dialog.on("hide", js_handler=f"() => document.getElementById('c{self.ready.id}')?.focus()")
        self.sync()

    def sync(self) -> None:
        self.ready.set_enabled(not self.busy and not self.reviewing and self.selector.value in self.options)
        self.selector.set_enabled(not self.busy)
        self.confirm.set_enabled(
            not self.busy and self.reviewed is not None and self.dialog.value
            and self.reviewed[0] == self.selector.value
            and self.phrase.value == t("restore_confirmation_phrase")
        )

    def clear_consent(self) -> None:
        self.request += 1
        self.reviewed = None
        self.phrase.set_value("")
        # QDialog unmounts its portal children; NiceGUI input.beforeUnmount can
        # preserve the old client value after the first reset. Re-publish even
        # when the authoritative Python value is already empty on reopening.
        self.phrase.update()
        self.sync()

    def cancel(self) -> None:
        self.clear_consent()
        self.dialog.close()
        if not self.busy:
            self.ready.run_method("focus")

    def selection_changed(self) -> None:
        self.cancel()
        self.sync()

    async def review_selected(self) -> None:
        selected = self.selector.value
        if self.busy or self.reviewing or selected not in self.options:
            return
        self.clear_consent()
        request = self.request
        self.reviewing = True
        self.failure.set_visibility(False)
        self.sync()

        def read_review():
            if self.guest:
                review = self.workflow.review_demo_backup(selected)
                token = review.get("workspaceRevision")
                if review.get("demo") is not True or type(token) is not int or token < 0:
                    raise WorkflowError("The memory checkpoint review is invalid.")
                return token, None
            review = self.workflow.verify_backup(Path(selected))
            token = review.get("sha256")
            if (review.get("valid") is not True or type(token) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", token) is None):
                raise WorkflowError("The selected backup could not be verified. Create a verified backup first.")
            return token, review.get("schemaRevision", "—")

        # The worker returns data only; translate with the page's locale afterward.
        try:
            result = await _run_with_progress(
                read_review, title_key="restore_review_action", working_key="restore_review_working",
                icon="fact_check", success_feedback=False,
            )
            if request != self.request or self.selector.is_deleted or selected != self.selector.value:
                return
            if result is _OPERATION_FAILED:
                self.failure.set_visibility(True)
                self.reload.set_visibility(True)
                return
            token, revision = result
            explanation = t("restore_demo_warning") if self.guest else t("restore_verified_summary", revision=revision)
            self.reviewed = (selected, token)
            self.summary.set_text(self.options[selected] + "\n" + explanation)
            self.dialog.open()
            self.phrase.run_method("focus")
        finally:
            self.reviewing = False
            if not self.selector.is_deleted:
                self.sync()

    async def submit(self) -> None:
        intent = self.reviewed
        if (self.busy or not self.dialog.value or intent is None
                or intent[0] != self.selector.value or self.phrase.value != t("restore_confirmation_phrase")):
            return
        self.busy = True
        self.receipt.set_visibility(False)
        self.failure.set_visibility(False)
        self.cancel()
        selected, token = intent  # Never re-read mutable controls in the IO callback.
        try:
            action = (lambda: self.workflow.restore_backup(selected, expected_workspace_revision=token)) if self.guest else (
                lambda: self.workflow.restore_backup(Path(selected), expected_sha256=token)
            )
            result = await _run_with_progress(
                action, title_key="progress_restore_title", working_key="progress_restore_working", icon="restore",
            )
            if self.selector.is_deleted:
                return
            self.reload.set_visibility(True)
            if result is _OPERATION_FAILED:
                self.failure.set_visibility(True)
            else:
                self.receipt.set_text(t("restore_demo_complete" if self.guest else "backup_restored"))
                self.receipt.set_visibility(True)
                self.selector.set_value(None)
        finally:
            self.busy = False
            if not self.selector.is_deleted:
                self.sync()
