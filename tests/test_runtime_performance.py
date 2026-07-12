from __future__ import annotations

from scripts.verify_runtime_performance import (
    HEAP_GROWTH_BUDGET_BYTES,
    LARGEST_RESOURCE_BUDGET_BYTES,
    LISTENER_GROWTH_BUDGET,
    NODE_GROWTH_BUDGET,
    MOBILE_OVERFLOW_BUDGET_PX,
    RESOURCE_BUDGET_BYTES,
    RESOURCE_COUNT_BUDGET,
    evaluate_budget,
)


def _metrics() -> dict[str, int]:
    return {
        "initial_transfer_bytes": RESOURCE_BUDGET_BYTES,
        "largest_resource_bytes": LARGEST_RESOURCE_BUDGET_BYTES,
        "initial_resource_count": RESOURCE_COUNT_BUDGET,
        "heap_growth_bytes": HEAP_GROWTH_BUDGET_BYTES,
        "node_growth": NODE_GROWTH_BUDGET,
        "listener_growth": LISTENER_GROWTH_BUDGET,
        "mobile_overflow_pixels": MOBILE_OVERFLOW_BUDGET_PX,
    }


def test_runtime_performance_budget_accepts_values_at_the_limits() -> None:
    assert evaluate_budget(_metrics()) == []


def test_runtime_performance_budget_returns_payload_free_failure_codes() -> None:
    metrics = _metrics()
    metrics["heap_growth_bytes"] += 1
    metrics["listener_growth"] += 1

    assert evaluate_budget(metrics) == ["heap_growth_bytes_over_budget", "listener_growth_over_budget"]
