"""Privacy-conscious local logging for operator support and handover."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
import threading
from time import perf_counter
import traceback as traceback_module
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from nicegui_app.config import PROJECT_ROOT


LOGGER_NAME = "sing_yin_roster"
_REFERENCE_PATTERN = re.compile(r"^OP-[A-F0-9]{8}$")
_REQUEST_REFERENCE_PATTERN = re.compile(r"^REQ-[A-F0-9]{8}$")
_request_reference: ContextVar[str] = ContextVar("sing_yin_request_reference", default="-")
_hooks_installed = False
_ASYNCIO_HOOK_MARKER = "_sing_yin_asyncio_exception_handler_installed"
_WINDOWS_CLIENT_DISCONNECT_CODES = frozenset({64, 10054})


def _positive_int_from_environment(name: str, default: int) -> int:
    """Accept only positive local logging limits; retain a safe default otherwise."""
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return value if value > 0 else default


def _configured_log_level() -> int:
    configured_name = os.getenv("SING_YIN_LOG_LEVEL", "INFO").upper()
    return getattr(logging, configured_name, logging.INFO)


def _console_logging_enabled() -> bool:
    return os.getenv("SING_YIN_LOG_CONSOLE", "true").strip().lower() not in {"0", "false", "no", "off"}


def current_request_reference() -> str:
    """Return the short trace token assigned to the current HTTP request, if any."""
    return _request_reference.get()


def new_request_reference() -> str:
    reference = f"REQ-{uuid4().hex[:8].upper()}"
    assert _REQUEST_REFERENCE_PATTERN.fullmatch(reference)
    return reference


class _RequestTraceFilter(logging.Filter):
    """Attach a request trace to every local line without recording request content."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_reference()
        return True


def _attach_trace_filter(handler: logging.Handler) -> None:
    if not any(isinstance(existing, _RequestTraceFilter) for existing in handler.filters):
        handler.addFilter(_RequestTraceFilter())


def _trace_location(traceback) -> str:  # type: ignore[no-untyped-def]
    """Return code locations without exception messages or local values."""
    frames = traceback_module.extract_tb(traceback) if traceback else []
    if not frames:
        return "unknown"
    return ">".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames)


def configure_local_logging(log_path: Path | None = None) -> Path:
    """Configure privacy-safe rotating file and optional live-console handlers."""
    configured_directory = Path(os.getenv("SING_YIN_LOG_DIR", PROJECT_ROOT / "logs"))
    destination = (log_path or configured_directory / "app.log").resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_configured_log_level())
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s trace=%(request_id)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    configured_file_handler: RotatingFileHandler | None = None
    configured_console_handler: logging.Handler | None = None

    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            try:
                if Path(handler.baseFilename).resolve() == destination:
                    configured_file_handler = handler
                    continue
            except (OSError, RuntimeError):
                pass
            handler.close()
            logger.removeHandler(handler)
        elif getattr(handler, "_sing_yin_console", False):
            if _console_logging_enabled():
                configured_console_handler = handler
            else:
                handler.close()
                logger.removeHandler(handler)

    if configured_file_handler is None:
        configured_file_handler = RotatingFileHandler(
            destination,
            maxBytes=_positive_int_from_environment("SING_YIN_LOG_MAX_BYTES", 2_000_000),
            backupCount=_positive_int_from_environment("SING_YIN_LOG_BACKUP_COUNT", 5),
            encoding="utf-8",
        )
        logger.addHandler(configured_file_handler)
    configured_file_handler.setLevel(logger.level)
    configured_file_handler.setFormatter(formatter)
    _attach_trace_filter(configured_file_handler)

    if _console_logging_enabled() and configured_console_handler is None:
        configured_console_handler = logging.StreamHandler()
        configured_console_handler._sing_yin_console = True  # type: ignore[attr-defined]
        logger.addHandler(configured_console_handler)
    if configured_console_handler is not None:
        configured_console_handler.setLevel(logger.level)
        configured_console_handler.setFormatter(formatter)
        _attach_trace_filter(configured_console_handler)

    logger.info(
        "event=logging_ready log_file=%s rotation_bytes=%s backups=%s console=%s",
        destination,
        configured_file_handler.maxBytes,
        configured_file_handler.backupCount,
        _console_logging_enabled(),
    )
    return destination


def logger() -> logging.Logger:
    """Return the application logger without configuring external outputs."""
    return logging.getLogger(LOGGER_NAME)


def new_operation_reference() -> str:
    """Create a short, non-identifying reference suitable for the UI."""
    reference = f"OP-{uuid4().hex[:8].upper()}"
    assert _REFERENCE_PATTERN.fullmatch(reference)
    return reference


def _request_target_category(path: str) -> str:
    """Classify a route without putting URLs, query strings, or user input in logs."""
    if path == "/":
        return "dashboard"
    if path == "/healthz":
        return "health"
    if path in {"/rosters", "/prefects", "/settings", "/handover", "/getting-started", "/guide", "/devotional"}:
        return path.removeprefix("/")
    if re.fullmatch(r"/rosters/\d+(?:/adjustments)?", path):
        return "roster_workflow"
    if path.startswith("/assets/") or path == "/favicon.ico":
        return "asset"
    if path.startswith("/_nicegui/"):
        return "nicegui_internal"
    return "other"


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Give each HTTP response and safe local log lines one non-identifying trace."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        reference = new_request_reference()
        token = _request_reference.set(reference)
        started_at = perf_counter()
        category = _request_target_category(request.url.path)
        try:
            response = await call_next(request)
        except Exception as error:
            logger().error(
                "event=http_request_failed method=%s target=%s error_type=%s duration_ms=%s",
                request.method,
                category,
                type(error).__name__,
                round((perf_counter() - started_at) * 1000),
            )
            raise
        else:
            response.headers["X-Request-ID"] = reference
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            if category not in {"asset", "nicegui_internal"}:
                response.headers["Cache-Control"] = "no-store"
            logger().info(
                "event=http_request method=%s target=%s status=%s duration_ms=%s",
                request.method,
                category,
                response.status_code,
                round((perf_counter() - started_at) * 1000),
            )
            return response
        finally:
            _request_reference.reset(token)


def install_request_tracing(application: object) -> None:
    """Install HTTP trace correlation once without changing NiceGUI route behavior."""
    if getattr(application, "_sing_yin_request_tracing_installed", False):
        return
    add_middleware = getattr(application, "add_middleware", None)
    if not callable(add_middleware):
        raise TypeError("The application does not support HTTP middleware.")
    add_middleware(RequestTracingMiddleware)
    setattr(application, "_sing_yin_request_tracing_installed", True)


def record_operator_event(
    *,
    action: str,
    outcome: str,
    reference: str,
    started_at: float | None = None,
) -> None:
    """Record a payload-free operator event with optional elapsed time."""
    duration_ms = round((perf_counter() - started_at) * 1000) if started_at is not None else None
    logger().info(
        "event=operator_action reference=%s action=%s outcome=%s duration_ms=%s",
        reference,
        action,
        outcome,
        duration_ms if duration_ms is not None else "not_recorded",
    )


def record_operator_failure(
    error: BaseException,
    *,
    action: str,
    reference: str | None = None,
    started_at: float | None = None,
) -> str:
    """Record a local traceback and return a safe reference for the operator.

    Action names are developer-controlled constants.  No form values, names,
    leave reasons, roster rows, or PDF content are passed to this function.
    """
    reference = reference or new_operation_reference()
    duration_ms = round((perf_counter() - started_at) * 1000) if started_at is not None else None
    logger().warning(
        "event=operator_action_failed reference=%s action=%s error_type=%s location=%s duration_ms=%s",
        reference,
        action,
        type(error).__name__,
        _trace_location(error.__traceback__),
        duration_ms if duration_ms is not None else "not_recorded",
    )
    return reference


def record_operator_partial_failure(
    error: BaseException,
    *,
    action: str,
    reference: str,
    started_at: float | None = None,
) -> None:
    """Record that the durable write committed but its recovery snapshot failed."""
    duration_ms = round((perf_counter() - started_at) * 1000) if started_at is not None else None
    logger().warning(
        "event=operator_action_partial reference=%s action=%s durable_state=committed backup=failed error_type=%s location=%s duration_ms=%s",
        reference,
        action,
        type(error).__name__,
        _trace_location(error.__traceback__),
        duration_ms if duration_ms is not None else "not_recorded",
    )


def install_exception_hooks() -> None:
    """Keep otherwise uncaught process and thread failures in the local log."""
    global _hooks_installed
    if _hooks_installed:
        return
    previous_sys_hook = sys.excepthook

    def handle_exception(error_type, error, traceback) -> None:  # type: ignore[no-untyped-def]
        if issubclass(error_type, KeyboardInterrupt):
            previous_sys_hook(error_type, error, traceback)
            return
        logger().critical(
            "event=uncaught_process_exception error_type=%s location=%s",
            error_type.__name__,
            _trace_location(traceback),
        )

    def handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        logger().critical(
            "event=uncaught_thread_exception thread=%s error_type=%s location=%s",
            args.thread.name if args.thread else "unknown",
            args.exc_type.__name__,
            _trace_location(args.exc_traceback),
        )

    if sys.excepthook is not handle_exception:
        sys.excepthook = handle_exception
    if threading.excepthook is not handle_thread_exception:
        threading.excepthook = handle_thread_exception
    _hooks_installed = True


def _is_expected_client_disconnect(error: object) -> bool:
    """Recognise the Windows socket reset emitted when a browser closes a local connection."""
    if not isinstance(error, ConnectionResetError):
        return False
    codes = {getattr(error, "errno", None), getattr(error, "winerror", None)}
    return bool(codes & _WINDOWS_CLIENT_DISCONNECT_CODES)


def install_asyncio_exception_handler(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Capture uncaught event-loop failures without exposing exception messages.

    Windows' proactor transport reports a browser closing a localhost socket as
    an event-loop exception.  That condition is recorded as an informational
    disconnect instead of alarming the operator.  Every other asynchronous
    failure remains critical and is delegated to the previous/default handler.
    """
    event_loop = loop or asyncio.get_running_loop()
    if getattr(event_loop, _ASYNCIO_HOOK_MARKER, False):
        return
    previous_handler = event_loop.get_exception_handler()

    def handle_asyncio_exception(
        active_loop: asyncio.AbstractEventLoop,
        context: dict[str, object],
    ) -> None:
        error = context.get("exception")
        if _is_expected_client_disconnect(error):
            logger().info("event=client_connection_closed error_type=ConnectionResetError")
            return

        error_type = type(error).__name__ if isinstance(error, BaseException) else "UnknownAsyncioError"
        traceback = error.__traceback__ if isinstance(error, BaseException) else None
        logger().critical(
            "event=uncaught_async_exception error_type=%s location=%s",
            error_type,
            _trace_location(traceback),
        )
        if previous_handler is not None:
            previous_handler(active_loop, context)
        else:
            active_loop.default_exception_handler(context)

    event_loop.set_exception_handler(handle_asyncio_exception)
    setattr(event_loop, _ASYNCIO_HOOK_MARKER, True)
