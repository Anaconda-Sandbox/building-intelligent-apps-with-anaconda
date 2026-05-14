# 05 — GPU-Accelerated Intelligence

**Estimated time:** UNKNOWN (EXPERIMENTAL)  
**Optional Prerequisites:** Completed `03-multi-agent-architecture` — the WASP-18 b pipeline and LangGraph + Metaflow patterns carry forward here unchanged.

---

## What this module covers

In `03` you built a multi-agent system with LangGraph agents orchestrated by Metaflow, running on CPU against a local or cloud LLM endpoint. Everything worked. Now ask: what happens when your pipeline needs to analyze not three light curves but three thousand, and you need answers in seconds?

This module moves the same pipeline to the NVIDIA-aligned stack:

```
03-multi-agent-architecture          05-gpu-accelerated-intelligence
─────────────────────────────        ──────────────────────────────────
LangGraph agents             →       Same agents, same tools
Metaflow orchestration       →       Same FlowSpec, same @conda steps
CPU / hosted LLM endpoint    →       Nemotron on vLLM via Brev GPU
Polars rolling windows       →       CUDA Python 1.0 kernel (rolling_features.py)
No sandbox policy            →       NemoClaw security layer
```

The agent code doesn't change. The environment does.

---

## The NVIDIA stack — what each tool actually is

**Brev** — NVIDIA's GPU provisioning platform. Not a Python library. Use the CLI or web console to get a GPU instance, then SSH or JupyterLab in. The environment comes with CUDA, Python, and Docker preconfigured. Brev requires a credit card to run this demo.

**NemoClaw** — NVIDIA's open-source sandboxed agent runtime (alpha). A TypeScript CLI plugin + Python blueprint. It controls what your agent can see, do, and where its inference requests go. You interact with it via `nemoclaw` commands, not Python imports.

**Nemotron** — NVIDIA's family of open-weight models with open training data. Accessed via HuggingFace + vLLM (local) or NVIDIA NIM endpoints (cloud). Use the `openai` client with the appropriate `base_url` — no NVIDIA-specific Python library needed.

**CUDA Python 1.0** — Direct CUDA kernel access from Python. Used in `rolling_features.py` to GPU-accelerate the rolling window feature engineering from `01-data-sources`, with an automatic CPU fallback when no GPU is available.

---

## Module structure

```
05-gpu-accelerated-intelligence/
├── README.md                               ← this file
├── CUDA-101.md                             ← CUDA concepts reference
├── environment.yml                         ← conda env: gpu-intelligence
├── 05_gpu_accelerated_intelligence.ipynb   ← narrated demo (pre-run, 6 parts)
├── analysis_agent.py                       ← LangGraph AnalysisAgent, configurable endpoint
├── gpu_lightcurve_flow.py                  ← Metaflow GPULightcurveFlow (4 steps)
├── rolling_features.py                     ← CUDA Python kernel + CPU fallback
└── wasp18b_lightcurve.csv                  ← TESS light curve data
```

**Import note:** `gpu_lightcurve_flow.py` and the notebook import `rolling_features` as `cuda_kernels.rolling_features` and `analysis_agent` as `agents.analysis_agent`. When running from the module directory, add the parent path to `sys.path` or symlink the files into `cuda_kernels/` and `agents/` subdirectories.

---

## Notebook structure (`05_gpu_accelerated_intelligence.ipynb`)

The notebook is pre-run and narrated in six parts:

| Part | Content |
|---|---|
| 1 | Brev GPU environment — `nvidia-smi`, CUDA Python version check |
| 2 | vLLM serving Nemotron — endpoint verification, first completion |
| 3 | CUDA Python feature engineering — `gpu_rolling_features()` on WASP-18 b |
| 4 | NemoClaw security layer — `nemoclaw wasp18b-agent status` output |
| 5 | Full GPU pipeline — `GPULightcurveFlow` run across 3 targets |
| 6 | CPU vs GPU benchmark — `benchmark_cpu_vs_gpu(n_curves=50)`, 47× speedup |

---

## Key files

### `rolling_features.py`

Computes rolling window features (mean, std, z-score, residual) using a CUDA C kernel compiled at runtime by CUDA Python 1.0. Falls back to numpy automatically if no GPU is present — the fallback produces identical results and is testable without a GPU.

```python
from rolling_features import gpu_rolling_features, benchmark_cpu_vs_gpu, CUDA_AVAILABLE

# Works with or without a GPU
features = gpu_rolling_features(flux_array, model_array, window=15)
# Returns: rolling_mean, rolling_std, flux_zscore, residual, abs_residual

# Benchmark CPU vs GPU throughput (50 light curves)
result = benchmark_cpu_vs_gpu(n_curves=50, n_points=1500, window=15)
print(result['speedup'])  # 47.5 on L40S, 'N/A' on CPU-only
```

### `analysis_agent.py`

The same LangGraph `AnalysisAgent` from Module 03, with one change: inference endpoint reads from env vars. The agent doesn't know whether it's talking to Nemotron, Claude, or AI Navigator.

```python
# Configure via environment variables before importing:
# export INFERENCE_BASE_URL="http://localhost:8000/v1"   # vLLM + Nemotron on Brev
# export INFERENCE_API_KEY="not-needed"
# export INFERENCE_MODEL="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"

from analysis_agent import run_analysis_agent
result = run_analysis_agent(report=validation_report, anomaly_result=anomaly_dict, verbose=True)
# Returns: classification, confidence, transit_depth_pct, reasoning_summary, recommended_next_steps
```

### `gpu_lightcurve_flow.py`

Metaflow `GPULightcurveFlow` — four steps, each with its own `@conda` environment:

```
start          → fan out over targets (Parameter: --targets "wasp18b,wasp12b")
  ingest       → @conda(polars, scikit-learn, pydantic) — same as Module 01
  compute_features → @conda(cuda-python, numpy) — GPU rolling windows via rolling_features.py
  analyze      → @conda(openai, langgraph) @retry(3) — Nemotron via inference_url parameter
join → end     → merge results, print summary
```

Run it:

```bash
# With a vLLM/Nemotron server running:
python gpu_lightcurve_flow.py run \
    --targets "wasp18b,wasp12b,hot_jupiter_3" \
    --inference_url "http://localhost:8000/v1"

# CPU-only demo (ingest + features work; analyze step needs an LLM endpoint):
export INFERENCE_BASE_URL="https://api.anthropic.com/v1"
export INFERENCE_API_KEY="sk-ant-..."
export INFERENCE_MODEL="claude-haiku-4-5-20251001"
python gpu_lightcurve_flow.py run --targets "wasp18b"
```

---

## Prerequisites

### 1. Provision a Brev GPU instance

```bash
# Install Brev CLI
curl -sL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh | sudo bash
brev login

# Create an L40S instance (sufficient for Nemotron 3 Nano)
brev create wasp18b-gpu --gpu-name L40S --min-vram 40
brev shell wasp18b-gpu
```

Or use the [Brev web console](https://brev.nvidia.com) to open JupyterLab in browser.

### 2. Verify GPU and CUDA

```bash
nvidia-smi
python -c "from cuda.bindings import runtime as cudart; print('CUDA Python available')"
```

### 3. Set up the conda environment

```bash
conda env create -f environment.yml
conda activate gpu-intelligence
```

### 4. Start vLLM serving Nemotron (separate terminal)

```bash
# Option A: Local model from HuggingFace (~17GB download)
python -m vllm.entrypoints.openai.api_server \
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
    --host 0.0.0.0 --port 8000

# Option B: NVIDIA NIM hosted (no local download, requires API key)
export NVIDIA_API_KEY=your_key_here
# Use INFERENCE_BASE_URL="https://integrate.api.nvidia.com/v1"
```

### 5. (Optional) Set up NemoClaw sandbox

```bash
npm install -g nemoclaw
nemoclaw onboard wasp18b-agent \
    --model nvidia/nemotron-3-super-120b-a12b \
    --provider vllm-local
nemoclaw wasp18b-agent status
```

---

## Running without a GPU

`rolling_features.py` detects CUDA availability at import time and falls back to a numpy CPU implementation automatically — identical output, no code changes:

```bash
conda activate gpu-intelligence
python -c "
from rolling_features import gpu_rolling_features, benchmark_cpu_vs_gpu
import numpy as np

flux  = np.random.normal(1.0, 0.0003, 1500).astype('float32')
model = flux + np.random.normal(0, 0.00005, 1500).astype('float32')

features = gpu_rolling_features(flux, model, window=15)
print('Features:', list(features.keys()))
print(benchmark_cpu_vs_gpu(n_curves=10, n_points=1500))
"
# Output: 'CUDA Python not available — falling back to numpy (CPU)'
# Features and benchmark both work; speedup shows 'N/A'
```

For the `analyze` step, substitute any OpenAI-compatible endpoint (AI Navigator, Anthropic, vLLM) via `INFERENCE_BASE_URL`.

---

## Environment

```bash
conda env create -f environment.yml
conda activate gpu-intelligence
```

| Package | Role |
|---|---|
| `cuda-python>=12.0` | Direct CUDA kernel access — `from cuda.core.experimental import Device` |
| `vllm>=0.4.0` | OpenAI-compatible inference server for Nemotron |
| `openai>=1.30` | Client for vLLM, NIM, or any OpenAI-compatible endpoint |
| `metaflow>=2.18` | Workflow orchestration — `@conda` per step, `@retry`, `foreach` |
| `langgraph>=0.2` | Agent loop — same as Module 03 |
| `polars>=1.0`, `numpy>=1.26`, `scikit-learn>=1.4`, `pydantic>=2.0` | Data pipeline |
| `huggingface-hub>=0.23`, `transformers>=4.40` | Nemotron model download |
| `anthropic>=0.40` | Fallback inference client for non-GPU environments |
| `pytest>=8.0` | Test suite |

---

## Benchmarks (50 light curves, L40S GPU)

| Metric | Value |
|---|---|
| Feature engineering speedup | 47.5× (CPU → GPU) |
| End-to-end pipeline speedup | 4.8× |
| GPU: 50 curves feature engineering | ~0.4s |
| CPU: 50 curves feature engineering | ~19s |

The `foreach` parallelism in Metaflow means GPU kernels for all targets launch simultaneously — the per-target compute time is nearly constant as target count scales.

---

## What changed vs Module 03

| Component | Module 03 | Module 05 |
|---|---|---|
| LangGraph agents | ✓ unchanged | ✓ unchanged |
| Metaflow FlowSpec | ✓ unchanged | + `compute_features` step |
| `ingestion.py` functions | ✓ unchanged | ✓ unchanged |
| Pydantic models | ✓ unchanged | ✓ unchanged |
| LLM client interface | `openai` client | `openai` client — same |
| `base_url` | Claude / AI Navigator | vLLM + Nemotron on Brev |
| Feature engineering | Polars CPU rolling | CUDA Python kernel + CPU fallback |
| Security layer | None | NemoClaw (optional) |
| Environment | One env for all steps | `@conda` per step (polars / cuda-python / openai isolated) |
