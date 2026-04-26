"""
langchain_agent_example.py

Module 02 — Your First Agent (LangGraph implementation).

Registers the WASP-18 b pipeline functions as LangGraph tools and runs a
ReAct agent that loads, validates, and summarizes the lightcurve.

Default inference target: AI Navigator (local, no API key needed).
Override with environment variables to point at any OpenAI-compatible endpoint:

    export INFERENCE_BASE_URL="http://localhost:8080/v1"        # AI Navigator (default)
    export INFERENCE_BASE_URL="https://api.anthropic.com/v1"    # Anthropic
    export INFERENCE_BASE_URL="http://your-server:8000/v1"      # vLLM
    export INFERENCE_API_KEY="sk-..."
    export INFERENCE_MODEL="claude-haiku-4-5-20251001"

Requirements (add to environment.yml):
    langchain-openai
    langchain-core
    langgraph>=0.2
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02-your-first-agent"))
sys.path.insert(0, str(ROOT / "01-data-sources"))

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_tools import (
    SCHEMA,
    build_agent_context,
    load_lightcurve,
    run_feature_anomaly_pipeline,
    validate_lightcurve,
)

# Primary CSV location; fall back to polars_demo copy if needed
DATA_PATH = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
if not DATA_PATH.exists():
    DATA_PATH = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"


# ── Tools ─────────────────────────────────────────────────────────────────────
# Docstrings are what the LLM reads to decide when to call each tool.
# Write them for the model, not a human reader.
# The @tool decorator uses the function name as the tool name — keep them
# descriptive. Optional parameters (window, contamination) are dropped here
# because LLMs reliably pass wrong types for numeric kwargs; use fixed defaults.

@tool
def load_lightcurve_tool(filepath: str) -> str:
    """Load a WASP-18 lightcurve CSV and confirm row count.
    Always call this first before validation or analysis."""
    if not Path(filepath).exists():
        return (
            f"Error: file not found at {filepath}. "
            "Check the path and try again."
        )
    df = load_lightcurve(Path(filepath), SCHEMA)
    return f"Loaded {len(df)} rows from {filepath}."


@tool
def validate_lightcurve_tool(filepath: str) -> str:
    """Validate a WASP-18 lightcurve CSV and return a structured JSON quality report.
    Checks for nulls, phase range, flux statistics, and schema conformance.
    Call this after loading to confirm data quality before anomaly detection."""
    if not Path(filepath).exists():
        return f"Error: file not found at {filepath}."
    df = load_lightcurve(Path(filepath), SCHEMA)
    report = validate_lightcurve(df)
    return json.dumps(report.model_dump(), indent=2)


@tool
def feature_anomaly_tool(filepath: str) -> str:
    """Run feature engineering and IsolationForest anomaly detection on a lightcurve.
    Returns transit window boundaries, transit depth, and anomalous point count.
    Call this after validation to identify the planetary transit signal."""
    if not Path(filepath).exists():
        return f"Error: file not found at {filepath}."
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
    """Build the complete structured agent context for a lightcurve file.
    Combines validation report, feature summary, and anomaly results into a
    single JSON payload. Use this to assemble a final summary for the user."""
    if not Path(filepath).exists():
        return f"Error: file not found at {filepath}."
    context = build_agent_context(filepath)
    return json.dumps(context, indent=2)


# ── LLM ───────────────────────────────────────────────────────────────────────

def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("INFERENCE_MODEL", "default"),
        base_url=os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1"),
        api_key=os.environ.get("INFERENCE_API_KEY", "not-needed"),
        temperature=0,
    )


# ── Reasoning trace ───────────────────────────────────────────────────────────

def print_trace(messages: list) -> None:
    """Print every tool call and intermediate response — the interesting part."""
    print("\n── Agent reasoning trace ─────────────────────────────────────────\n")
    for msg in messages[:-1]:
        role = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                print(f"  [{role}] → {tc['name']}({tc['args']})")
        elif content:
            display = content if len(content) < 400 else content[:400] + "…"
            print(f"  [{role}] {display}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not DATA_PATH.exists():
        print(
            "Error: wasp18b_lightcurve.csv not found.\n\n"
            "Quick fix:\n"
            "  cp 100-example-applications/polars_demo/wasp18b_lightcurve.csv "
            "01-data-sources/\n"
        )
        sys.exit(1)

    base_url = os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1")
    print(f"Inference target : {base_url}")
    print(f"Model            : {os.environ.get('INFERENCE_MODEL', 'default')}")
    print(f"Data             : {DATA_PATH.name}\n")

    try:
        llm = build_llm()
        agent = create_react_agent(
            llm,
            [load_lightcurve_tool, validate_lightcurve_tool, feature_anomaly_tool, build_context_tool],
        )
    except Exception as exc:
        print(f"Error building agent: {exc}")
        sys.exit(1)

    prompt = (
        f"You are an intelligent data analyst. The lightcurve file is at: {DATA_PATH}\n\n"
        "Use the available tools in this order:\n"
        "1. Load the WASP-18 lightcurve\n"
        "2. Validate its data quality\n"
        "3. Run anomaly detection\n"
        "4. Summarize the transit signal in plain language — depth, window, and "
        "what it tells us about the planet"
    )

    try:
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    except Exception as exc:
        err = str(exc)
        if "connection" in err.lower() or "connect" in err.lower():
            print(
                f"\nConnection error: could not reach {base_url}\n\n"
                "Is AI Navigator running? Start it from Anaconda Navigator or:\n"
                "  anaconda-navigator  (then launch AI Navigator)\n\n"
                "Or point at a different endpoint:\n"
                "  export INFERENCE_BASE_URL=https://api.anthropic.com/v1\n"
                "  export INFERENCE_API_KEY=sk-...\n"
                "  export INFERENCE_MODEL=claude-haiku-4-5-20251001\n"
            )
        else:
            print(f"\nAgent error: {exc}")
        sys.exit(1)

    print_trace(result["messages"])

    print("\n── Final answer ──────────────────────────────────────────────────\n")
    print(result["messages"][-1].content)

    print("""
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 02 COMPLETE                       ║
║                                                              ║
║  Your First Agent                                            ║
║  One agent. Four tools. One transit classification.          ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
