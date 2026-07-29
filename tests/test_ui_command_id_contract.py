from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "nicegui_app" / "ui"

# Public write boundaries whose idempotency receipt must be tied to one explicit
# UI intent. Keep this list deliberately small and semantic: helper/internal
# methods are covered by their owning service tests.
RETRY_SENSITIVE_UI_WRITES = {
    "archive_prefect",
    "create_prefect",
    "create_share",
    "import_prefects",
    "update_prefect",
}


def test_retry_sensitive_ui_writes_pass_an_explicit_command_id() -> None:
    missing: list[str] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in RETRY_SENSITIVE_UI_WRITES:
                continue
            if not any(keyword.arg == "command_id" for keyword in node.keywords):
                missing.append(
                    f"{path.relative_to(PROJECT_ROOT).as_posix()}:{node.lineno} "
                    f"{node.func.attr}"
                )

    assert missing == [], "UI writes missing explicit command_id:\n" + "\n".join(missing)
