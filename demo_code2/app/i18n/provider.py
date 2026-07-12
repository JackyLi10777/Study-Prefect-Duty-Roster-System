"""Language switching logic and state management."""
from nicegui import app


def set_language(lang_code: str):
    """Set the current language."""
    app.storage.user.update({"language": lang_code})


def toggle_language():
    """Toggle between zh and en."""
    current = app.storage.user.get("language", "zh")
    set_language("en" if current == "zh" else "zh")
