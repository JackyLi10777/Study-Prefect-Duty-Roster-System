# core.py (root shim / compatibility layer)
"""
Temporary root-level shim for the modular refactor (see approved plan.md).

All existing `from core import generate_roster, ...` continue to work unchanged.

The real implementation is now at:
    roster/core/engine.py
    (re-exported via roster/core/__init__.py)

Room 302/303 and AHP rules are preserved exactly.
This file will be cleaned up after full verification.
"""
from roster.core import (
    generate_roster,
    validate_and_compute,
    recommend_substitutes,
    apply_post_publication_leave_adjustment,
)

print("✅ [shim] root core.py now forwards to roster.core (generate_roster logic unchanged)")
