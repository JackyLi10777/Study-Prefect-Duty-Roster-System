from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_and_verification_dependencies_are_hash_locked() -> None:
    runtime = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    development = (ROOT / "requirements-dev.lock").read_text(encoding="utf-8")

    for dependency in ("nicegui==", "sqlalchemy==", "alembic==", "reportlab=="):
        assert dependency in runtime.lower()
    for tool in ("pytest==", "pip-audit==", "bandit==", "detect-secrets=="):
        assert tool in development.lower()
    assert "--hash=sha256:" in runtime
    assert "--hash=sha256:" in development


def test_hong_kong_timezone_data_is_available_and_locked_for_windows() -> None:
    runtime_requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    runtime_lock = (ROOT / "requirements.lock").read_text(encoding="utf-8").lower()

    assert ZoneInfo("Asia/Hong_Kong").key == "Asia/Hong_Kong"
    assert any(line.startswith("tzdata") for line in runtime_requirements.splitlines())
    assert "tzdata==" in runtime_lock


def test_github_quality_gates_use_full_history_and_locked_dependencies() -> None:
    workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")

    assert "fetch-depth: 0" in workflow
    assert "--require-hashes -r requirements-dev.lock" in workflow
    assert "check_repository_hygiene.py" in workflow
    assert "run_security_checks.py" in workflow


def test_codeql_and_dependabot_are_configured() -> None:
    assert (ROOT / ".github" / "workflows" / "codeql.yml").exists()
    dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: pip" in dependabot
    assert "package-ecosystem: github-actions" in dependabot
