"""
Global exception handling with request_id + traceback logging.
Provides reusable helpers for logging errors with full context.
"""

import logging
import traceback
from typing import Optional

from utils.context import get_request_id

logger = logging.getLogger("sing_yin.errors")


def log_exception_with_context(exc: Exception, request=None):
    """Log an exception with full traceback, request_id, and HTTP context.

    Uses logger.exception() to automatically capture the full stack trace.
    Includes HTTP method, path, and request_id when a request object is available.

    Args:
        exc: The exception that occurred.
        request: Optional Starlette/FastAPI Request object for HTTP context.
    """
    rid = get_request_id() or "-"

    # Build context string from request if available
    ctx_parts = []
    if request is not None:
        try:
            ctx_parts.append(f"method={request.method}")
            ctx_parts.append(f"path={request.url.path}")
        except Exception:
            pass
    ctx_parts.append(f"rid={rid}")
    context_str = " ".join(ctx_parts)

    logger.exception(f"[{context_str}] {type(exc).__name__}: {exc}")
    # Force flush to ensure error logs are written immediately
    for handler in logger.handlers + logging.getLogger("sing_yin").handlers:
        handler.flush()


def safe_call(func, *args, context: str = "", **kwargs):
    """Call a function safely, logging any exceptions without crashing.

    Args:
        func: The function to call.
        context: Human-readable label for the operation (for log readability).
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_exception_with_context(e)
        return None
