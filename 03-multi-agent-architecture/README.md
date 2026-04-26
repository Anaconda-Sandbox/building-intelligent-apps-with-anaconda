# Your First Intelligent App: Foundations of Intelligent Software Systems

What's the difference between a single agent and an intelligent application? An `agent` is one component of an autonomous system. Once you add orchestration, data ingress/egress, persistence, CI/CD, multi-agent coordination, and evaluation, you're building an intelligent software system.

This module introduces a higher-level architecture:

- **LangGraph** as the orchestrator for multi-agent workflows
- **MetaFlow** for workflow versioning, reproducibility, and model lifecycle tracking
- **promptfoo** for prompt quality and model response evaluation

## Why LangGraph?

LangGraph is designed for stateful, multi-step agent orchestration. It is a natural fit when your system has:

- multiple agents or tools collaborating on a task
- branching workflows based on intermediate results
- long-lived state and context that must flow between steps

Use LangGraph to wire together the same underlying tools from Module 2 and Module 1, while preserving the source-of-truth pipeline in `01-data-sources/ingestion.py`.

## Why MetaFlow?

MetaFlow is useful for building production-grade model workflows and tracking the lifecycle of your experiments.

Use MetaFlow to:

- define the overall end-to-end workflow for data, validation, and agent execution
- version the inputs, outputs, and model decisions
- capture metadata for repeatability and auditing

## Why promptfoo?

promptfoo is a lightweight, open-source toolkit for evaluating prompts and model responses.

Use promptfoo to:

- define evaluation scenarios for your agent prompts
- compare model outputs across prompt variants and LLM backends
- monitor quality regressions as your system evolves

## Recommended architecture

1. Keep `01-data-sources/ingestion.py` as the source-of-truth pipeline.
2. Use `02-your-first-agent` to expose those pipeline functions as tools.
3. Build a LangGraph orchestration layer in `03-multi-agent-architecture`:
   - agent/tool registration
   - workflow state transitions
   - decision logic between agent steps
4. Add MetaFlow around the workflow for reproducibility and tracking.
5. Use promptfoo to evaluate prompt variants and LLM outputs.

## Files in this module

- `langgraph_orchestrator.py` — LangGraph orchestration example for the Module 2 tools
- `metaflow_workflow.py` — MetaFlow workflow for the same load/validate/analyze pipeline
- `promptfoo_evaluation.py` — promptfoo evaluation sketch for prompt and model response quality

## Example workflow

- `load_lightcurve` loads a CSV with schema assurance
- `validate_lightcurve` returns a `ValidationReport` for decision-making
- `run_feature_anomaly_pipeline` generates features and anomaly summaries
- LangGraph routes the outputs to the next agent or evaluation step
- promptfoo scores the agent prompt and output quality
- MetaFlow records the run, inputs, and outputs for future comparison

## Run these examples

```bash
python langgraph_orchestrator.py
metaflow run metaflow_workflow.py
python promptfoo_evaluation.py
```

## Notes

This module is about architecture, not changing the pipeline. The data and model logic stay in Modules 1 and 2. Module 3 adds orchestration and evaluation layers on top.

