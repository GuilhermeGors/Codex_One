"""
Codex One v2 — FastAPI Application Entry Point

Enterprise RAG system with real-time SSE streaming,
LangGraph orchestration, and full LLMOps observability.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import documents, query, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print(f"[START] Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"   LLM Model:     {settings.OLLAMA_MODEL}")
    print(f"   Embed Model:   {settings.FASTEMBED_MODEL}")
    print(f"   Cross-Encoder: {settings.FLASHRANK_MODEL}")
    print(f"   Ollama URL:    {settings.OLLAMA_BASE_URL}")
    print(f"   ChromaDB:      {settings.CHROMA_PERSIST_DIR}")
    print(f"   Langfuse:      {'enabled' if settings.LANGFUSE_ENABLED else 'disabled'}")

    # Initialize vector DB on startup
    from app.data.vector_db import get_collection
    collection = get_collection()
    if collection:
        print(f"   Collection:    '{settings.CHROMA_COLLECTION_NAME}' ({collection.count()} chunks)")
    else:
        print("   [WARN] ChromaDB collection failed to initialize")

    yield

    print(f"[STOP] Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise RAG with real-time observability and LGPD compliance",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(query.router, prefix="/api/v1/query", tags=["Query"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """System health check with component status."""
    import ollama as ollama_client

    # Check Ollama
    ollama_ok = False
    try:
        ollama_client.list()
        ollama_ok = True
    except Exception:
        pass

    # Check ChromaDB
    from app.data.vector_db import get_collection
    collection = get_collection()
    chroma_ok = collection is not None

    return {
        "status": "healthy" if (ollama_ok and chroma_ok) else "degraded",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
        "components": {
            "ollama": {"status": "up" if ollama_ok else "down", "model": settings.OLLAMA_MODEL},
            "chromadb": {"status": "up" if chroma_ok else "down", "chunks": collection.count() if collection else 0},
            "langfuse": {"status": "configured" if settings.LANGFUSE_ENABLED else "disabled"},
        },
        "security": {
            "quarantine_enabled": settings.ENABLE_THREAT_QUARANTINE
        }
    }


@app.post("/api/v1/settings/quarantine", tags=["System"])
async def toggle_quarantine(enabled: bool):
    """Toggle the Threat Quarantine block for the ingestion pipeline."""
    settings.ENABLE_THREAT_QUARANTINE = enabled
    return {"status": "ok", "quarantine_enabled": settings.ENABLE_THREAT_QUARANTINE}
