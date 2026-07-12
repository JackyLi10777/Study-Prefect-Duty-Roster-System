"""roster.ui - UI / Presentation layer (Streamlit-specific).

Contains the original ui_components logic:
- render_sidebar
- show_daily_verse
- render_control_buttons

All original UI functionality preserved exactly.
Business calls (e.g. to generate_roster) kept as-is per plan.
"""

from .components import (
    show_daily_verse,
    render_sidebar,
    render_control_buttons,
)
