"""
Centralized logging configuration for the Sing Yin Study Prefect Roster.
Provides console + rotating file logging with request ID trace correlation.
Supports LOG_LEVEL and LOG_DIR environment variables.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.context import get_request_id

# Log directory: uses LOG_DIR env var if set, otherwise defaults to project-root/logs/
_LOG_DIR_ENV = os.getenv("LOG_DIR", "")
if _LOG_DIR_ENV:
    LOG_DIR = Path(_LOG_DIR_ENV)
else:
    LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file before rotation
BACKUP_COUNT = 10             # Keep up to 10 rotated log files


class RequestIDFilter(logging.Filter):
    """Automatically injects the current request_id into every log record.
    Falls back to "-" when no request context is active.
    """
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True


def setup_logging(level=None):
    """Initialize logging with console + rotating file handlers.

    Reads LOG_LEVEL env var if level is not provided (defaults to INFO).
    Adds RequestIDFilter to both handlers for automatic trace correlation.
    """
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
    """Get a child logger under the sing_yin namespace."""
    return logging.getLogger(f"sing_yin.{name}")
