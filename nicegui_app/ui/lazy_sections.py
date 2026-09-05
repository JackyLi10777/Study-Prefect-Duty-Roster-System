"""Retained first-use sections for operator details, not hidden eager forms."""
from collections.abc import Callable

from nicegui import events, ui


def lazy_expansion(label: str, *, icon: str, test_id: str, render: Callable[[], None]) -> ui.expansion:
    with ui.expansion(label, icon=icon, value=False).classes("w-full").props(
        f"data-testid={test_id}"
    ) as expansion:
        content = ui.column().classes("w-full").props(f"data-testid={test_id}-content")
    mounted = False

    def mount(event: events.ValueChangeEventArguments) -> None:
        nonlocal mounted
        if not event.value or mounted:
            return
        try:
            with content:
                render()
        except Exception:
            content.clear()
            raise
        mounted = True

    expansion.on_value_change(mount)
    expansion.on("before-hide", js_handler=f"""() => {{
        const root = document.getElementById('c{expansion.id}');
        const content = document.getElementById('c{content.id}');
        if (content?.contains(document.activeElement)) {{
            root?.querySelector('.q-expansion-item__container > .q-item')?.focus({{preventScroll:true}});
        }}
    }}""")
    return expansion
