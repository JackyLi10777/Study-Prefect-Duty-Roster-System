# ui_components.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing imports from ui_components continue to work.
The real UI components are now at:
    roster/ui/components.py
"""
from roster.ui.components import (
    render_sidebar,
    show_daily_verse,
    render_control_buttons,
)

print("✅ [shim] root ui_components.py now forwards to roster.ui.components")
