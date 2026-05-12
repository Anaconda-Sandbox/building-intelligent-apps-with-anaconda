#!/usr/bin/env bash
# run_demo.sh
#
# Module 06 — App Architecture
# Proves the combined Metaflow + LangGraph harness works in under 7 minutes.
#
# Prerequisites (fresh clone):
#   git submodule update --init --recursive
#   conda env create -f 06-app-architecture/environment.yml
#   conda activate app-architecture
#   python -m ipykernel install --user \
#       --name app-architecture \
#       --display-name "Python 3 (app-architecture)"
#
# Usage:
#   bash run_demo.sh              # assertions + memory smoke test (no LLM, ~2 min)
#   bash run_demo.sh --llm        # full harnessed flow with live agent (~5 min)
#   bash run_demo.sh --notebook   # open the narrated notebook in Jupyter
#   bash run_demo.sh --check      # environment check only, don't run
#
# Inference endpoint (--llm mode):
#   ANTHROPIC_API_KEY            set this for Anthropic (recommended)
#   INFERENCE_BASE_URL           default: http://localhost:8080/v1 (AI Navigator)
#   INFERENCE_API_KEY            default: not-needed
#   INFERENCE_MODEL              default: default

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; }
err()  { echo -e "  ${RED}✗${RESET}  $1"; }
step() { echo -e "\n${BOLD}${BLUE}$1${RESET}"; }

# ── Args ──────────────────────────────────────────────────────────────────────
RUN_LLM=false
RUN_NOTEBOOK=false
CHECK_ONLY=false

for arg in "$@"; do
  case $arg in
    --llm)      RUN_LLM=true ;;
    --notebook) RUN_NOTEBOOK=true ;;
    --check)    CHECK_ONLY=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║  🛸  Building Intelligent Apps with Anaconda                ║${RESET}"
echo -e "${BOLD}${CYAN}║      Module 06 — App Architecture                           ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Locate module root ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "06-app-architecture" ]]; then
  MODULE_DIR="$SCRIPT_DIR"
  ROOT_DIR="$(dirname "$SCRIPT_DIR")"
else
  ROOT_DIR="$SCRIPT_DIR"
  MODULE_DIR="$SCRIPT_DIR/06-app-architecture"
fi

# ── Step 1: Environment check ─────────────────────────────────────────────────
step "Step 1/5 — Environment check"

EXPECTED_ENV="app-architecture"
CONDA_ENV="${CONDA_DEFAULT_ENV:-}"

if [[ -z "$CONDA_ENV" ]]; then
  err "No conda environment is active."
  echo ""
  echo "     Run:  conda activate $EXPECTED_ENV"
  exit 1
elif [[ "$CONDA_ENV" != "$EXPECTED_ENV" ]]; then
  err "Wrong conda env active: '$CONDA_ENV' (expected: '$EXPECTED_ENV')"
  echo ""
  echo "     Run:  conda activate $EXPECTED_ENV"
  echo ""
  echo "     If the environment doesn't exist yet:"
  echo "       conda env create -f $MODULE_DIR/environment.yml"
  echo "       conda activate $EXPECTED_ENV"
  exit 1
else
  ok "conda env: $EXPECTED_ENV ✓"
fi

# Resolve Python from CONDA_PREFIX — avoids system Python on macOS
if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
  PYTHON="$CONDA_PREFIX/bin/python"
elif command -v conda &>/dev/null; then
  PYTHON="$(conda run -n "$EXPECTED_ENV" python -c 'import sys; print(sys.executable)' 2>/dev/null)"
else
  PYTHON="$(command -v python3)"
fi

if [[ ! -x "${PYTHON:-}" ]]; then
  err "Cannot find Python for conda env '$EXPECTED_ENV'"
  exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1 | awk '{print $2}')
ok "Python $PY_VER ($PYTHON)"

# Package check
MISSING=()
for pkg in polars pydantic metaflow duckdb langgraph; do
  if "$PYTHON" -c "import $pkg" 2>/dev/null; then
    :
  else
    MISSING+=("$pkg")
  fi
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
  ok "All required packages present"
  "$PYTHON" -c "
import metaflow, duckdb, langgraph, polars
import importlib.metadata
print(f'  metaflow  {metaflow.__version__}')
print(f'  duckdb    {duckdb.__version__}')
print(f'  langgraph {importlib.metadata.version(\"langgraph\")}')
print(f'  polars    {polars.__version__}')
  "
else
  err "Missing packages: ${MISSING[*]}"
  echo ""
  echo "     Reinstall:"
  echo "       conda env create -f $MODULE_DIR/environment.yml"
  echo "       conda activate $EXPECTED_ENV"
  exit 1
fi

# ── Step 2: Data check ────────────────────────────────────────────────────────
step "Step 2/5 — Data check"

DATA_PATH="$ROOT_DIR/01-data-sources/wasp18b_lightcurve.csv"
FALLBACK_PATH="$ROOT_DIR/100-example-applications/polars_demo/wasp18b_lightcurve.csv"
POLARS_DEMO_DIR="$ROOT_DIR/100-example-applications/polars_demo"

if [[ -d "$POLARS_DEMO_DIR" && -z "$(ls -A "$POLARS_DEMO_DIR" 2>/dev/null)" ]]; then
  err "polars_demo submodule is empty — git submodule was not initialised"
  echo ""
  echo "     Fix:  git submodule update --init --recursive"
  exit 1
fi

if [[ -f "$DATA_PATH" ]]; then
  ROWS=$(wc -l < "$DATA_PATH")
  ok "wasp18b_lightcurve.csv — $((ROWS - 1)) rows"
elif [[ -f "$FALLBACK_PATH" ]]; then
  warn "CSV found in polars_demo — copying to 01-data-sources/"
  cp "$FALLBACK_PATH" "$DATA_PATH"
  ok "wasp18b_lightcurve.csv copied"
else
  err "wasp18b_lightcurve.csv not found"
  echo "     Fix:  git submodule update --init --recursive"
  exit 1
fi

[[ "$CHECK_ONLY" == true ]] && {
  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${GREEN}║  🛸  WASP-18 b  ·  MODULE 06 READY                         ║${RESET}"
  echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
  echo -e "${BOLD}${GREEN}║  App Architecture                                            ║${RESET}"
  echo -e "${BOLD}${GREEN}║  Environment verified. Harness components ready.            ║${RESET}"
  echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
  echo -e "${BOLD}${GREEN}║  Next:  bash run_demo.sh          (assertions + memory)     ║${RESET}"
  echo -e "${BOLD}${GREEN}║         bash run_demo.sh --llm    (full harnessed flow)     ║${RESET}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""
  exit 0
}

[[ "$RUN_NOTEBOOK" == true ]] && {
  echo ""
  echo "  Launching Jupyter. Open 06_app_architecture.ipynb and press Run All."
  echo ""
  cd "$MODULE_DIR"
  jupyter lab 06_app_architecture.ipynb
  exit 0
}

# ── Step 3: Eval-as-CI — prove assertions work ────────────────────────────────
step "Step 3/5 — Eval-as-CI: assertion suite"
echo ""
echo "  The assertion suite in evals/assertions.py runs on every flow execution."
echo "  These are plain Python functions — no Metaflow dependency, pytest-testable."
echo ""

cd "$MODULE_DIR"
"$PYTHON" -c "
import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock
from evals.assertions import run_all_assertions

# ── Good result: all assertions should pass ───────────────────────────────────
good_report = MagicMock()
good_report.nulls             = {'PHASE': 0, 'LC_DETREND': 0, 'MODEL_INIT': 0}
good_report.flux_std          = 0.00031482
good_report.phase_range       = (-0.496, 0.496)
good_report.duplicate_phases  = 0

good_result = {
    'classification':        'confirmed_transit',
    'confidence':            0.91,
    'transit_depth_pct':     1.014,
    'reasoning_summary':     'Clear hot Jupiter transit consistent with WASP-18 b literature values.',
    'recommended_next_steps': ['Fit parametric model'],
}

print('  Running assertions on good result (wasp18b):')
good_eval = run_all_assertions(good_report, good_result)
for c in good_eval['results']:
    icon = '✓' if c['passed'] else ('✗' if c['critical'] else '⚠')
    print(f\"    {icon}  {c['name']:<35}{c['detail']}\")
print(f\"  Result: {good_eval['n_passed']}/8 passed — eval_result.passed = {good_eval['passed']}\")

print()

# ── Bad result: confidence out of range, reasoning too short ──────────────────
bad_result = {
    'classification':        'confirmed_transit',
    'confidence':            1.7,          # out of range
    'transit_depth_pct':     0.0001,       # implausibly shallow
    'reasoning_summary':     'OK',         # too short
    'recommended_next_steps': [],
}

print('  Running assertions on bad result (simulated bad target):')
bad_eval = run_all_assertions(good_report, bad_result)
for c in bad_eval['results']:
    icon = '✓' if c['passed'] else ('✗' if c['critical'] else '⚠')
    print(f\"    {icon}  {c['name']:<35}{c['detail']}\")
print(f\"  Result: {bad_eval['n_passed']}/8 passed — critical failures: {bad_eval['critical_failures']}\")
print()
print('  In the flow: critical failures raise AssertionError in the evaluate step.')
print('  Non-critical failures become warnings stored as artifacts.')
"

ok "Eval-as-CI demonstrated — assertions catch bad outputs before they propagate"

# ── Step 4: DuckDB memory — prove store/retrieve/format works ─────────────────
step "Step 4/5 — Agent memory: DuckDB vector store"
echo ""
echo "  The memory store persists results across Metaflow runs."
echo "  Before inference: retrieves similar past results → injects as context."
echo "  After inference:  stores the new result → available on next run."
echo ""

"$PYTHON" -c "
import sys, tempfile
from pathlib import Path
sys.path.insert(0, '.')
from vectordb.memory_store import AgentMemoryStore

# Use a temp file so demo runs don't pollute the real memory store
db_path = 'memory/demo_smoke_test.duckdb'
store = AgentMemoryStore(db_path)

# Store three past results (simulating three previous runs)
past = [
    ('wasp18b',     {'classification': 'confirmed_transit',  'confidence': 0.91, 'transit_depth_pct': 1.014,
                     'reasoning_summary': 'Clear hot Jupiter. Transit depth and anomaly clustering consistent with WASP-18 b.'},
                    {'flux_std': 0.000314, 'n_anomalies': 78, 'phase_span': 0.99}),
    ('wasp12b',     {'classification': 'confirmed_transit',  'confidence': 0.88, 'transit_depth_pct': 1.41,
                     'reasoning_summary': 'Confirmed transit. Deeper than WASP-18b, consistent with larger radius.'},
                    {'flux_std': 0.000289, 'n_anomalies': 91, 'phase_span': 0.99}),
    ('hot_jupiter_3', {'classification': 'candidate_transit', 'confidence': 0.61, 'transit_depth_pct': 0.87,
                       'reasoning_summary': 'Possible transit. Signal-to-noise marginal — follow-up recommended.'},
                    {'flux_std': 0.000198, 'n_anomalies': 34, 'phase_span': 0.97}),
]

print('  Storing 3 past results...')
for target, result, summary in past:
    rid = store.add(target=target, result=result, report_summary=summary)
    print(f'    stored {target} → {rid}')

print(f'  Store now contains {store.count()} records: {store.targets()}')
print()

# Retrieve similar results for a new target
new_summary = {'flux_std': 0.000301, 'n_anomalies': 65, 'phase_span': 0.98}
placeholder  = {'classification': '', 'confidence': 0.0, 'transit_depth_pct': 0.0}
similar = store.retrieve_similar(placeholder, new_summary, k=3, exclude_target='unknown_hj_4')
similar = [s for s in similar if s['similarity'] > 0.3]

print(f'  Retrieved {len(similar)} similar past results for new target (unknown_hj_4):')
for s in similar:
    print(f\"    {s['target']:<16} similarity={s['similarity']:.2f}  {s['classification']}\")

print()
context = store.format_context(similar)
print('  Memory context injected into agent system prompt:')
for ln in context.split('\n'):
    print(f'    {ln}')

store.close()

# Clean up the smoke test file
import os
try:
    os.remove(db_path)
except FileNotFoundError:
    pass
print()
print('  The real memory store (memory/lightcurve_memory.duckdb) accumulates')
print('  across runs — the agent improves over time without retraining.')
"

ok "DuckDB memory store demonstrated — store, retrieve, and context injection all working"

# ── Step 5: Run or describe the harnessed flow ────────────────────────────────
step "Step 5/5 — Harnessed flow"
echo ""

if [[ "$RUN_LLM" == true ]]; then
  echo "  Running HarnessedLightcurveFlow with live LangGraph agent..."
  echo "  Three targets: wasp18b (good), wasp12b (good), bad_target (deliberate failure)"
  echo ""
  echo "  Watch for:"
  echo "    @catch storing bad_target ingest error — flow continues"
  echo "    LangGraph checkpointing agent state at each superstep"
  echo "    evaluate step running assertions on every target"
  echo "    2/3 passing — partial results, not zero results"
  echo ""

  # Check inference endpoint
  if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    ok "Anthropic API key set"
  elif [[ -n "${INFERENCE_BASE_URL:-}" ]]; then
    ok "Inference endpoint: $INFERENCE_BASE_URL"
    if [[ "$INFERENCE_BASE_URL" == "http://localhost:8080/v1" ]]; then
      if ! curl -sf --max-time 2 "http://localhost:8080/health" >/dev/null 2>&1; then
        warn "AI Navigator doesn't appear to be running at localhost:8080"
        echo ""
        echo "     Start AI Navigator, load a model, start the API server."
        echo "     Or use Anthropic: export ANTHROPIC_API_KEY=sk-ant-..."
        echo ""
        read -rp "  Continue anyway? [y/N] " CONT
        [[ "${CONT,,}" != "y" ]] && exit 0
      fi
    fi
  else
    warn "No inference endpoint configured — agent will return mock results"
    echo "     For live results:"
    echo "       export ANTHROPIC_API_KEY=sk-ant-..."
    echo "       bash run_demo.sh --llm"
    echo ""
    echo "     Continuing with mock results to demonstrate harness structure..."
    echo ""
  fi

  cd "$MODULE_DIR"
  "$PYTHON" flows/harnessed_lightcurve_flow.py run \
    --targets wasp18b,wasp12b,bad_target

else
  # Default: demonstrate assertions + memory without the full flow
  echo "  The full flow (HarnessedLightcurveFlow) combines everything above:"
  echo ""
  echo "    start"
  echo "      └─ foreach [wasp18b, wasp12b, bad_target]"
  echo "           │"
  echo "           ├─ ingest   (@catch + @retry)"
  echo "           │    Metaflow @catch: bad_target CSV not found →"
  echo "           │    exception stored as artifact, flow continues"
  echo "           │"
  echo "           ├─ analyze  (@catch + @retry + LangGraph MemorySaver)"
  echo "           │    DuckDB: retrieve similar past results → inject as context"
  echo "           │    LangGraph: checkpoint at each superstep"
  echo "           │    On @retry: resume mid-loop, not from scratch"
  echo "           │    bad_target: ingest_error detected → insufficient_data"
  echo "           │"
  echo "           └─ evaluate (@card)"
  echo "                assertions.py: 8 checks on report + result"
  echo "                Critical failures: raise AssertionError (loud)"
  echo "                Warnings: stored as artifacts (soft)"
  echo "                Card: per-target HTML report"
  echo "      │"
  echo "      ├─ join"
  echo "      └─ end  (@card)"
  echo "           Card: run-level summary — 2/3 passed"
  echo ""
  echo "  To run the full flow with a live agent:"
  echo "    export ANTHROPIC_API_KEY=sk-ant-..."
  echo "    bash run_demo.sh --llm"
fi

# ── Completion screen ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║  🛸  WASP-18 b  ·  MODULE 06 COMPLETE                      ║${RESET}"
echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
echo -e "${BOLD}${GREEN}║  App Architecture                                            ║${RESET}"
echo -e "${BOLD}${GREEN}║  Metaflow @catch  +  LangGraph durable execution            ║${RESET}"
echo -e "${BOLD}${GREEN}║  Eval-as-CI  +  DuckDB agent memory                        ║${RESET}"
echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
echo -e "${BOLD}${GREEN}║  Show this screen at the Anaconda booth to claim your prize.║${RESET}"
echo -e "${BOLD}${GREEN}║  🐍  PyCon US 2026  ·  Long Beach                          ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""