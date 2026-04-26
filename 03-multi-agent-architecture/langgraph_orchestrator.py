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


def build_graph(llm: Any) -> Any:
    try:
        from langchain.graphs import Graph
        from langchain.tools import Tool
    except ImportError as exc:
        raise ImportError(
            "LangChain with LangGraph support is required. "
            "Install it with `pip install langchain` and the appropriate LangGraph extras."
        ) from exc

    tools = [
        Tool.from_function(
            func=load_lightcurve_tool,
            name="load_lightcurve",
            description="Load a WASP-18 lightcurve CSV with schema enforcement.",
        ),
        Tool.from_function(
            func=validate_lightcurve_tool,
            name="validate_lightcurve",
            description="Validate a loaded lightcurve and return a structured JSON report.",
        ),
        Tool.from_function(
            func=feature_anomaly_tool,
            name="feature_anomaly_pipeline",
            description="Run feature engineering and anomaly detection on a light curve.",
        ),
        Tool.from_function(
            func=build_agent_context_tool,
            name="build_agent_context",
            description="Build the JSON-ready context for the agent.",
        ),
    ]

    if hasattr(Graph, "from_tools"):
        return Graph.from_tools(tools, llm=llm)
    return Graph(llm=llm, tools=tools)


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
