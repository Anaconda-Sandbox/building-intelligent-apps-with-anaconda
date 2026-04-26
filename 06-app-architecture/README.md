# 06 — App Architecture

**Estimated time:** 7 minutes  
**Prerequisites:** `03-multi-agent-architecture` — the `LightcurveAnalysisFlow` is extended here, not replaced.

---

## What this module covers

Module 03 built a pipeline that works. This module makes it production-grade: something that keeps running, tells you when it's misbehaving, and degrades gracefully when things go wrong rather than failing silently.

Three additions to the Module 03 flow, each a single decorator or step, plus a new `vectordb/` module:

```
Module 03                          Module 06
─────────────────────────────      ────────────────────────────────────────
LightcurveAnalysisFlow             HarnessedLightcurveFlow
  start → ingest → analyze           start → ingest → analyze
          @conda per step              @conda + @retry + @catch per step
          @retry on analyze            + memory retrieval before inference
                                       + memory storage after inference
                                       + evaluate step (assertions as CI)
                                       + @card on evaluate (observability)
                                     → join → end
                                       @card on end (run summary)
```

The flow code from Module 03 is unchanged. These are additive decorators, one new step, and one new module.

---

## The four patterns

### 1. Harness — `@catch` for graceful degradation

`@retry` (already in Module 03) handles transient failures by retrying. `@catch` handles failures that can't be recovered — it catches the exception, stores it as an artifact, and lets the flow continue rather than halt.

### 2. Eval-as-CI — `evaluate` step with Pydantic assertions

An `evaluate` step runs after `analyze` on every execution. It calls assertion functions from `evals/assertions.py` — plain Python functions, testable with pytest, no Metaflow dependency. Critical failures raise `AssertionError`. Non-critical become stored warnings.

### 3. Observability — `@card` for run-level visibility

`@card` on `evaluate` produces a per-target HTML report. `@card` on `end` produces a run-level summary across all targets. Cards don't affect flow behavior — safe in production.

### 4. Agent memory — DuckDB vector store

The Module 03 agent is stateless. The `vectordb/memory_store.py` module stores embeddings of past results in a DuckDB file. Before each inference call, the `analyze` step retrieves the k most similar past results and injects them into the agent's context. The agent improves over runs.

**Why DuckDB:** embedded, no server, single portable file. Compatible with `conda-pack` for air-gapped deployment. See the comparison table in the notebook for when pgvector, MongoDB Atlas, or Neo4j Vector are better choices.

---

## Module structure

```
06-app-architecture/
├── README.md                              ← this file
├── environment.yml                        ← extends Module 03 env, adds duckdb
├── flows/
│   └── harnessed_lightcurve_flow.py      ← the extended FlowSpec
├── evals/
│   └── assertions.py                     ← assertion functions (importable + testable)
├── vectordb/
│   └── memory_store.py                   ← DuckDB-backed agent memory store
├── tests/
│   └── test_assertions.py                ← pytest suite for assertions
└── 06_app_architecture.ipynb             ← narrated demo (7 min, pre-run)
```

---

## Quick start

```bash
# Reuse the Module 03 environment — it has everything needed
conda activate multi-agent

# Or create fresh
conda env create -f environment.yml
conda activate app-architecture

export ANTHROPIC_API_KEY=your_key   # or INFERENCE_BASE_URL for any endpoint

# Run the harnessed flow
python flows/harnessed_lightcurve_flow.py run --targets wasp18b,wasp12b,bad_target

# View the card from the last run
python flows/harnessed_lightcurve_flow.py card view end

# Inspect results with Client API
python -c "
from metaflow import Flow
run = Flow('HarnessedLightcurveFlow').latest_run
print(run.data.eval_summary)
"
```
