import pathlib, py_compile, subprocess

# ===== 1. context.py - add generate_request_id, remove RequestIDFilter =====
ctx = """\"\"\"
Request ID context using ContextVar for cross-request trace correlation.
Provides thread-safe request ID propagation across async request lifecycle.
\"\"\"

import uuid
from contextvars import ContextVar

# ContextVar for storing the current request ID
# Default is None (no request context outside of middleware)
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    \"\"\"Generate a unique request ID using UUID4.\"\"\"
    return str(uuid.uuid4())


def get_request_id() -> str:
    \"\"\"Safely retrieve the current request_id from context.
    Returns None if no request context is active.
    \"\"\"
    return request_id_var.get()


def set_request_id(request_id: str):
    \"\"\"Set the request_id into the context.
    Returns the context token for later reset.
    \"\"\"
    return request_id_var.set(request_id)


def reset_request_id(token):
    \"\"\"Reset the request_id context to its previous value.\"\"\"
    request_id_var.reset(token)
"""

pathlib.Path(r"D:\code_v2\app\utils\context.py").write_text(ctx, "utf-8")
py_compile.compile(r"D:\code_v2\app\utils\context.py", doraise=True)
print("1. context.py: updated (generate_request_id + token pattern)")

# ===== 2. request_id.py - X-Request-ID header + try/finally =====
mid = """\"\"\"
Request ID Middleware for FastAPI/NiceGUI.
Assigns a unique ID to every HTTP request and propagates it via headers.
Uses contextvars token pattern for proper lifecycle management.
\"\"\"

from starlette.middleware.base import BaseHTTPMiddleware
from utils.context import generate_request_id, set_request_id, reset_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    \"\"\"Middleware that injects a unique request_id into every request.

    - Reads X-Request-ID from incoming headers if present
    - Otherwise generates a new UUID
    - Sets the ContextVar for the request lifecycle
    - Adds X-Request-ID to the response headers
    - Properly cleans up context in try/finally
    \"\"\"

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
"""

pathlib.Path(r"D:\code_v2\app\middleware\request_id.py").write_text(mid, "utf-8")
py_compile.compile(r"D:\code_v2\app\middleware\request_id.py", doraise=True)
print("2. request_id.py: updated (X-Request-ID + try/finally)")

# ===== 3. logging_config.py - add RequestIDFilter + update formatter =====
log_cfg = """\"\"\"
Centralized logging configuration for the Sing Yin Study Prefect Roster.
Provides console + rotating file logging with request ID trace correlation.
Supports LOG_LEVEL environment variable for controlling verbosity.
\"\"\"

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.context import get_request_id

# Log directory and file paths (relative to project root)
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file before rotation
BACKUP_COUNT = 10             # Keep up to 10 rotated log files


class RequestIDFilter(logging.Filter):
    \"\"\"Automatically injects the current request_id into every log record.
    Falls back to \"-\" when no request context is active.
    \"\"\"
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True


def setup_logging(level=None):
    \"\"\"Initialize logging with console + rotating file handlers.

    Reads LOG_LEVEL env var if level is not provided (defaults to INFO).
    Adds RequestIDFilter to both handlers for automatic trace correlation.
    \"\"\"
    if level is None:
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger("sing_yin")
    root_logger.setLevel(level)

    # Prevent duplicate handlers on hot-reload
    if root_logger.handlers:
        return root_logger

    # Log format includes request_id for trace correlation
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [rid=%(request_id)s] | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create RequestIDFilter instance
    rid_filter = RequestIDFilter()

    # Console handler: prints log messages to stdout during development
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    console.addFilter(rid_filter)
    root_logger.addHandler(console)

    # Rotating file handler: writes persistent logs with automatic rotation
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(rid_filter)
    root_logger.addHandler(file_handler)

    root_logger.info(
        f"Logging initialized: console + file (max {MAX_BYTES//1024//1024}MB, {BACKUP_COUNT} backups)"
    )
    return root_logger


def get_logger(name):
    \"\"\"Get a child logger under the sing_yin namespace.\"\"\"
    return logging.getLogger(f"sing_yin.{name}")
"""

pathlib.Path(r"D:\code_v2\app\utils\logging_config.py").write_text(log_cfg, "utf-8")
py_compile.compile(r"D:\code_v2\app\utils\logging_config.py", doraise=True)
print("3. logging_config.py: updated (RequestIDFilter + new formatter)")

# ===== 4. Update main.py - remove separate RequestIDFilter import =====
p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")
# Remove the separate RequestIDFilter import and handler filter injection
# (logging_config.py now handles this internally)
c = c.replace("from utils.context import RequestIDFilter\n", "")
c = c.replace("from middleware.request_id import RequestIDMiddleware\n", "from middleware.request_id import RequestIDMiddleware\n")
# Remove the manual filter injection (now done in setup_logging)
c = c.replace(
    "    for handler in logging.getLogger(\"sing_yin\").handlers:\n        handler.addFilter(RequestIDFilter())\n    ",
    "    "
)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("4. main.py: simplified (RequestIDFilter now in logging_config)")

# ===== Verify =====
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Functional test
import sys; sys.path.insert(0, r"D:\code_v2")
from utils.logging_config import setup_logging, get_logger
from utils.context import generate_request_id, set_request_id, get_request_id
rid = generate_request_id()
set_request_id(rid)
logger = setup_logging()
logger.info("Request ID functional test - should show rid=" + rid[:8] + "...")
print(f"Generated RID: {rid[:20]}...")
print(f"Context RID: {get_request_id()[:20]}...")
