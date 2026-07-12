"""Shared bilingual helper. Chinese primary, English secondary."""
from nicegui import app


def t(zh: str, en: str) -> str:
    """Return Chinese if language is zh, else English."""
    return zh if app.storage.user.get("language", "zh") == "zh" else en


def lang() -> str:
    """Return current language code ('zh' or 'en')."""
    return app.storage.user.get("language", "zh")


def is_zh() -> bool:
    """True if current language is Chinese."""
    return lang() == "zh"
