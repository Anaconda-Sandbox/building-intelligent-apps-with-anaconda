# 09 — Panel App
**Estimated time:** Under 7 minutes
**Prerequisites:** None beyond Module 01 — this is a standalone addendum showing the pipeline delivered in a new context.

---

## The point

Modules 01–07 built a production-grade intelligent pipeline. This module answers one question: **once you have a validated pipeline, how do you turn it into an interactive app a non-Python user can drive?**

One demonstration. Same five stellar targets. Same IsolationForest pipeline. Same validation schema as `ingestion.py` from Module 01. What changes is the delivery layer.

```
Panel + Material UI    Python web app served by a Bokeh server
                       Reactive widgets bound to param.Parameter values
                       hvplot/HoloViews for the lightcurve + score plots
                       panel-material-ui for polished MUI components
                       Run: panel serve app.py → localhost:5006
```

---

## Module structure

```
08-panel-app/
├── README.md                  ← this file
├── 08_panel_app.ipynb         ← narrated demo (7 min, pre-run)
└── app.py                     ← the entire app — Panel + pipeline
```

A single file. The pipeline functions (`_synthesise`, `_validate`, `_detect_anomalies`) live alongside a `LightcurveExplorer` class that wires them to widgets, a Tabulator table, and HoloViews plots.

---

## Quick start

```bash
pip install panel panel-material-ui hvplot scikit-learn pandas numpy
panel serve app.py --show
# Opens http://localhost:5006/app
```

No CSV needed. No build step. Select a target from the sidebar and press **Run Analysis**.

The Bokeh server runs the pipeline in a Python process and streams updates to the browser over a websocket — widgets, plots, and the anomaly table all stay in sync.

---

## What you get

The app surfaces the Module 01 pipeline as four tabs, all built from the same run:

- **Pipeline log** — the four-stage trace (synthesise → validate → detect → render), exactly the output `ingestion.py` would print to stdout.
- **Validation Report** — row count, nulls, duplicates, flux std dev, phase/flux ranges. The schema check, made visible.
- **Anomalous Points** — top 50 anomalies by IsolationForest score, in a sortable Tabulator grid.
- **Lightcurve + Anomaly Scores** — phase-folded flux with anomalies in crimson, plus the score panel with a dashed threshold line.

The sidebar holds the target selector and the Run button. The info card up top renders the target's published parameters as Markdown and refreshes reactively when the selection changes (`@param.depends("target_name", watch=True)`).

---

## How the pieces fit

```
param.Selector ──► panel_material_ui.Select ──► target_name
                                                    │
                                                    ▼
                                        (user clicks Run)
                                                    │
                            ┌───────────────────────┴───────────────────────┐
                            ▼                                               ▼
                   _synthesise(key)                            log_widget.value updates live
                            │
                            ▼
                   _validate(phase, lc, model)  ──► stats_md (Markdown pane)
                            │
                            ▼
                   _detect_anomalies(...)       ──► table (Tabulator)
                            │                  ──► plot_pane (HoloViews)
                            ▼
                  reports.visible = True
```

Every reactive piece is a `param.Parameter` or a Panel widget bound to one. No global state, no manual callbacks beyond the Run button.

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

**Panel** and **HoloViews/hvplot** are part of the [HoloViz](https://holoviz.org) ecosystem, stewarded by Anaconda. Panel sits on top of Bokeh and adds the reactive `param`-based widget layer used throughout this app.

**panel-material-ui** brings Material Design components (Select, Button, Paper, Tabs) to Panel apps — the polish you see in the sidebar and tab bar comes from there rather than vanilla Bokeh widgets.

Sources:
- [panel.holoviz.org](https://panel.holoviz.org)
- [panel-material-ui.holoviz.org](https://panel-material-ui.holoviz.org)
- [hvplot.holoviz.org](https://hvplot.holoviz.org)