from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTE_ROOT = PROJECT_ROOT / "nicegui_app" / "ui" / "page_routes"
SHARED_PATH = PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py"

EXPECTED_SHARED_ROUTE_API = {
    "_OPERATION_FAILED",
    "_delete_dialog_after_close",
    "_navigate_with_feedback",
    "_next_monday",
    "_open_roster_export_dialog",
    "_prefect_directory_rows",
    "_render_co_creation",
    "_render_empty_state",
    "_render_feedback_channel",
    "_render_flow_step",
    "_render_mobile_prefect_cards",
    "_render_operation_hint",
    "_render_responsive_table",
    "_render_roster_route_state",
    "_render_roster_table",
    "_render_storage_lifecycle",
    "_run_with_progress",
    "_safe_read_action",
    "_tone_badge",
}


def _route_modules() -> list[Path]:
    return sorted(path for path in ROUTE_ROOT.glob("*.py") if path.name != "__init__.py")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_page_routes_never_use_wildcard_imports() -> None:
    for path in _route_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        wildcard_imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and any(alias.name == "*" for alias in node.names)
        ]
        assert wildcard_imports == [], f"{path.name} must declare every dependency explicitly"


def test_page_shared_has_a_literal_stable_route_api() -> None:
    tree = ast.parse(SHARED_PATH.read_text(encoding="utf-8"), filename=str(SHARED_PATH))
    export_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    ]

    assert len(export_assignments) == 1
    exported = ast.literal_eval(export_assignments[0].value)
    assert isinstance(exported, tuple)
    assert set(exported) == EXPECTED_SHARED_ROUTE_API
    assert len(exported) == len(set(exported))


def test_routes_only_import_declared_page_shared_helpers() -> None:
    imported_helpers: set[str] = set()
    for path in _route_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "nicegui_app.ui.page_shared":
                imported_helpers.update(alias.name for alias in node.names)

    assert imported_helpers <= EXPECTED_SHARED_ROUTE_API
    assert imported_helpers == EXPECTED_SHARED_ROUTE_API


def test_page_shared_does_not_own_route_specific_dependencies() -> None:
    imported_modules = _imported_modules(SHARED_PATH)
    assert imported_modules.isdisjoint(
        {
            "nicegui_app.release_evidence",
            "nicegui_app.services.prefect_import_assistant",
            "nicegui_app.services.summary_report_export",
            "nicegui_app.ui.music",
            "nicegui_app.ui.platform_summary",
            "nicegui_app.ui.shell",
            "nicegui_app.utils.prefect_file_import",
            "nicegui_app.utils.prefect_import",
        }
    )


def test_route_package_imports_cleanly_in_a_fresh_process() -> None:
    env = os.environ.copy()
    python_paths = [
        PROJECT_ROOT,
        PROJECT_ROOT / "packages" / "roster_policy",
        PROJECT_ROOT / "packages" / "roster_core",
    ]
    existing_python_path = env.get("PYTHONPATH")
    if existing_python_path:
        python_paths.append(Path(existing_python_path))
    env["PYTHONPATH"] = os.pathsep.join(str(path) for path in python_paths)

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            (
                "import nicegui_app.ui.page_shared as shared; "
                "import nicegui_app.ui.page_routes as routes; "
                "assert len(shared.__all__) == 19; "
                "assert len(routes.__all__) == 6"
            ),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
