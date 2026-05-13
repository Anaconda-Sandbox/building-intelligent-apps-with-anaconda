# 03 — Multi-Agent Architecture

**Estimated time:** ~5 minutes  
**Prerequisites:** Fresh clone with submodules initialised — see below.
 
---

What's the difference between a single agent and an intelligent application? An `agent` is one component of an autonomous system. Once you add orchestration, data ingress/egress, persistence, CI/CD, multi-agent coordination, and evaluation, you're building an intelligent software system.

This module introduces a higher-level architecture:

- **LangGraph** as the orchestrator for multi-agent workflows
- **MetaFlow** for workflow versioning, reproducibility, and model lifecycle tracking
- **promptfoo** for prompt quality and model response evaluation

Module 02 built one agent with four tools. This module adds two things on top of it — without touching the tools:
 
```
┌─────────────────────────────────────────────────────┐
│          METAFLOW (infrastructure layer)            │
│  deployment · state · versioning · compute · data   │
│                                                     │
│   ┌──────────────────────────────────────────────┐  │
│   │         LANGGRAPH (agent loop layer)         │  │
│   │  graph state · tool calling · conditionals   │  │
│   │  memory · streaming · human-in-the-loop      │  │
│   └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```
# Before you start 

## Fresh clone

```bash
git clone https://github.com/Anaconda-Sandbox/building-intelligent-apps-with-anaconda
cd building-intelligent-apps-with-anaconda
git submodule update --init --recursive   # ← required: gets wasp18b_lightcurve.csv

conda env create -f 03-multi-agent-architecture/environment.yml
conda activate multi-agent

# Register the kernel so Jupyter can find it
python -m ipykernel install --user \
    --name multi-agent \
    --display-name "Python 3 (multi-agent)"
```

## Three ways to run this module

| Mode | LLM required | API key required | What you see |
|---|---|---|---|
| **1 — Metaflow** (default) | No | No | 5-step pipeline, versioned, completion screen |
| **2 — LangGraph** (`--llm`) | Local or remote | No (AI Navigator) / Yes (external) | Two-agent supervisor trace, completion screen |
| **3 — Check** (`--check`) | No | No | Environment verified, ready screen |

---


## Why LangGraph?

LangGraph is designed for stateful, multi-step agent orchestration. It is a natural fit when your system has:

- multiple agents or tools collaborating on a task
- branching workflows based on intermediate results
- long-lived state and context that must flow between steps

Use LangGraph to wire together the same underlying tools from Module 2 and Module 1, while preserving the source-of-truth pipeline in `01-data-sources/ingestion.py`.


### Mode 1 — Metaflow pipeline (no LLM, always works)

```bash
bash 03-multi-agent-architecture/run_demo.sh
```

Runs `metaflow_workflow.py` — a 5-step `FlowSpec` that loads, validates, engineers features, detects anomalies, and builds the agent context. No LLM call. Every step is versioned and independently retryable.

```
Steps: start → load_data → validate_data → feature_engineering → summarize → end
```

Ends with:
```
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 03 COMPLETE                       ║
║      Metaflow workflow: 5 steps, versioned, reproducible.   ║
╚══════════════════════════════════════════════════════════════╝
```

---

### Mode 2 — LangGraph two-agent supervisor (live LLM)

```bash
bash 03-multi-agent-architecture/run_demo.sh --llm
```

Runs `langgraph_orchestrator.py` — a `DataAgent` and `AnalysisAgent` coordinated by a LangGraph supervisor. Imports the `@tool`-decorated functions from Module 02 directly — no re-implementation.

**AI Navigator (local, no API key):**
```bash
# Start AI Navigator, load a model, start the API server — then:
bash 03-multi-agent-architecture/run_demo.sh --llm
# INFERENCE_BASE_URL defaults to http://localhost:8080/v1
```

**External endpoint:**
```bash
export INFERENCE_BASE_URL="https://api.anthropic.com/v1"
export INFERENCE_API_KEY="sk-ant-..."
export INFERENCE_MODEL="claude-haiku-4-5-20251001"
bash 03-multi-agent-architecture/run_demo.sh --llm

# vLLM (self-hosted):
export INFERENCE_BASE_URL="http://your-server:8000/v1"
export INFERENCE_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
bash 03-multi-agent-architecture/run_demo.sh --llm
```

---

### Mode 3 — Environment check only

```bash
bash 03-multi-agent-architecture/run_demo.sh --check
```

Runs all four verification steps (Python, conda env, packages, data + submodule + Module 02 files) and exits without running anything. Ends with a READY screen showing the next commands to run.

---

### Notebook

```bash
bash 03-multi-agent-architecture/run_demo.sh --notebook
# Opens 03_multi_agent_architecture.ipynb in Jupyter — press Run All
```

---

## What the script checks (all four modes)

1. **Environment** — Python 3.10+, `multi-agent` conda env, package versions (metaflow, langgraph, polars, pydantic)
2. **Data** — `polars_demo` submodule initialised, `wasp18b_lightcurve.csv` present
3. **Module 02 files** — `langchain_agent_example.py` and `agent_tools.py` present (Module 03 imports from them)
4. **Pipeline smoke test** — loads the CSV, validates, runs IsolationForest, confirms the numbers

---

## Environment

All packages install from conda-forge — no pip section required.

```bash
conda env create -f 03-multi-agent-architecture/environment.yml
conda activate multi-agent
```

| Package | Role |
|---|---|
| `metaflow>=2.18` | Workflow orchestration — `@step`, `@retry`, `FlowSpec` |
| `langgraph` | Stateful multi-agent graph orchestration |
| `langchain-core` | Core LangChain abstractions |
| `langchain-openai` | OpenAI-compatible client integration |
| `polars`, `numpy`, `scikit-learn`, `pydantic` | Data pipeline — inherited from Modules 01 and 02 |
| `ragas` | Agent output evaluation — Faithfulness, AnswerRelevancy, ContextRelevance |
| `ipykernel`, `jupyterlab` | Jupyter kernel registration and notebook interface |

---

## Files

```
03-multi-agent-architecture/
├── README.md                        ← this file
├── run_demo.sh                      ← start here
├── environment.yml                  ← conda env: multi-agent (all conda-forge)
├── langgraph_orchestrator.py        ← LangGraph two-agent supervisor
├── metaflow_workflow.py             ← Metaflow 5-step FlowSpec
└── ragas_evaluation.py              ← agent output evaluation (ragas)
```

---

## Why each tool

**LangGraph** is the agent loop — stateful graph execution, tool calling, conditional routing between agents. `DataAgent` owns the data quality gate; `AnalysisAgent` owns the science output. The supervisor routes between them.

**Metaflow** is the infrastructure layer — step versioning, artifact storage, retry logic, and the ability to move the same flow to remote compute without changing a line of code.

**ragas** evaluates the quality of the agent's output using LLM-as-judge metrics. It's a pure Python library — `conda install conda-forge::ragas` — no Node.js required. Three metrics are used:

- **Faithfulness** — are the agent's claims grounded in the context it was given? A score below 0.7 means the agent hallucinated facts not present in the pipeline data.
- **Answer Relevancy** — does the agent's answer actually address the question?
- **Context Relevance** — was the retrieved context useful for producing the answer?

```bash
# Default: evaluate a pre-built answer (ragas judge still needs an LLM endpoint)
python ragas_evaluation.py

# Live: run the LangGraph agent first, then evaluate its actual output
python ragas_evaluation.py --live
```

The evaluation uses the same `INFERENCE_BASE_URL` as the agent — AI Navigator, vLLM, or any OpenAI-compatible endpoint.

---

## Notes

`01-data-sources/ingestion.py` is the source of truth. `02-your-first-agent/agent_tools.py` is the tool layer. Module 03 adds orchestration on top — nothing in Modules 01 or 02 changes.

Module 03 imports directly from Module 02 (`langchain_agent_example.py`, `agent_tools.py`). Both modules must be present in the same repo clone.