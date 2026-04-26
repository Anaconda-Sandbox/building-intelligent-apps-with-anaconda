# 06 — App Architecture

**Estimated time:** 7 minutes  
**Prerequisites:** `03-multi-agent-architecture` — the `LightcurveAnalysisFlow` is extended here, not replaced.

---

## What this module covers

Module 03 built a pipeline that works. This module makes it production-grade: something that keeps running, tells you when it's misbehaving, and degrades gracefully when things go wrong rather than failing silently.

Three additions to the Module 03 flow, each a single decorator or step:

```
Module 03                          Module 06
─────────────────────────────      ────────────────────────────────────────
LightcurveAnalysisFlow             HarnesssedLightcurveFlow
  start → ingest → analyze           start → ingest → analyze
          @conda per step              @conda + @retry + @catch per step
          @retry on analyze            + evaluate step (assertions as CI)
                                       + @card on evaluate (observability)
                                     → join → end
                                       @card on end (run summary)
```

The flow code from Module 03 is unchanged. These are additive decorators and one new step.

---

## The three patterns

### 1. Harness — `@catch` for graceful degradation

`@retry` (already in Module 03) handles transient failures by retrying. `@catch` handles failures that can't be recovered — it catches the exception, stores it as an artifact, and lets the flow continue rather than halt. The difference:

- `@retry` → "try again, the problem might go away"
- `@catch` → "this target failed, record why, keep processing the others"

Without `@catch`, one bad target (malformed CSV, API timeout that exhausts retries) kills the entire `foreach` run including the targets that would have succeeded.

### 2. Eval-as-CI — `evaluate` step with Pydantic assertions

An `evaluate` step runs after `analyze`. It receives the `ValidationReport` and the agent's classification result and runs assertions against them. If assertions fail, the step raises — which becomes a visible failure in the Metaflow UI rather than a silent wrong answer propagating downstream.

This is the "evals as CI" pattern: assertions on pipeline output treated exactly like unit tests, running on every execution, surfacing failures before anyone acts on the results.

### 3. Observability — `@card` for run-level visibility

`@card` on the `evaluate` step produces a per-target HTML report showing validation stats, anomaly detection results, and the agent's classification with confidence score. `@card` on the `end` step produces a run summary across all targets.

Cards don't change flow behavior. If card generation fails, the flow continues — they're safe in production.

---

## Module structure

```
06-app-architecture/
├── README.md                              ← this file
├── environment.yml                        ← extends Module 03 env
├── flows/
│   └── harnessed_lightcurve_flow.py      ← the extended FlowSpec
├── evals/
│   └── assertions.py                     ← assertion functions (importable + testable)
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
