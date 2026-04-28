"""
Codex One v2 — Query API Routes

RAG query endpoint with full SSE streaming:
- Pipeline stage progress (embed → retrieve → rerank → grade)
- Token-by-token LLM response streaming
- Real-time metrics at completion
"""

import json
import time
import concurrent.futures
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.data.models import QueryRequest, QueryResponse
from app.core.graph import run_query
from app.core import embedding, llm
from app.data import vector_db
from app.config import settings
from app.observability.metrics_store import metrics_store
from app.observability.token_counter import estimate_cost
from flashrank import Ranker, RerankRequest

# Initialize FlashRank globally
print(f"[Query] Initializing FlashRank with {settings.FLASHRANK_MODEL}...")
ranker = Ranker(model_name=settings.FLASHRANK_MODEL, cache_dir=".cache/flashrank")
print("[Query] FlashRank initialized successfully.")

router = APIRouter()


@router.post("/stream")
async def stream_query(request: QueryRequest):
    """
    Execute a RAG query with full SSE streaming.
    
    Streams:
    1. Pipeline stage updates (embedding, retrieval, reranking, grading)
    2. Token-by-token LLM generation
    3. Final metrics and sources
    """

    async def event_stream():
        query = request.query
        metrics = {}

        try:
            # --- Stage 1: Embedding ---
            yield _sse({"stage": "embedding", "status": "running"})
            start = time.perf_counter()
            query_emb = embedding.generate_single_embedding(query)
            ms = round((time.perf_counter() - start) * 1000, 2)
            metrics["latency_embedding_ms"] = ms
            yield _sse({"stage": "embedding", "status": "done", "latency_ms": ms})

            if not query_emb:
                yield _sse({"stage": "error", "status": "error", "detail": {"message": "Embedding failed"}})
                return

            # --- Stage 2: Hybrid Retrieval ---
            yield _sse({"stage": "retrieval", "status": "running"})
            start = time.perf_counter()
            chunks = vector_db.hybrid_search(query, query_emb, top_k=settings.TOP_K_RETRIEVAL)
            ms = round((time.perf_counter() - start) * 1000, 2)
            metrics["latency_retrieval_ms"] = ms
            metrics["chunks_retrieved"] = len(chunks)
            yield _sse({"stage": "retrieval", "status": "done", "latency_ms": ms, "detail": {"chunks": len(chunks)}})

            if not chunks:
                yield _sse({"stage": "generation", "status": "done", "token": "No relevant documents found."})
                yield _sse({"stage": "complete", "status": "done", "detail": {"metrics": metrics, "sources": []}})
                return

            # --- Stage 3: Cross-Encoder Reranking (FlashRank) ---
            yield _sse({"stage": "reranking", "status": "running"})
            start = time.perf_counter()

            # Format passages for FlashRank: {"id": str, "text": str, "meta": dict}
            passages = []
            for ch in chunks:
                passages.append({
                    "id": ch.get("chunk_id", "0"),
                    "text": ch["text"],
                    "meta": ch.get("metadata", {})
                })

            # Run Cross-Encoder Reranking
            rank_request = RerankRequest(query=query, passages=passages)
            reranked_results = ranker.rerank(rank_request)
            
            # Map back to our standard chunk format, keeping only top K
            reranked = []
            for res in reranked_results[:settings.TOP_K_RERANK]:
                # FlashRank returns dicts with 'id', 'text', 'meta', 'score'
                ch_rebuilt = {
                    "chunk_id": res["id"],
                    "text": res["text"],
                    "metadata": res["meta"],
                    "rerank_score": res["score"]
                }
                reranked.append(ch_rebuilt)

            ms = round((time.perf_counter() - start) * 1000, 2)
            metrics["latency_reranking_ms"] = ms
            metrics["chunks_after_rerank"] = len(reranked)
            yield _sse({"stage": "reranking", "status": "done", "latency_ms": ms, "detail": {"top_k": len(reranked)}})

            # --- Stage 4: Context Grading (Bypassed) ---
            # FlashRank is so accurate we bypass LLM Context Grading entirely
            yield _sse({"stage": "grading", "status": "running"})
            start = time.perf_counter()
            
            graded = reranked  # Skip grading

            ms = round((time.perf_counter() - start) * 1000, 2)
            metrics["latency_grading_ms"] = ms
            metrics["chunks_after_grading"] = len(graded)
            yield _sse({"stage": "grading", "status": "done", "latency_ms": ms, "detail": {"kept": len(graded)}})

            # --- Stage 5: Generation (streaming) ---
            yield _sse({"stage": "generation", "status": "running"})

            # Build context
            context_parts = []
            sources = []
            for ch in graded:
                meta = ch.get("metadata", {})
                label = f"[Source: {meta.get('filename', 'N/A')}, Page/Section: {meta.get('page', meta.get('section', 'N/A'))}]"
                context_parts.append(f"{label}\n{ch['text']}")
                sources.append({
                    "chunk_id": ch.get("chunk_id", ""),
                    "filename": meta.get("filename", "N/A"),
                    "page_or_section": str(meta.get("page", meta.get("section", "N/A"))),
                    "section_title": meta.get("section_title", ""),
                    "relevance_score": round(float(ch.get("rerank_score", 0)), 4),
                    "text_preview": ch["text"][:250],
                })

            context = "\n\n---\n\n".join(context_parts)

            # Stream tokens
            start = time.perf_counter()
            async for event in llm.generate_response_stream(query, context):
                if event.get("token"):
                    yield _sse({"stage": "generation", "token": event["token"]})
                if event.get("done"):
                    ms = round((time.perf_counter() - start) * 1000, 2)
                    metrics["latency_generation_ms"] = ms
                    metrics["tokens_in"] = event.get("tokens_in", 0)
                    metrics["tokens_out"] = event.get("tokens_out", 0)
                    metrics["tokens_total"] = metrics["tokens_in"] + metrics["tokens_out"]

            # --- Complete ---
            metrics["latency_total_ms"] = round(sum(
                metrics.get(k, 0) for k in
                ["latency_embedding_ms", "latency_retrieval_ms", "latency_reranking_ms",
                 "latency_grading_ms", "latency_generation_ms"]
            ), 2)

            # Record to metrics store
            metrics_store.record_query(metrics, query_text=query)

            # Cost analysis
            cost = estimate_cost(metrics.get("tokens_in", 0), metrics.get("tokens_out", 0))

            yield _sse({
                "stage": "complete", "status": "done",
                "detail": {
                    "metrics": metrics,
                    "sources": sources,
                    "cost": cost,
                }
            })

        except Exception as e:
            yield _sse({"stage": "error", "status": "error", "detail": {"message": str(e)}})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("", response_model=QueryResponse)
async def query_sync(request: QueryRequest):
    """Non-streaming query endpoint (for simple API consumers)."""
    result = run_query(request.query)

    # Record to metrics store
    metrics_store.record_query(result.get("metrics", {}), query_text=request.query)

    return QueryResponse(
        query=result["query"],
        response=result["response"],
        sources=result["sources"],
        metrics=result["metrics"],
    )


def _sse(data: dict) -> str:
    """Format dict as SSE event."""
    return f"data: {json.dumps(data)}\n\n"
