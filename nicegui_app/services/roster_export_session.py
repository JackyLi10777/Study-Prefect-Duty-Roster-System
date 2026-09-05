"""UI-independent export lifecycle; generation tokens reject all stale work."""

from dataclasses import dataclass, field
from typing import Mapping
from uuid import uuid4

from nicegui_app.services.roster_document import RosterDocument


NATIVE_SHARE_LEASE_SECONDS = 15


@dataclass(slots=True)
class NativeShareLease:
    """One short-lived permission to start the already-delivered file share."""

    generation: str
    expires_at: float
    token: str = field(default_factory=lambda: uuid4().hex)
    active: bool = True
    started: bool = False

    def start(self, token: object, *, now: float) -> bool:
        if not self.active or self.started or token != self.token or now >= self.expires_at:
            return False
        self.started = True
        return True

    def finish(self, token: object, *, now: float) -> bool:
        if not self.active or token != self.token or (not self.started and now >= self.expires_at):
            return False
        self.active = False
        return True

    def expire(self, *, now: float) -> bool:
        if not self.active or self.started or now < self.expires_at:
            return False
        self.active = False
        return True

    def cancel(self) -> None:
        self.active = False


@dataclass(frozen=True, slots=True)
class ExportOptions:
    language: str = "zh"
    show_crest: bool = True
    show_footer_note: bool = False

    def __post_init__(self) -> None:
        if self.language not in {"zh", "en"}:
            raise ValueError("Export language must be zh or en.")


@dataclass(frozen=True, slots=True)
class ExportRequest:
    generation: int
    options: ExportOptions
    document: RosterDocument | None


class RosterExportSession:
    def __init__(self, options: ExportOptions | None = None) -> None:
        self.options = options or ExportOptions()
        self.document: RosterDocument | None = None
        self.generation = 0
        self.opened = False
        self.phase = "closed"

    def open(self) -> None:
        self.generation += 1
        self.opened = True
        self.document = None
        self.phase = "idle"

    def close(self) -> None:
        self.generation += 1
        self.opened = False
        self.document = None
        self.phase = "closed"

    def change_options(self, options: ExportOptions) -> None:
        if options == self.options:
            return
        self.generation += 1
        self.options = options
        self.phase = "idle" if self.opened else "closed"

    def begin(self) -> ExportRequest:
        if not self.opened:
            raise RuntimeError("Cannot prepare a closed export workspace.")
        self.generation += 1
        self.phase = "preparing"
        return ExportRequest(self.generation, self.options, self.document)

    def accepts(self, request: ExportRequest) -> bool:
        return self.opened and request.generation == self.generation and request.options == self.options

    def accepts_share_result(self, token: object) -> bool:
        """Only report a native share for the still-active prepared generation."""
        return self.opened and self.phase == "ready" and isinstance(token, str) and token == str(self.generation)

    def complete(self, request: ExportRequest, document: RosterDocument) -> bool:
        if not self.accepts(request):
            return False
        self.document = document
        self.phase = "ready"
        return True

    def fail(self, request: ExportRequest) -> None:
        if self.accepts(request):
            self.phase = "failed"

    def finish_direct_delivery(self, request: ExportRequest, *, delivered: bool) -> bool:
        """Settle a non-cached download, including rejected ticket admission."""
        if not self.accepts(request):
            return False
        self.phase = "idle" if delivered else "failed"
        return delivered

    def validate_revision(self, week: Mapping[str, object]) -> bool:
        if not self.opened or self.document is None:
            return False
        if self.document.matches_revision(week):
            return True
        self.invalidate_source()
        return False

    def invalidate_source(self) -> None:
        self.generation += 1
        self.document = None
        self.phase = "stale" if self.opened else "closed"
