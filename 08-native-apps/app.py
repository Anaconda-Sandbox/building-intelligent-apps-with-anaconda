"""
src/lightcurve/app.py

Exoplanet Lightcurve Explorer — BeeWare Toga native app.
Module 08, Option B.

Same five stellar targets and same IsolationForest pipeline as the PyScript
demo (Option A) — delivered here as a native OS app via Briefcase + Toga.

Toga widget mapping per platform:
  macOS:   NSWindow, NSSegmentedControl → selection, NSTableView → table
  Windows: Win32 Window, ComboBox, ListView
  Linux:   GtkWindow, GtkComboBoxText, GtkTreeView

Briefcase packages this single codebase into:
  macOS:   .app + .dmg
  Windows: .msi
  Linux:   AppImage / .deb / .rpm
  iOS:     Xcode project → App Store .ipa   (requires macOS + Xcode)
  Android: Gradle project → .aab / .apk     (requires Android Studio)

BeeWare is funded by Anaconda:
https://www.anaconda.com/blog/beeware-mobile-python
"""

from __future__ import annotations

import sys

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW, CENTER, LEFT, RIGHT

# ── numpy availability flag ────────────────────────────────────────────────────
# On mobile targets where numpy wheels are not yet available,
# set USE_NUMPY = False to fall back to a pure-Python synthesiser.
try:
    import numpy as _np
    USE_NUMPY = True
except ImportError:
    USE_NUMPY = False

# ── Target catalogue ───────────────────────────────────────────────────────────
# Matches Option A (PyScript) exactly — same targets, same parameters.

TARGETS = {
    "wasp18b": {
        "name":   "WASP-18 b",
        "type":   "Hot Jupiter",
        "period": "0.94 days",
        "depth":  0.0101,
        "dur":    0.042,
        "n":      1800,
        "noise":  0.00032,
        "summary": (
            "Ultra-hot Jupiter, 0.94-day orbit. 10× Jupiter mass. "
            "TESS Sectors 2, 29, 69. Transit depth ~1.01%, duration ~1.9 h."
        ),
    },
    "wasp12b": {
        "name":   "WASP-12 b",
        "type":   "Hot Jupiter",
        "period": "1.09 days",
        "depth":  0.0143,
        "dur":    0.055,
        "n":      1600,
        "noise":  0.00038,
        "summary": (
            "One of the hottest, most inflated hot Jupiters. Tidal forces "
            "may be disrupting outer layers. Transit depth ~1.43%. "
            "Dayside ~2900 K."
        ),
    },
    "hd209458b": {
        "name":   "HD 209458 b",
        "type":   "Hot Jupiter",
        "period": "3.52 days",
        "depth":  0.0147,
        "dur":    0.065,
        "n":      2200,
        "noise":  0.00028,
        "summary": (
            "'Osiris' — first exoplanet confirmed to transit its star (1999) "
            "and first with detected atmosphere. Transit depth ~1.47%. "
            "TESS 2-min cadence."
        ),
    },
    "trappist1e": {
        "name":   "TRAPPIST-1 e",
        "type":   "Rocky — habitable zone",
        "period": "6.10 days",
        "depth":  0.00350,
        "dur":    0.038,
        "n":      3200,
        "noise":  0.00060,
        "summary": (
            "1.07 Earth radii, habitable zone, M8 ultracool dwarf host. "
            "Shallow 0.35% transit — high noise environment. "
            "Three potentially habitable planets in this system."
        ),
    },
    "kepler7b": {
        "name":   "Kepler-7 b",
        "type":   "Inflated Hot Jupiter",
        "period": "4.89 days",
        "depth":  0.0083,
        "dur":    0.072,
        "n":      2600,
        "noise":  0.00041,
        "summary": (
            "Density ≈ styrofoam. Geometric albedo 0.35 mapped via Kepler "
            "phase curves — reflective cloud deck on western hemisphere. "
            "Transit depth ~0.83%, radius ~1.6 R_Jupiter."
        ),
    },
}

TARGET_KEYS  = list(TARGETS.keys())
TARGET_NAMES = [TARGETS[k]["name"] for k in TARGET_KEYS]

# ── Pipeline ───────────────────────────────────────────────────────────────────

def _synthesise(key: str, seed: int = 42):
    """
    Generate a phase-folded light curve from published parameters.
    Returns (phase, lc_detrend, model_init) as plain Python lists
    when USE_NUMPY is False, or numpy arrays when True.
    """
    t = TARGETS[key]
    depth, dur, n, noise_std = t["depth"], t["dur"], t["n"], t["noise"]

    if USE_NUMPY:
        import numpy as np
        rng   = np.random.default_rng(seed)
        phase = np.sort(rng.uniform(-0.5, 0.5, n))

        def transit(ph):
            model = np.ones_like(ph)
            in_t  = np.abs(ph) < dur
            x     = np.abs(ph[in_t]) / dur
            mu    = np.sqrt(np.maximum(1 - x**2, 0))
            ld    = 1 - 0.4 * (1 - mu) - 0.3 * (1 - mu) ** 2
            model[in_t] = 1 - depth * ld * (1 - x**2)
            return model

        model = transit(phase)
        white = rng.normal(0, noise_std, n)
        red   = np.convolve(
            rng.normal(0, noise_std * 0.35, n), np.ones(12) / 12, mode="same"
        )
        lc = model + white + red
        return phase, lc, model

    else:
        # Pure-Python fallback (slower, for mobile without numpy)
        import random, math
        rng = random.Random(seed)
        phase = sorted(rng.uniform(-0.5, 0.5) for _ in range(n))

        def transit_val(ph):
            x = abs(ph) / dur
            if x >= 1.0:
                return 1.0
            mu = math.sqrt(max(1 - x * x, 0))
            ld = 1 - 0.4 * (1 - mu) - 0.3 * (1 - mu) ** 2
            return 1 - depth * ld * (1 - x * x)

        model = [transit_val(p) for p in phase]
        lc    = [m + rng.gauss(0, noise_std) for m in model]
        return phase, lc, model


def _validate(phase, lc, model) -> dict:
    """Schema + quality checks — mirrors Module 01 ValidationReport."""
    n      = len(phase)
    nulls  = sum(1 for v in lc if v != v)   # NaN check
    n_dupes = n - len(set(f"{p:.8f}" for p in phase))

    if USE_NUMPY:
        import numpy as np
        flux_std  = float(np.std(lc))
        phase_min = float(np.min(phase))
        phase_max = float(np.max(phase))
        flux_min  = float(np.min(lc))
        flux_max  = float(np.max(lc))
    else:
        flux_std  = (sum((v - sum(lc)/n)**2 for v in lc) / n) ** 0.5
        phase_min = min(phase)
        phase_max = max(phase)
        flux_min  = min(lc)
        flux_max  = max(lc)

    return {
        "n_rows":      n,
        "nulls":       nulls,
        "n_dupes":     n_dupes,
        "flux_std":    flux_std,
        "phase_range": (phase_min, phase_max),
        "flux_range":  (flux_min, flux_max),
    }


def _detect_anomalies(phase, lc, model) -> dict:
    """
    IsolationForest anomaly detection.
    Falls back to a simple threshold method when scikit-learn unavailable.
    """
    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        X       = np.column_stack([phase, lc, model])
        iso     = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        labels  = iso.fit_predict(X)
        scores  = -iso.decision_function(X)
        is_anom = labels == -1
        n_anom  = int(is_anom.sum())
        baseline   = float(np.mean(np.array(lc)[~is_anom])) if (~is_anom).any() else 1.0
        min_flux   = float(np.min(np.array(lc)[is_anom]))    if n_anom > 0 else baseline
        depth_pct  = (baseline - min_flux) / baseline * 100  if n_anom > 0 else 0.0

        anom_rows = [
            (phase[i], lc[i], model[i], scores[i])
            for i in range(len(phase))
            if is_anom[i]
        ]
        anom_rows.sort(key=lambda r: r[3], reverse=True)
        return {
            "n_anomalies":       n_anom,
            "transit_depth_pct": depth_pct,
            "baseline":          baseline,
            "anomaly_rows":      anom_rows[:50],
            "method":            "IsolationForest",
        }

    except Exception:
        # Pure-Python threshold fallback
        mean_lc = sum(lc) / len(lc)
        std_lc  = (sum((v - mean_lc)**2 for v in lc) / len(lc)) ** 0.5
        threshold = mean_lc - 2.5 * std_lc
        anom_rows = [
            (phase[i], lc[i], model[i], abs(lc[i] - mean_lc) / std_lc)
            for i in range(len(lc))
            if lc[i] < threshold
        ]
        anom_rows.sort(key=lambda r: r[3], reverse=True)
        baseline  = mean_lc
        min_flux  = min(lc) if lc else baseline
        depth_pct = (baseline - min_flux) / baseline * 100
        return {
            "n_anomalies":       len(anom_rows),
            "transit_depth_pct": depth_pct,
            "baseline":          baseline,
            "anomaly_rows":      anom_rows[:50],
            "method":            "2.5σ threshold (fallback)",
        }


# ── App ────────────────────────────────────────────────────────────────────────

class LightcurveApp(toga.App):
    """
    Exoplanet Lightcurve Explorer.

    Widget hierarchy:
      MainWindow
        ScrollContainer
          Box (COLUMN, outer)
            ├── Box (header)
            ├── Divider
            ├── Box (selector row)
            ├── Box (info box)
            ├── Box (run button + status)
            ├── Divider
            ├── Box (pipeline log)
            ├── Divider
            ├── Box (stats section)   — visible after run
            └── Box (anomaly table)  — visible after run
    """

    def startup(self):
        self._current_key = TARGET_KEYS[0]
        self._ran = False

        outer = toga.Box(style=Pack(direction=COLUMN, padding=16, gap=12))

        # ── Header ────────────────────────────────────────────────────────────
        title = toga.Label(
            "🌟 Exoplanet Lightcurve Explorer",
            style=Pack(font_size=17, font_weight="bold"),
        )
        subtitle = toga.Label(
            "Module 08 · Option B  ·  BeeWare (Briefcase + Toga)  ·  Native OS widgets",
            style=Pack(font_size=10, color="#888888", padding_top=2),
        )
        outer.add(toga.Box(
            children=[title, subtitle],
            style=Pack(direction=COLUMN, padding_bottom=4),
        ))
        outer.add(toga.Divider())

        # ── Target selector ───────────────────────────────────────────────────
        selector_label = toga.Label(
            "Target system:",
            style=Pack(font_size=12, padding_right=8, alignment=CENTER),
        )
        self._selector = toga.Selection(
            items=TARGET_NAMES,
            on_change=self._on_target_change,
            style=Pack(flex=1),
        )
        run_btn = toga.Button(
            "▶  Run Analysis",
            on_press=self._on_run,
            style=Pack(padding_left=8),
        )
        self._run_btn = run_btn

        selector_row = toga.Box(
            children=[selector_label, self._selector, run_btn],
            style=Pack(direction=ROW, gap=8, alignment=CENTER),
        )
        outer.add(selector_row)

        # ── Target info box ───────────────────────────────────────────────────
        self._info_label = toga.Label(
            "",
            style=Pack(font_size=11, color="#666666", padding=(6, 0)),
        )
        outer.add(self._info_label)
        outer.add(toga.Divider())

        # ── Pipeline log ──────────────────────────────────────────────────────
        log_title = toga.Label(
            "Pipeline log",
            style=Pack(font_size=11, font_weight="bold", color="#888888"),
        )
        self._log = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, height=140, font_family="monospace", font_size=10),
        )
        outer.add(log_title)
        outer.add(self._log)
        outer.add(toga.Divider())

        # ── Stats section ─────────────────────────────────────────────────────
        self._stats_box = self._build_stats_box()
        outer.add(self._stats_box)

        # ── Anomaly table ─────────────────────────────────────────────────────
        self._table_box = self._build_table_box()
        outer.add(self._table_box)

        # ── Assemble window ───────────────────────────────────────────────────
        scroll = toga.ScrollContainer(content=outer, horizontal=False)
        self.main_window = toga.MainWindow(
            title="Lightcurve Explorer",
            size=(860, 680),
        )
        self.main_window.content = scroll
        self.main_window.show()

        # Populate info for default selection
        self._refresh_info()
        self._log_write("Ready. Select a target and press Run Analysis.")

    # ── Widget builders ────────────────────────────────────────────────────────

    def _build_stats_box(self) -> toga.Box:
        self._stat_lbl: dict[str, toga.Label] = {}
        fields = [
            ("target",           "Target"),
            ("n_rows",           "Rows"),
            ("nulls",            "Null values"),
            ("n_dupes",          "Duplicate phases"),
            ("flux_std",         "Flux std dev"),
            ("phase_range",      "Phase range"),
            ("flux_range",       "Flux range"),
            ("n_anomalies",      "Anomalies detected"),
            ("method",           "Detection method"),
            ("transit_depth_pct","Est. transit depth"),
        ]
        rows = []
        for key, disp in fields:
            k_lbl = toga.Label(
                f"{disp}:",
                style=Pack(font_size=11, font_weight="bold", width=200),
            )
            v_lbl = toga.Label("—", style=Pack(font_size=11, flex=1))
            self._stat_lbl[key] = v_lbl
            rows.append(toga.Box(
                children=[k_lbl, v_lbl],
                style=Pack(direction=ROW, gap=8, padding=(2, 0)),
            ))

        title = toga.Label(
            "Validation Report",
            style=Pack(font_size=13, font_weight="bold", padding_bottom=8),
        )
        box = toga.Box(
            children=[title] + rows,
            style=Pack(direction=COLUMN, gap=2, padding_top=4),
        )
        box.style.visibility = "hidden"
        return box

    def _build_table_box(self) -> toga.Box:
        title = toga.Label(
            "Anomalous Points  (top 50, sorted by score)",
            style=Pack(font_size=13, font_weight="bold", padding_bottom=8),
        )
        self._table = toga.Table(
            headings=["PHASE", "LC_DETREND", "MODEL_INIT", "Score"],
            style=Pack(flex=1, height=320),
        )
        box = toga.Box(
            children=[title, self._table],
            style=Pack(direction=COLUMN, gap=8, padding_top=12),
        )
        box.style.visibility = "hidden"
        return box

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _log_write(self, line: str):
        existing = self._log.value or ""
        self._log.value = (existing + line + "\n").lstrip("\n")

    def _refresh_info(self):
        t = TARGETS[self._current_key]
        self._info_label.text = (
            f"{t['name']}  ·  {t['type']}  ·  Period: {t['period']}  ·  "
            f"Transit depth: {t['depth']*100:.3f}%\n{t['summary']}"
        )

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_target_change(self, widget):
        idx = TARGET_NAMES.index(widget.value)
        self._current_key = TARGET_KEYS[idx]
        self._refresh_info()

    def _on_run(self, widget):
        key = self._current_key
        t   = TARGETS[key]

        self._run_btn.enabled = False
        self._log.value = ""
        self._stats_box.style.visibility = "hidden"
        self._table_box.style.visibility = "hidden"

        try:
            # Step 1 — synthesise
            self._log_write(f"[1/4] Synthesising {t['name']} ({t['n']:,} points)…")
            phase, lc, model = _synthesise(key)
            self._log_write(f"      ✓ {len(phase):,} phase-folded observations")

            # Step 2 — validate
            self._log_write("[2/4] Validating schema · nulls · flux std…")
            report = _validate(phase, lc, model)
            nf = "✓" if report["nulls"] == 0 else "✗"
            self._log_write(
                f"      {nf} nulls={report['nulls']}  "
                f"flux_std={report['flux_std']:.6f}  "
                f"phase=[{report['phase_range'][0]:.3f}, {report['phase_range'][1]:.3f}]"
            )

            # Step 3 — anomaly detection
            self._log_write("[3/4] Running anomaly detection…")
            result = _detect_anomalies(phase, lc, model)
            self._log_write(
                f"      ✓ Method: {result['method']}\n"
                f"        {result['n_anomalies']} anomalies  "
                f"depth ≈ {result['transit_depth_pct']:.3f}%  "
                f"baseline = {result['baseline']:.6f}"
            )

            # Step 4 — populate UI
            self._log_write("[4/4] Updating display…")
            self._populate_stats(t, report, result)
            self._populate_table(result)
            self._stats_box.style.visibility = "visible"
            self._table_box.style.visibility = "visible"
            self._log_write(
                f"      ✓ Done — {t['name']}  ·  "
                f"{result['n_anomalies']} anomalies  ·  "
                f"depth ≈ {result['transit_depth_pct']:.3f}%"
            )

        except Exception as e:
            self._log_write(f"✗ Error: {e}")
        finally:
            self._run_btn.enabled = True

    # ── UI population ──────────────────────────────────────────────────────────

    def _populate_stats(self, t: dict, report: dict, result: dict):
        self._stat_lbl["target"].text = t["name"]
        self._stat_lbl["n_rows"].text = f'{report["n_rows"]:,}'
        self._stat_lbl["nulls"].text  = str(report["nulls"])
        self._stat_lbl["n_dupes"].text = str(report["n_dupes"])
        self._stat_lbl["flux_std"].text = f'{report["flux_std"]:.8f}'
        self._stat_lbl["phase_range"].text = (
            f'{report["phase_range"][0]:.4f} → {report["phase_range"][1]:.4f}'
        )
        self._stat_lbl["flux_range"].text = (
            f'{report["flux_range"][0]:.6f} → {report["flux_range"][1]:.6f}'
        )
        self._stat_lbl["n_anomalies"].text = str(result["n_anomalies"])
        self._stat_lbl["method"].text = result["method"]
        self._stat_lbl["transit_depth_pct"].text = f'{result["transit_depth_pct"]:.4f}%'

    def _populate_table(self, result: dict):
        rows = [
            (
                f'{r[0]:+.5f}',
                f'{r[1]:.7f}',
                f'{r[2]:.7f}',
                f'{r[3]:.4f}',
            )
            for r in result["anomaly_rows"]
        ]
        self._table.data = rows


def main() -> LightcurveApp:
    return LightcurveApp(
        "Lightcurve Explorer",
        "com.anaconda.demos.lightcurve",
    )
