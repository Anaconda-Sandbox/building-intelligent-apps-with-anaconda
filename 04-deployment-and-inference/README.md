# 04 — Deployment and Inference

**Estimated time:** 7 minutes  
**Prerequisites:** Completed `03-multi-agent-architecture` — the `LightcurveAnalysisFlow` and `analysis_agent.py` are the things being deployed here.

---

## The point of this module

The agents from Module 03 call an LLM endpoint via the `openai` client. That endpoint is just a URL. This module shows what can live at that URL — and demonstrates that swapping it requires changing one environment variable, not rewriting your agents.

This is the **portable inference contract**:

```python
# Everything downstream of this is identical regardless of which server is running
client = OpenAI(
    base_url=os.environ["INFERENCE_BASE_URL"],
    api_key=os.environ["INFERENCE_API_KEY"],
)
```

---

## Three inference targets

```
Target                          base_url                            Use case
──────────────────────────────  ──────────────────────────────────  ─────────────────────────────
AI Navigator (local)            http://localhost:8080               Dev — no API key, no cloud
vLLM (self-hosted GPU)          http://your-server:8000/v1          Production GPU, full control
Anaconda Platform Model Server  $MODEL_SERVER_BASE_URL              Enterprise, governed, managed
```

All three are OpenAI API-compatible for chat completions. The agents don't know which one they're talking to.

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

## Quick start

```bash
conda env create -f environment.yml
conda activate deployment-inference

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
