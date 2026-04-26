# Building Intelligent Apps with Anaconda

> **WIP — PyCon US 2026, Long Beach, May 14–22**

A hands-on curriculum for building production-grade intelligent applications in the Anaconda ecosystem. Each module is a self-contained < 7-minute narrated demo with pre-run outputs — designed to show the code and the decisions, not walk through setup.

---

## The story

Data is the foundation. A clean pipeline becomes an agent tool. Multiple agents need coordination. Coordination at scale needs infrastructure. That infrastructure needs to be secure and reproducible. Anaconda can help you with that entire stack.

```
-1  MCP orientation          what MCP is and why it matters
00  Environment foundation   conda, environments, the base for everything
01  Data sources             ingest → validate → feature engineer → anomaly detect
02  Your first agent         single agent calling Module 01 as tools
03  Multi-agent architecture LangGraph agents + Metaflow orchestration
04  Deployment & inference   vLLM, Anaconda Platform Model Servers, portable contract
05  GPU-accelerated intel.   NVIDIA stack — Nemotron, CUDA Python, Brev, NemoClaw
06  App architecture         harness, feedback loops, graceful degradation
07  Mission-critical infra   supply chain, CVEs, conda-pack, air-gap, architecture
08  Native apps (addendum)   PyScript (browser) + BeeWare (mobile/desktop)
100 Example applications     reference implementations
101 Reference library        supporting docs, decision guides, best practices
```

---

## Modules

### `-1` — MCP: Your Environment
**Prerequisite orientation.** What the Model Context Protocol is, why it's the connective tissue for everything that follows, and how to verify your MCP setup before starting.

Tools: Anaconda MCP Server, Claude Desktop

---

### `00` — Foundation
**conda, environments, and the base for everything.**

Before any agent runs, someone has to manage the Python environment it runs in. This module establishes the Anaconda foundation — why conda over pip alone, how to think about environment isolation, and the tooling that makes reproducibility possible.

Tools: `conda`, `conda-lock`, `conda-forge`, `pixi`, Anaconda Distribution

---

### `01` — Data Sources
**Ingest → validate → feature engineer → detect.**

Picks up Daina Bouquin's [Polars time series tutorial](https://github.com/dbouquin/polars_demo) using WASP-18 b TESS light curve data and extends it into a production-ready data pipeline. Introduces Pydantic for structured outputs — the same contract that flows through every subsequent module.

- `ingestion.py` — `load_lightcurve()`, `validate_lightcurve()` with schema enforcement
- `ValidationReport` and `LightcurveSchema` — Pydantic models for typed pipeline outputs
- Polars rolling window feature engineering — residual, z-score, rolling std
- IsolationForest anomaly detection — transit detection without labeled data
- `agent_context` — the JSON the next module's agent receives

Tools: Polars, scikit-learn, Pydantic, Metaflow (intro), `ingestion.py`

---

### `02` — Your First Agent
**Single agent, MCP tools, structured outputs.**

The `ingestion.py` functions from Module 01 become agent tools. A single LangGraph agent calls `load_lightcurve` and `validate_lightcurve`, reasons over the `ValidationReport`, and returns a structured classification.

Default LLM: Claude Haiku (`claude-haiku-4-5-20251001`) via Anthropic API, or AI Navigator local server.

Tools: LangGraph, Anaconda MCP, `openai` client (OpenAI-compatible interface)

---

### `03` — Multi-Agent Architecture
**LangGraph agents + Metaflow orchestration.**

Two agents — a `DataAgent` and an `AnalysisAgent` — coordinated by a supervisor. LangGraph handles the agent loop. Metaflow wraps it as a `FlowSpec` with per-step `@conda` environments, `@retry`, and `foreach` parallelism across targets.

The key demonstration: `@conda` per step means each agent role has its own isolated, lockable, auditable environment. A dependency conflict between Polars and LangGraph is structurally impossible.

```
ingest step:    polars, scikit-learn, pydantic
analyze step:   openai, langgraph, pydantic
```

Default LLM: Claude Haiku via Anthropic API.

Tools: LangGraph, Metaflow 2.18+, `@conda` per step, `ValidationReport` (from Module 01)

---

### `04` — Deployment and Inference
**The portable inference contract.**

Three inference targets, one agent interface:

| Target | base_url | Use case |
|---|---|---|
| AI Navigator | `http://localhost:8080` | Local dev, no API key |
| vLLM (self-hosted) | `http://your-server:8000/v1` | Production GPU |
| Anaconda Platform Model Server | `$MODEL_SERVER_BASE_URL` | Enterprise, governed |

Anaconda Platform Model Servers are OpenAI API-compatible. Model selection via the Model Catalog (HellaSwag / WinoGrande / TruthfulQA benchmarks, AIBOM download, Responsible AI scoring via Gray Swan). Model Governance for org-wide policy enforcement.

Tools: vLLM, Anaconda Platform Model Servers, `openai` client

---

### `05` — GPU-Accelerated Intelligence
**The NVIDIA-aligned stack.**

The Module 03 pipeline — same agents, same Metaflow flow, same `ingestion.py` functions — moved to GPU with Nemotron reasoning and CUDA Python feature engineering.

```
Module 03                          Module 05
─────────────────────────────      ──────────────────────────────────
LangGraph agents      unchanged →  same agents
Metaflow FlowSpec     unchanged →  + compute_features step
ingestion.py          unchanged →  same functions
Polars features (CPU)           →  CUDA Python kernel (GPU)
Claude Haiku endpoint           →  Nemotron 3 Nano via vLLM on Brev
No sandbox policy               →  NemoClaw security layer
```

**What each NVIDIA tool actually is:**

- **Brev** — GPU provisioning platform (CLI, not a Python import). Provisions an L40S with CUDA, Python, and drivers in ~3 minutes.
- **CUDA Python 1.0** — Direct CUDA kernel access from Python. Used to GPU-accelerate the rolling window feature engineering from Module 01.
- **Nemotron** — NVIDIA's open-weight model family. Accessed via HuggingFace + vLLM or NVIDIA NIM. Not a Python package — use the `openai` client with the appropriate `base_url`.
- **NemoClaw** — NVIDIA's open-source sandboxed agent runtime (alpha). CLI tool built on OpenShell — controls what your agent can see, do, and where inference requests go. Not importable.

**conda-pypi note:** vLLM and the GPU inference stack exist only on PyPI and move too fast for conda-forge. The `environment.yml` uses a `pip:` section — the current pragmatic approach. `conda-pypi` (experimental, Q1 2026) is the safer long-term path; it converts wheels to `.conda` format and integrates with conda's solver. Track: [conda/conda-pypi](https://github.com/conda/conda-pypi).

Benchmark (50 light curves): 47.5× feature engineering speedup, 4.8× end-to-end speedup.

Tools: Brev, vLLM, Nemotron 3 Nano (BF16), CUDA Python 1.0, NemoClaw, `@conda` per step

---

### `06` — App Architecture
**Harness, feedback loops, graceful degradation.**

The intelligent app harness that keeps the pipeline running in production: feedback loop architecture, eval-as-CI (assertions on pipeline output as a Metaflow step), graceful degradation patterns, and observability via Metaflow Cards.

Tools: Metaflow, LangGraph, Pydantic

---

### `07` — Mission-Critical Infrastructure
**Supply chain, CVEs, conda-pack, air-gap, architecture.**

The conda ecosystem as production infrastructure for agents:

- **`anaconda-audit`** — CVE scanning against NVD/NIST, per environment, per step
- **Policy filters** — Anaconda Platform channel policies, auto-enforced on 4-hour schedule
- **`conda-lock`** — Fully pinned cross-platform lock files. The deployment specification.
- **`anaconda-project lock`** — Locks the full project environment before production promotion
- **`conda-pack`** — Ships an entire conda environment as a relocatable tarball. Deployable to systems without conda installed.
- **Channel mirroring** — Air-gapped internal copies of conda and PyPI channels, policy-filtered
- **Multi-architecture** — `linux-64`, `linux-aarch64`, `linux-ppc64le`, `osx-arm64` — same lock file, correct binaries per platform

Model governance: AIBOM (AI Bill of Materials, CycloneDX format), SHA-256 verification, Responsible AI scoring (OWASP, MITRE ATLAS, Gray Swan).

Tools: `anaconda-audit`, `conda-lock`, `conda-pack`, `anaconda-project`, Anaconda Platform

---

### `08` — Native Apps (addendum)
**PyScript and BeeWare — Python everywhere.**

An addendum, not a required step. Shows the doors that open once the pipeline from Modules 01–07 is built:

- **PyScript** — Python in the browser via WebAssembly. A static HTML file that calls the validated pipeline. No server, no backend. Package support via a curated subset of conda-forge.
- **BeeWare** — Python compiled to native mobile and desktop binaries via Briefcase + Toga. iOS, Android, macOS, Windows, Linux from one codebase.

The argument: the intelligent app you built runs in a browser tab or on someone's phone. `conda-pack` handles cross-platform environment packaging for BeeWare builds.

Tools: PyScript, BeeWare (Briefcase, Toga), `conda-pack`

---

### `100` — Example Applications
Reference implementations showing the full patterns from the curriculum applied to complete apps. Not tutorial material — working code you can fork and adapt.

---

### `101` — Reference Library
Supporting documentation, decision guides, and best-practice write-ups that apply across modules: package manager decision tree, conda concepts, modern conda tooling, local/sovereign AI patterns, secure AI best practices, environment setup, IDE integrations.

---

## Core tools

| Tool | Role | Introduced |
|---|---|---|
| `conda` / `conda-forge` | Environment management and package distribution | `00` |
| `conda-lock` | Reproducible environment pinning | `00`, `07` |
| `conda-pack` | Portable environment artifacts for deployment | `07` |
| `conda-pypi` | Safer PyPI wheel integration (experimental) | `05` |
| `anaconda-audit` | CVE scanning against NVD/NIST | `07` |
| Polars | Fast data manipulation | `01` |
| Pydantic | Typed structured outputs | `01` |
| Metaflow 2.18+ | ML/AI workflow orchestration with per-step envs | `03` |
| LangGraph | Agent loop and multi-agent coordination | `02`, `03` |
| Anaconda MCP Server | MCP tool exposure for Anaconda ecosystem | `-1`, `02` |
| vLLM | OpenAI-compatible GPU inference server | `04`, `05` |
| CUDA Python 1.0 | Direct CUDA kernel access from Python | `05` |
| Brev | On-demand GPU provisioning | `05` |
| NemoClaw | Sandboxed agent runtime (NVIDIA, alpha) | `05` |
| Nemotron | NVIDIA open-weight model family | `05` |
| Anaconda Platform | Model Catalog, Governance, CVE policy, Model Servers | `04`, `07` |
| PyScript | Python in the browser via WebAssembly | `08` |
| BeeWare | Native mobile/desktop apps in Python | `08` |

## Optional tools

| Tool | Role |
|---|---|
| LangChain | Broader LLM tooling ecosystem (used in `02`) |
| FastMCP | MCP server construction |
| pixi | Alternative conda environment manager |
| Numba | JIT-compiled Python for GPU/CPU acceleration |
| RAPIDS | GPU-accelerated data science (cuDF, cuML) |

---

## Prerequisites

```bash
# Anaconda Distribution or Miniconda
# https://www.anaconda.com/download

# Verify conda
conda --version   # should be 25.x or later

# Anaconda account (free) — required for AI Navigator and Platform features
# https://anaconda.com
```

Each module has its own `environment.yml`. Start with `-1-mcp-your-environment` and work through in order — each module builds on the data and patterns from the previous one.

---

## Data

The primary dataset across all modules is the **WASP-18 b phase-folded light curve** from NASA's TESS mission, originally developed for Daina Bouquin's [polars_demo](https://github.com/dbouquin/polars_demo). It's a real observational dataset (hot Jupiter exoplanet transit) that provides a concrete, interesting signal for demonstrating data ingestion, anomaly detection, and agent reasoning without requiring domain expertise.

`wasp18b_lightcurve.csv` is included in `01-data-sources`. Run `fetch_data.py` to pull a fresh copy from the STScI API.

---

## About

Anaconda demos for building intelligent apps. WIP for PyCon US 2026, Long Beach.

Built with the Anaconda ecosystem for 50M+ Python users.
