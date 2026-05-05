#!/usr/bin/env python3
"""
Exoplanet Lightcurve Explorer implemented with Panel + Material UI.

Run with:
    panel serve app.py
"""

from __future__ import annotations

from dataclasses import dataclass

import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import panel as pn
import pandas as pd
import panel_material_ui as pmui
import param

from sklearn.ensemble import IsolationForest

pn.extension("tabulator")


TARGETS = {
    "wasp18b": {
        "name": "WASP-18 b",
        "type": "Hot Jupiter",
        "period": "0.94 days",
        "depth": 0.0101,
        "dur": 0.042,
        "n": 1800,
        "noise": 0.00032,
        "summary": (
            "Ultra-hot Jupiter, 0.94-day orbit. 10x Jupiter mass. "
            "TESS Sectors 2, 29, 69. Transit depth ~1.01%, duration ~1.9 h."
        ),
    },
    "wasp12b": {
        "name": "WASP-12 b",
        "type": "Hot Jupiter",
        "period": "1.09 days",
        "depth": 0.0143,
        "dur": 0.055,
        "n": 1600,
        "noise": 0.00038,
        "summary": (
            "One of the hottest, most inflated hot Jupiters. Tidal forces "
            "may be disrupting outer layers. Transit depth ~1.43%. "
            "Dayside ~2900 K."
        ),
    },
    "hd209458b": {
        "name": "HD 209458 b",
        "type": "Hot Jupiter",
        "period": "3.52 days",
        "depth": 0.0147,
        "dur": 0.065,
        "n": 2200,
        "noise": 0.00028,
        "summary": (
            "'Osiris' - first exoplanet confirmed to transit its star (1999) "
            "and first with detected atmosphere. Transit depth ~1.47%. "
            "TESS 2-min cadence."
        ),
    },
    "trappist1e": {
        "name": "TRAPPIST-1 e",
        "type": "Rocky - habitable zone",
        "period": "6.10 days",
        "depth": 0.00350,
        "dur": 0.038,
        "n": 3200,
        "noise": 0.00060,
        "summary": (
            "1.07 Earth radii, habitable zone, M8 ultracool dwarf host. "
            "Shallow 0.35% transit - high noise environment. "
            "Three potentially habitable planets in this system."
        ),
    },
    "kepler7b": {
        "name": "Kepler-7 b",
        "type": "Inflated Hot Jupiter",
        "period": "4.89 days",
        "depth": 0.0083,
        "dur": 0.072,
        "n": 2600,
        "noise": 0.00041,
        "summary": (
            "Density about styrofoam. Geometric albedo 0.35 mapped via Kepler "
            "phase curves - reflective cloud deck on western hemisphere. "
            "Transit depth ~0.83%, radius ~1.6 R_Jupiter."
        ),
    },
}

TARGET_KEYS = list(TARGETS.keys())
TARGET_NAME_TO_KEY = {cfg["name"]: key for key, cfg in TARGETS.items()}
TARGET_OPTIONS = list(TARGET_NAME_TO_KEY.keys())


def _synthesise(key: str, seed: int = 42):
    """
    Generate a phase-folded light curve from published parameters.
    Returns (phase, lc_detrend, model_init) as lists or numpy arrays.
    """
    t = TARGETS[key]
    depth, dur, n, noise_std = t["depth"], t["dur"], t["n"], t["noise"]


    rng = np.random.default_rng(seed)
    phase = np.sort(rng.uniform(-0.5, 0.5, n))

    def transit(ph):
        model = np.ones_like(ph)
        in_t = np.abs(ph) < dur
        x = np.abs(ph[in_t]) / dur
        mu = np.sqrt(np.maximum(1 - x**2, 0))
        ld = 1 - 0.4 * (1 - mu) - 0.3 * (1 - mu) ** 2
        model[in_t] = 1 - depth * ld * (1 - x**2)
        return model

    model = transit(phase)
    white = rng.normal(0, noise_std, n)
    red = np.convolve(
        rng.normal(0, noise_std * 0.35, n), np.ones(12) / 12, mode="same"
    )
    lc = model + white + red
    return phase, lc, model



def _validate(phase, lc, model) -> dict:
    """Schema + quality checks."""
    n = len(phase)
    nulls = sum(1 for v in lc if v != v)
    n_dupes = n - len(set(f"{p:.8f}" for p in phase))
    flux_std = np.std(lc)
    phase_min = np.min(phase)
    phase_max = np.max(phase)
    flux_min = np.min(lc)
    flux_max = np.max(lc) 
    return {
        "n_rows": n,
        "nulls": nulls,
        "n_dupes": n_dupes,
        "flux_std": flux_std,
        "phase_range": (phase_min, phase_max),
        "flux_range": (flux_min, flux_max),
    }


def _detect_anomalies(phase, lc, model) -> dict:
    """
    IsolationForest anomaly detection with threshold fallback.
    """
    xvals = np.column_stack([phase, lc, model])
    iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    labels = iso.fit_predict(xvals)
    scores = -iso.decision_function(xvals)
    is_anom = labels == -1
    n_anom = int(is_anom.sum())
    baseline = float(np.mean(np.array(lc)[~is_anom])) if (~is_anom).any() else 1.0
    min_flux = float(np.min(np.array(lc)[is_anom])) if n_anom > 0 else baseline
    depth_pct = (baseline - min_flux) / baseline * 100 if n_anom > 0 else 0.0

    anom_rows = [
        (phase[i], lc[i], model[i], scores[i])
        for i in range(len(phase))
        if is_anom[i]
    ]
    anom_rows.sort(key=lambda r: r[3], reverse=True)
    return {
        "n_anomalies": n_anom,
        "transit_depth_pct": depth_pct,
        "baseline": baseline,
        "anomaly_rows": anom_rows[:50],
        "scores": scores,
        "is_anomaly": is_anom,
        "method": "IsolationForest",
    }


@dataclass
class Field:
    label: str
    value: str = "-"


def tab_label(label: str, icon: str | None):
    return label if icon is None else f'<p style="display: inline-flex; align-items: center;"><span class="material-icons" style="font-size: 1.2em; padding-right: 1em;">{icon}</span><span>{label}</span></p>'


class LightcurveExplorer(pn.viewable.Viewer):
    target_name = param.Selector(default=TARGET_OPTIONS[0], objects=TARGET_OPTIONS)

    def __init__(self, **params):
        super().__init__(**params)
        self._log_lines: list[str] = []
        self._fields = {
            "target": Field("Target"),
            "n_rows": Field("Rows"),
            "nulls": Field("Null values"),
            "n_dupes": Field("Duplicate phases"),
            "flux_std": Field("Flux std dev"),
            "phase_range": Field("Phase range"),
            "flux_range": Field("Flux range"),
            "n_anomalies": Field("Anomalies detected"),
            "method": Field("Detection method"),
            "transit_depth_pct": Field("Est. transit depth"),
        }

        self.target_widget = pmui.Select.from_param(
            self.param.target_name,
            label="Target system",
            options=TARGET_OPTIONS,
        )
        self.run_button = pmui.Button(name="Run Analysis", color="primary", icon="analytics")
        self.run_button.on_click(self._on_run)

        self.info_pane = pn.pane.Markdown("", sizing_mode="stretch_width")
        self.log_widget = pmui.TextAreaInput(
            name="Pipeline log",
            value="Ready. Select a target and press Run Analysis.",
            disabled=True,
            height=250,
            sizing_mode="stretch_width",
        )
        self.stats_md = pn.pane.Markdown("", sizing_mode="stretch_width")
        self.table = pn.widgets.Tabulator(
            value=self._empty_table(),
            disabled=True,
            show_index=False,
            pagination="local",
            page_size=12,
            height=320,
            sizing_mode="stretch_width",
        )
        self.plot_pane = pn.pane.HoloViews(margin=(0, 10), sizing_mode="stretch_width")
        self.reports = pmui.Paper(
            pmui.Tabs(
                (tab_label('Pipeline log', 'terminal'), self.log_widget),
                (tab_label('Validation Report', 'fact_check'), self.stats_md),
                (tab_label('Anomalous Points', 'table_view'), self.table),
                (tab_label('Lightcurve + Anomaly Scores', "insights"), self.plot_pane),
                sizing_mode="stretch_width"
            ),
            margin=10,
            visible=False
        )
        self.info_card = pmui.Paper(
            self.info_pane, margin=10, sizing_mode="stretch_width"
        )
        self._refresh_info()

    def _empty_table(self):
        if pd is None:
            return []
        return pd.DataFrame(columns=["PHASE", "LC_DETREND", "MODEL_INIT", "Score"])

    @param.depends("target_name", watch=True)
    def _refresh_info(self):
        key = TARGET_NAME_TO_KEY[self.target_name]
        t = TARGETS[key]
        self.info_pane.object = (
            f"### {t['name']}\n"
            f"**Type:** {t['type']}  \n"
            f"**Period:** {t['period']}  \n"
            f"**Transit depth:** {t['depth'] * 100:.3f}%\n\n"
            f"{t['summary']}"
        )
        self.reports.visible = False

    def _log_write(self, line: str) -> None:
        self._log_lines.append(line)
        self.log_widget.value = "\n".join(self._log_lines)

    def _render_stats(self) -> None:
        lines = [f"- **{fld.label}:** {fld.value}" for fld in self._fields.values()]
        self.stats_md.object = "\n".join(lines)

    def _populate_stats(self, target_cfg: dict, report: dict, result: dict) -> None:
        self._fields["target"].value = target_cfg["name"]
        self._fields["n_rows"].value = f"{report['n_rows']:,}"
        self._fields["nulls"].value = str(report["nulls"])
        self._fields["n_dupes"].value = str(report["n_dupes"])
        self._fields["flux_std"].value = f"{report['flux_std']:.8f}"
        self._fields["phase_range"].value = (
            f"{report['phase_range'][0]:.4f} -> {report['phase_range'][1]:.4f}"
        )
        self._fields["flux_range"].value = (
            f"{report['flux_range'][0]:.6f} -> {report['flux_range'][1]:.6f}"
        )
        self._fields["n_anomalies"].value = str(result["n_anomalies"])
        self._fields["method"].value = result["method"]
        self._fields["transit_depth_pct"].value = f"{result['transit_depth_pct']:.4f}%"
        self._render_stats()

    def _populate_table(self, result: dict) -> None:
        rows = [
            {
                "PHASE": f"{r[0]:+.5f}",
                "LC_DETREND": f"{r[1]:.7f}",
                "MODEL_INIT": f"{r[2]:.7f}",
                "Score": f"{r[3]:.4f}",
            }
            for r in result["anomaly_rows"]
        ]
        if pd is None:
            self.table.value = rows
        else:
            self.table.value = pd.DataFrame(rows)

    def _build_plot(self, phase, lc, model, result: dict) -> None:
        if pd is None:
            self.plot_pane.object = "Plot unavailable: pandas is required."
            return

        results = pd.DataFrame(
            {
                "phase": phase,
                "lc_detrend": lc,
                "model_init": model,
                "anomaly_score": result["scores"],
                "is_anomaly": result["is_anomaly"],
            }
        )
        normal = results[~results["is_anomaly"]]
        anomalous = results[results["is_anomaly"]]

        normal_points = normal.hvplot.points(
            x="phase",
            y="lc_detrend",
            alpha=0.2,
            grid=True,
            label="Normal",
            legend="top_right",
            title=f"{TARGETS[TARGET_NAME_TO_KEY[self.target_name]]['name']} Light Curve - Anomaly Detection",
            xaxis=None,
            ylabel="Detrended Flux",
            autorange="y",
            responsive=True,
            min_height=400,
        )
        anomalous_points = anomalous.hvplot.points(
            x="phase",
            y="lc_detrend",
            color="crimson",
            label="Anomaly",
            responsive=True,
            min_height=400,
        )

        score_points = results.hvplot.points(
            x="phase",
            y="anomaly_score",
            color="darkorange",
            grid=True,
            xlabel="Phase (days)",
            ylabel="Anomaly Score (higher = more anomalous)",
            min_height=400,
            responsive=True
        )

        if len(anomalous):
            threshold = float(anomalous["anomaly_score"].min())
            hline = hv.HLine(threshold).opts(color="crimson", line_dash="dashed")
            score_panel = score_points * hline
        else:
            score_panel = score_points

        self.plot_pane.object = (normal_points * anomalous_points + score_panel).cols(1)

    def _on_run(self, _event=None) -> None:
        key = TARGET_NAME_TO_KEY[self.target_name]
        t = TARGETS[key]
        self.run_button.loading = True
        self.reports.visible = False
        self._log_lines = []
        self.log_widget.value = ""

        try:
            self._log_write(f"[1/4] Synthesising {t['name']} ({t['n']:,} points)...")
            phase, lc, model = _synthesise(key)
            self._log_write(f"      OK {len(phase):,} phase-folded observations")

            self._log_write("[2/4] Validating schema, nulls, flux std...")
            report = _validate(phase, lc, model)
            marker = "OK" if report["nulls"] == 0 else "WARN"
            self._log_write(
                f"      {marker} nulls={report['nulls']}  "
                f"flux_std={report['flux_std']:.6f}  "
                f"phase=[{report['phase_range'][0]:.3f}, {report['phase_range'][1]:.3f}]"
            )

            self._log_write("[3/4] Running anomaly detection...")
            result = _detect_anomalies(phase, lc, model)
            self._log_write(
                f"      OK Method: {result['method']}\n"
                f"         {result['n_anomalies']} anomalies  "
                f"depth ~= {result['transit_depth_pct']:.3f}%  "
                f"baseline = {result['baseline']:.6f}"
            )

            self._log_write("[4/4] Updating display...")
            self._populate_stats(t, report, result)
            self._populate_table(result)
            self._build_plot(phase, lc, model, result)
            self.reports.visible = True
            self._log_write(
                f"      OK Done - {t['name']}  -  "
                f"{result['n_anomalies']} anomalies  -  "
                f"depth ~= {result['transit_depth_pct']:.3f}%"
            )
        except Exception as exc:
            self._log_write(f"ERROR: {exc}")
        finally:
            self.run_button.loading = False

    def __panel__(self):
        return pmui.Page(
            title="Exoplanet Lightcurve Explorer",
            main=[self.info_card, self.reports],
            sidebar=[self.target_widget, self.run_button],
            theme_config={
                "light": {
                    "palette": {"primary": {"main": "#3f51b5", "contrastText": "#ffffff"}}
                },
                "dark": {
                    "palette": {"primary": {"main": "#90caf9", "contrastText": "#000000"}}
                },
            },
        )


LightcurveExplorer().servable()
