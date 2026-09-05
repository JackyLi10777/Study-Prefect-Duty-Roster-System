from copy import deepcopy

import pytest

from scripts.verify_roster_png_performance import compare_reports, summarize


def report(times=(1, 2, 3, 4, 5), peaks=(100, 100, 100, 100, 100)):
    samples = [{"elapsed_ms": time, "peak_rss_bytes": peak} for time, peak in zip(times, peaks)]
    return {
        "schema_version": 1,
        "environment": {"machine": "fictional-host", "assets": "fixture"},
        "languages": {language: summarize(samples) for language in ("zh", "en")},
    }


def test_summary_uses_nearest_rank_p75_and_native_peak():
    result = report()["languages"]["zh"]
    assert result["p75_elapsed_ms"] == 4
    assert result["peak_rss_bytes"] == 100
    assert result["sample_count"] == 5


def test_ten_percent_limit_is_inclusive_but_never_relaxed():
    baseline = report()
    assert compare_reports(baseline, report((1, 2, 3, 4.4, 5), (110,) * 5)) == []
    failures = compare_reports(baseline, report((1, 2, 3, 4.41, 5), (111,) * 5))
    assert any("elapsed" in failure for failure in failures)
    assert any("memory" in failure for failure in failures)


def test_comparison_rejects_other_machine_and_incomplete_samples():
    baseline = report()
    other = deepcopy(baseline)
    other["environment"]["machine"] = "other-host"
    assert any("environment" in failure for failure in compare_reports(baseline, other))
    other = deepcopy(baseline)
    other["languages"]["zh"]["samples"].pop()
    assert compare_reports(baseline, other)


@pytest.mark.parametrize("invalid", [0, -1, float("nan"), float("inf")])
def test_summary_rejects_unmeasured_or_non_finite_values(invalid):
    with pytest.raises(ValueError):
        summarize([{"elapsed_ms": invalid, "peak_rss_bytes": 100}] * 5)


def test_comparison_recalculates_aggregates_instead_of_trusting_report():
    baseline = report()
    candidate = report((1, 2, 3, 10, 11))
    candidate["languages"]["zh"]["p75_elapsed_ms"] = 1
    assert compare_reports(baseline, candidate)
