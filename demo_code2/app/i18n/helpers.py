"""i18n helper functions. Thin wrappers over language state."""
from nicegui import app


def lang() -> str:
    """Return current language code ('zh' or 'en')."""
    return app.storage.user.get("language", "zh")


def is_zh() -> bool:
    """True if current language is Chinese."""
    return lang() == "zh"


def t(zh: str, en: str) -> str:
    """Return Chinese if language is zh, else English."""
    return zh if is_zh() else en

def notify_t(zh_msg: str, en_msg: str, type: str = "positive", position: str = "top", timeout: int = None, **kwargs):
    """Issue a language-aware notification. Uses zh or en based on current language."""
    from nicegui import ui
    msg = zh_msg if is_zh() else en_msg
    if timeout is not None:
        ui.notify(msg, type=type, position=position, timeout=timeout, **kwargs)
    else:
        ui.notify(msg, type=type, position=position, **kwargs)

