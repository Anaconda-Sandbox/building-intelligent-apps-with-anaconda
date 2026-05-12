# 04 — Deployment and Inference

**Estimated time:** 7 minutes  
**Prerequisites:** Completed `03-multi-agent-architecture` — the `LightcurveAnalysisFlow` and `analysis_agent.py` are the things being deployed here.

---

## The point of this module

The agents from Module 03 call an LLM via an inference client. That client points at a URL. This module shows what lives at that URL — Anthropic's API, AI Navigator, vLLM, or Anaconda Platform — and proves that swapping between them is a one-line env var change, not a code change.

The portable inference contract — the same client works with Anthropic, AI Navigator, vLLM, or Anaconda Platform:
 
```python
from anthropic import Anthropic
 
client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],   # or "not-needed" for local endpoints
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)
```
 
Or via the OpenAI-compatible wrapper (for AI Navigator, vLLM, Anaconda Platform):
 
```python
from openai import OpenAI
 
client = OpenAI(
    base_url=os.environ["INFERENCE_BASE_URL"],
    api_key=os.environ["INFERENCE_API_KEY"],
)

---

## Three inference targets

```
Target                                              base_url                            Use case
──────────────────────────────                      ──────────────────────────────────  ─────────────────────────────
AI Navigator or Anaconda Desktop (local)            http://localhost:8080               Dev — no API key, no cloud
vLLM (self-hosted GPU)                              http://your-server:8000/v1          Production GPU, full control
Anaconda Platform Model Server                      $MODEL_SERVER_BASE_URL              Enterprise, governed, managed
```

All three are API-compatible for chat completions. The agents don't know which one they're talking to.

---

## Local inference: AI Navigator and Anaconda Desktop
 
Anaconda provides two desktop applications for running LLMs locally — both expose an OpenAI-compatible API server that `inference_client.py` connects to without any code changes.
 
**Anaconda AI Navigator** is the current shipping product. It downloads and manages open-source LLMs, serves them via a built-in llama.cpp API server, and exposes an OpenAI-compatible endpoint at `http://localhost:8080/v1`. No API key required. Available on macOS and Windows.
 
**Anaconda Desktop** is the next generation — it adds secure local model deployment, an integrated chat interface, environment management, and Anaconda Platform integration alongside the same inference server capabilities. Currently available through a limited early access program; AI Navigator covers the same inference use case today.
 
For this module, either application works identically:
 
```bash
export INFERENCE_BASE_URL="http://localhost:8080/v1"
export INFERENCE_API_KEY="not-needed"
```
 
Setup steps:
1. Open AI Navigator (or Anaconda Desktop)
2. Go to **Models** — download any Desktop Deployable model
3. Go to **API Server** — select the model and press **Start**
4. The server is ready when you see `Server listening on 127.0.0.1:8080`
---

## Module structure

```
04-deployment-and-inference/
├── README.md                           ← this file
├── environment.yml                     ← conda env for this module
├── inference_client.py                 ← the portable client wrapper
├── 04_deployment_and_inference.ipynb   ← the full module (7 min, pre-run)
└── deploy/
    ├── ai-navigator.md                 ← setup guide: AI Navigator API server
    ├── vllm.md                         ← setup guide: vLLM on a GPU box
    └── anaconda-platform.md            ← setup guide: Anaconda Platform Model Servers
```

The notebook covers both dimensions in a single narrated demo:
- **Part 1** — where the Metaflow flow runs (Outerbounds / AWS / Linux + cron)
- **Part 2** — what the agents call (AI Navigator / vLLM / Anaconda Platform)
- **Part 3** — the portable contract: any flow target + any inference target, no code changes

The `deploy/` docs are reference material for setup steps that happen outside Python.

---

# Before you start

## Fresh clone

```bash
git clone https://github.com/Anaconda-Sandbox/building-intelligent-apps-with-anaconda
cd building-intelligent-apps-with-anaconda
git submodule update --init --recursive   # ← required: gets wasp18b_lightcurve.csv

conda env create -f 04-deployment-and-inference/environment.yml
conda activate deployment-inference

# Register the kernel so Jupyter can find it
python -m ipykernel install --user \
    --name deployment-inference \
    --display-name "Python 3 (deployment-inference)"
```

## Quick start

```bash
# Set your inference target (pick one):
export INFERENCE_BASE_URL="http://localhost:8080/v1"       # AI Navigator
export INFERENCE_BASE_URL="http://your-server:8000/v1"    # vLLM
export INFERENCE_BASE_URL="$MODEL_SERVER_BASE_URL"         # Anaconda Platform

export INFERENCE_API_KEY="your_key_or_not-needed"
export INFERENCE_MODEL="your_model_or_empty_string"

jupyter lab 04_deployment_and_inference.ipynb
```

---

## Important: AI Navigator vs vLLM endpoint format

AI Navigator runs llama.cpp under the hood. Its native endpoint is `/completion` (llama.cpp format), not `/v1/chat/completions` (OpenAI format). The `openai` Python client expects the OpenAI format.

**Use `http://localhost:8080/v1` as your `base_url`** — the `/v1` prefix routes to the OpenAI-compatible layer. Without it, you'll get 404s.

See [`deploy/ai-navigator.md`](deploy/ai-navigator.md) for setup details.

---

## What's next

[Module 05 — GPU-Accelerated Intelligence](../05-gpu-accelerated-intelligence/) takes this same inference contract and moves it to Nemotron on vLLM, running on a Brev GPU instance. The agent code doesn't change — only `INFERENCE_BASE_URL` and `INFERENCE_MODEL` do.
