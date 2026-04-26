"""
agent_example.py

The simplest entry point for Module 02. No LLM required.

Builds and prints the structured agent context from the WASP-18 b lightcurve,
then shows a completion card you can screenshot at the booth.

Run from anywhere inside the repo:

    python 02-your-first-agent/agent_example.py

To run with a live LLM agent, see langchain_agent_example.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Path resolution ───────────────────────────────────────────────────────────
# Works whether you run from the repo root, from 02-your-first-agent/, or
# from anywhere else on the machine — no fragile relative paths.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02-your-first-agent"))
sys.path.insert(0, str(ROOT / "01-data-sources"))

from agent_tools import build_agent_context

# Primary location; fall back to the polars_demo copy if 01-data-sources/
# doesn't have it yet (common if Module 01 setup hasn't been run).
DATA_PATH = ROOT / "01-data-sources" / "wasp18b_lightcurve.csv"
if not DATA_PATH.exists():
    DATA_PATH = ROOT / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"


def main() -> None:
    if not DATA_PATH.exists():
        print(
            "Error: wasp18b_lightcurve.csv not found.\n"
            "Expected at: 01-data-sources/wasp18b_lightcurve.csv\n\n"
            "Quick fix:\n"
            "  cp 100-example-applications/polars_demo/wasp18b_lightcurve.csv "
            "01-data-sources/\n"
            "Or fetch a fresh copy:\n"
            "  python 100-example-applications/polars_demo/fetch_data.py"
        )
        sys.exit(1)

    print(f"Building agent context for: {DATA_PATH.name}\n")

    context = build_agent_context(str(DATA_PATH))

    print("── Agent context ─────────────────────────────────────────────────\n")
    print(json.dumps(context, indent=2))

    print("""
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 02 COMPLETE                       ║
║                                                              ║
║  Your First Agent                                            ║
║  Pipeline functions registered. Agent context built.         ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
