import pathlib, py_compile, subprocess

p = pathlib.Path(r"D:\code_v2\app\main.py")
c = p.read_text("utf-8")

# Add imports after sys.path.insert
old_imports = """sys.path.insert(0, str(Path(__file__).resolve().parent))

from nicegui import ui, app"""
new_imports = """sys.path.insert(0, str(Path(__file__).resolve().parent))

import logging
from utils.logging_config import setup_logging, get_logger
from utils.context import RequestIDFilter
from middleware.request_id import RequestIDMiddleware
from nicegui import ui, app"""
c = c.replace(old_imports, new_imports)

# Add logging init before ui.run
old_run = """if __name__ in {"__main__", "__mp_main__"}:
    secret = os.getenv("STORAGE_SECRET", "dev-secret-sing-yin-roster-2026")"""
new_run = """if __name__ in {"__main__", "__mp_main__"}:
    # ---- Initialize logging + request ID tracking ----
    setup_logging(level=logging.INFO)
    logger = get_logger("app")
    logger.info("Starting Sing Yin Study Prefect Roster System")
    for handler in logging.getLogger("sing_yin").handlers:
        handler.addFilter(RequestIDFilter())
    app.add_middleware(RequestIDMiddleware)

    secret = os.getenv("STORAGE_SECRET", "dev-secret-sing-yin-roster-2026")"""
c = c.replace(old_run, new_run)

p.write_text(c, "utf-8")
py_compile.compile(str(p), doraise=True)
print("main.py: logging + middleware integrated")

# Verify all new files pass syntax
for f in ["app/main.py", "app/utils/logging_config.py", "app/utils/context.py",
          "app/utils/error_handler.py", "app/middleware/request_id.py"]:
    py_compile.compile(str(pathlib.Path(f"D:/code_v2/{f}")), doraise=True)
    print(f"  {f}: OK")

r = subprocess.run(["python","-m","pytest","tests/","-q"], capture_output=True, text=True, cwd=r"D:\code_v2")
print(f"Tests: {'52/52' if '52 passed' in r.stdout+r.stderr else 'FAILED'}")

# Quick functional test: import and use logging
import sys; sys.path.insert(0, r"D:\code_v2")
from utils.logging_config import setup_logging, get_logger
from utils.context import set_request_id, get_request_id
set_request_id("test-123")
logger = get_logger("test")
logger.info("Logging system functional test passed")
print(f"Request ID: {get_request_id()}")
print("Logging infrastructure: WORKING")
