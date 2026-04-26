# 08 — Native Apps

**Estimated time:** Under 7 minutes per option  
**Prerequisites:** None beyond Module 01 — this is a standalone addendum showing the pipeline delivered in new contexts.

---

## The point

Modules 01–07 built a production-grade intelligent pipeline. This module answers one question: **once you have a validated pipeline, where else can Python deliver it?**

Two demonstrations. Same five stellar targets. Same IsolationForest pipeline. Same validation schema as `ingestion.py` from Module 01. What changes is the delivery layer.

```
Option A — PyScript    Python in the browser via WebAssembly
                        Single HTML file, no server, no install
                        cdn.jsdelivr.net loads Pyodide into the tab
                        Run: python -m http.server 8080 → localhost:8080

Option B — BeeWare     Python as a native OS application
                        Briefcase packages it for macOS, Windows, Linux, iOS, Android
                        Toga widgets map to native controls on each platform
                        Run: briefcase dev
```

---

## Module structure

```
08-native-apps/
├── README.md                              ← this file
├── 08_native_apps.ipynb                  ← narrated demo (7 min, pre-run)
│
├── option-a-pyscript/
│   └── index.html                        ← the entire app — open in browser
│
└── option-b-beeware/
    ├── pyproject.toml                    ← Briefcase config for all platforms
    ├── BUILDING.md                       ← platform-by-platform build guide
    └── src/
        └── lightcurve/
            ├── __main__.py               ← Briefcase entry point
            └── app.py                    ← Toga app + pipeline
```

---

## Option A — PyScript quick start

```bash
cd option-a-pyscript
python -m http.server 8080
# Open http://localhost:8080
```

No CSV needed. No install. Select a target from the dropdown and press Run Analysis.
The page serves itself — the Python pipeline runs entirely in the browser tab.

**What Pyodide loads (~10 MB, cached after first visit):**
numpy, pandas, matplotlib, scikit-learn — all bundled in Pyodide, no micropip needed.

---

## Option B — BeeWare quick start

```bash
cd option-b-beeware
pip install briefcase

# Fastest path — no build step, runs immediately:
briefcase dev

# When ready to distribute:
briefcase create   # scaffold for current OS
briefcase build    # compile
briefcase run      # run compiled app
briefcase package  # produce .dmg / .msi / AppImage
```

For mobile targets (iOS requires macOS + Xcode; Android requires Android Studio):

```bash
briefcase create iOS  && briefcase run iOS
briefcase create android && briefcase run android
```

See `BUILDING.md` for the complete per-platform guide including signing, distribution, and the BriefCase command lifecycle.

---

## The five targets

| Target | Type | Period | Transit depth |
|---|---|---|---|
| WASP-18 b | Hot Jupiter | 0.94 days | 1.01% |
| WASP-12 b | Hot Jupiter | 1.09 days | 1.43% |
| HD 209458 b | Hot Jupiter | 3.52 days | 1.47% |
| TRAPPIST-1 e | Rocky — habitable zone | 6.10 days | 0.35% |
| Kepler-7 b | Inflated Hot Jupiter | 4.89 days | 0.83% |

Data is synthesised from published TESS orbital parameters — same PHASE / LC_DETREND / MODEL_INIT schema as Module 01.

---

## Anaconda connection

**PyScript** was launched by Anaconda at PyCon US 2022.  
**BeeWare** (Briefcase + Toga) is funded by Anaconda. The OSS engineering team is actively adding iOS and Android binary wheels for numpy and scikit-learn — tracked in BeeWare's monthly status updates.

Sources:  
- [anaconda.com/blog/beeware-mobile-python](https://www.anaconda.com/blog/beeware-mobile-python)  
- [pyscript.net](https://pyscript.net)
