"""
langgraph_orchestrator.py

Module 03 — Multi-Agent Architecture (LangGraph orchestrator).

Builds a two-agent LangGraph supervisor: a DataAgent that handles loading
and validation, and an AnalysisAgent that handles feature engineering and
anomaly detection. A supervisor routes between them.

Imports the @tool-decorated functions from Module 02 directly — no
re-implementation. Module 03 adds orchestration on top of Module 02's tools.

Default inference target: AI Navigator (local, no API key needed).
Override with environment variables:

    export INFERENCE_BASE_URL="http://localhost:8080/v1"        # AI Navigator (default)
    export INFERENCE_BASE_URL="https://api.anthropic.com/v1"    # Anthropic
    export INFERENCE_API_KEY="sk-..."
    export INFERENCE_MODEL="claude-haiku-4-5-20251001"

Requirements:
    langchain-openai
    langchain-core
    langgraph>=0.2
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02-your-first-agent"))
sys.path.insert(0, str(ROOT / "01-data-sources"))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from typing import TypedDict, Annotated
import operator

# Import tools from Module 02 — single source of truth, no re-implementation
from langchain_agent_example import (
    load_lightcurve_tool,
    validate_lightcurve_tool,
    feature_anomaly_tool,
    build_context_tool,
    build_llm,
)

# CSV path — resolved the same way as Module 02
DATA_PATH = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
if not DATA_PATH.exists():
    DATA_PATH = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"


# ── Shared graph state ────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    messages: Annotated[list, operator.add]
    data_ready: bool
    analysis_ready: bool


# ── Agents ────────────────────────────────────────────────────────────────────
# Each agent is a compiled ReAct graph with a focused tool subset.
# The supervisor routes to the right agent based on pipeline state.

def build_data_agent(llm: ChatOpenAI):
    """Handles load + validate. Owns the data quality gate."""
    return create_react_agent(
        llm,
        [load_lightcurve_tool, validate_lightcurve_tool],
        state_modifier=(
            "You are the DataAgent. Your job is to load the WASP-18 lightcurve "
            "and validate its quality. Use load_lightcurve_tool first, then "
            "validate_lightcurve_tool. Report any data quality issues clearly."
        ),
    )


def build_analysis_agent(llm: ChatOpenAI):
    """Handles feature engineering + anomaly detection. Owns the science output."""
    return create_react_agent(
        llm,
        [feature_anomaly_tool, build_context_tool],
        state_modifier=(
            "You are the AnalysisAgent. Your job is to run anomaly detection on "
            "the WASP-18 lightcurve and summarize the transit signal. Use "
            "feature_anomaly_tool to detect anomalies, then build_context_tool "
            "to assemble the final structured context."
        ),
    )


# ── Supervisor graph ──────────────────────────────────────────────────────────

def build_supervisor(llm: ChatOpenAI, data_agent, analysis_agent):
    """
    Simple two-step supervisor: DataAgent first, AnalysisAgent second.

    In a production system this would be a full LangGraph supervisor with
    conditional routing. Here we use a linear pipeline — correct for this
    dataset where data must be validated before analysis.
    """

    def run_data_agent(state: PipelineState) -> PipelineState:
        filepath = str(DATA_PATH)
        prompt = (
            f"The lightcurve file is at: {filepath}\n"
            "Load it and validate its quality."
        )
        result = data_agent.invoke({"messages": [HumanMessage(content=prompt)]})
        return {
            "messages": result["messages"],
            "data_ready": True,
            "analysis_ready": False,
        }

    def run_analysis_agent(state: PipelineState) -> PipelineState:
        filepath = str(DATA_PATH)
        prompt = (
            f"The lightcurve file is at: {filepath}\n"
            "Run anomaly detection and build the full agent context."
        )
        result = analysis_agent.invoke({"messages": [HumanMessage(content=prompt)]})
        return {
            "messages": result["messages"],
            "data_ready": True,
            "analysis_ready": True,
        }

    def should_analyze(state: PipelineState) -> str:
        return "analysis" if state.get("data_ready") else END

    graph = StateGraph(PipelineState)
    graph.add_node("data", run_data_agent)
    graph.add_node("analysis", run_analysis_agent)
    graph.set_entry_point("data")
    graph.add_conditional_edges("data", should_analyze, {"analysis": "analysis", END: END})
    graph.add_edge("analysis", END)
    return graph.compile()


# ── Reasoning trace ───────────────────────────────────────────────────────────

def print_trace(messages: list, label: str) -> None:
    print(f"\n── {label} ──────────────────────────────────────────────\n")
    for msg in messages:
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
    print(f"Data             : {DATA_PATH.name}")
    print( "Architecture     : DataAgent → AnalysisAgent (LangGraph supervisor)\n")

    try:
        llm = build_llm()
        data_agent     = build_data_agent(llm)
        analysis_agent = build_analysis_agent(llm)
        supervisor     = build_supervisor(llm, data_agent, analysis_agent)
    except Exception as exc:
        print(f"Error building graph: {exc}")
        sys.exit(1)

    try:
        result = supervisor.invoke({
            "messages": [],
            "data_ready": False,
            "analysis_ready": False,
        })
    except Exception as exc:
        err = str(exc)
        if "connection" in err.lower() or "connect" in err.lower():
            print(
                f"\nConnection error: could not reach {base_url}\n\n"
                "Is AI Navigator running? Start it from Anaconda Navigator, or:\n"
                "  export INFERENCE_BASE_URL=https://api.anthropic.com/v1\n"
                "  export INFERENCE_API_KEY=sk-...\n"
                "  export INFERENCE_MODEL=claude-haiku-4-5-20251001\n"
            )
        else:
            print(f"\nGraph error: {exc}")
        sys.exit(1)

    all_messages = result.get("messages", [])
    print_trace(all_messages, "Multi-agent reasoning trace")

    final = all_messages[-1].content if all_messages else "(no output)"
    print("\n── Final answer ──────────────────────────────────────────────────\n")
    print(final)

    print("""
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 03 COMPLETE                       ║
║                                                              ║
║  Multi-Agent Architecture                                    ║
║  DataAgent + AnalysisAgent. One supervisor. Zero conflicts.  ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
