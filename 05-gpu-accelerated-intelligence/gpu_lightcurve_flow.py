"""
flows/gpu_lightcurve_flow.py

GPU-accelerated version of the LightcurveAnalysisFlow from
03-multi-agent-architecture.

What changed from Module 03:
  - ingest step: same conda env + same Polars pipeline
  - features step: NEW — CUDA Python rolling window computation (GPU)
  - analyze step: same LangGraph agent, now pointed at Nemotron via vLLM
  - join/end: unchanged

The @conda decorator per step is the Anaconda supply chain story:
each step has its own locked, auditable environment.
A CVE in vllm doesn't touch the ingest environment.
"""

from metaflow import FlowSpec, step, conda, retry, Parameter
import os


class GPULightcurveFlow(FlowSpec):
    """
    Analyze WASP-18 b and other TESS light curves at scale.
    Routes feature engineering to GPU and LLM inference to Nemotron.
    """

    targets = Parameter(
        "targets",
        help="Comma-separated list of light curve targets to analyze",
        default="wasp18b",
    )

    inference_url = Parameter(
        "inference_url",
        help="vLLM or NIM endpoint base URL",
        default="http://localhost:8000/v1",
    )

    # ── Step 1: Ingest ────────────────────────────────────────────────────────
    @step
    def start(self):
        """Fan out over targets."""
        self.target_list = [t.strip() for t in self.targets.split(",")]
        print(f"Processing {len(self.target_list)} targets: {self.target_list}")
        self.next(self.ingest, foreach="target_list")

    @conda(libraries={
        "polars":       ">=1.0",
        "scikit-learn": ">=1.4",
        "pydantic":     ">=2.0",
        "pyarrow":      ">=14.0",
    })
    @step
    def ingest(self):
        """
        Load and validate the light curve.
        Same Polars pipeline as Module 01 — no changes.
        This step's conda env is independently locked and auditable.
        """
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Import from Module 01 ingestion module
        try:
            from ingestion import load_lightcurve, validate_lightcurve, SCHEMA
            from pathlib import Path

            data_file = Path(f"{self.input}_lightcurve.csv")
            if not data_file.exists():
                # Fall back to WASP-18b data for demo
                data_file = Path("wasp18b_lightcurve.csv")

            df = load_lightcurve(data_file, SCHEMA)
            self.report = validate_lightcurve(df)

            # Store raw arrays for GPU feature step
            self.flux_array  = df["LC_DETREND"].to_numpy()
            self.model_array = df["MODEL_INIT"].to_numpy()

        except Exception as e:
            # Graceful fallback with synthetic data for demo purposes
            import numpy as np
            rng = np.random.default_rng(42)
            n = 1500
            self.flux_array  = rng.normal(1.0, 0.0003, n).astype("float32")
            self.model_array = self.flux_array + rng.normal(0, 0.00005, n).astype("float32")

            from pydantic import BaseModel
            class MockReport(BaseModel):
                nulls: dict = {"PHASE": 0, "LC_DETREND": 0, "MODEL_INIT": 0}
                phase_range: tuple = (-0.5, 0.5)
                flux_range: tuple = (0.989, 1.001)
                flux_std: float = 0.00031
                duplicate_phases: int = 0

            self.report = MockReport()
            print(f"[ingest] Warning: using synthetic data ({e})")

        print(f"[ingest/{self.input}] Loaded {len(self.flux_array)} points, "
              f"flux_std={self.report.flux_std:.8f}")
        self.next(self.compute_features)

    # ── Step 2: GPU Feature Engineering ──────────────────────────────────────
    @conda(libraries={
        "cuda-python": ">=12.0",
        "numpy":       ">=1.26",
    })
    @step
    def compute_features(self):
        """
        GPU-accelerated rolling window feature engineering.
        Uses CUDA Python 1.0 to compute the same five features as
        Module 01 but on GPU — critical for batch processing at scale.

        Falls back to CPU numpy if CUDA is not available.
        This step's conda env includes cuda-python independently —
        a CVE here doesn't affect the ingest or analysis envs.
        """
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        from cuda_kernels.rolling_features import gpu_rolling_features

        self.features = gpu_rolling_features(
            flux=self.flux_array,
            model=self.model_array,
            window=15,
        )

        # IsolationForest anomaly detection on GPU features
        from sklearn.ensemble import IsolationForest
        import numpy as np

        X = np.column_stack([
            self.features["residual"],
            self.features["rolling_std"],
            self.features["flux_zscore"],
            self.features["abs_residual"],
        ])

        iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        labels = iso.fit_predict(X)
        anomaly_scores = -iso.decision_function(X)

        is_anomaly = labels == -1
        n_anomalies = int(is_anomaly.sum())

        if n_anomalies > 0:
            anomalous_flux = self.flux_array[is_anomaly]
            baseline_flux  = float(self.flux_array[~is_anomaly].mean())
            min_flux       = float(anomalous_flux.min())
            transit_depth  = (baseline_flux - min_flux) / baseline_flux * 100
            transit_phases = np.where(is_anomaly)[0]
        else:
            baseline_flux = float(self.flux_array.mean())
            transit_depth = 0.0
            transit_phases = []

        self.anomaly_result = {
            "n_anomalous_points": n_anomalies,
            "transit_depth_pct":  round(transit_depth, 6),
            "transit_start":      float(transit_phases.min()) if len(transit_phases) else None,
            "transit_end":        float(transit_phases.max()) if len(transit_phases) else None,
            "baseline_flux":      round(baseline_flux, 8),
        }

        print(f"[features/{self.input}] {n_anomalies} anomalies, "
              f"transit_depth={transit_depth:.4f}%")
        self.next(self.analyze)

    # ── Step 3: Nemotron Analysis ─────────────────────────────────────────────
    @conda(libraries={
        "openai":    ">=1.30",
        "pydantic":  ">=2.0",
        "langgraph": ">=0.2",
    })
    @retry(times=3)
    @step
    def analyze(self):
        """
        LangGraph AnalysisAgent reasoning over validated pipeline output.
        Pointed at Nemotron via vLLM — endpoint set via inference_url parameter.
        @retry handles transient inference failures without losing upstream work.

        The agent code is identical to Module 03 — only base_url changed.
        """
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

        # Set inference endpoint for this step
        os.environ["INFERENCE_BASE_URL"] = self.inference_url
        os.environ["INFERENCE_API_KEY"]  = os.environ.get("NVIDIA_API_KEY", "not-needed")
        os.environ["INFERENCE_MODEL"]    = os.environ.get(
            "INFERENCE_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
        )

        from agents.analysis_agent import run_analysis_agent

        self.result = run_analysis_agent(
            report=self.report,
            anomaly_result=self.anomaly_result,
            verbose=True,
        )

        print(f"[analyze/{self.input}] classification={self.result.get('classification')}, "
              f"confidence={self.result.get('confidence')}")
        self.next(self.join)

    # ── Step 4: Collect results ───────────────────────────────────────────────
    @step
    def join(self, inputs):
        """Merge results from all parallel branches."""
        self.all_results = {}
        for inp in inputs:
            self.all_results[inp.input] = {
                "report":        inp.report.model_dump() if hasattr(inp.report, "model_dump") else vars(inp.report),
                "anomaly":       inp.anomaly_result,
                "classification": inp.result,
            }
        self.next(self.end)

    @step
    def end(self):
        """Print summary and store final artifact."""
        print("\n" + "=" * 60)
        print("GPU Lightcurve Analysis — Results")
        print("=" * 60)
        for target, data in self.all_results.items():
            cls    = data["classification"]
            anom   = data["anomaly"]
            print(f"\n{target}:")
            print(f"  Classification:  {cls.get('classification', 'N/A')}")
            print(f"  Confidence:      {cls.get('confidence', 0):.2f}")
            print(f"  Transit depth:   {anom.get('transit_depth_pct', 0):.4f}%")
            print(f"  Anomalous pts:   {anom.get('n_anomalous_points', 0)}")
            print(f"  Summary:         {cls.get('reasoning_summary', '')[:80]}...")


if __name__ == "__main__":
    GPULightcurveFlow()
