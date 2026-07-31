"""Opt-in, payload-free SQL timing for local diagnosis and scale evidence."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import re
from time import perf_counter
from typing import Iterator

from sqlalchemy import Engine, event

from nicegui_app.config import SLOW_SQL_MS, SQL_DIAGNOSTICS_ENABLED
from nicegui_app.observability import current_request_reference, logger


_WHITESPACE = re.compile(r"\s+")
_CAPTURE: ContextVar["SQLDiagnosticSnapshot | None"] = ContextVar(
    "sing_yin_sql_diagnostic_capture",
    default=None,
)


def _operation(statement: str) -> str:
    normalized = statement.lstrip().split(None, 1)
    return normalized[0].upper()[:16] if normalized else "UNKNOWN"


def statement_fingerprint(statement: str) -> str:
    """Return a stable identifier without retaining SQL text or parameters."""
    normalized = _WHITESPACE.sub(" ", statement.strip()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@dataclass
class SQLDiagnosticSnapshot:
    statement_count: int = 0
    total_db_ms: float = 0.0
    slowest_ms: float = 0.0
    slowest_fingerprint: str | None = None
    fingerprints: dict[str, int] = field(default_factory=dict)

    def record(self, *, duration_ms: float, fingerprint: str) -> None:
        self.statement_count += 1
        self.total_db_ms += duration_ms
        self.fingerprints[fingerprint] = self.fingerprints.get(fingerprint, 0) + 1
        if duration_ms >= self.slowest_ms:
            self.slowest_ms = duration_ms
            self.slowest_fingerprint = fingerprint


@contextmanager
def capture_sql_diagnostics() -> Iterator[SQLDiagnosticSnapshot]:
    """Collect aggregate timings for a bounded operation or isolated verifier."""
    snapshot = SQLDiagnosticSnapshot()
    token = _CAPTURE.set(snapshot)
    try:
        yield snapshot
    finally:
        _CAPTURE.reset(token)


def install_sql_diagnostics(engine: Engine) -> None:
    """Attach one privacy-safe listener set to an engine."""
    if getattr(engine, "_sing_yin_sql_diagnostics_installed", False):
        return

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(_conn, _cursor, _statement, _parameters, context, _executemany) -> None:  # type: ignore[no-untyped-def]
        context._sing_yin_started_at = perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(_conn, cursor, statement, _parameters, context, _executemany) -> None:  # type: ignore[no-untyped-def]
        started_at = getattr(context, "_sing_yin_started_at", None)
        if started_at is None:
            return
        duration_ms = (perf_counter() - started_at) * 1_000
        fingerprint = statement_fingerprint(statement)
        snapshot = _CAPTURE.get()
        if snapshot is not None:
            snapshot.record(duration_ms=duration_ms, fingerprint=fingerprint)
        if SQL_DIAGNOSTICS_ENABLED and duration_ms >= SLOW_SQL_MS:
            logger().warning(
                "event=slow_sql operation=%s fingerprint=%s duration_ms=%.2f row_count=%s request_reference=%s",
                _operation(statement),
                fingerprint,
                duration_ms,
                getattr(cursor, "rowcount", -1),
                current_request_reference(),
            )

    setattr(engine, "_sing_yin_sql_diagnostics_installed", True)


__all__ = (
    "SQLDiagnosticSnapshot",
    "capture_sql_diagnostics",
    "install_sql_diagnostics",
    "statement_fingerprint",
)
