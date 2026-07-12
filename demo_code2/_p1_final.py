import pathlib, py_compile, subprocess

script = """\"\"\"
Centralized logging configuration for the Sing Yin Study Prefect Roster.
Provides console + rotating file logging with clean formatting.
Supports LOG_LEVEL environment variable for controlling verbosity.
\"\"\"

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Log directory and file paths (relative to project root)
LOG_DIR = Path(__file__).resolve().parent.parent.parent / \"logs\"
LOG_FILE = LOG_DIR / \"app.log\"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file before rotation
BACKUP_COUNT = 10             # Keep up to 10 rotated log files


def setup_logging(level=None):
    \"\"\"Initialize logging with console + rotating file handlers.

    Reads LOG_LEVEL env var if level is not provided (defaults to INFO).
    \"\"\"
    if level is None:
        level = getattr(logging, os.getenv(\"LOG_LEVEL\", \"INFO\").upper(), logging.INFO)

    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger(\"sing_yin\")
    root_logger.setLevel(level)

    # Prevent duplicate handlers on hot-reload
    if root_logger.handlers:
        return root_logger

    # Clean, readable log format
    formatter = logging.Formatter(
        \"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s\",
        datefmt=\"%Y-%m-%d %H:%M:%S\",
    )

    # Console handler: prints log messages to stdout during development
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # Rotating file handler: writes persistent logs with automatic rotation
    file_handler = RotatingFileHandler(
        str(LOG_FILE), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding=\"utf-8\"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    root_logger.info(
        f\"Logging initialized: console + file (max {MAX_BYTES//1024//1024}MB, {BACKUP_COUNT} backups)\"
    )
    return root_logger


def get_logger(name):
    \"\"\"Get a child logger under the sing_yin namespace.\"\"\"
    return logging.getLogger(f\"sing_yin.{name}\")
"""

pathlib.Path(r"D:\code_v2\app\utils\logging_config.py").write_text(script, "utf-8")
py_compile.compile(r"D:\code_v2\app\utils\logging_config.py", doraise=True)
print("logging_config.py: updated - OK")

# Update main.py startup message
p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")
c = c.replace(
    'logger.info(\"Starting Sing Yin Study Prefect Roster System\")',
    'logger.info(\"Sing Yin Study Prefect Roster System starting...\")\n'
    '    logger.info(\"Logging system initialized. Writing logs to logs/app.log\")'
)
p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("main.py: updated - OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")
