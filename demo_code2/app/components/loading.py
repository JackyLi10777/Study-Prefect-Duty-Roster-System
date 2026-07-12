"""
Loading and progress feedback components.
HyperOS-style loading states for long operations.
"""
from nicegui import ui
from components.sounds import play_success, play_error


def show_loading(message: str = "Loading..."):
    """Create a centered loading spinner with message. Use as context manager.

    Usage:
        with show_loading("Generating roster..."):
            # long operation
            pass
        ui.notify("Done!", type="positive")
    """
    container = ui.element("div").classes(
        "flex flex-col items-center justify-center py-12 gap-4"
    )
    with container:
        ui.spinner(size="lg", type="bars").props("color=teal-7")
        ui.label(message).classes("text-sm text-slate-500 dark:text-slate-400 h-loading-text")
    return LoadingContext(container)


class LoadingContext:
    """Context manager that clears the loading UI on exit."""
    def __init__(self, container):
        self.container = container

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.container.clear()


def show_progress(message: str = "Processing..."):
    """Create a progress bar with message. Returns update function.

    Usage:
        update = show_progress("Generating roster...")
        update(0.3, "Analyzing prefects...")
        update(0.7, "Assigning slots...")
        update(1.0, "Done!")
    """
    container = ui.element("div").classes("flex flex-col items-center gap-3 py-8")
    with container:
        bar = ui.linear_progress(value=0).props("rounded color=teal-7 size=20px").classes("w-full max-w-md")
        label = ui.label(message).classes("text-sm text-slate-500 dark:text-slate-400")

    def update(value: float, msg: str = None):
        bar.value = value
        if msg:
            label.set_text(msg)

    return update


def show_skeleton(lines: int = 3):
    """Create skeleton loading placeholders for content areas.

    Usage:
        with show_skeleton(4):
            pass
        # Replace with real content
    """
    container = ui.element("div").classes("flex flex-col gap-3 py-4 w-full")
    with container:
        for i in range(lines):
            width = [100, 85, 70, 60][i % 4]  # Varying widths
            ui.element("div").classes(f"h-skeleton h-6 w-[{width}pct]")
    return LoadingContext(container)


def notify_success(message: str):
    """Show success notification with subtle sound."""
    ui.notify(message, type="positive", position="top", timeout=4000)
    play_success()


def notify_error(message: str):
    """Show error notification with subtle sound."""
    ui.notify(message, type="negative", position="top", timeout=6000)
    play_error()


def notify_warning(message: str):
    """Show warning notification."""
    ui.notify(message, type="warning", position="top", timeout=5000)
