from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT_TOOLS_PATH = ROOT / "02-your-first-agent"
if str(AGENT_TOOLS_PATH) not in sys.path:
    sys.path.append(str(AGENT_TOOLS_PATH))

from agent_tools import (
    SCHEMA,
    build_agent_context,
    load_lightcurve,
    run_feature_anomaly_pipeline,
    validate_lightcurve,
)


def load_lightcurve_tool(filepath: str) -> str:
    df = load_lightcurve(Path(filepath), SCHEMA)
    return f"Loaded {len(df)} rows from {filepath}."


def validate_lightcurve_tool(filepath: str) -> str:
    df = load_lightcurve(Path(filepath), SCHEMA)
    report = validate_lightcurve(df)
    return json.dumps(report.model_dump(), indent=2)


def feature_anomaly_tool(filepath: str, window: int = 15, contamination: float = 0.05) -> str:
    df = load_lightcurve(Path(filepath), SCHEMA)
    pipeline = run_feature_anomaly_pipeline(df, window=window, contamination=contamination)
    summary: dict[str, Any] = {
        "transit_window": pipeline["transit_window"],
        "transit_depth": pipeline["transit_depth"],
        "n_anomalous_points": pipeline["anomaly_summary"]["n_anomalous_points"],
    }
    return json.dumps(summary, indent=2)


def build_agent_context_tool(filepath: str) -> str:
    return json.dumps(build_agent_context(filepath), indent=2)


def build_graph(llm):
    from langgraph.prebuilt import create_react_agent
    from langchain_core.tools import tool

    @tool
    def load_lightcurve_tool(filepath: str) -> str:
        """Load a WASP-18 lightcurve CSV with schema enforcement."""
        df = load_lightcurve(Path(filepath), SCHEMA)
        return f"Loaded {len(df)} rows from {filepath}."

    @tool
    def validate_lightcurve_tool(filepath: str) -> str:
        """Validate a loaded lightcurve and return a structured JSON report."""
        df = load_lightcurve(Path(filepath), SCHEMA)
        report = validate_lightcurve(df)
        return json.dumps(report.model_dump(), indent=2)

    @tool
    def feature_anomaly_tool(filepath: str) -> str:
        """Run feature engineering and anomaly detection on a light curve."""
        df = load_lightcurve(Path(filepath), SCHEMA)
        pipeline = run_feature_anomaly_pipeline(df)
        return json.dumps({
            "transit_window": pipeline["transit_window"],
            "transit_depth": pipeline["transit_depth"],
            "n_anomalous_points": pipeline["anomaly_summary"]["n_anomalous_points"],
        }, indent=2)

    return create_react_agent(llm, [load_lightcurve_tool, validate_lightcurve_tool, feature_anomaly_tool])


def main() -> None:
    try:
        from langchain.chat_models import ChatOpenAI
    except ImportError as exc:
        raise ImportError(
            "LangChain is required for the orchestrator. Install it with `pip install langchain`."
        ) from exc

    llm = ChatOpenAI(temperature=0)
    graph = build_graph(llm)

    prompt = (
        "You are an intelligent workflow conductor. "
        "Use the available tools to load the WASP-18 light curve, validate it, run anomaly detection, "
        "and return a concise summary of the transit signal."
    )
    result = graph.run(prompt)
    print(result)


if __name__ == "__main__":
    main()
