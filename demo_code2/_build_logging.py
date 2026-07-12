import pathlib

# Pass 1: logging_config.py
script1 = '''"""
Centralized logging configuration for Sing Yin Study Prefect Roster.
Provides console + rotating file logging with consistent formatting.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logging(level: int = logging.INFO):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger("sing_yin")
    root_logger.setLevel(level)
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str):
    return logging.getLogger(f"sing_yin.{name}")
'''

pathlib.Path(r"D:\code_v2\app\utils\logging_config.py").write_text(script1, "utf-8")
print("Pass 1: logging_config.py created")

# Pass 2: context.py + middleware
script2 = '''"""
Request ID context using ContextVar for cross-request trace correlation.
"""

import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="--------")


def set_request_id(rid: str = None) -> str:
    """Set a new request ID. If none provided, generates a UUID."""
    rid = rid or uuid.uuid4().hex[:12]
    request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    """Get the current request ID."""
    return request_id_var.get()


class RequestIDFilter(logging.Filter):
    """Inject request_id into log records."""
    def filter(self, record):
        record.request_id = get_request_id()
        return True
'''

pathlib.Path(r"D:\code_v2\app\utils\context.py").write_text(script2, "utf-8")

# Create middleware directory
pathlib.Path(r"D:\code_v2\app\middleware").mkdir(exist_ok=True)

script3 = '''"""
Request ID Middleware for FastAPI/NiceGUI.
Assigns a unique ID to every HTTP request for trace correlation.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from utils.context import set_request_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = set_request_id()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
'''

pathlib.Path(r"D:\code_v2\app\middleware\__init__.py").write_text("", "utf-8")
pathlib.Path(r"D:\code_v2\app\middleware\request_id.py").write_text(script3, "utf-8")
print("Pass 2: context.py + middleware created")

# Pass 3: Exception handlers
script4 = '''"""
Global exception handling with request_id + traceback logging.
"""

import logging
import traceback
from utils.context import get_request_id

logger = logging.getLogger("sing_yin.errors")


def log_exception(exc: Exception, context: str = ""):
    """Log an exception with full traceback and request context."""
    rid = get_request_id()
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(
        f"[{context}] {type(exc).__name__}: {exc}\\nTraceback:\\n{tb}"
    )


def safe_call(func, *args, context: str = "", **kwargs):
    """Call a function safely, logging any exceptions."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_exception(e, context)
        return None
'''

pathlib.Path(r"D:\code_v2\app\utils\error_handler.py").write_text(script4, "utf-8")
print("Pass 3: error_handler.py created")

import py_compile
for f in ["app/utils/logging_config.py", "app/utils/context.py", 
          "app/middleware/request_id.py", "app/utils/error_handler.py"]:
    py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    print(f"  {f}: syntax OK")

import subprocess
r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
