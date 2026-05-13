# 06 — App Architecture

**Estimated time:** ~5-7 minutes
**Prerequisites:** None — all dependencies are copied locally (Option B). See `agents/`, `evals/`, `vectordb/`, and `ingestion.py`.

---

## The combined harness

Module 03 built a pipeline that works. This module makes it self-healing: something that keeps running when things go wrong, tells you when it's misbehaving, and improves over time.

The key insight is that "harness" means different things at different layers. Metaflow and LangGraph each use the term, and they're not duplicates — they operate at separate levels of the stack:

```
┌──────────────────────────────────────────────────────────────────────┐
│  METAFLOW (infrastructure harness)                                   │
│  @catch, @retry, @card, foreach, artifact versioning                 │
│  Operates outside Python — at the orchestration layer                │
│  Handles: step crashes, data failures, platform issues               │
│                                                                      │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │  LANGGRAPH (agent runtime harness)                             │ │
│   │  MemorySaver checkpointer, durable execution, thread_id        │ │
│   │  Operates inside the agent loop — at the reasoning layer       │ │
│   │  Handles: LLM timeouts, mid-loop failures, runaway agents      │ │
│   └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

Together they produce a self-healing pipeline. Every failure mode is covered at the right layer:

| Failure | Layer | Mechanism |
|---|---|---|
| LLM timeout, first call | LangGraph | Superstep checkpoint saved; on @retry, resumes mid-loop |
| LLM timeout, all retries | Metaflow | `@catch` stores exception, flow continues to `evaluate` |
| Bad CSV / missing file | Metaflow | `@catch` on `ingest`, graceful `insufficient_data` result |
| Agent returns garbage JSON | Agent code | `try/except` in `run_analysis_agent()`, safe default returned |
| Classification out of range | Eval layer | `assertions.py` catches it, `evaluate` step raises loudly |
| Runaway reasoning loop | LangGraph | `recursion_limit` terminates, `@catch` catches the error |
| Silent wrong answer | Eval layer | Confidence + depth assertions flag it as a warning |

---

## What changed from Module 03

```
Module 03                          Module 06
─────────────────────────────      ────────────────────────────────────────
LightcurveAnalysisFlow             HarnessedLightcurveFlow
  start → ingest → analyze           start → ingest → analyze
          @conda per step              @conda + @retry + @catch per step
          @retry on analyze            + LangGraph MemorySaver checkpoint
                                       + memory retrieval before inference
                                       + memory storage after inference
                                       + evaluate step (assertions as CI)
                                       + @card on evaluate (observability)
                                     → join → end
                                       @card on end (run summary)
```

The flow code from Module 03 is unchanged. Every addition is either a new decorator, a new step, or a new module.

---

## The four patterns in detail

### 1. Metaflow `@catch` — infrastructure fault tolerance

`@retry` handles transient failures by retrying. `@catch` handles permanent failures — it catches the exception after all retries are exhausted, stores it as a versioned artifact, and lets the flow continue rather than halt.

The main upside of `@catch` is that it handles all error scenarios from faulty code and faulty data to platform issues. The main downside is that your code needs to be modified so that it can tolerate faulty steps. The `analyze` step checks for `ingest_error` and produces a safe `insufficient_data` result when the upstream step failed.

### 2. LangGraph `MemorySaver` — agent-loop durable execution

If you are using LangGraph with a checkpointer, you already have durable execution enabled. You can pause and resume workflows at any point, even after interruptions or failures.

The `MemorySaver` checkpointer saves agent state at each superstep — each LLM call, each tool call. When Metaflow's `@retry` re-executes the `analyze` step, it passes the same `thread_id` (`target + run_id`) so LangGraph resumes mid-reasoning from the last saved superstep, not from the beginning of the loop.

When a graph node fails mid-execution at a given superstep, LangGraph stores pending checkpoint writes from any other nodes that completed successfully at that superstep, so that whenever execution resumes from that superstep the successful nodes are not re-run.

For local runs, `MemorySaver` is in-process only. For distributed Metaflow runs (Outerbounds, AWS Batch), swap it for `SqliteSaver` or `PostgresSaver` and ensure the checkpoint store is accessible from all worker nodes.

### 3. Eval-as-CI — `evaluate` step with assertion functions

An `evaluate` step runs after `analyze` on every execution. It calls assertion functions from `evals/assertions.py` — plain Python, no Metaflow dependency, testable with `pytest evals/`. Critical failures raise `AssertionError`. Non-critical become stored warnings in the artifact and card.

### 4. Agent memory — DuckDB vector store

The Module 03 agent is stateless. The `vectordb/memory_store.py` module stores embeddings of past results in a local DuckDB file. Before each inference call, the `analyze` step retrieves the k most similar past results and injects them into the agent's context via `memory_context`. The agent improves over runs without retraining.

Why DuckDB: embedded, no server, single portable file — compatible with `conda-pack` for air-gapped deployment. The notebook's comparison table covers when pgvector, MongoDB Atlas, and Neo4j Vector are better choices.

---

## Module structure

```
06-app-architecture/
├── README.md
├── environment.yml                        ← conda env: app-architecture (all conda-forge)
├── ingestion.py                           ← copied from Module 01 (standalone)
├── agents/
│   └── analysis_agent.py                 ← LangGraph agent + MemorySaver checkpointer
├── evals/
│   └── assertions.py                     ← assertion suite (importable + pytest-testable)
├── vectordb/
│   └── memory_store.py                   ← DuckDB-backed agent memory store
├── flows/
│   └── harnessed_lightcurve_flow.py      ← the combined Metaflow + LangGraph flow
├── memory/                               ← DuckDB file written here at runtime
└── 06_app_architecture.ipynb             ← narrated demo (7 min, pre-run)
```

---

## Quick start

```bash
conda env create -f environment.yml
conda activate app-architecture
python -m ipykernel install --user \
    --name app-architecture \
    --display-name "Python 3 (app-architecture)"

git submodule update --init --recursive
```

### Three ways to run this module

| Mode | LLM required | API key required | What you see |
|---|---|---|---|
| **Default** | No | No | Assertions + DuckDB memory demo (~2 min) |
| **`--llm`** | Local or remote | No (AI Navigator) / Yes (external) | Full harnessed flow, 3 targets (~5 min) |
| **`--notebook`** | Optional | Optional | Narrated notebook in Jupyter |
| **`--check`** | No | No | Environment check only, READY screen |

```bash
# Default — proves assertions and DuckDB memory work (no LLM needed)
bash run_demo.sh

# Full harnessed flow with live agent
export ANTHROPIC_API_KEY=sk-ant-...   # recommended
bash run_demo.sh --llm

# Or with AI Navigator (no API key, start it first)
export INFERENCE_BASE_URL=http://localhost:8080/v1
bash run_demo.sh --llm

# Narrated notebook
bash run_demo.sh --notebook

# Environment check only
bash run_demo.sh --check
```

### What the default run proves

The script runs five steps — the first four work without any LLM:

1. **Environment** — Python version, conda env, package versions (metaflow, duckdb, langgraph, polars)
2. **Data** — submodule initialised, `wasp18b_lightcurve.csv` present
3. **Eval-as-CI** — runs `run_all_assertions()` live against a good result (8/8 pass) and a bad result (confidence=1.7, critical failure caught). Shows exactly what happens in the `evaluate` step on every flow run.
4. **DuckDB memory** — stores 3 past results, retrieves similar ones for a new target, prints the formatted context string the agent would receive. Proves store → retrieve → inject works end to end.
5. **Flow structure** — prints the full step tree with annotations showing where `@catch` fires, where LangGraph checkpoints, and where assertions run. With `--llm`, runs the actual flow.

### After running with `--llm`

```bash
# View the run-level summary card
python flows/harnessed_lightcurve_flow.py card view end

# Inspect results with the Client API
python -c "
from metaflow import Flow
run = Flow('HarnessedLightcurveFlow').latest_run
print(run.data.eval_summary)
"

# Run the assertion suite standalone with pytest
pytest evals/ -v
```

---

## Environment

All packages from conda-forge. No pip section.

| Package | Role |
|---|---|
<<<<<<< HEAD
| `metaflow>=2.18` | Workflow orchestration — `@catch`, `@retry`, `@card`, `foreach` |
=======
| `metaflow>=2.18` | Workflow orchestration and env setup — `@conda`, `@catch`, `@retry`, `@card`, `foreach` |
>>>>>>> working
| `langgraph` | Agent runtime — `MemorySaver` checkpointer, durable execution |
| `anthropic` | Primary inference — Claude Haiku default |
| `openai>=1.30` | OpenAI-compatible client — AI Navigator / vLLM fallback |
| `duckdb>=0.10` | Agent memory vector store — embedded, no server |
| `polars`, `numpy`, `scikit-learn`, `pydantic` | Data pipeline |
| `pytest>=8.0` | Run `evals/assertions.py` as a test suite |
| `ipykernel`, `jupyterlab` | Jupyter kernel and notebook interface |
