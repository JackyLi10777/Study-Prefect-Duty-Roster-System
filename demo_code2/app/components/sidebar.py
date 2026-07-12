"""
Sidebar navigation for the Sing Yin Study Prefect Duty Roster System.
Follows Professional Teal Design System v4.0. Dark mode aware.
"""
from nicegui import ui, app
from theme import get_theme, toggle_theme
from utils.i18n import t


def create_sidebar():
    """Create a persistent sidebar with navigation links."""
    with ui.left_drawer(value=True, elevated=True, bordered=True).classes(
        "bg-white dark:bg-slate-900 w-64 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700 transition-colors duration-200"
    ) as drawer:
        with ui.column().classes("w-full"):
            # Brand area with subtle HyperOS gradient
            with ui.row().classes(
                "w-full items-center px-4 py-5 gap-2 bg-gradient-to-br from-teal-50 to-white dark:from-teal-900/40 dark:to-slate-900"
            ):
                ui.icon("school", size="28px").classes("text-teal-700 dark:text-teal-400")
                ui.label(t("\u8056\u8a00\u4e2d\u5b78", "Sing Yin")).classes("text-lg font-bold text-teal-700 dark:text-teal-400")

            ui.separator().classes("mb-2 dark:bg-slate-700 mx-2")

            # Navigation items
            nav_items = [
                ("/dashboard", "space_dashboard", t("\u5100\u8868\u677f", "Dashboard")),
                ("/roster", "grid_view", t("\u503c\u65e5\u8868", "Roster")),
                ("/prefects", "people", t("\u98a8\u7d00\u7ba1\u7406", "Prefects")),
                ("/leave", "event_busy", t("\u8acb\u5047\u8abf\u6574", "Leave")),
                ("/audit", "history", t("\u5be9\u8a08\u65e5\u8a8c", "Audit Log")),
                ("/design", "palette", t("\u8a2d\u8a08\u7cfb\u7d71", "Design")),
            ]

            current_page = ui.context.client.page.path if hasattr(ui.context.client, 'page') else "/dashboard"

            for path, icon, label in nav_items:
                is_active = current_page == path
                bg = "bg-teal-50 dark:bg-teal-900/40 border-l-4 border-teal-600 dark:border-teal-400 pl-2" if is_active else "hover:bg-slate-100 dark:hover:bg-slate-800"
                text_color = "text-teal-700 dark:text-teal-300 font-semibold" if is_active else "text-slate-600 dark:text-slate-300"

                with ui.link(target=path).classes(f"no-underline {bg} mx-2 rounded-lg transition-colors duration-150 cursor-pointer"):
                    with ui.row().classes("w-full items-center px-3 py-2.5 gap-3"):
                        ui.icon(icon, size="20px").classes(text_color)
                        ui.label(label).classes(f"text-sm {text_color}")

            ui.separator().classes("my-2 dark:bg-slate-700 mx-2")

            # Theme toggle
            with ui.row().classes("w-full items-center px-4 py-3 gap-2"):
                current = get_theme()
                icon_name = "dark_mode" if current == "light" else "light_mode"
                label_text = t("\u6df1\u8272\u6a21\u5f0f", "Dark Mode") if current == "light" else t("\u6dfa\u8272\u6a21\u5f0f", "Light Mode")
                ui.button(icon=icon_name, on_click=toggle_theme).props("flat round size=sm")
                ui.label(label_text).classes("text-xs text-slate-500 dark:text-slate-400")

            # Language toggle
            with ui.row().classes("w-full items-center px-4 py-2 gap-2"):
                lang = app.storage.user.get("language", "zh")
                ui.button("\u4e2d", on_click=lambda: app.storage.user.update({"language": "zh"})).props(
                    "flat round size=sm color=teal-7" if lang == "zh" else "flat round size=sm text-slate-500 dark:text-slate-400"
                )
                ui.button("EN", on_click=lambda: app.storage.user.update({"language": "en"})).props(
                    "flat round size=sm color=teal-7" if lang == "en" else "flat round size=sm text-slate-500 dark:text-slate-400"
                )

    return drawer
