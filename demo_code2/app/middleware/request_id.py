"""
Request ID Middleware for FastAPI/NiceGUI.
Assigns a unique ID to every HTTP request and propagates it via headers.
Uses contextvars token pattern for proper lifecycle management.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from utils.context import generate_request_id, set_request_id, reset_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a unique request_id into every request.

    - Reads X-Request-ID from incoming headers if present
    - Otherwise generates a new UUID
    - Sets the ContextVar for the request lifecycle
    - Adds X-Request-ID to the response headers
    - Properly cleans up context in try/finally
    """

    async def dispatch(self, request, call_next):
        # Try to use existing request ID from headers, or generate new one
        request_id = request.headers.get("X-Request-ID", generate_request_id())

        # Set context var and store token for cleanup
        token = set_request_id(request_id)

        try:
            response = await call_next(request)
            # Add request ID to response so clients can correlate
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Always reset context to prevent leakage between requests
            reset_request_id(token)
