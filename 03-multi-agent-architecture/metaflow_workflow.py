"""
metaflow_workflow.py

Module 03 — Multi-Agent Architecture (Metaflow workflow).

Wraps the WASP-18 b pipeline as a Metaflow FlowSpec with versioned steps.
Each step is independently retryable and auditable. The same flow code runs
locally, on AWS Batch, or on Outerbounds — target is a deploy-time decision.

Run locally:

    python metaflow_workflow.py run

View results after a run:

    python metaflow_workflow.py show

Requirements:
    metaflow>=2.18
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────────────────────
# Absolute paths — Metaflow steps can run in different working directories
# depending on the executor. Never use relative paths inside a FlowSpec.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02-your-first-agent"))
sys.path.insert(0, str(ROOT / "01-data-sources"))

from metaflow import FlowSpec, step, Parameter

from agent_tools import (
    SCHEMA,
    build_agent_context,
    load_lightcurve,
    run_feature_anomaly_pipeline,
    validate_lightcurve,
)

# Primary CSV location; fall back to polars_demo copy if needed
_PRIMARY   = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
_FALLBACK  = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"
DEFAULT_CSV = str(_PRIMARY if _PRIMARY.exists() else _FALLBACK)


class LightcurveAgentFlow(FlowSpec):
    """
    Metaflow workflow for the WASP-18 b lightcurve agent pipeline.

    Steps
    -----
    start              → resolve and validate the CSV path
    load_data          → load with schema enforcement
    validate_data      → run quality checks, store ValidationReport
    feature_engineering→ rolling window features + IsolationForest
    summarize          → build structured agent context
    end                → print completion card
    """

    csv_path = Parameter(
        "csv",
        help="Path to the WASP-18 b lightcurve CSV",
        default=DEFAULT_CSV,
    )

    @step
    def start(self):
        path = Path(self.csv_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Lightcurve CSV not found at {self.csv_path}\n"
                "Quick fix: cp 100-example-applications/polars_demo/"
                "wasp18b_lightcurve.csv 01-data-sources/"
            )
        self.filepath = str(path.resolve())
        print(f"CSV path resolved: {self.filepath}")
        self.next(self.load_data)

    @step
    def load_data(self):
        self.df = load_lightcurve(Path(self.filepath), SCHEMA)
        print(f"Loaded {len(self.df)} rows")
        self.next(self.validate_data)

    @step
    def validate_data(self):
        report = validate_lightcurve(self.df)
        self.validation_report = report.model_dump()
        print(f"Nulls       : {report.nulls}")
        print(f"Phase range : {report.phase_range}")
        print(f"Flux std    : {report.flux_std:.8f}")
        print(f"Duplicates  : {report.duplicate_phases}")
        self.next(self.feature_engineering)

    @step
    def feature_engineering(self):
        pipeline = run_feature_anomaly_pipeline(self.df)
        # Store only JSON-serialisable data — Metaflow artifacts must pickle cleanly
        self.transit_window  = pipeline["transit_window"]
        self.transit_depth   = pipeline["transit_depth"]
        self.anomaly_summary = pipeline["anomaly_summary"]
        print(f"Anomalies detected : {self.anomaly_summary['n_anomalous_points']}")
        print(f"Transit depth      : {self.transit_depth}")
        self.next(self.summarize)

    @step
    def summarize(self):
        self.agent_context = build_agent_context(self.filepath)
        print("\nAgent context built successfully.")
        self.next(self.end)

    @step
    def end(self):
        print("\n── Pipeline summary ──────────────────────────────────────────\n")
        print(f"  Dataset   : {Path(self.filepath).name}")
        print(f"  Rows      : {self.agent_context['data_quality']['rows']}")
        print(f"  Anomalies : {self.agent_context['anomaly_detection']['n_anomalous_points']}")
        depth = self.agent_context["anomaly_detection"]["transit_depth_pct"]
        print(f"  Depth     : {depth}%")
        start = self.agent_context["anomaly_detection"]["transit_start"]
        end_  = self.agent_context["anomaly_detection"]["transit_end"]
        print(f"  Window    : {start:.4f} → {end_:.4f} (phase)")

        print("""
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 03 COMPLETE                       ║
║                                                              ║
║  Multi-Agent Architecture                                    ║
║  Metaflow workflow: 5 steps, versioned, reproducible.        ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    LightcurveAgentFlow()
