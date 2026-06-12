# core.py (root shim / compatibility layer)
"""
Ultra-thin root-level compatibility shim.

Legacy `from core import generate_roster, ...` still work.

**Best practice:** Import directly from `roster.core`.

Core logic (with full AGENTS.md compliance: AHP gates, Room 302/303 rules, fairness, leave revocation) lives in roster/core/engine.py.
"""
from roster.core import (
    generate_roster,
    validate_and_compute,
    recommend_substitutes,
    apply_post_publication_leave_adjustment,
)

print("✅ [shim] root core.py → roster.core (thin compat)")
