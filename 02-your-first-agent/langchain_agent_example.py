from __future__ import annotations

import json
import os
from pathlib import Path

from agent_tools import (
    SCHEMA,
    build_agent_context,
    load_lightcurve,
    run_feature_anomaly_pipeline,
    validate_lightcurve,
)

DATA_PATH = "../01-data-sources/wasp18b_lightcurve.csv"


# ── Tools ─────────────────────────────────────────────────────────────────────
# Docstrings are the tool descriptions the LLM sees — write for the model.

@tool
def load_lightcurve_tool(filepath: str) -> str:
    """Load a WASP-18 lightcurve CSV and return row count confirmation.
    Use this first before any validation or analysis."""
    df = load_lightcurve(Path(filepath), SCHEMA)
    return f"Loaded {len(df)} rows from {filepath}."


@tool
def validate_lightcurve_tool(filepath: str) -> str:
    """Validate a WASP-18 lightcurve CSV and return a structured JSON report.
    Checks for nulls, phase range, flux statistics, and schema conformance."""
    df = load_lightcurve(Path(filepath), SCHEMA)
    report = validate_lightcurve(df)
    return json.dumps(report.model_dump(), indent=2)


@tool
def feature_anomaly_tool(filepath: str) -> str:
    """Run feature engineering and IsolationForest anomaly detection on a lightcurve.
    Returns transit window, transit depth, and anomalous point count."""
    df = load_lightcurve(Path(filepath), SCHEMA)
    pipeline = run_feature_anomaly_pipeline(df, window=15, contamination=0.05)
    return json.dumps(
        {
            "transit_window": pipeline["transit_window"],
            "transit_depth": pipeline["transit_depth"],
            "n_anomalous_points": pipeline["anomaly_summary"]["n_anomalous_points"],
        },
        indent=2,
    )


@tool
def build_context_tool(filepath: str) -> str:
    """Build the full JSON agent context for a lightcurve file.
    Combines validation report, feature summary, and anomaly results
    into a single structured payload ready for downstream reasoning."""
    context = build_agent_context(filepath)
    return json.dumps(context, indent=2)


# ── LLM ───────────────────────────────────────────────────────────────────────
# Defaults to AI Navigator (local, no API key needed).
# Override via environment variables to point at any OpenAI-compatible endpoint.

def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("INFERENCE_MODEL", "default"),
        base_url=os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1"),
        api_key=os.environ.get("INFERENCE_API_KEY", "not-needed"),
        temperature=0,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent
    llm = build_llm()
    agent = create_react_agent(
        llm,
        [load_lightcurve_tool, validate_lightcurve_tool, feature_anomaly_tool, build_context_tool],
    )

    prompt = (
        f"You are an intelligent data analyst. The lightcurve file is at: {DATA_PATH}\n\n"
        "Use the available tools to:\n"
        "1. Load the WASP-18 lightcurve\n"
        "2. Validate its quality\n"
        "3. Run anomaly detection\n"
        "4. Summarize the transit signal in plain language"
    )

    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})

    # Print the reasoning trace (tool calls + intermediate steps)
    print("\n── Agent reasoning trace ─────────────────────────────────────────\n")
    for msg in result["messages"]:
        role = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                print(f"[{role}] → tool call: {tc['name']}({tc['args']})")
        elif content:
            print(f"[{role}] {content}")

    # Final answer is the last message
    print("\n── Final answer ──────────────────────────────────────────────────\n")
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()