from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AGENT_TOOLS_PATH = ROOT / "02-your-first-agent"
if str(AGENT_TOOLS_PATH) not in sys.path:
    sys.path.append(str(AGENT_TOOLS_PATH))

from agent_tools import build_agent_context


def build_evaluation_input(filepath: str) -> dict[str, Any]:
    context = build_agent_context(filepath)
    return {
        "name": "wasp18_agent_context",
        "input": {"context": context},
        "expected_output_keys": [
            "dataset",
            "data_quality",
            "feature_engineering",
            "anomaly_detection",
        ],
    }


def main() -> None:
    try:
        from promptfoo import Prompt, LLM, run
    except ImportError as exc:
        raise ImportError(
            "promptfoo is required to run this evaluation. "
            "Install it with `pip install promptfoo`."
        ) from exc

    prompt_template = (
        "You are evaluating the quality of an autonomous data analysis workflow. "
        "Given the agent context below, generate a short summary of the detected transit and "
        "the next best action.\n\nContext:\n{context}"
    )

    evaluator = Prompt(
        name="agent-context-evaluator",
        template=prompt_template,
        input_variables=["context"],
    )

    llm = LLM("openai/gpt-4o-mini", temperature=0)
    example = build_evaluation_input("../01-data-sources/wasp18b_lightcurve.csv")

    result = run(
        prompt=evaluator,
        llm=llm,
        inputs=[example["input"]],
        run_name="wasp18-agent-evaluation",
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
