"""
Shared page layout: Header + Sidebar + Content.
Every page uses this to guarantee consistent navigation and theming.
"""
from nicegui import ui, app
from theme import apply_theme, get_theme, toggle_theme, Type
from components.sidebar import create_sidebar
from components.sounds import inject_sound_api


def page_layout(title: str = "Sing Yin Study Prefect Roster"):
    """Apply the shared layout skeleton for any page.
    
    Call this at the top of every @ui.page handler.
    It applies the design theme, creates the sidebar, and provides a content column.
    
    Usage inside a page function:
        @ui.page("/my-page")
        def my_page():
            apply_theme()
            page_layout("My Page Title")
            with ui.column().classes("w-full px-6 py-6 gap-4"):
                # Your page content here
    """
    apply_theme()
    inject_sound_api()
    create_sidebar()
    return None  # Sidebar is created as a side effect via left_drawer
