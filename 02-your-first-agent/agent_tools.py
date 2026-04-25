from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest

# Allow module 2 to import the source-of-truth pipeline from module 1.
ROOT = Path(__file__).resolve().parents[1]
SYS_PATH = ROOT / "01-data-sources"
if str(SYS_PATH) not in sys.path:
    sys.path.append(str(SYS_PATH))

from ingestion import SCHEMA, load_lightcurve, validate_lightcurve

FEATURE_COLS = ["residual", "flux_rolling_std", "flux_zscore", "abs_residual"]


def run_feature_anomaly_pipeline(df: pl.DataFrame, window: int = 15, contamination: float = 0.05) -> dict[str, Any]:
    """Run the feature + anomaly detection pipeline from Module 1 on a loaded DataFrame."""
    features = (
        df.sort("PHASE")
        .with_columns([
            (pl.col("LC_DETREND") - pl.col("MODEL_INIT")).alias("residual"),
            pl.col("LC_DETREND")
            .rolling_mean(window_size=window, center=True)
            .alias("flux_rolling_mean"),
            pl.col("LC_DETREND")
            .rolling_std(window_size=window, center=True)
            .alias("flux_rolling_std"),
        ])
        .with_columns([
            ((pl.col("LC_DETREND") - pl.col("flux_rolling_mean")) /
             (pl.col("flux_rolling_std") + 1e-10))
            .alias("flux_zscore"),
            pl.col("residual").abs().alias("abs_residual"),
        ])
        .drop_nulls()
    )

    X = features.select(FEATURE_COLS).to_numpy()
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X)

    anomaly_scores = -model.decision_function(X)
    labels = model.predict(X)

    results = features.with_columns([
        pl.Series("anomaly_score", anomaly_scores),
        pl.Series("is_anomaly", labels == -1),
    ])

    anomalous = results.filter(pl.col("is_anomaly"))
    normal = results.filter(~pl.col("is_anomaly"))

    transit_window = {
        "transit_start": float(anomalous["PHASE"].min()) if len(anomalous) else None,
        "transit_end": float(anomalous["PHASE"].max()) if len(anomalous) else None,
        "min_flux": float(anomalous["LC_DETREND"].min()) if len(anomalous) else None,
        "mean_anomaly_score": float(anomalous["anomaly_score"].mean()) if len(anomalous) else None,
        "n_anomalous_points": int(len(anomalous)),
    }

    baseline_flux = float(normal["LC_DETREND"].mean()) if len(normal) else None
    min_flux = float(anomalous["LC_DETREND"].min()) if len(anomalous) else None
    transit_depth = (
        (baseline_flux - min_flux) / baseline_flux if baseline_flux and min_flux is not None else None
    )

    return {
        "results": results,
        "transit_window": transit_window,
        "transit_depth": transit_depth,
        "anomaly_summary": {
            "n_anomalous_points": int(len(anomalous)),
            "contamination": contamination,
        },
    }


def build_agent_context(
    filepath: str,
    window: int = 15,
    contamination: float = 0.05,
) -> dict[str, Any]:
    """Create the structured context dict that the agent receives."""
    df = load_lightcurve(Path(filepath), SCHEMA)
    report = validate_lightcurve(df)
    pipeline = run_feature_anomaly_pipeline(df, window=window, contamination=contamination)
    transit_window = pipeline["transit_window"]
    n_anomalies = pipeline["anomaly_summary"]["n_anomalous_points"]

    context = {
        "dataset": Path(filepath).name,
        "data_quality": {
            "rows": len(df),
            "nulls": report.nulls,
            "phase_range_days": report.phase_range,
            "flux_std": round(report.flux_std, 8),
        },
        "feature_engineering": {
            "method": "Polars rolling window expressions",
            "window_size": window,
            "features": FEATURE_COLS,
        },
        "anomaly_detection": {
            "model": "IsolationForest",
            "contamination": contamination,
            "n_anomalous_points": n_anomalies,
            "transit_depth_pct": round(float(transit_depth * 100), 6) if (transit_depth := pipeline["transit_depth"]) is not None else None,
            "transit_start": transit_window["transit_start"],
            "transit_end": transit_window["transit_end"],
        },
        "validation_report": report.model_dump(),
    }

    return context


def agent_context_json(filepath: str, window: int = 15, contamination: float = 0.05) -> str:
    """Return the agent context as a JSON string."""
    return json.dumps(build_agent_context(filepath, window, contamination), indent=2)
