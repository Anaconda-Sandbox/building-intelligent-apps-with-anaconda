# 🚀 Building Intelligent Apps with Anaconda

> **Mission status: WIP — PyCon US 2026, Long Beach, May 14–22**

A hands-on curriculum for building production-grade intelligent applications with the Anaconda ecosystem. Every module is a self-contained 7-minute narrated demo with pre-run outputs — designed to show the code and the decisions, not walk you through setup.

Our data is real: WASP-18 b, a hot Jupiter exoplanet caught transiting its star by NASA's TESS telescope. We process its light curve, build agents to reason about it, deploy those agents to production, secure the supply chain, and ship the result — to a browser tab, to a native app, to an air-gapped server 800km away. Same data. Every module.

---

## 🌌 Mission arc

```
                     ┌─────────────────────────────────────────────┐
                     │         THE WASP-18 b PIPELINE              │
                     │  a hot Jupiter 1,300 light-years from home  │
                     └─────────────────────────────────────────────┘

 PRE-LAUNCH         -1   MCP orientation     talk to Anaconda tools before liftoff
 ────────────────────────────────────────────────────────────────────────────────
 CORE STACK         00   Foundation          conda — the launch pad
                    01   Data sources        TESS photons → Python → ValidationReport
                    02   Your first agent    one agent, one tool, one answer
                    03   Multi-agent         crew of agents, Metaflow orchestration
 ────────────────────────────────────────────────────────────────────────────────
 DEEP SPACE         04   Deployment          swap the LLM endpoint, keep the agents
                    05   GPU acceleration    Nemotron on NVIDIA iron, 47× faster
                    06   App architecture    harness, evals, vector memory, cards
                    07   Mission critical    CVEs, conda-lock, air-gap, AIBOM
 ────────────────────────────────────────────────────────────────────────────────
 EXTRAVEHICULAR     08   Native apps         PyScript (browser) + BeeWare (native)
 ────────────────────────────────────────────────────────────────────────────────
 MISSION CONTROL   100   Example apps        full reference implementations
                   101   Reference library   decision guides, best practices
```

The payload — `ingestion.py` and `ValidationReport` — never changes. What changes is where it runs and what reasons about it.

---

## 📡 Modules

### `-1` — MCP: Pre-flight Checklist
**Make sure ground control can hear you.**

The Model Context Protocol is how AI assistants talk to Anaconda tools. Before the first `conda install`, verify your MCP setup so Claude Desktop can manage environments, query packages, and inspect CVEs on your behalf.

Tools: `anaconda-mcp`, Claude Desktop

---

### `00` — Foundation: The Launch Pad
**You can't reach orbit without a stable platform.**

Every agent, every pipeline step, every GPU kernel in this curriculum runs inside a conda environment. This module makes that concrete: why conda over pip alone, how environment isolation works, and the tools that turn a fleeting `pip install` into a reproducible, lockable, shippable artifact.

```bash
conda create -n mission python=3.11
conda activate mission
conda-lock -f environment.yml -p linux-64   # lock for reproducibility
```

Tools: `conda`, `conda-lock`, `conda-forge`, `pixi`, Anaconda Distribution

---

### `01` — Data Sources: First Contact
**Raw photons from 1,300 light-years away, cleaned up and ready for agents.**

Built on Daina Bouquin's [polars_demo](https://github.com/dbouquin/polars_demo) — a real TESS phase-folded light curve of WASP-18 b, a hot Jupiter completing an orbit every 22 hours. We extend it into a production-ready pipeline: schema enforcement, Pydantic validation, IsolationForest anomaly detection, and the `ValidationReport` that every subsequent module consumes.

```
PHASE | LC_DETREND | MODEL_INIT
──────────────────────────────
The three columns that travel through the entire curriculum.
```

- `ingestion.py` — `load_lightcurve()`, `validate_lightcurve()`, schema enforcement
- `ValidationReport` — typed Pydantic output, JSON-serialisable, agent-ready
- IsolationForest — transit anomaly detection without labelled data
- `agent_context` — the structured payload that becomes Module 02's agent input

Tools: Polars, scikit-learn, Pydantic, `ingestion.py`

---

### `02` — Your First Agent: One Crew Member
**A single agent, two tools, a classification.**

`ingestion.py` functions become LangGraph tools. One agent calls `load_lightcurve`, passes the result to `validate_lightcurve`, reasons over the `ValidationReport`, and returns a structured transit classification. Claude Haiku is the default crew member — swap the `base_url` for AI Navigator to fly offline.

Default LLM: `claude-haiku-4-5-20251001` via Anthropic API, or AI Navigator local server.

Tools: LangGraph, Anaconda MCP, `openai` client

---

### `03` — Multi-Agent Architecture: Assemble the Crew
**Two agents, one supervisor, `foreach` parallelism across 50 targets.**

`DataAgent` and `AnalysisAgent` fly in formation, coordinated by a LangGraph supervisor. Metaflow wraps the whole operation as a `FlowSpec` with `@conda` per step — each agent role gets its own isolated, lockable environment. A dependency conflict between Polars and LangGraph is structurally impossible.

```
start → ingest (polars, scikit-learn)
      → analyze (openai, langgraph)
      → join → end
Each step: its own @conda env, @retry, auditable supply chain.
```

Deployed to Outerbounds, AWS EKS, or a Linux box + cron. Flow code unchanged for all three. `deploy/` has the guides.

Tools: LangGraph, Metaflow 2.18+, `@conda` per step, Outerbounds

---

### `04` — Deployment and Inference: Mission Control Endpoints
**Three LLM targets, one agent interface, zero code changes.**

The agents from Module 03 call an LLM via the `openai` client. That client points at a URL. This module shows what lives at the URL — and proves that swapping it is a one-line env var change.

| Target | `base_url` | Best for |
|---|---|---|
| AI Navigator | `http://localhost:8080/v1` | Local dev, no API key |
| vLLM (self-hosted) | `http://server:8000/v1` | Production GPU, full control |
| Anaconda Platform | `$MODEL_SERVER_BASE_URL` | Enterprise, governed, AIBOM |

Anaconda Platform adds: Model Catalog with HellaSwag/WinoGrande/TruthfulQA benchmarks, downloadable AIBOM (CycloneDX JSON), Responsible AI scoring via Gray Swan, Model Governance for org-wide policy.

Supporting docs in `deploy/`: `ai-navigator.md`, `vllm.md`, `anaconda-platform.md`

Tools: vLLM, Anaconda Platform Model Servers, `inference_client.py`

---

### `05` — GPU-Accelerated Intelligence: Afterburners
**Same pipeline. NVIDIA iron. 47× faster feature engineering.**

The Module 03 flow gets a CUDA upgrade. `compute_features` moves from Polars CPU rolling windows to a CUDA Python 1.0 kernel. The LLM switches from Claude Haiku to Nemotron 3 Nano on vLLM via Brev. The agents don't know any of this happened.

```
Module 03                    Module 05
─────────────────────────    ────────────────────────────────
@conda per step   same  →    + nvidia channel, cuda-python
ingestion.py      same  →    same functions
Claude Haiku            →    Nemotron 3 Nano (BF16) on vLLM
CPU rolling windows     →    CUDA Python kernel
no sandbox              →    NemoClaw security layer (alpha)
```

**What each NVIDIA tool actually is (not Python imports):**
- **Brev** — CLI to provision an L40S in ~3 minutes: `brev create`
- **CUDA Python 1.0** — `from cuda.core.experimental import Device` — direct kernel access
- **Nemotron** — HuggingFace model, served via vLLM, called via `openai` client
- **NemoClaw** — TypeScript CLI + Python blueprint, sandboxed agent runtime (alpha)

**conda-pypi note:** vLLM is PyPI-only. The `pip:` section in `environment.yml` is the current pragmatic path. `conda-pypi` (experimental, Q1 2026) is the safer long-term approach — converts wheels to `.conda` format, integrates with the solver. Track: [conda/conda-pypi](https://github.com/conda/conda-pypi)

Benchmarks (50 light curves): **47.5× feature engineering speedup · 4.8× end-to-end**

Tools: Brev, CUDA Python 1.0, vLLM, Nemotron 3 Nano (BF16), NemoClaw

---

### `06` — App Architecture: Mission Hardening
**The pipeline that keeps flying when things go wrong.**

Module 03's flow works on good data with a responsive LLM. This module adds four additive patterns that keep it running in production:

```
Pattern              Metaflow tool         What it solves
─────────────────    ──────────────────    ────────────────────────────────────────
Graceful degradation @catch                One bad target doesn't abort the mission
Eval-as-CI           evaluate step         Assertions run every execution, fail loud
Observability        @card                 HTML reports per target + per run
Agent memory         DuckDB vector store   Past results injected as context at inference
```

The `evaluate` step runs assertion functions from `evals/assertions.py` — plain Python, no Metaflow dependency, testable with pytest. Critical failures raise `AssertionError`. The `@card` on `end` is the single view you check after every production run.

The DuckDB memory store (from the vector DB comparison: pgvector / MongoDB Atlas / Neo4j / **DuckDB** — embedded, portable, `conda-pack`-able) gives agents memory across runs: past `ValidationReport` results retrieved by cosine similarity and injected into the system prompt.

Tools: Metaflow, LangGraph, Pydantic, DuckDB, `@catch`, `@card`

---

### `07` — Mission-Critical Infrastructure: No Failures Tolerated
**Prove the environment is safe before it flies.**

Supply chain security isn't a feature you add at the end. It's the infrastructure the pipeline runs on. Five layers, zero pipeline code changes:

```
Layer    Tool                               The question it answers
───────  ─────────────────────────────────  ─────────────────────────────────────────
Lock     conda-lock                         Is this environment bit-for-bit reproducible?
Scan     anaconda-audit                     Does it contain known vulnerabilities?
Gate     Anaconda Platform policy filter    Did anything vulnerable get in upstream?
Pack     conda-pack                         Can we deploy without internet access?
Verify   AIBOM + SHA-256                    Is the model file what we think it is?
```

- `anaconda-audit scan --name app-architecture` — CVE scan against NVD/NIST, Anaconda-curated statuses (Active / Cleared / Mitigated / Disputed)
- Policy filters block packages with CVE score ≥ 7 or Active status before they reach your channel
- `conda-lock` turns a floating `environment.yml` into a pinned deployment contract
- `conda-pack` ships the entire environment as a relocatable tarball — Python, CUDA binaries, DuckDB memory store — to a machine with no conda, no internet
- AIBOM (CycloneDX JSON from Anaconda Platform Model Catalog) includes SHA-256 checksums, benchmark scores, ethical considerations, software dependencies

CI script: `scripts/lock_and_scan.sh` — lock → scan → gate, exits 1 on critical CVEs.
Deploy script: `scripts/pack_and_ship.sh` — AIBOM verify → conda-pack → scp to target.

Tools: `anaconda-audit`, `conda-lock`, `conda-pack`, Anaconda Platform, `security/verify_aibom.py`

---

### `08` — Native Apps: Escape Velocity
**The same pipeline, delivered everywhere Python runs.**

An addendum. Not required. The answer to: *after all that, where else can this fly?*

Two options, same five exoplanet targets, same IsolationForest pipeline, same `ValidationReport` schema:

**Option A — PyScript** *(Python in the browser, no server)*

Launched by Anaconda at PyCon US 2022. Pyodide loads a full CPython interpreter into your browser tab via WebAssembly. One HTML file. Select a target → Run Analysis → validation report + three matplotlib charts render in the page. numpy, pandas, matplotlib, scikit-learn all bundled in Pyodide.

```bash
cd option-a-pyscript && python -m http.server 8080
# open http://localhost:8080 — that's it
```

**Option B — BeeWare** *(Python as a native OS app)*

Funded by Anaconda. Briefcase packages the same Python source into native apps for every platform. Toga maps Python widgets to native OS controls (NSTableView on macOS, GtkTreeView on Linux, ListView on Windows). One `pyproject.toml`, six targets.

```bash
cd option-b-beeware
pip install briefcase
briefcase dev        # opens a native window immediately
briefcase package    # → .dmg / .msi / AppImage / .ipa / .aab
```

See `BUILDING.md` for the complete per-platform build guide including signing, distribution, and the full Briefcase command lifecycle.

Tools: PyScript (Pyodide/WASM), BeeWare (Briefcase + Toga)

---

### `100` — Example Applications
Complete reference implementations using the patterns from the full curriculum. Working code to fork and adapt, not tutorial material.

---

### `101` — Reference Library
Supporting docs, decision guides, and best-practice write-ups: package manager decision tree, conda concepts and modern tooling, local/sovereign AI patterns, secure AI best practices, environment setup, IDE integrations.

---

## 🛠️ Core tools

| Tool | Role | First seen |
|---|---|---|
| `conda` / `conda-forge` | Environment management + package distribution | `00` |
| `conda-lock` | Reproducible cross-platform lock files | `00`, `07` |
| `conda-pack` | Portable environment tarballs for air-gap deployment | `07`, `08` |
| `conda-pypi` | Safer PyPI wheel integration (experimental, Q1 2026) | `05` |
| `anaconda-audit` | CVE scanning against NVD/NIST | `07` |
| Anaconda Platform | Model Catalog, Governance, CVE policy, Model Servers | `04`, `07` |
| Anaconda MCP Server | MCP tool exposure for Anaconda ecosystem | `-1`, `02` |
| Polars | Fast DataFrame manipulation | `01` |
| Pydantic | Typed, validated, JSON-serialisable pipeline outputs | `01` |
| Metaflow 2.18+ | ML/AI workflow orchestration with per-step `@conda` | `03` |
| LangGraph | Agent loop and multi-agent coordination | `02`, `03` |
| vLLM | OpenAI-compatible self-hosted GPU inference server | `04`, `05` |
| CUDA Python 1.0 | Direct CUDA kernel access from Python | `05` |
| Brev | On-demand GPU instance provisioning | `05` |
| Nemotron | NVIDIA open-weight model family (via HuggingFace + vLLM) | `05` |
| NemoClaw | Sandboxed agent runtime (NVIDIA, alpha CLI) | `05` |
| DuckDB | Embedded vector store for agent memory | `06` |
| PyScript | Python in the browser via WebAssembly | `08` |
| BeeWare | Native mobile/desktop apps in Python | `08` |

## ⚙️ Optional tools

| Tool | Role |
|---|---|
| LangChain | Broader LLM tooling ecosystem (`02`) |
| FastMCP | MCP server construction |
| pixi | Alternative conda environment manager |
| Numba | JIT-compiled Python for GPU/CPU acceleration |
| RAPIDS | GPU-accelerated data science (cuDF, cuML) |
| Outerbounds | Managed Metaflow (Argo + metadata service + UI) |

---

## 🌠 Prerequisites

```bash
# Anaconda Distribution or Miniconda
# https://www.anaconda.com/download

conda --version   # 25.x or later

# Free Anaconda account — required for AI Navigator and Platform features
# https://anaconda.com
```

Each module has its own `environment.yml`. Start with `-1-mcp-your-environment` and work in order — every module builds on the data and patterns from the one before it.

---

## 🔭 The data

Every module uses the **WASP-18 b phase-folded light curve** from NASA's TESS mission, originally prepared by Daina Bouquin for [polars_demo](https://github.com/dbouquin/polars_demo).

WASP-18 b is a real exoplanet — a hot Jupiter 10× the mass of Jupiter, completing a full orbit every 22.6 hours. TESS measured its host star's brightness dropping by ~1% each time the planet crossed in front of it. Those brightness measurements are our CSV: 1,800 rows, three columns, one recurring signal buried in noise.

It's a good dataset for this curriculum because it has a real anomaly (the transit dip), realistic noise, and enough physical context that the agent's reasoning outputs make intuitive sense. You don't need to know astrophysics — but if you look it up, the numbers check out.

`wasp18b_lightcurve.csv` is in `01-data-sources/`. Run `fetch_data.py` to pull a fresh copy from the STScI archive.

---

## 🛸 About

Anaconda demos for PyCon US 2026, Long Beach, May 14–22.

Built with the Anaconda ecosystem for 50M+ Python users.  
The pipeline never changes. Everything else does.

For questions contact @dawnwages
Target Audience: Software Engineers, AI Developers, ML Engineers, Data Scientists
Resource Type: Show
Metrics: Stars, forks, completions

# License
MIT License - see LICENSE file for details.