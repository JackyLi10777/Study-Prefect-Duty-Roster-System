"""
Reusable KPI stat card component.
Supports optional HyperOS gradient background (135 deg, restrained).
"""
from nicegui import ui

class KpiCard:
    """A KPI stat card showing a large number with a label.

    Usage:
        KpiCard("28", "Total Prefects")
        KpiCard("12.5", "Avg Load (pts)", gradient=True)
    """
    def __init__(self, value: str, label: str, *, color: str = "text-teal-700 dark:text-teal-400", gradient: bool = False):
        gradient_cls = ""
        if gradient:
            gradient_cls = "bg-gradient-to-br from-teal-50 to-white dark:from-teal-900/20 dark:to-slate-800"
        with ui.card().classes(
            f"flex-1 min-w-[160px] rounded-xl shadow-sm dark:shadow-md p-5 text-center {gradient_cls}"
        ):
            ui.label(value).classes(f"text-3xl font-bold {color}")
            ui.label(label).classes(f"text-[13px] font-normal leading-snug text-slate-500 dark:text-slate-400 mt-1")
