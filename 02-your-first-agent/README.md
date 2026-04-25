# Your First Agent: Building Intelligent Workflows

This module turns the deterministic Module 1 pipeline into an agent-driven workflow.

## What this module covers

In **Module 2: Your First Agent**, you'll:

1. Register `load_lightcurve`, `validate_lightcurve`, and the feature/anomaly pipeline as **agent tools**
2. Give an LLM the `agent_context` dict from Module 1 as initial context
3. Let the agent decide *which* light curves to analyze, *how* to interpret results, and *what follow-up questions* to ask

The underlying pipeline does not change — it only gets a smarter driver.

## Files

- `agent_tools.py` — agent-friendly wrapper around the Module 1 ingestion and analysis pipeline
- `agent_example.py` — simple script showing the basic bridge
- `langchain_agent_example.py` — concrete LangChain integration example
- `README.md` — this guide

## Getting started

1. Activate the same environment used in Module 1.
2. Install your preferred LLM framework and tools. For LangChain, install `langchain`; for LangGraph, install `langchain` and `langchain-graph` if required.
3. Follow the `LangChain example` or `LangGraph example` below.

## Core agent tools

- `load_lightcurve(filepath, SCHEMA)`
- `validate_lightcurve(df)`
- `run_feature_anomaly_pipeline(df, window=15, contamination=0.05)`
- `build_agent_context(filepath, window=15, contamination=0.05)`

## LangChain example

This module ships a concrete example at `langchain_agent_example.py`.

It registers pipeline wrappers as LangChain tools and then initializes an agent capable of:

- loading a CSV
- validating the light curve
- running feature engineering and anomaly detection
- returning structured results

### Run it

```bash
python langchain_agent_example.py
```

### What it does

- loads `../01-data-sources/wasp18b_lightcurve.csv`
- validates the dataset with `validate_lightcurve`
- runs `run_feature_anomaly_pipeline`
- uses an LLM agent to decide what to do next

## LangGraph example

LangGraph is a good fit when you want a stateful workflow instead of a one-shot agent.

A LangGraph workflow can use the same tool functions as nodes in a graph:

```python
from langchain.chat_models import ChatOpenAI
from langchain.graphs import Graph

# Wrap the same underlying functions as graph-accessible tools.
# This is a starter pattern; adapt to your LangGraph version.

def load_lightcurve_tool(filepath: str) -> str:
    return load_lightcurve(filepath, SCHEMA)

# Build the graph and wire the steps.
graph = Graph()
graph.add_tool(
    name="load_lightcurve",
    func=load_lightcurve_tool,
    description="Load a WASP-18 lightcurve CSV with schema enforcement.",
)
# Add validation and anomaly tools similarly.

llm = ChatOpenAI(temperature=0)
result = graph.run(
    llm=llm,
    input="Load the light curve, validate it, and summarize the transit anomaly.",
)
print(result)
```

> Use `load_lightcurve`, `validate_lightcurve`, and the feature/anomaly pipeline as the building blocks of a LangGraph workflow.

## Optional FastMCP complement

If you want the same tools to be hosted as service endpoints, `fastmcp` can be a complementary layer.

The pattern is:

1. expose `load_lightcurve`, `validate_lightcurve`, and `run_feature_anomaly_pipeline` as MCP/HTTP tools
2. let the agent call those tools by name
3. keep the source-of-truth pipeline in `01-data-sources/ingestion.py`

A minimal FastMCP-style sketch looks like:

```python
from fastmcp import FastMCPServer
from agent_tools import load_lightcurve, validate_lightcurve, run_feature_anomaly_pipeline, SCHEMA

server = FastMCPServer()
server.register_tool(load_lightcurve, name="load_lightcurve")
server.register_tool(validate_lightcurve, name="validate_lightcurve")
server.register_tool(run_feature_anomaly_pipeline, name="feature_anomaly_pipeline")
server.start()
```

Only use FastMCP if you want a lightweight service layer on top of these functions. The core LangChain/LangGraph examples are the recommended path for this module.

## Notes

Keep the pipeline in `01-data-sources/ingestion.py` as the source of truth. Module 2 adds the agent wrapper and the bridge between the pipeline and an LLM-driven workflow.
