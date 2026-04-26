"""
tests/test_assertions.py

Tests for evals/assertions.py — the same functions the evaluate step runs.

Run with:
    pytest tests/test_assertions.py -v

The point: assertions are plain Python functions, not Metaflow-specific code.
That means they're testable here and runnable in the flow. One source of truth.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock
from evals.assertions import (
    assert_no_nulls,
    assert_flux_std_reasonable,
    assert_phase_range_sensible,
    assert_no_duplicate_phases,
    assert_classification_valid,
    assert_confidence_in_range,
    assert_reasoning_present,
    assert_transit_depth_physical,
    run_all_assertions,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def good_report():
    r = MagicMock()
    r.nulls            = {"PHASE": 0, "LC_DETREND": 0, "MODEL_INIT": 0}
    r.flux_std         = 0.00031
    r.phase_range      = (-0.5, 0.5)
    r.duplicate_phases = 0
    r.model_dump       = lambda: {}
    return r

@pytest.fixture
def good_result():
    return {
        "classification":       "confirmed_transit",
        "confidence":           0.91,
        "transit_depth_pct":    1.014,
        "reasoning_summary":    "Clear periodic flux decrease consistent with hot Jupiter transit.",
        "recommended_next_steps": ["Fit model"],
    }


# ── Validation report assertions ──────────────────────────────────────────────

class TestValidationAssertions:

    def test_no_nulls_passes_on_clean_data(self, good_report):
        assert assert_no_nulls(good_report)["passed"] is True

    def test_no_nulls_fails_with_nulls(self, good_report):
        good_report.nulls = {"PHASE": 0, "LC_DETREND": 3, "MODEL_INIT": 0}
        assert assert_no_nulls(good_report)["passed"] is False

    def test_flux_std_reasonable_passes(self, good_report):
        assert assert_flux_std_reasonable(good_report)["passed"] is True

    def test_flux_std_too_low_fails(self, good_report):
        good_report.flux_std = 1e-8   # suspiciously flat
        assert assert_flux_std_reasonable(good_report)["passed"] is False

    def test_flux_std_too_high_fails(self, good_report):
        good_report.flux_std = 0.1    # far too noisy
        assert assert_flux_std_reasonable(good_report)["passed"] is False

    def test_phase_range_ordered_passes(self, good_report):
        assert assert_phase_range_sensible(good_report)["passed"] is True

    def test_phase_range_inverted_fails(self, good_report):
        good_report.phase_range = (0.5, -0.5)
        assert assert_phase_range_sensible(good_report)["passed"] is False

    def test_phase_range_too_narrow_fails(self, good_report):
        good_report.phase_range = (-0.1, 0.1)   # span=0.2, less than 0.5
        assert assert_phase_range_sensible(good_report)["passed"] is False

    def test_no_duplicate_phases_passes(self, good_report):
        assert assert_no_duplicate_phases(good_report)["passed"] is True

    def test_duplicate_phases_is_warning_not_critical(self, good_report):
        good_report.duplicate_phases = 5
        result = assert_no_duplicate_phases(good_report)
        assert result["passed"] is False
        assert result["critical"] is False   # warning, not hard failure


# ── Agent classification assertions ───────────────────────────────────────────

class TestClassificationAssertions:

    def test_valid_classifications_pass(self, good_result):
        for cls in ("confirmed_transit", "candidate_transit", "no_transit", "insufficient_data"):
            good_result["classification"] = cls
            assert assert_classification_valid(good_result)["passed"] is True

    def test_invalid_classification_fails(self, good_result):
        good_result["classification"] = "maybe_transit"
        assert assert_classification_valid(good_result)["passed"] is False

    def test_confidence_in_range_passes(self, good_result):
        assert assert_confidence_in_range(good_result)["passed"] is True

    def test_confidence_above_one_fails(self, good_result):
        good_result["confidence"] = 1.7
        assert assert_confidence_in_range(good_result)["passed"] is False

    def test_confidence_negative_fails(self, good_result):
        good_result["confidence"] = -0.1
        assert assert_confidence_in_range(good_result)["passed"] is False

    def test_reasoning_present_passes(self, good_result):
        assert assert_reasoning_present(good_result)["passed"] is True

    def test_short_reasoning_is_warning(self, good_result):
        good_result["reasoning_summary"] = "OK"
        result = assert_reasoning_present(good_result)
        assert result["passed"] is False
        assert result["critical"] is False

    def test_transit_depth_physical_skipped_for_no_transit(self, good_result):
        good_result["classification"]  = "no_transit"
        good_result["transit_depth_pct"] = 0.0
        result = assert_transit_depth_physical(good_result)
        assert result["passed"] is True   # skipped — not applicable

    def test_transit_depth_implausibly_shallow_is_warning(self, good_result):
        good_result["transit_depth_pct"] = 0.0001
        result = assert_transit_depth_physical(good_result)
        assert result["passed"] is False
        assert result["critical"] is False   # warning not hard failure

    def test_transit_depth_too_deep_is_warning(self, good_result):
        good_result["transit_depth_pct"] = 7.0   # binary star range
        result = assert_transit_depth_physical(good_result)
        assert result["passed"] is False
        assert result["critical"] is False


# ── run_all_assertions ────────────────────────────────────────────────────────

class TestRunAllAssertions:

    def test_all_pass_on_good_data(self, good_report, good_result):
        result = run_all_assertions(good_report, good_result)
        assert result["passed"] is True
        assert result["n_failed"] == 0

    def test_critical_failure_fails_run(self, good_report, good_result):
        good_report.nulls = {"PHASE": 0, "LC_DETREND": 10, "MODEL_INIT": 0}
        result = run_all_assertions(good_report, good_result)
        assert result["passed"] is False
        assert "no_nulls" in result["critical_failures"]

    def test_warning_does_not_fail_run(self, good_report, good_result):
        good_result["reasoning_summary"] = "OK"   # too short → warning
        good_result["transit_depth_pct"] = 0.0001  # shallow → warning
        result = run_all_assertions(good_report, good_result)
        assert result["passed"] is True          # warnings don't fail
        assert result["n_warnings"] == 2

    def test_results_list_has_entry_per_assertion(self, good_report, good_result):
        result = run_all_assertions(good_report, good_result)
        assert len(result["results"]) == 8
