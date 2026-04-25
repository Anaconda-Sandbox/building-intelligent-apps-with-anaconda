"""
tests/test_ingestion.py

Pytest suite for the Module 01 data ingestion pipeline.
Run from the module root:

    conda activate ai-foundations
    conda install -c conda-forge pytest pydantic -y
    pytest tests/test_ingestion.py -v

These tests are designed to be readable — they double as documentation
of the contracts the pipeline guarantees.
"""

import io
import pytest
import polars as pl
from pathlib import Path
from pydantic import ValidationError

# ── Import the things we're testing ──────────────────────────────────────────
# Adjust this import path once the pipeline code lives in a proper module.
# For now, tests assume ingestion.py is in the same directory.
from ingestion import (
    SCHEMA,
    LightcurveSchema,
    ValidationReport,
    load_lightcurve,
    validate_lightcurve,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — minimal synthetic data, no file I/O needed for most tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_csv(tmp_path) -> Path:
    """Write a small valid light curve CSV and return its path."""
    content = "PHASE,LC_DETREND,MODEL_INIT\n"
    for i in range(50):
        phase = -0.5 + i * 0.02
        flux  = 1.0 - (0.01 if -0.05 < phase < 0.05 else 0.0)
        content += f"{phase:.5f},{flux:.6f},{flux + 0.0001:.6f}\n"
    p = tmp_path / "test_lightcurve.csv"
    p.write_text(content)
    return p


@pytest.fixture
def valid_df(valid_csv) -> pl.DataFrame:
    """Pre-loaded DataFrame from the valid CSV fixture."""
    return load_lightcurve(valid_csv, SCHEMA)


@pytest.fixture
def missing_col_csv(tmp_path) -> Path:
    """CSV missing the MODEL_INIT column."""
    content = "PHASE,LC_DETREND\n"
    for i in range(10):
        content += f"{i * 0.1:.3f},0.99999\n"
    p = tmp_path / "missing_col.csv"
    p.write_text(content)
    return p


@pytest.fixture
def csv_with_nulls(tmp_path) -> Path:
    """CSV with some null flux values."""
    content = "PHASE,LC_DETREND,MODEL_INIT\n"
    content += "-0.1,0.99999,0.99999\n"
    content += "0.0,,1.00000\n"    # null LC_DETREND
    content += "0.1,0.99999,\n"   # null MODEL_INIT
    p = tmp_path / "nulls.csv"
    p.write_text(content)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# load_lightcurve tests
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadLightcurve:

    def test_loads_valid_csv(self, valid_csv):
        df = load_lightcurve(valid_csv, SCHEMA)
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 50

    def test_schema_columns_present(self, valid_csv):
        df = load_lightcurve(valid_csv, SCHEMA)
        assert set(SCHEMA.keys()).issubset(set(df.columns))

    def test_column_dtypes_enforced(self, valid_csv):
        df = load_lightcurve(valid_csv, SCHEMA)
        for col, expected_dtype in SCHEMA.items():
            assert df[col].dtype == expected_dtype, (
                f"Column '{col}' expected {expected_dtype}, got {df[col].dtype}"
            )

    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_lightcurve(tmp_path / "does_not_exist.csv", SCHEMA)

    def test_raises_on_missing_column(self, missing_col_csv):
        with pytest.raises(ValueError, match="Missing expected columns"):
            load_lightcurve(missing_col_csv, SCHEMA)

    def test_phase_is_sorted_ascending(self, valid_df):
        """Phase values should be monotonically non-decreasing after load."""
        phases = valid_df["PHASE"].to_list()
        assert phases == sorted(phases)

    def test_returns_nonempty_dataframe(self, valid_csv):
        df = load_lightcurve(valid_csv, SCHEMA)
        assert len(df) > 0, "Loaded DataFrame must not be empty"


# ─────────────────────────────────────────────────────────────────────────────
# validate_lightcurve tests
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateLightcurve:

    def test_returns_validation_report_model(self, valid_df):
        """validate_lightcurve should return a valid ValidationReport."""
        report = validate_lightcurve(valid_df)
        assert isinstance(report, ValidationReport)

    def test_zero_nulls_on_clean_data(self, valid_df):
        report = validate_lightcurve(valid_df)
        assert all(v == 0 for v in report.nulls.values()), (
            f"Expected zero nulls on clean data, got: {report.nulls}"
        )

    def test_detects_nulls(self, csv_with_nulls):
        df = pl.read_csv(csv_with_nulls, schema_overrides=SCHEMA)
        report = validate_lightcurve(df)
        assert report.nulls["LC_DETREND"] >= 1
        assert report.nulls["MODEL_INIT"] >= 1

    def test_phase_range_is_ordered(self, valid_df):
        report = validate_lightcurve(valid_df)
        assert report.phase_range[0] < report.phase_range[1], (
            "phase_range min should be less than max"
        )

    def test_flux_std_is_positive(self, valid_df):
        report = validate_lightcurve(valid_df)
        assert report.flux_std > 0, "Flux std should be > 0 for non-flat data"

    def test_duplicate_phases_zero_for_clean_data(self, valid_df):
        report = validate_lightcurve(valid_df)
        assert report.duplicate_phases == 0

    def test_report_serializes_to_json(self, valid_df):
        """ValidationReport must be JSON-serializable — it's going to an LLM."""
        report = validate_lightcurve(valid_df)
        serialized = report.model_dump_json()
        assert isinstance(serialized, str)
        assert "phase_range" in serialized


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic model tests — validate the schema models themselves
# ─────────────────────────────────────────────────────────────────────────────

class TestPydanticModels:

    def test_lightcurve_schema_accepts_valid_row(self):
        row = LightcurveSchema(PHASE=0.0, LC_DETREND=0.9999, MODEL_INIT=1.0000)
        assert row.PHASE == 0.0

    def test_lightcurve_schema_rejects_non_float(self):
        with pytest.raises(ValidationError):
            LightcurveSchema(PHASE="not-a-float", LC_DETREND=0.999, MODEL_INIT=1.0)

    def test_validation_report_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            ValidationReport(
                nulls={"PHASE": 0},
                # missing phase_range, flux_range, flux_std, duplicate_phases
            )

    def test_validation_report_phase_range_ordering(self):
        """Phase range must be (min, max) — validator should catch reversal."""
        with pytest.raises(ValidationError, match="phase_range"):
            ValidationReport(
                nulls={"PHASE": 0, "LC_DETREND": 0, "MODEL_INIT": 0},
                phase_range=(0.5, -0.5),   # reversed — invalid
                flux_range=(-0.01, 0.01),
                flux_std=0.0003,
                duplicate_phases=0,
            )

    def test_validation_report_flux_std_non_negative(self):
        with pytest.raises(ValidationError, match="flux_std"):
            ValidationReport(
                nulls={"PHASE": 0, "LC_DETREND": 0, "MODEL_INIT": 0},
                phase_range=(-0.5, 0.5),
                flux_range=(-0.01, 0.01),
                flux_std=-1.0,             # invalid — std can't be negative
                duplicate_phases=0,
            )
