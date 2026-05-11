"""
ragas_evaluation.py

Module 03 — Multi-Agent Architecture (agent output evaluation).

Replaces promptfoo_evaluation.py. Uses ragas — a pure Python evaluation
framework available on conda-forge — instead of a Node.js CLI tool.

ragas evaluates the quality of LLM agent outputs using three metrics
directly relevant to this pipeline:

  Faithfulness       — are the agent's claims supported by the context
                       it was given? Catches hallucination.
  Answer Relevancy   — does the agent's answer address the question asked?
  Context Relevance  — was the retrieved context actually useful for the answer?

For this module, we treat the agent_context dict (built by build_agent_context)
as the "retrieved context" and the agent's final answer as the "response".
This lets us evaluate whether the LangGraph agent reasoned faithfully from
the pipeline data it received.

Install:
    conda install conda-forge::ragas

Run:
    python ragas_evaluation.py               # uses pre-built context, no LLM needed
    python ragas_evaluation.py --live        # calls the agent, then evaluates its output

References:
    https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/
    https://anaconda.org/conda-forge/ragas
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

from agent_tools import build_agent_context

DATA_PATH = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
if not DATA_PATH.exists():
    DATA_PATH = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"


# ── Sample dataset ────────────────────────────────────────────────────────────

def build_eval_dataset(context: dict, agent_answer: str) -> list[dict]:
    """
    Build a ragas SingleTurnSample dataset from agent context + answer.

    ragas expects:
      user_input   — the question posed to the agent
      response     — the agent's answer
      retrieved_contexts — the context the agent had available

    We use the structured agent_context JSON as the retrieved context.
    This lets ragas judge whether the agent's reasoning is grounded in
    the data pipeline's actual outputs.
    """
    context_str = json.dumps(context, indent=2)
    depth_pct   = context["anomaly_detection"]["transit_depth_pct"]
    n_anomalies = context["anomaly_detection"]["n_anomalous_points"]
    t_start     = context["anomaly_detection"]["transit_start"]
    t_end       = context["anomaly_detection"]["transit_end"]

    return [
        {
            "user_input": (
                "Summarize the WASP-18 b planetary transit signal from the "
                "lightcurve analysis. Include the transit depth, the phase "
                "window, and what it tells us about the planet."
            ),
            "response": agent_answer,
            "retrieved_contexts": [context_str],
            # reference: what a faithful answer should contain
            "reference": (
                f"The WASP-18 b lightcurve shows a transit depth of "
                f"{depth_pct:.4f}% with {n_anomalies} anomalous points "
                f"detected by IsolationForest. The transit window spans "
                f"phase {t_start:.4f} to {t_end:.4f}. "
                f"There are no null values in the dataset."
            ),
        }
    ]


# ── Evaluation ────────────────────────────────────────────────────────────────

def run_evaluation(dataset: list[dict], base_url: str, api_key: str, model: str) -> None:
    """
    Run ragas evaluation using Faithfulness, Answer Relevancy, and
    Context Relevance metrics.

    ragas uses an LLM as a judge — it calls the same inference endpoint
    the agent uses, so the same AI Navigator / vLLM / Anthropic config works.
    """
    try:
        from ragas import evaluate
        from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRelevance
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        print(f"Import error: {e}")
        print("\nInstall ragas:")
        print("  conda install conda-forge::ragas")
        sys.exit(1)

    # Build ragas dataset
    samples = [SingleTurnSample(**row) for row in dataset]
    eval_dataset = EvaluationDataset(samples=samples)

    # Use the same inference endpoint as the agent
    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0,
    )
    ragas_llm = LangchainLLMWrapper(llm)

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm),
        ContextRelevance(llm=ragas_llm),
    ]

    print("Running ragas evaluation...")
    print(f"  Metrics : Faithfulness · AnswerRelevancy · ContextRelevance")
    print(f"  Judge   : {model} at {base_url}")
    print(f"  Samples : {len(samples)}")
    print()

    result = evaluate(dataset=eval_dataset, metrics=metrics)
    df = result.to_pandas()

    print("── Evaluation results ────────────────────────────────────────────\n")
    for _, row in df.iterrows():
        print(f"  Faithfulness     : {row.get('faithfulness', 'n/a'):.3f}  "
              f"(1.0 = all claims grounded in context)")
        print(f"  Answer Relevancy : {row.get('answer_relevancy', 'n/a'):.3f}  "
              f"(1.0 = fully addresses the question)")
        print(f"  Context Relevance: {row.get('context_relevance', 'n/a'):.3f}  "
              f"(1.0 = context was fully useful)")

    mean_scores = df[["faithfulness", "answer_relevancy", "context_relevance"]].mean()
    overall = float(mean_scores.mean())
    print(f"\n  Overall score    : {overall:.3f}")

    # Gate — fail loudly if faithfulness is below threshold
    # Faithfulness < 0.7 means the agent hallucinated claims not in the data.
    faith = float(mean_scores.get("faithfulness", 1.0))
    if faith < 0.7:
        print(f"\n  ⚠  Faithfulness {faith:.3f} below threshold (0.7)")
        print("     The agent's answer contains claims not supported by the pipeline data.")
        print("     Review the agent prompt and tool docstrings.")
    else:
        print(f"\n  ✓  Faithfulness {faith:.3f} — agent reasoning grounded in pipeline data")


# ── Pre-built answer (no LLM needed for default run) ─────────────────────────

PREBUILT_ANSWER = """
The WASP-18 b lightcurve shows a clear planetary transit signal. The
IsolationForest algorithm detected 91 anomalous flux points clustered
between phase -0.042 and +0.042 — a window of approximately 2 hours
consistent with a hot Jupiter transiting its host star.

The transit depth is approximately 1.014%, meaning the star's brightness
drops by just over 1% during each transit. At WASP-18 b's 22-hour orbital
period, this depth and the clean null-free dataset (1,800 rows, no missing
values) give high confidence in the signal detection.
""".strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    live_mode = "--live" in sys.argv

    if not DATA_PATH.exists():
        print(
            "Error: wasp18b_lightcurve.csv not found.\n\n"
            "Most likely fix:\n"
            "  git submodule update --init --recursive\n"
        )
        sys.exit(1)

    base_url = os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1")
    api_key  = os.environ.get("INFERENCE_API_KEY",  "not-needed")
    model    = os.environ.get("INFERENCE_MODEL",    "default")

    print(f"Building agent context from: {DATA_PATH.name}")
    context = build_agent_context(str(DATA_PATH))
    print(f"  rows      : {context['data_quality']['rows']}")
    print(f"  anomalies : {context['anomaly_detection']['n_anomalous_points']}")
    print(f"  depth     : {context['anomaly_detection']['transit_depth_pct']:.4f}%")
    print()

    if live_mode:
        # Call the LangGraph agent, then evaluate its actual output
        print("Live mode — running LangGraph agent before evaluation...")
        try:
            from langchain_openai import ChatOpenAI
            from langgraph.prebuilt import create_react_agent
            from langchain_core.tools import tool
            from langchain_core.messages import HumanMessage
            from ingestion import SCHEMA, load_lightcurve, validate_lightcurve
            from agent_tools import run_feature_anomaly_pipeline

            @tool
            def build_context_tool(filepath: str) -> str:
                """Build the complete structured agent context for a lightcurve."""
                return json.dumps(build_agent_context(filepath), indent=2)

            llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0)
            agent = create_react_agent(llm, [build_context_tool])
            result = agent.invoke({"messages": [HumanMessage(content=(
                f"The lightcurve file is at: {DATA_PATH}\n"
                "Use build_context_tool then summarize the transit signal — "
                "depth, phase window, and what it tells us about the planet."
            ))]})
            agent_answer = result["messages"][-1].content
            print(f"\nAgent answer:\n{agent_answer}\n")
        except Exception as e:
            print(f"Agent error: {e}")
            print("Falling back to pre-built answer for evaluation.")
            agent_answer = PREBUILT_ANSWER
    else:
        # Default: evaluate the pre-built answer — no LLM call for inference,
        # but ragas still needs an LLM judge endpoint for the metrics.
        print("Using pre-built agent answer (no inference call).")
        print("To run with a live agent: python ragas_evaluation.py --live\n")
        agent_answer = PREBUILT_ANSWER

    dataset = build_eval_dataset(context, agent_answer)
    run_evaluation(dataset, base_url, api_key, model)

    print("""
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 03 EVALUATION COMPLETE            ║
║                                                              ║
║  Multi-Agent Architecture                                    ║
║  ragas: Faithfulness · Relevancy · Context grounding         ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
