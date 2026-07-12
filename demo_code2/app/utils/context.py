"""
Request ID context using ContextVar for cross-request trace correlation.
Provides thread-safe request ID propagation across async request lifecycle.
"""

import uuid
from contextvars import ContextVar

# ContextVar for storing the current request ID
# Default is None (no request context outside of middleware)
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a unique request ID using UUID4."""
    return str(uuid.uuid4())


def get_request_id() -> str:
    """Safely retrieve the current request_id from context.
    Returns None if no request context is active.
    """
    return request_id_var.get()


def set_request_id(request_id: str):
    """Set the request_id into the context.
    Returns the context token for later reset.
    """
    return request_id_var.set(request_id)


def reset_request_id(token):
    """Reset the request_id context to its previous value."""
    request_id_var.reset(token)
