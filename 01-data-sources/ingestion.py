"""
ingestion.py

Extracted pipeline functions for Module 01: Data Foundations for Intelligent Apps.
Import these into the notebook and into tests — single source of truth.

Why this exists as a module (not just notebook cells):
  - Tests can import it directly
  - Agents can register these functions as tools
  - The notebook stays clean; logic lives here
"""

from pathlib import Path
from typing import Tuple

import polars as pl
from pydantic import BaseModel, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Schema — declared once, used everywhere
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA = {
    "PHASE":      pl.Float64,
    "LC_DETREND": pl.Float64,
    "MODEL_INIT": pl.Float64,
}


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
#
# Two models, two jobs:
#
#   LightcurveSchema  — validates individual rows (useful for API payloads,
#                       spot-checking samples, or agent tool inputs)
#
#   ValidationReport  — validates the *summary* the pipeline produces.
#                       This is what gets passed to an LLM as context.
#                       Pydantic here means the agent always gets well-formed,
#                       type-safe data — not a dict that might be missing a key.
# ─────────────────────────────────────────────────────────────────────────────

class LightcurveSchema(BaseModel):
    """
    Schema for a single light curve observation.
    Use for row-level validation of API payloads or sampled data.
    Not intended to validate entire DataFrames row-by-row (use Polars for that).
    """
    PHASE:      float
    LC_DETREND: float
    MODEL_INIT: float


class ValidationReport(BaseModel):
    """
    Structured output of validate_lightcurve().

    This model does two things:
      1. Enforces that the report has all required fields before anything
         downstream (including an LLM) consumes it.
      2. Catches nonsensical values (negative std, inverted range) at the
         boundary between pipeline and consumer.

    Serialize for an agent with: report.model_dump_json()
    """
    nulls:             dict[str, int]
    phase_range:       Tuple[float, float]
    flux_range:        Tuple[float, float]
    flux_std:          float
    duplicate_phases:  int

    @field_validator("flux_std")
    @classmethod
    def flux_std_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"flux_std must be >= 0, got {v}")
        return v

    @model_validator(mode="after")
    def phase_range_ordered(self) -> "ValidationReport":
        lo, hi = self.phase_range
        if lo >= hi:
            raise ValueError(
                f"phase_range must be (min, max) with min < max, got ({lo}, {hi})"
            )
        return self

    @model_validator(mode="after")
    def duplicate_phases_non_negative(self) -> "ValidationReport":
        if self.duplicate_phases < 0:
            raise ValueError("duplicate_phases cannot be negative")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline functions
# ─────────────────────────────────────────────────────────────────────────────

def load_lightcurve(filepath: Path, schema: dict) -> pl.DataFrame:
    """
    Load a light curve CSV with strict schema enforcement.

    Raises FileNotFoundError if the file is missing.
    Raises ValueError if any expected columns are absent.

    This function is designed to be registered as an agent tool in Module 02.
    Its error messages are written to be readable by both humans and LLMs.
    """
    if not filepath.exists():
        raise FileNotFoundError(
            f"{filepath} not found. Run fetch_data.py or download "
            f"wasp18b_lightcurve.csv from https://github.com/dbouquin/polars_demo"
        )

    df = pl.read_csv(filepath, schema_overrides=schema)

    missing = set(schema.keys()) - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing expected columns: {missing}. "
            f"Got columns: {list(df.columns)}"
        )

    return df


def validate_lightcurve(df: pl.DataFrame) -> ValidationReport:
    """
    Run data quality checks on a light curve DataFrame.

    Returns a ValidationReport (Pydantic model) — not a plain dict.
    This means the output is type-safe, JSON-serializable, and validated
    before anything downstream consumes it.

    Usage:
        report = validate_lightcurve(df)
        print(report.model_dump_json(indent=2))   # for an LLM
        print(report.nulls)                        # direct field access
    """
    null_counts = df.null_count()

    return ValidationReport(
        nulls={col: null_counts[col][0] for col in df.columns},
        phase_range=(df["PHASE"].min(), df["PHASE"].max()),
        flux_range=(df["LC_DETREND"].min(), df["LC_DETREND"].max()),
        flux_std=float(df["LC_DETREND"].std()),
        duplicate_phases=len(df) - df["PHASE"].n_unique(),
    )
