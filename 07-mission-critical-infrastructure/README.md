# 07 — Mission-Critical Infrastructure

**Estimated time:** 7 minutes  
**Prerequisites:** `06-app-architecture` — the `HarnessedLightcurveFlow` is deployed here unchanged.

---

## The story

Modules 01–06 built a production-grade pipeline. This module asks: **can you prove it's safe to run?**

The pipeline code doesn't change. What changes is the infrastructure around it — the supply chain that produces the environments the pipeline runs in, and the model provenance record for the LLM it calls.

Five layers:

```
Layer                Tool(s)                          What it answers
───────────────────  ───────────────────────────────  ─────────────────────────────────────────
1. Lock              conda-lock                       "Is this environment reproducible?"
2. Scan              anaconda-audit                   "Does it have known vulnerabilities?"
3. Gate              Anaconda Platform policy filter  "Did anything vulnerable get in upstream?"
4. Pack + ship       conda-pack                       "Can we deploy it without internet access?"
5. Verify model      AIBOM + SHA-256                  "Is the model file what we think it is?"
```

None of these require pipeline code changes. They wrap the environment and the model, not the flow.

---

## Module structure

```
07-mission-critical-infrastructure/
├── README.md                              ← this file
├── environment.yml                        ← module environment
├── 07_mission_critical.ipynb             ← narrated demo (7 min, pre-run)
├── flows/
│   └── secured_flow.py                   ← HarnessedLightcurveFlow + security checks
├── security/
│   ├── policy.yaml                        ← example Anaconda Platform policy config
│   ├── mirror.yaml                        ← channel mirror config (air-gap pattern)
│   └── verify_aibom.py                   ← SHA-256 model verification against AIBOM
└── scripts/
    ├── lock_and_scan.sh                   ← lock → scan → gate CI script
    └── pack_and_ship.sh                   ← conda-pack → verify → deploy
```

---

## Quick start

```bash
conda env create -f environment.yml
conda activate mission-critical

# Step 1 — lock the environment from Module 06
conda-lock -f ../06-app-architecture/environment.yml -p linux-64

# Step 2 — scan it
conda install --name base anaconda-cloud::anaconda-env-manager
anaconda audit scan --name app-architecture

# Step 3 — verify the model AIBOM
python security/verify_aibom.py \
    --aibom path/to/model.aibom.json \
    --model path/to/model.gguf

# Step 4 — pack for deployment
conda-pack -n app-architecture -o app-architecture.tar.gz
```
