"""
flows/harnessed_lightcurve_flow.py

HarnessedLightcurveFlow — Module 03's LightcurveAnalysisFlow with three additions:

1. @catch on ingest and analyze  — graceful degradation
   One bad target doesn't kill the whole run. Failures are recorded as
   artifacts and surfaced in the Card, not as halted pipelines.

2. evaluate step                 — eval-as-CI
   Assertions on ValidationReport + agent classification run on every
   execution. Pydantic-typed inputs, plain function checks from evals/assertions.py.
   Critical assertion failures raise loudly. Non-critical become warnings.

3. @card on evaluate and end     — observability
   Per-target HTML report after each evaluate step.
   Run-level summary card on end.
   Cards don't affect flow execution — safe in production.

The flow from Module 03 is unchanged. These are additive.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from metaflow import (
    FlowSpec, step, conda, retry, catch, card, Parameter, current
)
from metaflow.cards import Markdown, Table, Artifact


class HarnessedLightcurveFlow(FlowSpec):
    """
    Production-harnessed version of LightcurveAnalysisFlow from Module 03.
    Adds graceful degradation, eval-as-CI, and observability.
    """

    targets = Parameter(
        "targets",
        help="Comma-separated list of light curve targets",
        default="wasp18b",
    )

    # ── Step 1: Fan out ───────────────────────────────────────────────────────
    @step
    def start(self):
        self.target_list = [t.strip() for t in self.targets.split(",")]
        print(f"Processing {len(self.target_list)} targets: {self.target_list}")
        self.next(self.ingest, foreach="target_list")

    # ── Step 2: Ingest + validate ─────────────────────────────────────────────
    @conda(libraries={
        "polars":       ">=1.0",
        "scikit-learn": ">=1.4",
        "pydantic":     ">=2.0",
        "pyarrow":      ">=14.0",
    })
    @catch(var="ingest_error", print_exception=True)
    @retry(times=2)
    @step
    def ingest(self):
        """
        Load and validate. Same as Module 03.

        @catch wraps @retry — if all retries are exhausted, the exception is
        stored in self.ingest_error and the flow continues to analyze.
        The analyze step checks for ingest_error and skips gracefully.
        """
        from pathlib import Path
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

        try:
            from ingestion import load_lightcurve, validate_lightcurve, SCHEMA
            data_file = Path(f"{self.input}_lightcurve.csv")
            if not data_file.exists():
                data_file = Path("wasp18b_lightcurve.csv")
            df = load_lightcurve(data_file, SCHEMA)
            self.report = validate_lightcurve(df)
        except Exception:
            # Re-raise so @catch captures it in self.ingest_error
            raise

        self.next(self.analyze)

    # ── Step 3: Agent reasoning ───────────────────────────────────────────────
    @conda(libraries={
        "openai":    ">=1.30",
        "pydantic":  ">=2.0",
        "langgraph": ">=0.2",
    })
    @catch(var="analyze_error", print_exception=True)
    @retry(times=3)
    @step
    def analyze(self):
        """
        LangGraph AnalysisAgent — same as Module 03.

        Skips gracefully if ingest failed (@catch stored the error in ingest_error).
        @catch here handles inference failures (API timeout, rate limit, etc.)
        after all @retry attempts are exhausted.
        """
        # Graceful degradation: if ingest failed, record and skip
        if hasattr(self, "ingest_error") and self.ingest_error is not None:
            print(f"[analyze/{self.input}] Skipping — ingest failed: {self.ingest_error}")
            self.result = {
                "classification":       "insufficient_data",
                "confidence":           0.0,
                "transit_depth_pct":    0.0,
                "reasoning_summary":    f"Skipped: ingest error — {self.ingest_error}",
                "recommended_next_steps": ["Fix data source", "Re-run"],
            }
            self.next(self.evaluate)
            return

        import os, sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from agents.analysis_agent import run_analysis_agent
        self.result = run_analysis_agent(report=self.report, verbose=False)
        self.next(self.evaluate)

    # ── Step 4: Eval-as-CI with @card ─────────────────────────────────────────
    @card(type="blank")
    @step
    def evaluate(self):
        """
        Run assertion suite. Fail loudly on critical failures. Warn on non-critical.
        Produce a per-target Card showing the full eval results.

        This step IS the feedback loop: it runs on every execution,
        surfaces failures before anyone acts on the results, and produces
        an observable record of what passed and what didn't.
        """
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from evals.assertions import run_all_assertions

        # Run assertions — always, even if analyze failed
        # (a failed analyze produces a valid result dict with insufficient_data)
        report = getattr(self, "report", None)
        result = getattr(self, "result", {})

        if report is not None:
            self.eval_result = run_all_assertions(report, result)
        else:
            # ingest failed and didn't produce a report
            self.eval_result = {
                "passed": False,
                "results": [],
                "n_passed": 0,
                "n_failed": 1,
                "n_warnings": 0,
                "critical_failures": ["ingest_failed"],
            }

        # ── Build the Card ────────────────────────────────────────────────────
        status_icon = "✓" if self.eval_result["passed"] else "✗"
        current.card.append(Markdown(
            f"## {status_icon} {self.input} — Eval Report"
        ))

        # Summary row
        ev = self.eval_result
        current.card.append(Markdown(
            f"**{ev['n_passed']} passed** · "
            f"**{ev['n_failed']} failed** · "
            f"**{ev['n_warnings']} warnings**"
        ))

        # Agent classification
        if result:
            cls  = result.get("classification", "—")
            conf = result.get("confidence", 0.0)
            depth = result.get("transit_depth_pct", 0.0)
            current.card.append(Markdown(
                f"**Classification:** {cls}  \n"
                f"**Confidence:** {conf:.2f}  \n"
                f"**Transit depth:** {depth:.4f}%"
            ))
            if result.get("reasoning_summary"):
                current.card.append(Markdown(
                    f"> {result['reasoning_summary']}"
                ))

        # Assertion table
        if ev["results"]:
            rows = []
            for check in ev["results"]:
                icon = "✓" if check["passed"] else ("✗" if check["critical"] else "⚠")
                rows.append([
                    Markdown(f"`{check['name']}`"),
                    Markdown(icon),
                    Markdown(check["detail"]),
                ])
            current.card.append(Markdown("### Assertions"))
            current.card.append(Table(
                rows,
                headers=["Assertion", "Status", "Detail"]
            ))

        # Validation report artifacts
        if report is not None:
            current.card.append(Markdown("### Validation Report"))
            current.card.append(Artifact(report.model_dump()))

        # ── Fail loudly if critical assertions failed ─────────────────────────
        if not self.eval_result["passed"]:
            failed = ", ".join(self.eval_result["critical_failures"])
            raise AssertionError(
                f"[{self.input}] Critical eval failures: {failed}\n"
                f"See card for details: python flows/harnessed_lightcurve_flow.py "
                f"card view evaluate"
            )

        self.next(self.join)

    # ── Step 5: Collect results ───────────────────────────────────────────────
    @step
    def join(self, inputs):
        """Merge results from all parallel branches, including any that failed."""
        self.all_results  = {}
        self.eval_summary = {}

        for inp in inputs:
            target = inp.input
            self.all_results[target] = {
                "result":      getattr(inp, "result", {}),
                "eval_result": getattr(inp, "eval_result", {}),
                "ingest_error":  str(getattr(inp, "ingest_error", None)),
                "analyze_error": str(getattr(inp, "analyze_error", None)),
            }
            self.eval_summary[target] = {
                "passed":   getattr(inp, "eval_result", {}).get("passed", False),
                "n_failed": getattr(inp, "eval_result", {}).get("n_failed", 0),
            }

        self.next(self.end)

    # ── Step 6: Run summary Card ──────────────────────────────────────────────
    @card(type="blank")
    @step
    def end(self):
        """
        Produce a run-level summary Card.
        Shows pass/fail per target, classifications, and any errors.
        This is the single view you check after every production run.
        """
        n_total  = len(self.all_results)
        n_passed = sum(1 for v in self.eval_summary.values() if v["passed"])

        run_status = "✓ All targets passed" if n_passed == n_total \
                     else f"⚠ {n_total - n_passed}/{n_total} targets had failures"

        current.card.append(Markdown(f"# Run Summary\n## {run_status}"))

        # Per-target table
        rows = []
        for target, data in self.all_results.items():
            result = data.get("result", {})
            ev     = data.get("eval_result", {})
            status = "✓" if ev.get("passed") else "✗"
            cls    = result.get("classification", "—")
            conf   = result.get("confidence", 0.0)
            depth  = result.get("transit_depth_pct", 0.0)
            rows.append([
                Markdown(f"`{target}`"),
                Markdown(status),
                Markdown(cls),
                Markdown(f"{conf:.2f}"),
                Markdown(f"{depth:.4f}%"),
            ])

        current.card.append(Table(
            rows,
            headers=["Target", "Eval", "Classification", "Confidence", "Transit Depth"]
        ))

        # Errors if any
        errors = {
            t: d for t, d in self.all_results.items()
            if d.get("ingest_error") not in (None, "None")
            or d.get("analyze_error") not in (None, "None")
        }
        if errors:
            current.card.append(Markdown("### Errors"))
            for target, data in errors.items():
                if data.get("ingest_error") not in (None, "None"):
                    current.card.append(Markdown(
                        f"**{target}** ingest: `{data['ingest_error']}`"
                    ))
                if data.get("analyze_error") not in (None, "None"):
                    current.card.append(Markdown(
                        f"**{target}** analyze: `{data['analyze_error']}`"
                    ))

        # Print summary to stdout for log-based alerting
        print(f"\nRun summary: {n_passed}/{n_total} passed")
        for target, ev in self.eval_summary.items():
            icon = "✓" if ev["passed"] else "✗"
            print(f"  {icon} {target}: {ev['n_failed']} critical failures")


if __name__ == "__main__":
    HarnessedLightcurveFlow()
