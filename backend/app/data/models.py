"""
Codex One v2 — Pydantic Schemas

All request/response models for the API, ensuring strict type safety
and automatic Swagger documentation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# Documents
# ============================================================

class DocumentInfo(BaseModel):
    """Metadata for an indexed document."""
    doc_id: str
    filename: str
    title: Optional[str] = None
    author: Optional[str] = None
    chunk_count: int = 0
    indexed_at: Optional[str] = None
    file_size_bytes: Optional[int] = None


class DocumentListResponse(BaseModel):
    """Response for listing all indexed documents."""
    documents: list[DocumentInfo]
    total_chunks: int


class IngestEvent(BaseModel):
    """SSE event during document ingestion."""
    stage: str  # parsing | chunking | embedding | storing | complete | error
    status: str  # running | done | error
    message: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    detail: Optional[dict] = None


# ============================================================
# Query
# ============================================================

class QueryRequest(BaseModel):
    """Incoming query from the user."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks for final context")


class SourceChunk(BaseModel):
    """A source chunk returned with the response."""
    chunk_id: str
    filename: str
    page_or_section: Optional[str] = None
    section_title: Optional[str] = None
    relevance_score: float
    text_preview: str = Field(..., max_length=300)


class QueryResponse(BaseModel):
    """Full query response (non-streaming)."""
    query: str
    response: str
    sources: list[SourceChunk]
    metrics: "QueryMetrics"


class QueryStreamEvent(BaseModel):
    """SSE event during query processing."""
    stage: str  # embedding | retrieval | reranking | grading | generation | complete
    status: str  # running | done
    token: Optional[str] = None  # For streaming generation
    latency_ms: Optional[float] = None
    detail: Optional[dict] = None


# ============================================================
# Metrics
# ============================================================

class QueryMetrics(BaseModel):
    """Token and latency metrics for a single query."""
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


class RAGASScores(BaseModel):
    """RAGAS evaluation scores for a query."""
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None


class PipelineMetrics(BaseModel):
    """Aggregated pipeline metrics."""
    total_queries: int = 0
    total_documents: int = 0
    total_chunks: int = 0
    avg_latency_ms: float = 0
    avg_faithfulness: float = 0
    total_tokens_processed: int = 0
    queries_history: list[QueryMetrics] = []
