# 05 — GPU-Accelerated Intelligence

**Estimated time:** 7 minutes  
**Prerequisites:** Completed `03-multi-agent-architecture` — the WASP-18 b pipeline and LangGraph + Metaflow patterns carry forward here unchanged.

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
Standard Python              →       CUDA Python 1.0 for data ops
No sandbox policy            →       NemoClaw security layer
```

The agent code doesn't change. The environment does.

---

## The NVIDIA stack — what each tool actually is

```
┌─────────────────────────────────────────────────────────────────┐
│                    BREV (infrastructure)                        │
│  Provisions GPU instance on demand — CUDA, Python, drivers      │
│  preconfigured. SSH in or use JupyterLab. Pay by the hour.      │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │               NemoClaw (security layer)                   │  │
│  │  Sandboxed agent runtime: Landlock + seccomp + netns      │  │
│  │  Policy-controlled inference routing and network egress   │  │
│  │  CLI tool — wraps the environment the notebook runs in    │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │            vLLM serving Nemotron                    │  │  │
│  │  │  OpenAI-compatible endpoint, continuous batching    │  │  │
│  │  │  Handles concurrent agent requests efficiently      │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │            CUDA Python 1.0                          │  │  │
│  │  │  Direct CUDA kernel calls from Python               │  │  │
│  │  │  GPU-accelerated feature engineering in the         │  │  │
│  │  │  data pipeline (replaces the CPU numpy ops)         │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Brev** — NVIDIA's GPU provisioning platform. Not a Python library. Use the CLI or web console to get a GPU instance, then SSH or JupyterLab in. The environment comes with CUDA, Python, and Docker preconfigured.

**NemoClaw** — NVIDIA's open-source sandboxed agent runtime (alpha). A TypeScript CLI plugin + Python blueprint built on OpenShell. It controls what your agent can see, do, and where its inference requests go. You interact with it via `nemoclaw` commands, not Python imports.

**Nemotron** — NVIDIA's family of open-weight models with open training data. Accessed via HuggingFace + vLLM (local) or NVIDIA NIM endpoints (cloud). No `nvidia.generativeai` package — use the `openai` client with the appropriate `base_url`.

**CUDA Python 1.0** — Direct CUDA kernel access from Python. Used here to GPU-accelerate the rolling window feature engineering from `01-data-sources`, eliminating the bottleneck when processing large batches.

---

## Prerequisites

### 1. Provision a Brev GPU instance

```bash
# Install Brev CLI
curl -sL https://raw.githubusercontent.com/brevdev/brev-cli/main/bin/install-latest.sh | sudo bash
brev login

# Create an L40S instance (sufficient for Nemotron 3 Nano)
brev create wasp18b-gpu --gpu L40S
brev shell wasp18b-gpu
```

Or use the [Brev web console](https://brev.nvidia.com) to launch an instance and open JupyterLab in browser.

### 2. Verify GPU and CUDA

```bash
nvidia-smi
python -c "import cuda; print('CUDA Python available')"
```

### 3. Set up the conda environment

```bash
conda env create -f environment.yml
conda activate gpu-intelligence
```

### 4. Start vLLM serving Nemotron (in a separate terminal)

```bash
# Option A: Local model from HuggingFace (downloads ~17GB)
python -m vllm.entrypoints.openai.api_server \
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
    --host 0.0.0.0 --port 8000

# Option B: NVIDIA NIM hosted (no local download, requires API key)
export NVIDIA_API_KEY=your_key_here
# Use base_url = "https://integrate.api.nvidia.com/v1" in notebook
```

### 5. (Optional) Set up NemoClaw sandbox

```bash
# Install NemoClaw CLI
npm install -g nemoclaw

# Onboard an agent sandbox
nemoclaw onboard wasp18b-agent \
    --model nvidia/nemotron-3-super-120b-a12b \
    --provider vllm-local

nemoclaw wasp18b-agent status
```

---

## Module structure

```
05-gpu-accelerated-intelligence/
├── README.md                           ← this file
├── environment.yml                     ← conda env with CUDA Python + vLLM
├── 01_gpu_verification.ipynb           ← confirm GPU, CUDA Python, vLLM
├── 02_cuda_feature_engineering.ipynb   ← GPU-accelerated data pipeline
├── 03_nemotron_agents.ipynb            ← LangGraph agents → Nemotron endpoint
├── 04_nemoclaw_security.ipynb          ← NemoClaw sandbox walkthrough
├── 05_benchmark.ipynb                  ← CPU vs GPU comparison (pre-run)
├── agents/
│   ├── data_agent.py                   ← from 03, unchanged
│   ├── analysis_agent.py               ← from 03, updated endpoint
│   └── supervisor.py                   ← from 03, unchanged
├── flows/
│   └── gpu_lightcurve_flow.py          ← Metaflow flow with @cuda step
└── cuda_kernels/
    └── rolling_features.py             ← CUDA Python feature engineering
```

---

## The story in one sentence

The same pipeline from module 03 — WASP-18 b light curve ingestion, validation, and anomaly detection — now runs on GPU with Nemotron reasoning about the results, under NemoClaw's security policy, with CUDA Python handling the data math. The Anaconda conda environment manages all of it.
