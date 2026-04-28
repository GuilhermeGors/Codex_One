"""
Codex One v2 — Centralized Configuration

Hardware Profile: Intel i5 12th Gen + GTX 3050 4GB VRAM
All model selections optimized for this hardware constraint.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable override support."""

    # --- Application ---
    APP_NAME: str = "Codex One v2"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # --- API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Ollama ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Generation Model — Optimized for 4GB VRAM
    # phi4-mini: 3.8B params, exceptional reasoning, fits in 4GB
    OLLAMA_MODEL: str = "phi4-mini"

    # --- Embedding Model (FastEmbed CPU) ---
    # Moved to CPU (Intel AVX2) to prevent Ollama VRAM thrashing
    FASTEMBED_MODEL: str = "nomic-ai/nomic-embed-text-v1.5"

    # --- Cross-Encoder Reranker (FlashRank CPU) ---
    # Multilingual model to support Portuguese PDFs against English/Portuguese queries
    FLASHRANK_MODEL: str = "ms-marco-MultiBERT-L-12"

    # --- LLM Parameters ---
    LLM_TEMPERATURE: float = 0.2  # Low for RAG faithfulness
    LLM_TOP_P: float = 0.9
    LLM_CONTEXT_WINDOW: int = 8192  # Safe for 4GB VRAM
    LLM_MAX_TOKENS: int = 2048

    # --- RAG Pipeline ---
    CHUNK_SIZE: int = 512  # Smaller chunks = higher precision
    CHUNK_OVERLAP: int = 64
    SEMANTIC_CHUNK_THRESHOLD: float = 0.75  # Cosine similarity threshold for splits
    TOP_K_RETRIEVAL: int = 20  # First stage: broad retrieval
    TOP_K_RERANK: int = 5  # Second stage: precise reranking
    RELEVANCE_THRESHOLD: float = 0.5  # Minimum score for context grader

    # --- ChromaDB ---
    CHROMA_PERSIST_DIR: str = Field(default="")
    CHROMA_COLLECTION_NAME: str = "codex_documents"

    # --- Data Directories ---
    DATA_DIR: str = Field(default="")
    DOCUMENTS_DIR: str = Field(default="")
    UPLOAD_DIR: str = Field(default="")

    # --- Security & Governance ---
    ENABLE_THREAT_QUARANTINE: bool = False  # Blocks ingestion if threats are detected
    ENABLE_CONTEXT_GRADING: bool = False  # Skip LLM-as-a-judge grading to save 8-10s latency

    # --- Langfuse (Observability) ---
    LANGFUSE_ENABLED: bool = True
    LANGFUSE_HOST: str = "http://localhost:3001"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # --- RAGAS (Evaluation) ---
    RAGAS_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_post_init(self, __context) -> None:
        """Set derived paths after initialization."""
        base = Path(__file__).resolve().parent.parent
        if not self.DATA_DIR:
            self.DATA_DIR = str(base / "data")
        if not self.CHROMA_PERSIST_DIR:
            self.CHROMA_PERSIST_DIR = str(Path(self.DATA_DIR) / "chroma_db")
        if not self.DOCUMENTS_DIR:
            self.DOCUMENTS_DIR = str(Path(self.DATA_DIR) / "documents")
        if not self.UPLOAD_DIR:
            self.UPLOAD_DIR = str(Path(self.DATA_DIR) / "uploads")

        # Ensure directories exist
        for d in [self.DATA_DIR, self.CHROMA_PERSIST_DIR, self.DOCUMENTS_DIR, self.UPLOAD_DIR]:
            os.makedirs(d, exist_ok=True)


# Singleton
settings = Settings()
