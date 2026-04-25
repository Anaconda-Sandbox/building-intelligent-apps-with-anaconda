from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    return json.dumps(
        {
            "transit_window": pipeline["transit_window"],
            "transit_depth": pipeline["transit_depth"],
            "n_anomalous_points": pipeline["anomaly_summary"]["n_anomalous_points"],
        },
        indent=2,
    )


def build_context_tool(filepath: str) -> str:
    context = build_agent_context(filepath)
    return json.dumps(context, indent=2)


def main() -> None:
    try:
        from langchain.chat_models import ChatOpenAI
        from langchain.agents import AgentType, initialize_agent
        from langchain.tools import Tool
    except ImportError as exc:
        raise ImportError(
            "LangChain is required to run this example. Install it with `pip install langchain` "
            "and any optional LLM backend you prefer."
        ) from exc

    tools = [
        Tool.from_function(
            func=load_lightcurve_tool,
            name="load_lightcurve",
            description="Load a local WASP-18 lightcurve CSV with strict schema enforcement.",
        ),
        Tool.from_function(
            func=validate_lightcurve_tool,
            name="validate_lightcurve",
            description="Validate a loaded lightcurve and return a structured JSON validation report.",
        ),
        Tool.from_function(
            func=feature_anomaly_tool,
            name="feature_anomaly_pipeline",
            description="Run the feature engineering and anomaly detection pipeline and return a summary.",
        ),
        Tool.from_function(
            func=build_context_tool,
            name="build_agent_context",
            description="Build the JSON-ready agent context for a given lightcurve file.",
        ),
    ]

    llm = ChatOpenAI(temperature=0)
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )

    prompt = (
        "You are an intelligent data analyst. Use the available tools to load the WASP-18 light curve, "
        "validate its quality, run anomaly detection, and summarize the transit signal in plain language."
    )
    result = agent.run(prompt)
    print(result)


if __name__ == "__main__":
    main()
