"""
agents/analysis_agent.py

AnalysisAgent — unchanged from 03-multi-agent-architecture in structure,
but now accepts a configurable inference endpoint.

The agent itself doesn't know or care whether it's talking to:
  - A vLLM server running Nemotron on a Brev GPU
  - NVIDIA NIM hosted endpoints
  - Anthropic Claude
  - The local AI Navigator API server

That's the portable inference contract. One base_url change, same agent.
"""

import os
from typing import Any
from openai import OpenAI
from pydantic import BaseModel

# Import the ValidationReport from Module 01 — same contract throughout
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

try:
    from ingestion import ValidationReport
except ImportError:
    # Fallback if running standalone
    class ValidationReport(BaseModel):
        nulls: dict
        phase_range: tuple
        flux_range: tuple
        flux_std: float
        duplicate_phases: int


# ── Inference endpoint configuration ─────────────────────────────────────────
# The agent reads base_url and api_key from environment variables.
# This is the only thing that changes between CPU and GPU deployments.
#
# For vLLM + Nemotron on Brev:
#   export INFERENCE_BASE_URL="http://localhost:8000/v1"
#   export INFERENCE_API_KEY="not-needed"
#   export INFERENCE_MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
#
# For NVIDIA NIM (hosted):
#   export INFERENCE_BASE_URL="https://integrate.api.nvidia.com/v1"
#   export INFERENCE_API_KEY="your_nvidia_api_key"
#   export INFERENCE_MODEL="nvidia/nemotron-3-super-120b"
#
# For Anaconda Platform Model Server (from Module 04):
#   export INFERENCE_BASE_URL="$MODEL_SERVER_BASE_URL"
#   export INFERENCE_API_KEY="$ANACONDA_API_KEY"
#   export INFERENCE_MODEL=""
#
# For local AI Navigator (from Module 02):
#   export INFERENCE_BASE_URL="http://localhost:8080"
#   export INFERENCE_API_KEY="your_navigator_key"
#   export INFERENCE_MODEL="any"  # Navigator ignores model param

INFERENCE_BASE_URL = os.environ.get("INFERENCE_BASE_URL", "http://localhost:8000/v1")
INFERENCE_API_KEY  = os.environ.get("INFERENCE_API_KEY",  "not-needed")
INFERENCE_MODEL    = os.environ.get("INFERENCE_MODEL",    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16")


def get_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at the configured endpoint."""
    return OpenAI(
        base_url=INFERENCE_BASE_URL,
        api_key=INFERENCE_API_KEY,
    )


def run_analysis_agent(
    report: ValidationReport,
    anomaly_result: dict | None = None,
    verbose: bool = False,
) -> dict:
    """
    Run the AnalysisAgent against a ValidationReport.

    The agent reasons over the structured pipeline output and returns
    a structured interpretation — transit classification, confidence,
    and recommended next steps.

    This function is called identically whether the endpoint is a local
    vLLM/Nemotron server on Brev, an NVIDIA NIM, or any other backend.

    Args:
        report:         ValidationReport from validate_lightcurve()
        anomaly_result: Optional dict from IsolationForest step
        verbose:        Print the full model response if True

    Returns:
        dict with: classification, confidence, transit_depth_pct,
                   reasoning_summary, recommended_next_steps
    """
    client = get_client()

    # Build the context from structured pipeline outputs.
    # The model reasons on facts, not raw data.
    context_lines = [
        f"Dataset quality: {report.null_count()} null values, "
        f"flux_std={report.flux_std:.8f}, "
        f"phase_range={report.phase_range[0]:.4f} to {report.phase_range[1]:.4f} days",
        f"Duplicate phase values: {report.duplicate_phases}",
    ]

    if anomaly_result:
        context_lines += [
            f"Anomaly detection: {anomaly_result.get('n_anomalous_points', 0)} anomalous points detected",
            f"Transit depth estimate: {anomaly_result.get('transit_depth_pct', 0):.4f}%",
            f"Suspected transit window: "
            f"{anomaly_result.get('transit_start', 'unknown')} to "
            f"{anomaly_result.get('transit_end', 'unknown')} days",
        ]

    context = "\n".join(context_lines)

    system_prompt = (
        "You are an astrophysics data analysis agent specializing in exoplanet "
        "transit detection from TESS light curve data. "
        "You receive structured pipeline outputs — not raw data — and provide "
        "expert interpretation. Always respond in JSON format."
    )

    user_prompt = f"""
Analyze this light curve pipeline output and classify the transit signal.

Pipeline results:
{context}

Respond with a JSON object containing exactly these fields:
- classification: "confirmed_transit", "candidate_transit", "no_transit", or "insufficient_data"
- confidence: float between 0.0 and 1.0
- transit_depth_pct: float (your estimate of the transit depth in percent)
- reasoning_summary: string (2-3 sentences explaining your classification)
- recommended_next_steps: list of strings (2-3 concrete follow-up actions)

Respond with JSON only, no preamble.
"""

    response = client.chat.completions.create(
        model=INFERENCE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=500,
        temperature=0.1,  # Low temperature for deterministic classification
    )

    raw_content = response.choices[0].message.content

    if verbose:
        print(f"[AnalysisAgent] Model: {INFERENCE_MODEL}")
        print(f"[AnalysisAgent] Endpoint: {INFERENCE_BASE_URL}")
        print(f"[AnalysisAgent] Response: {raw_content}")

    # Parse structured output
    import json
    try:
        # Strip any markdown code fences if present
        clean = raw_content.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
    except json.JSONDecodeError:
        # Fallback if model didn't return clean JSON
        result = {
            "classification":      "insufficient_data",
            "confidence":          0.0,
            "transit_depth_pct":   0.0,
            "reasoning_summary":   f"JSON parsing failed. Raw response: {raw_content[:200]}",
            "recommended_next_steps": ["Check model endpoint", "Verify prompt format"],
        }

    return result
