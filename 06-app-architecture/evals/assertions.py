"""
evals/assertions.py

Assertion suite for Module 06 — App Architecture.

Plain Python functions — no Metaflow dependency, fully testable with pytest:
    pytest evals/ -v

The evaluate step in flows/harnessed_lightcurve_flow.py calls
run_all_assertions() and raises AssertionError on critical failures.

Each assertion returns:
    {
        "name":     str,    # identifier
        "passed":   bool,
        "critical": bool,   # True → failure raises AssertionError in evaluate step
        "detail":   str,    # human-readable result shown in the card
    }
"""
from __future__ import annotations
from typing import Any


# ── Validation report assertions ──────────────────────────────────────────────

def assert_no_nulls(report: Any) -> dict:
    """Pipeline should produce zero null values after ingestion."""
    total = sum(report.nulls.values()) if hasattr(report, "nulls") else 0
    return {
        "name":     "no_nulls",
        "passed":   total == 0,
        "critical": True,
        "detail":   f"Total nulls: {total}",
    }


def assert_flux_std_reasonable(
    report: Any,
    min_std: float = 1e-6,
    max_std: float = 0.01,
) -> dict:
    """
    Flux standard deviation must be in a physically reasonable range.
    Too low (< 1e-6) → suspiciously flat signal.
    Too high (> 0.01) → noise floor problem.
    """
    std = getattr(report, "flux_std", None)
    if std is None:
        return {"name": "flux_std_reasonable", "passed": False, "critical": True,
                "detail": "flux_std not present in report"}
    in_range = min_std < std < max_std
    return {
        "name":     "flux_std_reasonable",
        "passed":   in_range,
        "critical": True,
        "detail":   f"flux_std={std:.8f} (expected {min_std}–{max_std})",
    }


def assert_phase_range_sensible(report: Any) -> dict:
    """Phase range should be ordered and span at least 0.5 days."""
    pr = getattr(report, "phase_range", None)
    if pr is None:
        return {"name": "phase_range_sensible", "passed": False, "critical": True,
                "detail": "phase_range not present"}
    lo, hi = pr
    span = hi - lo
    return {
        "name":     "phase_range_sensible",
        "passed":   lo < hi and span >= 0.5,
        "critical": True,
        "detail":   f"phase_range=({lo:.3f}, {hi:.3f}), span={span:.3f}",
    }


def assert_no_duplicate_phases(report: Any) -> dict:
    """Well-phased light curves should have no duplicate phase values."""
    dupes = getattr(report, "duplicate_phases", 0)
    return {
        "name":     "no_duplicate_phases",
        "passed":   dupes == 0,
        "critical": False,   # warning, not hard failure
        "detail":   f"duplicate_phases={dupes}",
    }


# ── Agent result assertions ───────────────────────────────────────────────────

def assert_classification_valid(result: dict) -> dict:
    """Agent must return one of the four known classification labels."""
    valid = {"confirmed_transit", "candidate_transit", "no_transit", "insufficient_data"}
    cls = result.get("classification", "")
    return {
        "name":     "classification_valid",
        "passed":   cls in valid,
        "critical": True,
        "detail":   f"classification='{cls}'",
    }


def assert_confidence_in_range(result: dict) -> dict:
    """Confidence must be a float in [0.0, 1.0]."""
    conf = result.get("confidence", -1)
    in_range = isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0
    return {
        "name":     "confidence_in_range",
        "passed":   in_range,
        "critical": True,
        "detail":   f"confidence={conf}",
    }


def assert_reasoning_present(result: dict) -> dict:
    """Agent should always provide a non-trivial reasoning summary."""
    summary = result.get("reasoning_summary", "")
    has_summary = isinstance(summary, str) and len(summary.strip()) > 10
    return {
        "name":     "reasoning_present",
        "passed":   has_summary,
        "critical": False,   # warning — agent should explain itself
        "detail":   f"reasoning_summary length={len(summary)}",
    }


def assert_transit_depth_physical(result: dict) -> dict:
    """
    Transit depth must be in a physically plausible range for a hot Jupiter.
    Only checked for confirmed or candidate transit classifications.
    """
    depth = result.get("transit_depth_pct", 0.0)
    cls   = result.get("classification", "")

    if cls in ("no_transit", "insufficient_data"):
        return {
            "name":     "transit_depth_physical",
            "passed":   True,
            "critical": False,
            "detail":   f"Skipped — classification='{cls}'",
        }

    plausible = 0.01 <= depth <= 5.0
    return {
        "name":     "transit_depth_physical",
        "passed":   plausible,
        "critical": False,   # flag for human review
        "detail":   f"transit_depth_pct={depth:.4f}% (expected 0.01–5.0%)",
    }


# ── Suite runner ──────────────────────────────────────────────────────────────

def run_all_assertions(report: Any, result: dict) -> dict:
    """
    Run the full assertion suite against a ValidationReport and agent result.

    Returns:
        {
            "passed":            bool,
            "results":           list[dict],
            "n_passed":          int,
            "n_failed":          int,
            "n_warnings":        int,
            "critical_failures": list[str],
        }
    """
    checks = [
        assert_no_nulls(report),
        assert_flux_std_reasonable(report),
        assert_phase_range_sensible(report),
        assert_no_duplicate_phases(report),
        assert_classification_valid(result),
        assert_confidence_in_range(result),
        assert_reasoning_present(result),
        assert_transit_depth_physical(result),
    ]

    critical_failures = [c["name"] for c in checks if c["critical"] and not c["passed"]]
    warnings          = [c["name"] for c in checks if not c["critical"] and not c["passed"]]

    return {
        "passed":            len(critical_failures) == 0,
        "results":           checks,
        "n_passed":          sum(1 for c in checks if c["passed"]),
        "n_failed":          len(critical_failures),
        "n_warnings":        len(warnings),
        "critical_failures": critical_failures,
    }
