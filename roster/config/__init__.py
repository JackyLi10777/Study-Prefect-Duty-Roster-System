"""roster.config - SSOT for all scheduling rules and constants (see AGENTS.md §1 and §3).

Re-exports everything from constants so that:
    from roster.config import DAYS, ROWS_ROSTER, ROOMS_CONFIG, get_weight, is_assistant_head_only_role, ...
still works cleanly.
"""
from .constants import *  # noqa: F401,F403
