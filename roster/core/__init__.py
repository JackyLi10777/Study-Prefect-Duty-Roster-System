"""roster.core - Business logic layer.

The core scheduler and fairness engine. All AGENTS.md §1 rules (student eligibility, Room 302/303 restrictions, AHP privileges/hard restrictions, fixed priority, fairness, one-per-day + no-consecutive invariants, leave adjustment mutation semantics) are enforced here.

Public exports (keep signatures 100% identical):
    generate_roster
    validate_and_compute
    recommend_substitutes
    apply_post_publication_leave_adjustment
"""
from .engine import (
    generate_roster,
    validate_and_compute,
    recommend_substitutes,
    apply_post_publication_leave_adjustment,
    annotate_mentoring_pairs,
)
