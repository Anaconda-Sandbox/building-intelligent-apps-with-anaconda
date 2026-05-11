# Your First Agent: Building Intelligent Workflows

This module turns the deterministic Module 1 pipeline into an agent-driven workflow.

## What this module covers

Module 01 built a deterministic pipeline: load → validate → feature engineer → detect anomalies. It's good code. It has no idea an LLM exists.
 
This module changes that. We register those pipeline functions as **agent tools**, give a LangGraph ReAct agent access to them, and watch it reason through the same pipeline it would otherwise never know about.

In **Module 2: Your First Agent**, you'll:

1. Register `load_lightcurve`, `validate_lightcurve`, and the feature/anomaly pipeline as **agent tools**
2. Give an LLM the `agent_context` dict from Module 1 as initial context
3. Let the agent decide *which* light curves to analyze, *how* to interpret results, and *what follow-up questions* to ask

The underlying pipeline does not change — it only gets a smarter driver.

```
Module 01                         Module 02
──────────────────────────────    ──────────────────────────────────────
load_lightcurve()      function → @tool  ← LLM reads the docstring
validate_lightcurve()  function → @tool  ← LLM decides when to call it
run_feature_anomaly_pipeline()  → @tool  ← LLM interprets the output
build_agent_context()  function → @tool  ← LLM assembles the summary
```

## Files

```
02-your-first-agent/
├── README.md                     ← this file
├── run_demo.sh                   ← start here
├── 02_your_first_agent.ipynb     ← narrated walkthrough -- experimental (all five parts)
├── agent_tools.py                ← pipeline functions wrapped as LangGraph tools
├── agent_example.py              ← Mode 1: no LLM, builds and prints agent context
├── langchain_agent_example.py    ← Modes 2 & 3: live LangGraph agent with reasoning trace
└── environment.yml               ← conda env: first-agent
```

## Getting started

### Three ways to complete this module
 
Do you need an API key? Do you need an LLM running? Depends on the mode.
 
| Mode | LLM required | API key required | What you see |
|---|---|---|---|
| **1 — Shell script** | No | No | Agent context + completion screen |
| **2 — Anaconda AI Navigator** | Local (on your machine) | No | Full agent reasoning trace |
| **3 — vLLM / external endpoint** | Remote | Yes | Full agent reasoning trace |

#### Mode 1 — Shell script
**No LLM. No API key. No internet after clone.**
 
```bash
bash 02-your-first-agent/run_demo.sh
```

This runs the pipeline — loads the WASP-18 b light curve, validates it, runs IsolationForest anomaly detection, and builds the structured JSON context that an agent *would receive* before it starts reasoning. No LLM call is made. You're seeing the output of the data pipeline: the structured payload that becomes the agent's starting point in Modes 2 and 3.

The script runs four steps:
1. **Environment check** — Python version, conda env, required packages
2. **Data check** — submodule initialised, CSV accessible
3. **Pipeline smoke test** — runs the real pipeline, prints the numbers
4. **Demo** — prints the agent context JSON, then shows the completion screen
```
╔══════════════════════════════════════════════════════════════╗
║  🛸  WASP-18 b  ·  MODULE 02 COMPLETE                       ║
║                                                              ║
║  Your First Agent                                            ║
║  Pipeline functions registered. Agent context built.         ║
║                                                              ║
║  Show this screen at the Anaconda booth to claim your prize. ║
║  🐍  PyCon US 2026  ·  Long Beach                           ║
╚══════════════════════════════════════════════════════════════╝
```

#### Mode 2 — Anaconda AI Navigator (local LLM, no API key)
**Runs a model on your machine. No API key. No data leaves your computer.**
 
Anaconda AI Navigator is a desktop application that downloads and runs open-source LLMs locally. It exposes an OpenAI-compatible API server at `http://localhost:8080/v1` — the agent code calls it exactly like any remote endpoint, but the model is running on your hardware.
 
> **Anaconda Desktop** (early access) extends this with environment management and Anaconda Platform integration. For this demo, AI Navigator is the recommended path. See [anaconda.com/docs/tools/ai-navigator](https://anaconda.com/docs/tools/ai-navigator/main) for installation.
 
**Setup:**
1. Download and install [Anaconda AI Navigator](https://anaconda.com/products/ai-navigator) (macOS or Windows)
2. Open AI Navigator → **Models** tab → download any **Desktop Deployable** model (Llama 3.2 3B is a fast starting point, ~2GB)
3. Go to **API Server** tab → select your model → press **Start**
4. The server is ready when you see `Server listening on 127.0.0.1:8080`
No API key is required by default. AI Navigator's API key field is optional — if you leave it blank, the server accepts requests without authentication.
 
**Run:**
```bash
bash 02-your-first-agent/run_demo.sh --llm
# INFERENCE_BASE_URL defaults to http://localhost:8080/v1
# INFERENCE_API_KEY  defaults to not-needed
```
 
The script checks that AI Navigator is responding before attempting the agent run. If it isn't, you'll get the exact steps to start it rather than a cryptic connection error.
 
What you see: the live LangGraph ReAct reasoning trace — every tool call the agent decides to make, every result it reads, and its final plain-language summary of the WASP-18 b transit.

### Mode 3 — vLLM or any external endpoint (API key required)
**Self-hosted GPU inference or any OpenAI-compatible remote endpoint.**
 
vLLM is an open-source inference server optimised for GPU throughput. It serves HuggingFace models and exposes the same OpenAI-compatible API. This is the path for production GPU deployments — covered in depth in Module 04 and 05.
 
```bash
# Self-hosted vLLM (your GPU server)
export INFERENCE_BASE_URL="http://your-server:8000/v1"
export INFERENCE_MODEL="mistralai/Mistral-7B-Instruct-v0.3"
export INFERENCE_API_KEY="your-key-if-configured"
bash 02-your-first-agent/run_demo.sh --llm
 
# Anthropic (if you have an API key)
export INFERENCE_BASE_URL="https://api.anthropic.com/v1"
export INFERENCE_API_KEY="sk-ant-..."
export INFERENCE_MODEL="claude-haiku-4-5-20251001"
bash 02-your-first-agent/run_demo.sh --llm
```
 
The agent code is identical across all three modes. The only thing that changes is `INFERENCE_BASE_URL`. That's the portable inference contract — demonstrated properly in Module 04.
 

## Core agent tools

- `load_lightcurve(filepath, SCHEMA)`
- `validate_lightcurve(df)`
- `run_feature_anomaly_pipeline(df, window=15, contamination=0.05)`
- `build_agent_context(filepath, window=15, contamination=0.05)`


### What it does

- loads `../01-data-sources/wasp18b_lightcurve.csv`
- validates the dataset with `validate_lightcurve`
- runs `run_feature_anomaly_pipeline`
- uses an LLM agent to decide what to do next

## Notes
 
`01-data-sources/ingestion.py` is the source of truth. This module adds the agent wrapper — nothing in `ingestion.py` changes. Module 03 wraps this same pattern in a Metaflow `FlowSpec`, adds a second agent, runs `foreach` parallelism across 50 targets, and deploys without touching the tool definitions.
