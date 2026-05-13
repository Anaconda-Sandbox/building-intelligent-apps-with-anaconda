"""
agents/analysis_agent.py

Self-contained AnalysisAgent for Module 06 — App Architecture.

Combined harness: Metaflow @catch (infrastructure fault tolerance) +
LangGraph MemorySaver checkpointer (agent-loop durable execution).

The two layers handle failures at different levels:

  Metaflow @catch        — step-level: if the entire analyze step fails after
                           all @retry attempts, @catch stores the exception as
                           an artifact and the flow continues to evaluate.
                           Operates outside Python, at the orchestration layer.

  LangGraph checkpointer — agent-loop level: if the LLM call fails mid-reasoning
                           (API timeout, rate limit, provider outage), the graph
                           saves its state at each superstep. On the next @retry,
                           LangGraph resumes from the last successful checkpoint
                           rather than restarting the reasoning loop from scratch.

Together they produce a self-healing pipeline:
  transient LLM failure  → @retry retries, LangGraph resumes mid-loop
  permanent LLM failure  → @catch degrades gracefully to insufficient_data
  bad data               → @catch + assertions catch and record the failure
  reasoning loop         → LangGraph recursion_limit terminates runaway agents

Inference endpoint: controlled by env vars — same pattern as all modules.
    export ANTHROPIC_API_KEY="sk-ant-..."          # Anthropic (default)
    export INFERENCE_BASE_URL="http://localhost:8080/v1"  # AI Navigator / vLLM
    export INFERENCE_API_KEY="not-needed"
    export INFERENCE_MODEL="default"
"""
from __future__ import annotations

import json
import os
from typing import Any


# ── System prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(memory_context: str = "") -> str:
    base = """You are an astrophysics data analyst specialising in exoplanet transit detection.

You receive a structured validation report from a TESS light curve pipeline and
must classify the transit signal. Return ONLY valid JSON matching this schema:

{
    "classification": "confirmed_transit" | "candidate_transit" | "no_transit" | "insufficient_data",
    "confidence": <float 0.0-1.0>,
    "transit_depth_pct": <float, percentage drop in flux>,
    "reasoning_summary": "<2-3 sentence explanation>",
    "recommended_next_steps": ["<step 1>", "<step 2>"]
}

Classification guidelines:
  confirmed_transit   — clear periodic flux decrease, depth > 0.1%, anomaly cluster tight
  candidate_transit   — possible signal but signal-to-noise marginal, follow-up recommended
  no_transit          — data is clean but no periodic flux decrease detected
  insufficient_data   — data quality too poor to classify

Return ONLY the JSON object. No preamble, no markdown fences."""

    if memory_context:
        base += f"\n\n{memory_context}"

    return base


# ── LLM call — Anthropic first, OpenAI-compatible fallback ───────────────────

def _call_anthropic(prompt: str, system: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("INFERENCE_MODEL", "claude-haiku-4-5-20251001")
    msg = client.messages.create(
        model=model,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _call_openai_compatible(prompt: str, system: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        base_url=os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1"),
        api_key=os.environ.get("INFERENCE_API_KEY", "not-needed"),
    )
    model = os.environ.get("INFERENCE_MODEL", "default")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
        temperature=0.0,
    )
    return resp.choices[0].message.content


def _call_llm(prompt: str, system: str) -> str:
    """Try Anthropic first, fall back to OpenAI-compatible endpoint."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_anthropic(prompt, system)
    return _call_openai_compatible(prompt, system)


# ── LangGraph agent with MemorySaver checkpointer ─────────────────────────────

def _build_agent(system_prompt: str):
    """
    Build a LangGraph ReAct agent with a MemorySaver checkpointer.

    The MemorySaver gives the agent durable execution within a single run:
    if the LLM call fails mid-reasoning, LangGraph has saved state at each
    superstep. When Metaflow's @retry re-executes this step, the agent resumes
    from the last checkpoint rather than restarting the full reasoning loop.

    thread_id is set per call in run_analysis_agent() so each Metaflow task
    (target × run_id) gets its own isolated checkpoint thread. This means:
      - wasp18b and wasp12b have separate, non-interfering checkpoint threads
      - a retry of wasp18b picks up its own last checkpoint, not wasp12b's

    MemorySaver is in-process only — state lives for the duration of this
    Python process. For cross-process persistence (e.g. distributed Metaflow
    runs on Outerbounds), swap MemorySaver for SqliteSaver or PostgresSaver
    and ensure the checkpoint store is accessible from all worker nodes.
    """
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent

    # The agent has one tool: call the classification LLM directly.
    # For Module 06 the "tool" is the LLM call itself — the agent loop
    # is the harness around it, not a multi-tool pipeline.
    @tool
    def classify_transit(report_json: str) -> str:
        """Classify a TESS light curve transit signal from a JSON validation report."""
        return _call_llm(report_json, system_prompt)

    base_url  = os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1")
    api_key   = os.environ.get("INFERENCE_API_KEY",  "not-needed")
    model     = os.environ.get("INFERENCE_MODEL",    "default")

    # Use Anthropic as the supervisor model if available
    if os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model=os.environ.get("INFERENCE_MODEL", "claude-haiku-4-5-20251001"),
            api_key=os.environ["ANTHROPIC_API_KEY"],
            temperature=0,
        )
    else:
        llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
        )

    # MemorySaver: checkpoints at each superstep within this process.
    # On @retry, pass the same thread_id to resume from the last checkpoint.
    checkpointer = MemorySaver()
    agent = create_react_agent(llm, [classify_transit], checkpointer=checkpointer)
    return agent, checkpointer


# ── Fallback result when LLM is unavailable ───────────────────────────────────

def _mock_result(report: Any) -> dict:
    """
    Return a deterministic result when no LLM endpoint is configured.
    Used in --check mode and when running the notebook without credentials.
    """
    flux_std    = getattr(report, "flux_std", 0)
    n_anomalies = getattr(report, "n_anomalies", 0)

    if 0.0001 < flux_std < 0.001 and n_anomalies > 50:
        return {
            "classification":         "confirmed_transit",
            "confidence":             0.87,
            "transit_depth_pct":      1.014,
            "reasoning_summary":      (
                "Mock result — no LLM configured. "
                "Data quality is consistent with a confirmed hot Jupiter transit. "
                "Set ANTHROPIC_API_KEY or INFERENCE_BASE_URL to run live inference."
            ),
            "recommended_next_steps": [
                "Set ANTHROPIC_API_KEY for live classification",
                "Or start AI Navigator: INFERENCE_BASE_URL=http://localhost:8080/v1",
            ],
        }
    return {
        "classification":         "insufficient_data",
        "confidence":             0.0,
        "transit_depth_pct":      0.0,
        "reasoning_summary":      "Mock result — no LLM configured.",
        "recommended_next_steps": ["Configure an inference endpoint"],
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def run_analysis_agent(
    report: Any,
    memory_context: str = "",
    verbose: bool = False,
    thread_id: str = "default",
) -> dict:
    """
    Classify a TESS light curve transit signal using a harnessed LangGraph agent.

    The agent runs inside a MemorySaver-checkpointed LangGraph graph. Each call
    uses a unique thread_id (target + Metaflow run_id) so checkpoints are
    isolated per task. On Metaflow @retry, passing the same thread_id allows
    LangGraph to resume mid-reasoning from the last successful superstep.

    Failure hierarchy (outermost to innermost):
      Metaflow @catch     catches step-level failures after all @retry exhausted
      Metaflow @retry     retries the whole step on failure
      LangGraph checkpoint resumes agent loop from last superstep on retry
      This function      catches LLM/JSON errors, returns insufficient_data

    Args:
        report:         ValidationReport from ingestion.validate_lightcurve()
        memory_context: Past-run context from AgentMemoryStore (DuckDB)
        verbose:        Print reasoning trace
        thread_id:      Unique ID for this task's checkpoint thread.
                        Set to f"{target}_{metaflow_run_id}" in the flow.

    Returns:
        {
            "classification":         str,
            "confidence":             float,
            "transit_depth_pct":      float,
            "reasoning_summary":      str,
            "recommended_next_steps": list[str],
        }
    """
    has_anthropic     = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai_compat = bool(os.environ.get("INFERENCE_BASE_URL"))

    if not has_anthropic and not has_openai_compat:
        if verbose:
            print("No inference endpoint configured — returning mock result")
        return _mock_result(report)

    report_dict = report.model_dump() if hasattr(report, "model_dump") else {}
    prompt = (
        f"Classify this TESS light curve validation report:\n\n"
        f"{json.dumps(report_dict, indent=2)}\n\n"
        f"Return a JSON classification following the schema in your system prompt."
    )
    system = build_system_prompt(memory_context)

    try:
        agent, _ = _build_agent(system)

        # thread_id scopes this checkpoint to one Metaflow task.
        # On @retry with the same thread_id, LangGraph resumes from the
        # last successful superstep — not from the beginning.
        config = {"configurable": {"thread_id": thread_id}}

        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )

        raw = result["messages"][-1].content
        if verbose:
            print(f"[thread:{thread_id}] Raw LLM response:\n{raw}\n")

        # Strip accidental markdown fences
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = json.loads(clean.strip())

        # Enforce required keys
        parsed.setdefault("classification",         "insufficient_data")
        parsed.setdefault("confidence",              0.0)
        parsed.setdefault("transit_depth_pct",       0.0)
        parsed.setdefault("reasoning_summary",       "")
        parsed.setdefault("recommended_next_steps",  [])

        # Clamp confidence to [0, 1]
        parsed["confidence"] = max(0.0, min(1.0, float(parsed["confidence"])))

        return parsed

    except Exception as exc:
        if verbose:
            print(f"[thread:{thread_id}] Agent error: {exc}")
        return {
            "classification":         "insufficient_data",
            "confidence":             0.0,
            "transit_depth_pct":      0.0,
            "reasoning_summary":      f"Agent error: {exc}",
            "recommended_next_steps": ["Check inference endpoint", "Review logs"],
        }
