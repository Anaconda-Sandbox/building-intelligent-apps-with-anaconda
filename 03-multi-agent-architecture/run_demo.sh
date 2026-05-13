#!/usr/bin/env bash
# run_demo.sh
#
# Module 03 — Multi-Agent Architecture
# One-command setup, verify, and run.
#
# Prerequisites (fresh clone):
#   git submodule update --init --recursive
#   conda env create -f 03-multi-agent-architecture/environment.yml
#   conda activate multi-agent
#   python -m ipykernel install --user --name multi-agent \
#       --display-name "Python 3 (multi-agent)"
#
# Three modes:
#
#   bash run_demo.sh              ← Metaflow pipeline (no LLM, always works)
#   bash run_demo.sh --llm        ← LangGraph two-agent supervisor (needs endpoint)
#   bash run_demo.sh --notebook   ← open notebook in Jupyter
#   bash run_demo.sh --check      ← env check only, don't run
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
echo -e "${BOLD}${CYAN}║      Module 03 — Multi-Agent Architecture                   ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Locate repo root ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "03-multi-agent-architecture" ]]; then
  MODULE_DIR="$SCRIPT_DIR"
  ROOT_DIR="$(dirname "$SCRIPT_DIR")"
else
  ROOT_DIR="$SCRIPT_DIR"
  MODULE_DIR="$SCRIPT_DIR/03-multi-agent-architecture"
fi

# ── Step 1: Environment check ─────────────────────────────────────────────────
step "Step 1/4 — Environment check"

EXPECTED_ENV="multi-agent"

# Conda env check — exit immediately if wrong env is active.
# We check this first because PYTHON is derived from the conda env.
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

# Python version check
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
for pkg in polars pydantic langgraph langchain_core metaflow; do
  if "$PYTHON" -c "import $pkg" 2>/dev/null; then
    :
  else
    MISSING+=("$pkg")
  fi
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
  ok "All required packages present"
  "$PYTHON" -c "
import metaflow, polars, pydantic
import langgraph
import importlib.metadata
print(f'  metaflow  {metaflow.__version__}')
print(f'  langgraph {importlib.metadata.version(\"langgraph\")}')
print(f'  polars    {polars.__version__}')
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

# ── Step 2: Data + submodule check ────────────────────────────────────────────
step "Step 2/4 — Data check"

DATA_PATH="$ROOT_DIR/01-data-sources/wasp18b_lightcurve.csv"
FALLBACK_PATH="$ROOT_DIR/100-example-applications/polars_demo/wasp18b_lightcurve.csv"
POLARS_DEMO_DIR="$ROOT_DIR/100-example-applications/polars_demo"

# Submodule check — same pattern as Module 02
if [[ -d "$POLARS_DEMO_DIR" && -z "$(ls -A "$POLARS_DEMO_DIR" 2>/dev/null)" ]]; then
  err "polars_demo submodule is empty — git submodule was not initialised"
  echo ""
  echo "     Fix (run from the repo root):"
  echo "       git submodule update --init --recursive"
  echo ""
  echo "     Then re-run this script."
  exit 1
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
  exit 1
fi

# Module 02 dependency check — 03 imports from 02's langchain_agent_example
M02_AGENT="$ROOT_DIR/02-your-first-agent/langchain_agent_example.py"
M02_TOOLS="$ROOT_DIR/02-your-first-agent/agent_tools.py"
if [[ -f "$M02_AGENT" && -f "$M02_TOOLS" ]]; then
  ok "Module 02 files present (langchain_agent_example.py, agent_tools.py)"
else
  err "Module 02 files not found — 03 imports from 02"
  echo "     Expected: $ROOT_DIR/02-your-first-agent/"
  exit 1
fi

# ── Step 3: Pipeline smoke test ───────────────────────────────────────────────
step "Step 3/4 — Pipeline smoke test"

SMOKE=$("$PYTHON" - <<'PYEOF'
import sys, os
from pathlib import Path

cwd = Path(os.getcwd())
root = cwd if (cwd / "01-data-sources").exists() else cwd.parent

sys.path.insert(0, str(root / "02-your-first-agent"))
sys.path.insert(0, str(root / "01-data-sources"))

from ingestion import SCHEMA, load_lightcurve, validate_lightcurve
from agent_tools import run_feature_anomaly_pipeline

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
print(f"n_anomalies={tw['n_anomalous_points']}")
print(f"transit_depth_pct={td*100:.4f}" if td else "transit_depth_pct=None")
PYEOF
)

while IFS='=' read -r key val; do
  case $key in
    rows)               ok "rows loaded         : $val" ;;
    nulls)              [[ "$val" == "0" ]] && ok "nulls               : $val" || warn "nulls: $val" ;;
    n_anomalies)        ok "anomalies detected  : $val" ;;
    transit_depth_pct)  ok "transit depth       : ${val}%" ;;
  esac
done <<< "$SMOKE"

ok "Pipeline smoke test passed — pipeline is ready for orchestration"

[[ "$CHECK_ONLY" == true ]] && {
  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${GREEN}║  🛸  WASP-18 b  ·  MODULE 03 READY                         ║${RESET}"
  echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
  echo -e "${BOLD}${GREEN}║  Multi-Agent Architecture                                    ║${RESET}"
  echo -e "${BOLD}${GREEN}║  Environment verified. Pipeline ready for orchestration.     ║${RESET}"
  echo -e "${BOLD}${GREEN}║                                                              ║${RESET}"
  echo -e "${BOLD}${GREEN}║  Next:  bash run_demo.sh          (Metaflow, no LLM)        ║${RESET}"
  echo -e "${BOLD}${GREEN}║         bash run_demo.sh --llm    (LangGraph supervisor)    ║${RESET}"
  echo -e "${BOLD}${GREEN}║  🐍  PyCon US 2026  ·  Long Beach                          ║${RESET}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""
  exit 0
}

# ── Step 4: Run ───────────────────────────────────────────────────────────────
step "Step 4/4 — Running demo"

if [[ "$RUN_NOTEBOOK" == true ]]; then
  echo ""
  echo "  Launching Jupyter. Open 03_multi_agent_architecture.ipynb and press Run All."
  echo ""
  cd "$MODULE_DIR"
  jupyter lab 03_multi_agent_architecture.ipynb

elif [[ "$RUN_LLM" == true ]]; then
  echo ""
  echo "  Running live LangGraph two-agent supervisor — $(date)"
  INFERENCE_BASE_URL="${INFERENCE_BASE_URL:-http://localhost:8080/v1}"
  echo "  Endpoint    : $INFERENCE_BASE_URL"
  echo "  Model       : ${INFERENCE_MODEL:-default}"
  echo "  Architecture: DataAgent → AnalysisAgent (LangGraph supervisor)"
  echo ""

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
  "$PYTHON" "$MODULE_DIR/langgraph_orchestrator.py"

else
  # Default: Metaflow workflow — no LLM, always works
  echo ""
  echo "  Running Metaflow pipeline (no LLM required)..."
  echo "  To run with a live two-agent supervisor: bash run_demo.sh --llm"
  echo ""
  echo "  Architecture: DataAgent + AnalysisAgent wrapped in a Metaflow FlowSpec"
  echo "  Steps: start → load_data → validate_data → feature_engineering → summarize → end"
  echo ""
  cd "$ROOT_DIR"
  "$PYTHON" "$MODULE_DIR/metaflow_workflow.py" run
fi