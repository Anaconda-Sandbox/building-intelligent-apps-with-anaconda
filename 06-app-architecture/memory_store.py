"""
vectordb/memory_store.py

Agent memory across runs using DuckDB + numpy for local/edge deployments.

The problem this solves:
    Module 03's AnalysisAgent is stateless. Every run starts from scratch.
    It can't learn that WASP-18b consistently shows a 1.01% transit depth,
    or that a particular target's data quality is unreliable, or that the
    anomaly pattern in Sector 12 resembles Sector 7.

    Agent memory = embeddings of past results stored in a vector DB,
    retrieved at inference time and injected into the agent's context.

Why DuckDB here:
    This module runs locally. DuckDB is embedded (no server), reads Parquet
    directly, and the entire memory store is a single file you can
    conda-pack and ship alongside the environment. The comparison table
    shows where the other options win — pgvector for production SQL apps,
    MongoDB Atlas for managed cloud scale, Neo4j for graph relationships.

Anaconda vectordb (AI Navigator / AI Catalyst):
    Anaconda's `anaconda-ai` CLI exposes a managed vector database:
        anaconda-ai launch-vectordb
        anaconda-ai create-table <name>
        anaconda-ai list-tables
    The SDK (anaconda-ai SDK, currently in early access) provides a Python
    interface over the same backend. When available, swap this module's
    DuckDB store for the Anaconda-managed store — the interface is the same.
    See: https://anaconda.com/docs/api-reference/vectordb/
"""

from __future__ import annotations

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Any


# ── Embedding generation ──────────────────────────────────────────────────────

def embed_result(result: dict, report_summary: dict) -> np.ndarray:
    """
    Produce a lightweight embedding from pipeline outputs.

    For local use, we build a deterministic feature vector from the
    structured Pydantic outputs rather than calling a sentence-similarity
    model. This keeps the memory store self-contained with no extra server.

    For production, swap this for a real embedding:
        POST http://localhost:8080/embedding  (AI Navigator, sentence-similarity model)
        or any OpenAI-compatible /embeddings endpoint
    """
    # Encode classification as integer
    classification_map = {
        "confirmed_transit":  1.0,
        "candidate_transit":  0.7,
        "no_transit":         0.0,
        "insufficient_data": -1.0,
    }

    features = np.array([
        classification_map.get(result.get("classification", ""), 0.0),
        float(result.get("confidence", 0.0)),
        float(result.get("transit_depth_pct", 0.0)),
        float(report_summary.get("flux_std", 0.0)) * 1000,   # scale up
        float(report_summary.get("n_anomalies", 0.0)) / 100,
        float(report_summary.get("phase_span", 0.0)),
    ], dtype=np.float32)

    # L2 normalise so cosine similarity = dot product
    norm = np.linalg.norm(features)
    return features / norm if norm > 0 else features


def embed_text_via_navigator(text: str, base_url: str = "http://localhost:8080") -> np.ndarray | None:
    """
    Optional: use AI Navigator's sentence-similarity model for richer embeddings.

    Requires a sentence-similarity model loaded in AI Navigator.
    Falls back to None if the server isn't running — the memory store
    degrades to structured-feature embeddings instead.

    API: POST http://localhost:8080/embedding
         Body: {"content": "<text>"}
         Response: [{"embedding": [float, ...]}]
    """
    try:
        import requests
        resp = requests.post(
            f"{base_url}/embedding",
            json={"content": text},
            headers={"Content-Type": "application/json"},
            timeout=2.0,
        )
        if resp.status_code == 200:
            vec = np.array(resp.json()[0]["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
    except Exception:
        pass
    return None


# ── DuckDB memory store ───────────────────────────────────────────────────────

class AgentMemoryStore:
    """
    Persistent vector memory for the AnalysisAgent, backed by DuckDB.

    Stores embeddings of past analysis results. At inference time, the
    evaluate step retrieves the k most similar past runs and injects
    their summaries into the agent's prompt as context.

    The store is a single .duckdb file — portable, no server required,
    compatible with conda-pack for offline deployment.

    Usage:
        store = AgentMemoryStore("memory/lightcurve_memory.duckdb")
        store.add(target="wasp18b", result=result, report_summary=summary)
        similar = store.retrieve_similar(result, report_summary, k=3)
        context = store.format_context(similar)
    """

    def __init__(self, db_path: str = "memory/lightcurve_memory.duckdb"):
        import duckdb
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_memory (
                id           VARCHAR PRIMARY KEY,
                target       VARCHAR NOT NULL,
                run_id       VARCHAR,
                timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classification VARCHAR,
                confidence   FLOAT,
                transit_depth_pct FLOAT,
                reasoning_summary TEXT,
                flux_std     FLOAT,
                n_anomalies  INTEGER,
                embedding    FLOAT[6],
                result_json  TEXT
            )
        """)

    def add(
        self,
        target: str,
        result: dict,
        report_summary: dict,
        run_id: str | None = None,
    ) -> str:
        """Store a result and its embedding. Returns the record ID."""
        # Stable ID: hash of target + result content
        content_hash = hashlib.md5(
            f"{target}{json.dumps(result, sort_keys=True)}".encode()
        ).hexdigest()[:12]
        record_id = f"{target}_{content_hash}"

        embedding = embed_result(result, report_summary)

        self.conn.execute("""
            INSERT OR REPLACE INTO analysis_memory
                (id, target, run_id, classification, confidence,
                 transit_depth_pct, reasoning_summary,
                 flux_std, n_anomalies, embedding, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            record_id,
            target,
            run_id,
            result.get("classification"),
            result.get("confidence"),
            result.get("transit_depth_pct"),
            result.get("reasoning_summary"),
            report_summary.get("flux_std"),
            report_summary.get("n_anomalies"),
            embedding.tolist(),
            json.dumps(result),
        ])
        return record_id

    def retrieve_similar(
        self,
        result: dict,
        report_summary: dict,
        k: int = 3,
        exclude_target: str | None = None,
    ) -> list[dict]:
        """
        Return the k most similar past results by cosine similarity.
        Used to build context for the agent before inference.
        """
        query_vec = embed_result(result, report_summary)

        rows = self.conn.execute("""
            SELECT id, target, classification, confidence,
                   transit_depth_pct, reasoning_summary,
                   flux_std, n_anomalies, embedding
            FROM analysis_memory
            WHERE (? IS NULL OR target != ?)
        """, [exclude_target, exclude_target]).fetchall()

        if not rows:
            return []

        cols = ["id", "target", "classification", "confidence",
                "transit_depth_pct", "reasoning_summary",
                "flux_std", "n_anomalies", "embedding"]
        records = [dict(zip(cols, row)) for row in rows]

        # Cosine similarity against query vector
        for rec in records:
            vec = np.array(rec["embedding"], dtype=np.float32)
            rec["similarity"] = float(np.dot(query_vec, vec))

        records.sort(key=lambda r: r["similarity"], reverse=True)
        return records[:k]

    def format_context(self, similar_results: list[dict]) -> str:
        """
        Format retrieved memories as a string to inject into the agent prompt.
        Keeps it concise — past context should inform, not overwhelm.
        """
        if not similar_results:
            return ""

        lines = ["Relevant past analyses (for context):"]
        for rec in similar_results:
            sim_pct = int(rec["similarity"] * 100)
            lines.append(
                f"  - {rec['target']}: {rec['classification']} "
                f"(confidence={rec['confidence']:.2f}, "
                f"depth={rec['transit_depth_pct']:.4f}%, "
                f"similarity={sim_pct}%)"
            )
            if rec.get("reasoning_summary"):
                # Truncate long summaries
                summary = rec["reasoning_summary"][:120]
                lines.append(f"    Reasoning: {summary}...")

        return "\n".join(lines)

    def count(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM analysis_memory"
        ).fetchone()[0]

    def targets(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT target FROM analysis_memory ORDER BY target"
        ).fetchall()
        return [r[0] for r in rows]

    def close(self):
        self.conn.close()
