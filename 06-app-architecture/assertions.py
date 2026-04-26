"""
evals/assertions.py

Assertion functions for the pipeline eval step.

These are plain Python functions — no Metaflow dependency.
That means they're importable in tests, in notebooks, and in the flow.
Treating evals as functions rather than ad hoc checks is what makes
them CI-able: run them in the flow, run them in pytest, same code.

Design rule: every assertion returns a dict with at minimum:
    {"passed": bool, "name": str, "detail": str}

The evaluate step in the flow calls all of them and:
  - stores the results as an artifact (always)
  - raises AssertionError if any critical assertion fails (fail loudly)
  - records warnings for non-critical assertions (fail softly)
"""

from __future__ import annotations
from typing import Any


# ── Validation report assertions ──────────────────────────────────────────────

def assert_no_nulls(report: Any) -> dict:
    """Pipeline should produce zero null values after ingestion."""
    total_nulls = sum(report.nulls.values())
    return {
        "name":   "no_nulls",
        "passed": total_nulls == 0,
        "detail": f"Total nulls: {total_nulls}",
        "critical": True,
    }


def assert_flux_std_reasonable(report: Any, min_std: float = 1e-6, max_std: float = 0.01) -> dict:
    """
    Flux standard deviation should be in a physically reasonable range.
    Too low → suspiciously flat signal (data issue).
    Too high → noise floor problem or wrong dataset.
    """
    in_range = min_std < report.flux_std < max_std
    return {
        "name":   "flux_std_reasonable",
        "passed": in_range,
        "detail": f"flux_std={report.flux_std:.8f} (expected {min_std}–{max_std})",
        "critical": True,
    }


def assert_phase_range_sensible(report: Any) -> dict:
    """Phase range should be ordered and span at least 0.5 days."""
    lo, hi = report.phase_range
    span = hi - lo
    return {
        "name":   "phase_range_sensible",
        "passed": lo < hi and span >= 0.5,
        "detail": f"phase_range=({lo:.3f}, {hi:.3f}), span={span:.3f}",
        "critical": True,
    }


def assert_no_duplicate_phases(report: Any) -> dict:
    """Well-phased light curves should have no duplicate phase values."""
    return {
        "name":   "no_duplicate_phases",
        "passed": report.duplicate_phases == 0,
        "detail": f"duplicate_phases={report.duplicate_phases}",
        "critical": False,   # warning, not a hard failure
    }


# ── Agent classification assertions ───────────────────────────────────────────

def assert_classification_valid(result: dict) -> dict:
    """Agent must return one of the four valid classification labels."""
    valid = {"confirmed_transit", "candidate_transit", "no_transit", "insufficient_data"}
    cls = result.get("classification", "")
    return {
        "name":   "classification_valid",
        "passed": cls in valid,
        "detail": f"classification='{cls}'",
        "critical": True,
    }


def assert_confidence_in_range(result: dict) -> dict:
    """Confidence must be a float between 0 and 1."""
    conf = result.get("confidence", -1)
    in_range = isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0
    return {
        "name":   "confidence_in_range",
        "passed": in_range,
        "detail": f"confidence={conf}",
        "critical": True,
    }


def assert_reasoning_present(result: dict) -> dict:
    """Agent should always provide a reasoning summary."""
    summary = result.get("reasoning_summary", "")
    has_summary = isinstance(summary, str) and len(summary.strip()) > 10
    return {
        "name":   "reasoning_present",
        "passed": has_summary,
        "detail": f"reasoning_summary length={len(summary)}",
        "critical": False,   # warning — agent should explain itself but we won't halt for this
    }


def assert_transit_depth_physical(result: dict) -> dict:
    """
    Transit depth should be in a physically plausible range for a hot Jupiter.
    < 0.01% → probably noise, not a real transit.
    > 5%    → too deep for a planet (would be a binary star).
    """
    depth = result.get("transit_depth_pct", 0.0)
    cls   = result.get("classification", "")

    # Only assert depth range when a transit was actually claimed
    if cls in ("no_transit", "insufficient_data"):
        return {
            "name":   "transit_depth_physical",
            "passed": True,
            "detail": f"Skipped — classification='{cls}'",
            "critical": False,
        }

    plausible = 0.01 <= depth <= 5.0
    return {
        "name":   "transit_depth_physical",
        "passed": plausible,
        "detail": f"transit_depth_pct={depth:.4f}% (expected 0.01–5.0%)",
        "critical": False,   # warning — flag for human review, don't halt
    }


# ── Run all assertions ─────────────────────────────────────────────────────────

def run_all_assertions(report: Any, result: dict) -> dict:
    """
    Run the full assertion suite against a ValidationReport and agent result.

    Returns:
        {
            "passed": bool,          # True only if all critical assertions passed
            "results": list[dict],   # one dict per assertion
            "n_passed": int,
            "n_failed": int,
            "n_warnings": int,
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

    critical_failures = [
        c["name"] for c in checks
        if c["critical"] and not c["passed"]
    ]

    n_passed   = sum(1 for c in checks if c["passed"])
    n_failed   = sum(1 for c in checks if not c["passed"] and c["critical"])
    n_warnings = sum(1 for c in checks if not c["passed"] and not c["critical"])

    return {
        "passed":            len(critical_failures) == 0,
        "results":           checks,
        "n_passed":          n_passed,
        "n_failed":          n_failed,
        "n_warnings":        n_warnings,
        "critical_failures": critical_failures,
    }
