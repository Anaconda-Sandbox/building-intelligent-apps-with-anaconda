"""
inference_client.py

The portable inference contract for Module 04.

All three inference targets — AI Navigator, vLLM, Anaconda Platform —
expose an OpenAI-compatible API. This module provides a single client
factory that reads configuration from environment variables.

The agent code from Module 03 imports this directly. Only the env vars
change between targets. Nothing else does.

Usage:
    from inference_client import get_client, INFERENCE_MODEL

    client = get_client()
    response = client.chat.completions.create(
        model=INFERENCE_MODEL,
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=100,
    )
"""

import os
from openai import OpenAI

# ── Configuration — set these env vars before importing ───────────────────────
#
# AI Navigator (local, no API key needed):
#   export INFERENCE_BASE_URL="http://localhost:8080/v1"
#   export INFERENCE_API_KEY="any-string"
#   export INFERENCE_MODEL="any"   # Navigator ignores this — model set in UI
#
# vLLM (self-hosted):
#   export INFERENCE_BASE_URL="http://your-server:8000/v1"
#   export INFERENCE_API_KEY="not-needed"
#   export INFERENCE_MODEL="model-name-as-loaded-in-vllm"
#
# Anaconda Platform Model Server:
#   export INFERENCE_BASE_URL="$MODEL_SERVER_BASE_URL"   # from server details page
#   export INFERENCE_API_KEY="$ANACONDA_API_KEY"         # from API keys page
#   export INFERENCE_MODEL=""                            # already loaded on server
#
# Anthropic Claude (fallback, used in Module 03):
#   Use anthropic client directly — not OpenAI-compatible at base level
#   See agents/analysis_agent.py for the Anthropic path

INFERENCE_BASE_URL = os.environ.get("INFERENCE_BASE_URL", "http://localhost:8080/v1")
INFERENCE_API_KEY  = os.environ.get("INFERENCE_API_KEY",  "not-needed")
INFERENCE_MODEL    = os.environ.get("INFERENCE_MODEL",    "")


def get_client() -> OpenAI:
    """
    Return an OpenAI-compatible client pointed at the configured endpoint.

    All three targets in Module 04 use this same client.
    The agents from Module 03 use this same client.
    Module 05 uses this same client pointed at Nemotron on vLLM.
    """
    return OpenAI(
        base_url=INFERENCE_BASE_URL,
        api_key=INFERENCE_API_KEY,
    )


def check_connection() -> dict:
    """
    Verify the inference endpoint is reachable and responsive.
    Returns a dict with status, base_url, and model info.
    """
    import time
    client = get_client()

    try:
        t0 = time.perf_counter()
        response = client.chat.completions.create(
            model=INFERENCE_MODEL,
            messages=[{"role": "user", "content": "Reply with one word: ready"}],
            max_tokens=10,
            temperature=0.0,
        )
        latency = time.perf_counter() - t0

        return {
            "status":    "ok",
            "base_url":  INFERENCE_BASE_URL,
            "model":     INFERENCE_MODEL or "(loaded on server)",
            "response":  response.choices[0].message.content.strip(),
            "latency_s": round(latency, 3),
        }
    except Exception as e:
        return {
            "status":   "error",
            "base_url": INFERENCE_BASE_URL,
            "error":    str(e),
        }


if __name__ == "__main__":
    result = check_connection()
    for k, v in result.items():
        print(f"  {k}: {v}")
