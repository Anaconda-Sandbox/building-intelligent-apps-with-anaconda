#!/usr/bin/env bash
# run_demo.sh
#
# Module 02 — Your First Agent
# One-command setup, verify, and run.
#
# Prerequisites (fresh clone):
#   git submodule update --init --recursive
#   conda env create -f 02-your-first-agent/environment.yml
#   conda activate first-agent
#
# Usage:
#   bash run_demo.sh              # pipeline demo, no LLM required
#   bash run_demo.sh --llm        # live LangGraph agent (requires an endpoint)
#   bash run_demo.sh --notebook   # launch Jupyter instead of the CLI script
#   bash run_demo.sh --check      # environment + data check only, don't run
#
# Inference endpoint (--llm mode, all optional):
#   INFERENCE_BASE_URL   default: http://localhost:8080/v1  (AI Navigator)
#   INFERENCE_API_KEY    default: not-needed
#   INFERENCE_MODEL      default: default

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
echo -e "${BOLD}${CYAN}║      Module 02 — Your First Agent                           ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Locate repo root ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Handle being called from repo root or from 02-your-first-agent/
if [[ "$(basename "$SCRIPT_DIR")" == "02-your-first-agent" ]]; then
  MODULE_DIR="$SCRIPT_DIR"
  ROOT_DIR="$(dirname "$SCRIPT_DIR")"
else
  ROOT_DIR="$SCRIPT_DIR"
  MODULE_DIR="$SCRIPT_DIR/02-your-first-agent"
fi

# ── Step 1: Environment check ─────────────────────────────────────────────────
step "Step 1/4 — Environment check"

EXPECTED_ENV="first-agent"

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

# Resolve Python from the conda env's prefix directly.
# bash run_demo.sh inherits CONDA_PREFIX from the parent shell's activation,
# so this is reliable even when 'python3' on PATH points at a system interpreter.
if [[ -n "${CONDA_PREFIX:-}" && -x "$CONDA_PREFIX/bin/python" ]]; then
  PYTHON="$CONDA_PREFIX/bin/python"
elif command -v conda &>/dev/null; then
  PYTHON="$(conda run -n "$EXPECTED_ENV" python -c 'import sys; print(sys.executable)' 2>/dev/null)"
else
  PYTHON="$(command -v python3)"
fi

if [[ ! -x "${PYTHON:-}" ]]; then
  err "Cannot find Python for conda env '$EXPECTED_ENV'"
  echo "     Try: conda activate $EXPECTED_ENV"
  exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
  ok "Python $PY_VER ($PYTHON)"
else
  err "Python 3.10+ required, found $PY_VER"
  exit 1
fi

# Package check
MISSING=()
for pkg in polars pydantic langchain_core langgraph langchain_openai sklearn; do
  if "$PYTHON" -c "import $pkg" 2>/dev/null; then
    :
  else
    MISSING+=("$pkg")
  fi
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
  ok "All required packages present"
  "$PYTHON" -c "
import polars, pydantic, langgraph
import importlib.metadata
print(f'  polars    {polars.__version__}')
print(f'  langgraph {importlib.metadata.version(\"langgraph\")}')
print(f'  pydantic  {pydantic.__version__}')
  "
else
  err "Missing packages: ${MISSING[*]}"
  echo ""
  echo "     Python in use : $PYTHON"
  echo "     Expected env  : $EXPECTED_ENV"
  echo ""
  echo "     Reinstall the environment:"
  echo "       conda env create -f $MODULE_DIR/environment.yml"
  echo "       conda activate $EXPECTED_ENV"
  exit 1
fi

# ── Step 2: Data check ────────────────────────────────────────────────────────
step "Step 2/4 — Data check"

DATA_PATH="$ROOT_DIR/01-data-sources/wasp18b_lightcurve.csv"
FALLBACK_PATH="$ROOT_DIR/100-example-applications/polars_demo/wasp18b_lightcurve.csv"
POLARS_DEMO_DIR="$ROOT_DIR/100-example-applications/polars_demo"

# ── Submodule check ───────────────────────────────────────────────────────────
# wasp18b_lightcurve.csv lives in the polars_demo git submodule.
# If the submodule wasn't initialised on clone, the directory exists but is empty.
if [[ -d "$POLARS_DEMO_DIR" && -z "$(ls -A "$POLARS_DEMO_DIR" 2>/dev/null)" ]]; then
  err "polars_demo submodule is empty — git submodule was not initialised"
  echo ""
  echo "     Fix (run from the repo root):"
  echo "       git submodule update --init --recursive"
  echo ""
  echo "     Then re-run this script."
  exit 1
fi

if [[ ! -d "$POLARS_DEMO_DIR" ]]; then
  warn "polars_demo directory not found — may be a partial clone"
fi

if [[ -f "$DATA_PATH" ]]; then
  ROWS=$(wc -l < "$DATA_PATH")
  ok "wasp18b_lightcurve.csv — $((ROWS - 1)) rows"
elif [[ -f "$FALLBACK_PATH" ]]; then
  warn "CSV found in polars_demo — copying to 01-data-sources/"
  cp "$FALLBACK_PATH" "$DATA_PATH"
  ok "wasp18b_lightcurve.csv copied to 01-data-sources/"
else
  err "wasp18b_lightcurve.csv not found"
  echo ""
  echo "     Most likely cause: submodule not initialised. Fix:"
  echo "       git submodule update --init --recursive"
  echo ""
  echo "     Or fetch the CSV directly:"
  echo "       python3 $ROOT_DIR/100-example-applications/polars_demo/fetch_data.py"
  exit 1
fi

# ── Step 3: Pipeline smoke test ───────────────────────────────────────────────
step "Step 3/4 — Pipeline smoke test"

SMOKE=$("$PYTHON" - <<'PYEOF'
import sys
from pathlib import Path

script_dir = Path(__file__ if "__file__" in dir() else ".").resolve()
# resolve paths relative to this heredoc's cwd
import os
cwd = Path(os.getcwd())
root = cwd if (cwd / "01-data-sources").exists() else cwd.parent

sys.path.insert(0, str(root / "02-your-first-agent"))
sys.path.insert(0, str(root / "01-data-sources"))

from ingestion import SCHEMA, load_lightcurve, validate_lightcurve
from agent_tools import run_feature_anomaly_pipeline, build_agent_context

data_path = root / "01-data-sources" / "wasp18b_lightcurve.csv"
if not data_path.exists():
    data_path = root / "100-example-applications" / "polars_demo" / "wasp18b_lightcurve.csv"

df     = load_lightcurve(data_path, SCHEMA)
report = validate_lightcurve(df)
result = run_feature_anomaly_pipeline(df)
td     = result["transit_depth"]
tw     = result["transit_window"]

print(f"rows={len(df)}")
print(f"nulls={sum(report.nulls.values())}")
print(f"flux_std={report.flux_std:.8f}")
print(f"n_anomalies={tw['n_anomalous_points']}")
print(f"transit_depth_pct={td*100:.4f}" if td else "transit_depth_pct=None")
print(f"transit_start={tw['transit_start']:+.5f}" if tw['transit_start'] else "transit_start=None")
PYEOF
)

# Parse and display results
while IFS='=' read -r key val; do
  case $key in
    rows)               ok "rows loaded         : $val" ;;
    nulls)              [[ "$val" == "0" ]] && ok "nulls               : $val" || warn "nulls: $val (unexpected)" ;;
    flux_std)           ok "flux_std            : $val" ;;
    n_anomalies)        ok "anomalies detected  : $val" ;;
    transit_depth_pct)  ok "transit depth       : ${val}%" ;;
    transit_start)      ok "transit start       : $val" ;;
  esac
done <<< "$SMOKE"

ok "Pipeline smoke test passed"

[[ "$CHECK_ONLY" == true ]] && { echo -e "\n${GREEN}Environment check complete.${RESET}"; exit 0; }

# ── Step 4: Run ───────────────────────────────────────────────────────────────
step "Step 4/4 — Running demo"

if [[ "$RUN_NOTEBOOK" == true ]]; then
  echo ""
  echo "  Launching Jupyter. Open 02_your_first_agent.ipynb and press Run All."
  echo ""
  cd "$MODULE_DIR"
  jupyter lab 02_your_first_agent.ipynb

elif [[ "$RUN_LLM" == true ]]; then
  echo ""
  echo "  Running live LLM agent — $(date)"
  INFERENCE_BASE_URL="${INFERENCE_BASE_URL:-http://localhost:8080/v1}"
  echo "  Endpoint: $INFERENCE_BASE_URL"
  echo ""

  # Check if AI Navigator is up when using default
  if [[ "$INFERENCE_BASE_URL" == "http://localhost:8080/v1" ]]; then
    if ! curl -sf --max-time 2 "http://localhost:8080/health" >/dev/null 2>&1; then
      warn "AI Navigator does not appear to be running at localhost:8080"
      echo ""
      echo "     Start AI Navigator, load a model, and start the API server."
      echo "     Or point at another endpoint:"
      echo "       export INFERENCE_BASE_URL=https://api.anthropic.com/v1"
      echo "       export INFERENCE_API_KEY=sk-ant-..."
      echo "       export INFERENCE_MODEL=claude-haiku-4-5-20251001"
      echo "       bash run_demo.sh --llm"
      echo ""
      read -rp "  Continue anyway? [y/N] " CONT
      [[ "${CONT,,}" != "y" ]] && exit 0
    fi
  fi

  cd "$ROOT_DIR"
  "$PYTHON" "$MODULE_DIR/langchain_agent_example.py"

else
  # Default: no-LLM pipeline demo — always works
  echo ""
  echo "  Running pipeline demo (no LLM required)..."
  echo "  To run with a live agent: bash run_demo.sh --llm"
  echo ""
  cd "$ROOT_DIR"
  "$PYTHON" "$MODULE_DIR/agent_example.py"
fi