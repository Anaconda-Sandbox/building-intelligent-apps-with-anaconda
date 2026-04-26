from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_TOOLS_PATH = ROOT / "02-your-first-agent"
if str(AGENT_TOOLS_PATH) not in sys.path:
    sys.path.append(str(AGENT_TOOLS_PATH))

from metaflow import FlowSpec, step

from agent_tools import (
    SCHEMA,
    build_agent_context,
    load_lightcurve,
    run_feature_anomaly_pipeline,
    validate_lightcurve,
)


class LightcurveAgentFlow(FlowSpec):
    """MetaFlow workflow for the WASP-18 lightcurve agent pipeline."""

    @step
    def start(self):
        self.filepath = Path("../01-data-sources/wasp18b_lightcurve.csv")
        self.next(self.load_data)

    @step
    def load_data(self):
        self.df = load_lightcurve(self.filepath, SCHEMA)
        self.next(self.validate_data)

    @step
    def validate_data(self):
        self.validation_report = validate_lightcurve(self.df)
        self.next(self.feature_engineering)

    @step
    def feature_engineering(self):
        self.pipeline_result = run_feature_anomaly_pipeline(self.df)
        self.next(self.summarize)

    @step
    def summarize(self):
        self.agent_context = build_agent_context(str(self.filepath))
        print("Agent context built successfully.")
        print(self.agent_context)
        self.next(self.end)

    @step
    def end(self):
        print("MetaFlow workflow complete.")


if __name__ == "__main__":
    LightcurveAgentFlow()
