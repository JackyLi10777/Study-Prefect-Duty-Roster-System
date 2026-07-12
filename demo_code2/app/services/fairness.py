"""
Fairness calculation service for the Sing Yin Duty Roster System.
Handles workload balancing, variance analysis, and fairness metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import math

from models.prefect import Prefect
from models.enums import SchoolRules


@dataclass
class FairnessService:
    """Service for calculating and optimizing workload fairness.

    Uses the history_weight system and workload multiplier to track
    and balance cumulative duty load across all prefects.
    """
    prefects: List[Prefect] = field(default_factory=list)

    # =========================================================================
    # Load queries
    # =========================================================================

    def get_loads(self) -> Dict[str, float]:
        """Return {prefect_name: history_weight} for all active prefects."""
        return {p.name: p.history_weight for p in self.prefects if p.active}

    def get_load(self, prefect_name: str) -> float:
        """Get a single prefect's load."""
        for p in self.prefects:
            if p.name == prefect_name:
                return p.history_weight
        return 0.0

    # =========================================================================
    # Fairness metrics
    # =========================================================================

    def compute_variance(self) -> float:
        """Compute the variance of workload across all active prefects."""
        loads = list(self.get_loads().values())
        if len(loads) < 2:
            return 0.0
        mean = sum(loads) / len(loads)
        return sum((x - mean) ** 2 for x in loads) / len(loads)

    def compute_std_dev(self) -> float:
        """Compute the standard deviation of workload."""
        return math.sqrt(self.compute_variance())

    def compute_range(self) -> float:
        """Return the range (max - min) of workload values."""
        loads = list(self.get_loads().values())
        if not loads:
            return 0.0
        return max(loads) - min(loads)

    def compute_fairness_index(self) -> float:
        """Compute a fairness index (0 = perfectly unfair, 1 = perfectly fair).

        Formula: 1 - (std_dev / mean), clamped to [0, 1].
        Higher is better.
        """
        loads = list(self.get_loads().values())
        if not loads:
            return 1.0
        mean = sum(loads) / len(loads)
        if mean == 0:
            return 1.0
        std = self.compute_std_dev()
        return max(0.0, min(1.0, 1.0 - std / mean))

    def get_summary(self) -> dict:
        """Return a summary of fairness metrics."""
        loads = list(self.get_loads().values())
        n = len(loads)
        return {
            "count": n,
            "total_load": sum(loads),
            "mean_load": sum(loads) / max(n, 1),
            "min_load": min(loads) if loads else 0,
            "max_load": max(loads) if loads else 0,
            "range": self.compute_range(),
            "std_dev": self.compute_std_dev(),
            "variance": self.compute_variance(),
            "fairness_index": self.compute_fairness_index(),
        }

    # =========================================================================
    # Optimization helpers (skeleton -- full implementation in Phase 3)
    # =========================================================================

    def find_least_loaded(self, candidates: List[Prefect]) -> Prefect:
        """Find the prefect with the lowest history_weight from a candidate list."""
        if not candidates:
            raise ValueError("No candidates provided.")
        return min(candidates, key=lambda p: p.history_weight)

    def apply_load(self, prefect_name: str, points: float):
        """Add load points to a specific prefect."""
        for p in self.prefects:
            if p.name == prefect_name:
                p.add_load(points)
                return
        raise ValueError(f"Prefect not found: {prefect_name}")

    def rebase_loads(self, target_mean: float = 0.0):
        """Rebase all history_weights to a new target mean (for period resets)."""
        if not self.prefects:
            return
        current_mean = sum(p.history_weight for p in self.prefects) / len(self.prefects)
        offset = target_mean - current_mean
        for p in self.prefects:
            p.history_weight = max(0.0, p.history_weight + offset)
