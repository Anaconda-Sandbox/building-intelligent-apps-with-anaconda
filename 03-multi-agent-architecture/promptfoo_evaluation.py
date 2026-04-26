"""
promptfoo_evaluation.py

Module 03 — Multi-Agent Architecture (prompt evaluation).

promptfoo is a CLI tool, not a Python library. There is no `from promptfoo import`
API. This script generates a promptfoo config YAML from the agent context and
runs the evaluation via `npx promptfoo eval`.

Requirements:
    Node.js 18+ (for npx)
    promptfoo installed globally or via npx (no install needed with npx)

Run:
    python promptfoo_evaluation.py

Or run the evaluation directly after config is generated:
    npx promptfoo eval --config promptfoo_config.yaml
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

# ── Path resolution ───────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02-your-first-agent"))
sys.path.insert(0, str(ROOT / "01-data-sources"))

from agent_tools import build_agent_context

DATA_PATH = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
if not DATA_PATH.exists():
    DATA_PATH = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"

CONFIG_PATH = Path(__file__).parent / "promptfoo_config.yaml"


# ── Config generation ─────────────────────────────────────────────────────────

def build_promptfoo_config(context: dict) -> dict:
    """
    Build a promptfoo evaluation config from the agent context.

    Tests that the agent:
      1. Mentions the transit depth correctly
      2. Identifies the phase window
      3. Avoids hallucinating data quality issues that aren't present
    """
    context_str = json.dumps(context, indent=2)
    depth_pct   = context["anomaly_detection"]["transit_depth_pct"]
    n_anomalies = context["anomaly_detection"]["n_anomalous_points"]

    return {
        "prompts": [
            {
                "id": "transit-summary",
                "raw": (
                    "You are an astrophysics data analyst. "
                    "Given the following lightcurve analysis context, summarize "
                    "the planetary transit signal in 2-3 sentences for a general audience.\n\n"
                    f"Context:\n{context_str}"
                ),
            }
        ],
        "providers": [
            {"id": "openai:gpt-4o-mini"},  # swap to your provider
        ],
        "tests": [
            {
                "description": "Mentions transit depth",
                "assert": [
                    {
                        "type": "contains",
                        "value": str(round(depth_pct, 2)),
                    }
                ],
            },
            {
                "description": "Mentions anomaly count",
                "assert": [
                    {
                        "type": "contains",
                        "value": str(n_anomalies),
                    }
                ],
            },
            {
                "description": "Does not hallucinate null data quality issues",
                "assert": [
                    {
                        "type": "not-contains",
                        "value": "missing values",
                    }
                ],
            },
            {
                "description": "Response is concise (under 300 words)",
                "assert": [
                    {
                        "type": "javascript",
                        "value": "output.split(' ').length < 300",
                    }
                ],
            },
        ],
    }


def check_node() -> bool:
    """Return True if Node.js is available for npx."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main() -> None:
    if not DATA_PATH.exists():
        print(
            "Error: wasp18b_lightcurve.csv not found.\n\n"
            "Quick fix:\n"
            "  cp 100-example-applications/polars_demo/wasp18b_lightcurve.csv "
            "01-data-sources/\n"
        )
        sys.exit(1)

    print(f"Building agent context from: {DATA_PATH.name}")
    context = build_agent_context(str(DATA_PATH))

    config = build_promptfoo_config(context)

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"promptfoo config written to: {CONFIG_PATH}\n")
    print("── Evaluation config preview ─────────────────────────────────────\n")
    print(yaml.dump(config, default_flow_style=False, sort_keys=False))

    if not check_node():
        print(
            "Node.js not found — skipping live evaluation.\n\n"
            "To run the evaluation manually:\n"
            "  1. Install Node.js: https://nodejs.org\n"
            f"  2. npx promptfoo eval --config {CONFIG_PATH}\n"
            "  3. npx promptfoo view  (opens results in browser)\n"
        )
        return

    print("Running: npx promptfoo eval ...\n")
    try:
        subprocess.run(
            ["npx", "promptfoo", "eval", "--config", str(CONFIG_PATH)],
            check=True,
        )
        print("\nEvaluation complete. View results with: npx promptfoo view")
    except subprocess.CalledProcessError as exc:
        print(f"promptfoo eval failed (exit {exc.returncode}).")
        print(f"Check {CONFIG_PATH} and re-run manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
