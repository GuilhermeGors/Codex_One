"""
Codex One v2 — In-Memory Metrics Store

Centralized store for pipeline execution metrics, node-level
performance tracking, and query history. Feeds both the REST
metrics API and the frontend dashboard.

In Phase 4 this will be backed by SQLite for persistence.
"""

import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NodeExecution:
    """Record of a single graph node execution."""
    node_name: str
    latency_ms: float
    success: bool
    timestamp: str


@dataclass
class QueryRecord:
    """Full metrics for a completed query."""
    query: str
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_total: int = 0
    latency_embedding_ms: float = 0
    latency_retrieval_ms: float = 0
    latency_reranking_ms: float = 0
    latency_grading_ms: float = 0
    latency_generation_ms: float = 0
    latency_total_ms: float = 0
    chunks_retrieved: int = 0
    chunks_after_rerank: int = 0
    chunks_after_grading: int = 0
    timestamp: str = ""
    cost_savings: float = 0.0


@dataclass
class IngestRecord:
    """Metrics for a document ingestion."""
    doc_id: str
    filename: str
    pages: int = 0
    chunks: int = 0
    latency_parse_ms: float = 0
    latency_chunk_ms: float = 0
    latency_embed_ms: float = 0
    latency_store_ms: float = 0
    latency_total_ms: float = 0
    timestamp: str = ""


class MetricsStore:
    """Thread-safe in-memory metrics store."""

    def __init__(self, max_history: int = 200):
        self.max_history = max_history
        self._queries: list[QueryRecord] = []
        self._ingests: list[IngestRecord] = []
        self._node_executions: list[NodeExecution] = []
        self._threat_findings: list[dict] = []
        self._start_time = datetime.now(timezone.utc).isoformat()

    # --- Query Metrics ---

    def record_query(self, metrics: dict, query_text: str = ""):
        """Record metrics from a completed query."""
        from app.observability.token_counter import estimate_cost

        tokens_in = metrics.get("tokens_in", 0)
        tokens_out = metrics.get("tokens_out", 0)
        cost = estimate_cost(tokens_in, tokens_out)

        record = QueryRecord(
            query=query_text[:100],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tokens_total=tokens_in + tokens_out,
            latency_embedding_ms=metrics.get("latency_embedding_ms", 0),
            latency_retrieval_ms=metrics.get("latency_retrieval_ms", 0),
            latency_reranking_ms=metrics.get("latency_reranking_ms", 0),
            latency_grading_ms=metrics.get("latency_grading_ms", 0),
            latency_generation_ms=metrics.get("latency_generation_ms", 0),
            latency_total_ms=metrics.get("latency_total_ms", 0),
            chunks_retrieved=metrics.get("chunks_retrieved", 0),
            chunks_after_rerank=metrics.get("chunks_after_rerank", 0),
            chunks_after_grading=metrics.get("chunks_after_grading", 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost_savings=cost.get("savings_vs_gpt4o", 0),
        )
        self._queries.append(record)
        if len(self._queries) > self.max_history:
            self._queries.pop(0)

    def record_ingest(self, data: dict):
        """Record metrics from a document ingestion."""
        record = IngestRecord(
            doc_id=data.get("doc_id", ""),
            filename=data.get("filename", ""),
            pages=data.get("pages", 0),
            chunks=data.get("chunks", 0),
            latency_total_ms=data.get("total_time_ms", 0),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._ingests.append(record)
        if len(self._ingests) > self.max_history:
            self._ingests.pop(0)

    # --- Node Metrics ---

    def record_node(self, node_name: str, latency_ms: float, success: bool = True):
        """Record a single node execution."""
        self._node_executions.append(NodeExecution(
            node_name=node_name,
            latency_ms=round(latency_ms, 2),
            success=success,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        if len(self._node_executions) > self.max_history * 5:
            self._node_executions = self._node_executions[-self.max_history:]

    # --- Threat Metrics ---

    def record_threats(self, findings: list[dict]):
        """Record threat scan findings from document ingestion."""
        self._threat_findings.extend(findings)
        if len(self._threat_findings) > self.max_history * 10:
            self._threat_findings = self._threat_findings[-self.max_history * 5:]

    def get_threat_summary(self) -> dict:
        """Get aggregated threat intelligence for the security dashboard."""
        if not self._threat_findings:
            return {
                "total_threats": 0,
                "by_severity": {},
                "by_category": {},
                "risk_score": 0,
                "affected_documents": [],
                "findings": [],
            }

        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        affected_docs: set[str] = set()

        for f in self._threat_findings:
            sev = f.get("severity", "UNKNOWN")
            cat = f.get("category", "Unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
            if f.get("filename"):
                affected_docs.add(f["filename"])

        weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1}
        risk_score = sum(weights.get(f.get("severity", ""), 0) for f in self._threat_findings)

        return {
            "total_threats": len(self._threat_findings),
            "by_severity": by_severity,
            "by_category": by_category,
            "risk_score": risk_score,
            "affected_documents": list(affected_docs),
            "findings": self._threat_findings[-50:],
        }

    # --- Aggregated Metrics ---

    def get_dashboard_metrics(self) -> dict:
        """Get aggregated metrics for the dashboard."""
        from app.data.vector_db import get_all_documents, get_total_chunks

        total_tokens_in = sum(q.tokens_in for q in self._queries)
        total_tokens_out = sum(q.tokens_out for q in self._queries)
        avg_latency = (
            sum(q.latency_total_ms for q in self._queries) / len(self._queries)
            if self._queries else 0
        )
        total_cost_saved = sum(q.cost_savings for q in self._queries)

        return {
            "total_queries": len(self._queries),
            "total_documents": len(get_all_documents()),
            "total_chunks": get_total_chunks(),
            "total_ingests": len(self._ingests),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens_processed": total_tokens_in + total_tokens_out,
            "total_tokens_in": total_tokens_in,
            "total_tokens_out": total_tokens_out,
            "total_cost_saved_usd": round(total_cost_saved, 6),
            "uptime_since": self._start_time,
            "queries_history": [
                {
                    "tokens_in": q.tokens_in,
                    "tokens_out": q.tokens_out,
                    "latency_total_ms": q.latency_total_ms,
                    "chunks_retrieved": q.chunks_retrieved,
                    "chunks_after_grading": q.chunks_after_grading,
                    "timestamp": q.timestamp,
                }
                for q in self._queries[-50:]
            ],
        }

    def get_token_usage(self) -> dict:
        """Get detailed token usage for analytics page."""
        from app.observability.token_counter import estimate_cost

        total_in = sum(q.tokens_in for q in self._queries)
        total_out = sum(q.tokens_out for q in self._queries)
        cost = estimate_cost(total_in, total_out)

        return {
            "total_queries": len(self._queries),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "total_tokens": total_in + total_out,
            "avg_tokens_per_query": round(
                (total_in + total_out) / max(len(self._queries), 1), 1
            ),
            "cost_analysis": cost,
            "history": [
                {
                    "tokens_in": q.tokens_in,
                    "tokens_out": q.tokens_out,
                    "latency_ms": q.latency_total_ms,
                    "timestamp": q.timestamp,
                }
                for q in self._queries[-50:]
            ],
        }

    def get_node_performance(self) -> dict:
        """Get per-node performance breakdown."""
        node_stats: dict[str, list[float]] = {}
        for ex in self._node_executions:
            if ex.node_name not in node_stats:
                node_stats[ex.node_name] = []
            node_stats[ex.node_name].append(ex.latency_ms)

        return {
            node: {
                "count": len(latencies),
                "avg_ms": round(sum(latencies) / len(latencies), 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2),
            }
            for node, latencies in node_stats.items()
        }


# Singleton
metrics_store = MetricsStore()


def record_node_execution(node_name: str, latency_ms: float, success: bool = True):
    """Convenience function for the trace_node decorator."""
    metrics_store.record_node(node_name, latency_ms, success)
