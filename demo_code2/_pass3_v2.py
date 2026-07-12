import pathlib, py_compile, subprocess

# ===== 1. Rewrite error_handler.py =====
script = """\"\"\"
Global exception handling with request_id + traceback logging.
Provides reusable helpers for logging errors with full context.
\"\"\"

import logging
import traceback
from typing import Optional

from utils.context import get_request_id

logger = logging.getLogger("sing_yin.errors")


def log_exception_with_context(exc: Exception, request=None):
    \"\"\"Log an exception with full traceback, request_id, and HTTP context.

    Uses logger.exception() to automatically capture the full stack trace.
    Includes HTTP method, path, and request_id when a request object is available.

    Args:
        exc: The exception that occurred.
        request: Optional Starlette/FastAPI Request object for HTTP context.
    \"\"\"
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


def safe_call(func, *args, context: str = "", **kwargs):
    \"\"\"Call a function safely, logging any exceptions without crashing.

    Args:
        func: The function to call.
        context: Human-readable label for the operation (for log readability).
    \"\"\"
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_exception_with_context(e)
        return None
"""

pathlib.Path(r"D:\code_v2\app\utils\error_handler.py").write_text(script, "utf-8")
py_compile.compile(r"D:\code_v2\app\utils\error_handler.py", doraise=True)
print("1. error_handler.py: updated")

# ===== 2. Add exception handlers to main.py =====
p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")

# Add imports for exception handling
old_imports = "from components.sidebar import create_sidebar"
new_imports = """from components.sidebar import create_sidebar
from utils.error_handler import log_exception_with_context

# Exception handler imports
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException"""
c = c.replace(old_imports, new_imports)

# Add exception handlers before the route section
old_routes = """# =============================================================================
# Root redirect + Design System page
# =============================================================================

@ui.page("/design")"""
new_routes = """# =============================================================================
# Global Exception Handlers
# =============================================================================

async def global_exception_handler(request: Request, exc: Exception):
    \"\"\"Catch-all handler for unhandled exceptions.
    Logs full traceback with request context and returns JSON 500.
    \"\"\"
    log_exception_with_context(exc, request)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "request_id": request.headers.get("X-Request-ID", "-"),
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    \"\"\"Handler for HTTP exceptions (4xx, 5xx).
    Logs warning with context and returns appropriate JSON response.
    \"\"\"
    logger = __import__("logging").getLogger("sing_yin.http")
    rid = request.headers.get("X-Request-ID", "-")
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path} [rid={rid}]: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": rid,
        },
    )


# Register exception handlers
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


# =============================================================================
# Root redirect + Design System page
# =============================================================================

@ui.page("/design")"""
c = c.replace(old_routes, new_routes)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("2. main.py: exception handlers added + registered")

# ===== Verify =====
for f in ["app/utils/error_handler.py", "app/main.py"]:
    py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    print(f"  {f}: syntax OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Quick import test
import sys; sys.path.insert(0, r"D:\code_v2")
try:
    from utils.error_handler import log_exception_with_context
    print("Import test: OK")
except Exception as e:
    print(f"Import test: {e}")
