"""
Codex One v2 — Metrics API Routes

Exposes pipeline metrics, token usage, cost analysis,
and per-node performance for the dashboard.
"""

from fastapi import APIRouter
from app.observability.metrics_store import metrics_store

router = APIRouter()


@router.get("/pipeline")
async def get_pipeline_metrics():
    """Aggregated pipeline metrics for the main dashboard."""
    return metrics_store.get_dashboard_metrics()


@router.get("/tokens")
async def get_token_usage():
    """Detailed token usage with cloud cost comparison."""
    return metrics_store.get_token_usage()


@router.get("/nodes")
async def get_node_performance():
    """Per-node latency breakdown (avg, min, max, p95)."""
    return metrics_store.get_node_performance()


@router.get("/cost")
async def get_cost_analysis():
    """Cost savings analysis: local vs cloud API equivalents."""
    usage = metrics_store.get_token_usage()
    return {
        "total_queries": usage["total_queries"],
        "total_tokens": usage["total_tokens"],
        "local_cost_usd": 0.0,
        "cloud_equivalents": usage.get("cost_analysis", {}).get("cloud_equivalent", {}),
        "total_saved_usd": usage.get("cost_analysis", {}).get("savings_vs_gpt4o", 0),
        "privacy_compliance": "LGPD - 100% local processing, zero data egress",
    }


@router.get("/threats")
async def get_threat_intelligence():
    """Threat scan summary: detected threats by category and severity."""
    return metrics_store.get_threat_summary()


@router.delete("/threats")
async def clear_threat_intelligence():
    """Clear all threat scan history from memory."""
    metrics_store.clear_all_threats()
    return {"status": "cleared", "message": "Threat intelligence dashboard has been reset."}
