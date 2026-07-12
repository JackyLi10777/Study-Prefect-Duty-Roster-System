import pathlib, py_compile, subprocess

# ===== 1. Update logging_config.py: LOG_DIR env var + better comments =====
p = pathlib.Path(r"D:\code_v2\app\utils\logging_config.py")
c = p.read_text("utf-8")

# Replace the LOG_DIR/LOG_FILE section with env var support
old_log = """# Log directory and file paths (relative to project root)
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file before rotation
BACKUP_COUNT = 10             # Keep up to 10 rotated log files"""

new_log = """# Log directory: uses LOG_DIR env var if set, otherwise defaults to project-root/logs/
_LOG_DIR_ENV = os.getenv("LOG_DIR", "")
if _LOG_DIR_ENV:
    LOG_DIR = Path(_LOG_DIR_ENV)
else:
    LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per log file before rotation
BACKUP_COUNT = 10             # Keep up to 10 rotated log files"""

c = c.replace(old_log, new_log)

# Update the docstring to mention LOG_DIR
c = c.replace(
    "Supports LOG_LEVEL environment variable for controlling verbosity.",
    "Supports LOG_LEVEL and LOG_DIR environment variables."
)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("1. logging_config.py: LOG_DIR env var support added")

# ===== 2. Update error_handler.py: flush after critical errors =====
p2 = pathlib.Path(r"D:\code_v2\app\utils\error_handler.py")
c2 = p2.read_text("utf-8")

# Add flush after exception logging
old_flush = """    logger.exception(f"[{context_str}] {type(exc).__name__}: {exc}")"""
new_flush = """    logger.exception(f"[{context_str}] {type(exc).__name__}: {exc}")
    # Force flush to ensure error logs are written immediately
    for handler in logger.handlers + logging.getLogger("sing_yin").handlers:
        handler.flush()"""

c2 = c2.replace(old_flush, new_flush)

# Add logging import if not already there
if "import logging" not in c2:
    c2 = c2.replace("import logging\n", "")
    c2 = c2.replace("import traceback", "import logging\nimport traceback")

p2.write_text(c2, "utf-8")
py_compile.compile(str(p2), doraise=True)
print("2. error_handler.py: flush() on critical errors")

# ===== 3. Verify =====
for f in ["app/utils/logging_config.py", "app/utils/error_handler.py"]:
    py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    print(f"   {f}: syntax OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Quick functional check: LOG_DIR env var
import os
os.environ["LOG_DIR"] = r"D:\code_v2\logs"
import sys; sys.path.insert(0, r"D:\code_v2")
from utils.logging_config import LOG_DIR, LOG_FILE
print(f"\nLOG_DIR (from env): {LOG_DIR}")
print(f"LOG_FILE: {LOG_FILE}")
del os.environ["LOG_DIR"]
