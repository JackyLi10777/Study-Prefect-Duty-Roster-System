"""
App header bar with theme toggle and language switch.
"""
from nicegui import ui, app
from theme import get_theme, toggle_theme


def create_header(title: str = "Sing Yin Study Prefect Roster", lang_toggle: bool = True):
    """Create the app header bar with theme toggle and optional language switch."""
    with ui.header(elevated=True).classes(
        "bg-white dark:bg-slate-800 px-6 py-3"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(title).classes(
                "text-[18px] font-semibold leading-snug text-teal-700 dark:text-teal-400"
            )
            ui.space()
            theme_icon = "light_mode" if get_theme() == "dark" else "dark_mode"
            ui.button(icon=theme_icon, on_click=toggle_theme).props("flat round")
            if lang_toggle:
                current_lang = app.storage.user.get("language", "en")
                lang_label = "EN" if current_lang == "zh" else "ZH"
                ui.button(
                    lang_label,
                    icon="translate",
                    on_click=lambda: _switch_language()
                ).props("flat color=teal-7").classes("text-xs font-medium")


def _switch_language():
    """Toggle between English and Chinese."""
    current = app.storage.user.get("language", "en")
    new_lang = "zh" if current == "en" else "en"
    app.storage.user["language"] = new_lang
    ui.notify(
        "Switched to Chinese" if new_lang == "zh" else "Switched to English",
        type="info", position="top",
    )
