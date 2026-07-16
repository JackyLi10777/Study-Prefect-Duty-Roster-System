from pathlib import Path


def test_only_access_aware_preference_module_may_use_persistent_user_storage() -> None:
    project_root = Path(__file__).resolve().parents[1]
    python_sources = (project_root / "nicegui_app").rglob("*.py")
    offenders = []
    for source in python_sources:
        text = source.read_text(encoding="utf-8")
        if "app.storage.user" in text and source.name != "preferences.py":
            offenders.append(source.relative_to(project_root).as_posix())
    assert offenders == []


def test_guest_preference_branch_is_connection_local() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "nicegui_app"
        / "ui"
        / "preferences.py"
    ).read_text(encoding="utf-8")
    assert "app.storage.client if mode is AccessMode.GUEST else app.storage.user" in source
