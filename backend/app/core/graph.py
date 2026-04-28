"""
Codex One v2 — LangGraph RAG State Machine

Enterprise-grade agentic RAG pipeline with:
- Adaptive query routing
- Hybrid retrieval (dense + BM25)
- Cross-encoder reranking  
- LLM-as-Judge context grading
- Self-correction loops (query rewriting)
- Full metrics collection at every node

This is the brain of Codex One v2.
"""

import time
from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END

from app.config import settings
from app.core import embedding, llm
from app.data import vector_db


# ============================================================
# State Schema
# ============================================================

class PipelineState(TypedDict):
    """The shared state that flows through every node in the graph."""
    # Input
    query: str

    # Pipeline intermediates
    query_embedding: Optional[list[float]]
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    graded_chunks: list[dict]

    # Output
    context: str
    response: str
    sources: list[dict]

    # Metrics (collected at each node for real-time dashboard)
    metrics: dict

    # Control flow
    retry_count: int
    should_rewrite: bool


# ============================================================
# Graph Nodes
# ============================================================

def embed_query(state: PipelineState) -> dict:
    """Node 1: Generate embedding for the user query."""
    start = time.perf_counter()

    query = state.get("query", "")
    query_emb = embedding.generate_single_embedding(query)

    elapsed = (time.perf_counter() - start) * 1000
    metrics = state.get("metrics", {})
    metrics["latency_embedding_ms"] = round(elapsed, 2)

    return {
        "query_embedding": query_emb,
        "metrics": metrics,
    }


def retrieve(state: PipelineState) -> dict:
    """Node 2: Hybrid search — dense + BM25 with Reciprocal Rank Fusion."""
    start = time.perf_counter()

    query = state["query"]
    query_emb = state.get("query_embedding")

    if not query_emb:
        return {"retrieved_chunks": [], "metrics": state.get("metrics", {})}

    chunks = vector_db.hybrid_search(
        query=query,
        query_embedding=query_emb,
        top_k=settings.TOP_K_RETRIEVAL,
    )

    elapsed = (time.perf_counter() - start) * 1000
    metrics = state.get("metrics", {})
    metrics["latency_retrieval_ms"] = round(elapsed, 2)
    metrics["chunks_retrieved"] = len(chunks)

    return {
        "retrieved_chunks": chunks,
        "metrics": metrics,
    }


def rerank(state: PipelineState) -> dict:
    """
    Node 3: Reranking — re-score chunks by relevance to query.
    
    Uses embedding similarity as a lightweight cross-encoder proxy.
    For production, replace with a dedicated reranker model.
    """
    start = time.perf_counter()

    query_emb = state.get("query_embedding", [])
    chunks = state.get("retrieved_chunks", [])

    if not chunks or not query_emb:
        return {"reranked_chunks": [], "metrics": state.get("metrics", {})}

    # Re-score each chunk by cosine similarity with query
    for chunk in chunks:
        chunk_emb = embedding.generate_single_embedding(chunk["text"][:500])
        if chunk_emb:
            chunk["rerank_score"] = embedding.cosine_similarity(query_emb, chunk_emb)
        else:
            chunk["rerank_score"] = chunk.get("rrf_score", 0)

    # Sort by rerank score and take top-K
    reranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
    reranked = reranked[: settings.TOP_K_RERANK]

    elapsed = (time.perf_counter() - start) * 1000
    metrics = state.get("metrics", {})
    metrics["latency_reranking_ms"] = round(elapsed, 2)
    metrics["chunks_after_rerank"] = len(reranked)

    return {
        "reranked_chunks": reranked,
        "metrics": metrics,
    }


def grade_context(state: PipelineState) -> dict:
    """
    Node 4: LLM-as-Judge — grade each chunk for relevance.
    
    Removes chunks that the LLM deems irrelevant to the query,
    reducing hallucination risk.
    """
    start = time.perf_counter()

    query = state["query"]
    chunks = state.get("reranked_chunks", [])

    graded = []
    for chunk in chunks:
        is_relevant = llm.grade_chunk_relevance(query, chunk["text"][:500])
        if is_relevant:
            graded.append(chunk)

    elapsed = (time.perf_counter() - start) * 1000
    metrics = state.get("metrics", {})
    metrics["latency_grading_ms"] = round(elapsed, 2)
    metrics["chunks_after_grading"] = len(graded)

    # Decide if we need to rewrite the query
    should_rewrite = len(graded) == 0 and state.get("retry_count", 0) < 2

    return {
        "graded_chunks": graded,
        "should_rewrite": should_rewrite,
        "metrics": metrics,
    }


def generate(state: PipelineState) -> dict:
    """Node 5: Generate response using the LLM with graded context."""
    start = time.perf_counter()

    query = state["query"]
    chunks = state.get("graded_chunks", [])

    if not chunks:
        return {
            "response": "The provided documents do not contain sufficient information to answer this question.",
            "context": "",
            "sources": [],
            "metrics": state.get("metrics", {}),
        }

    # Build context string with source annotations
    context_parts = []
    for i, ch in enumerate(chunks):
        meta = ch.get("metadata", {})
        source_label = f"[Source: {meta.get('filename', 'N/A')}, Page/Section: {meta.get('page', meta.get('section', 'N/A'))}]"
        context_parts.append(f"{source_label}\n{ch['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # Generate
    result = llm.generate_response(query, context)

    elapsed = (time.perf_counter() - start) * 1000
    metrics = state.get("metrics", {})
    metrics["latency_generation_ms"] = round(elapsed, 2)
    metrics["tokens_in"] = result.get("tokens_in", 0)
    metrics["tokens_out"] = result.get("tokens_out", 0)
    metrics["tokens_total"] = metrics["tokens_in"] + metrics["tokens_out"]

    # Total latency
    metrics["latency_total_ms"] = round(
        metrics.get("latency_embedding_ms", 0)
        + metrics.get("latency_retrieval_ms", 0)
        + metrics.get("latency_reranking_ms", 0)
        + metrics.get("latency_grading_ms", 0)
        + metrics.get("latency_generation_ms", 0),
        2,
    )

    # Format sources
    sources = []
    for ch in chunks:
        meta = ch.get("metadata", {})
        sources.append({
            "chunk_id": ch.get("chunk_id", ""),
            "filename": meta.get("filename", "N/A"),
            "page_or_section": str(meta.get("page", meta.get("section", "N/A"))),
            "section_title": meta.get("section_title", ""),
            "relevance_score": round(ch.get("rerank_score", ch.get("rrf_score", 0)), 4),
            "text_preview": ch["text"][:250],
        })

    return {
        "response": result["response"],
        "context": context,
        "sources": sources,
        "metrics": metrics,
    }


def rewrite_query(state: PipelineState) -> dict:
    """Node 6: Rewrite the query for better retrieval (self-correction)."""
    query = state["query"]
    retry_count = state.get("retry_count", 0) + 1

    # Simple rewrite: make query more specific
    try:
        result = llm.generate_response(
            query=f"Rewrite this question to be more specific and searchable: {query}",
            context="",
        )
        new_query = result["response"].strip()
        if new_query and len(new_query) > 5:
            return {"query": new_query, "retry_count": retry_count}
    except Exception:
        pass

    return {"retry_count": retry_count}


# ============================================================
# Routing Logic
# ============================================================

def should_rewrite_or_generate(state: PipelineState) -> str:
    """Conditional edge: rewrite query or proceed to generation."""
    if state.get("should_rewrite", False):
        return "rewrite"
    return "generate"


# ============================================================
# Build the Graph
# ============================================================

def build_rag_graph() -> StateGraph:
    """Construct and compile the LangGraph RAG pipeline."""
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("embed_query", embed_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank", rerank)
    graph.add_node("grade_context", grade_context)
    graph.add_node("generate", generate)
    graph.add_node("rewrite_query", rewrite_query)

    # Define edges
    graph.set_entry_point("embed_query")
    graph.add_edge("embed_query", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "grade_context")

    # Conditional: grade → generate OR grade → rewrite → embed (loop)
    graph.add_conditional_edges(
        "grade_context",
        should_rewrite_or_generate,
        {"generate": "generate", "rewrite": "rewrite_query"},
    )
    graph.add_edge("rewrite_query", "embed_query")  # Loop back
    graph.add_edge("generate", END)

    return graph.compile()


# Singleton compiled graph
rag_graph = build_rag_graph()


def run_query(query: str) -> dict:
    """Execute a full RAG query through the LangGraph pipeline."""
    initial_state: PipelineState = {
        "query": query,
        "query_embedding": None,
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "graded_chunks": [],
        "context": "",
        "response": "",
        "sources": [],
        "metrics": {},
        "retry_count": 0,
        "should_rewrite": False,
    }

    result = rag_graph.invoke(initial_state)

    return {
        "query": query,
        "response": result.get("response", ""),
        "sources": result.get("sources", []),
        "metrics": result.get("metrics", {}),
    }
