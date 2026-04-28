"""
Codex One v2 — Embedding Manager

Uses FastEmbed for CPU-based local embeddings via ONNX Runtime.
Prevents GPU VRAM thrashing by isolating embeddings from the LLM.
"""

import os
import time
import numpy as np
from typing import Optional
from fastembed import TextEmbedding
from app.config import settings

# Initialize globally to load into RAM once
print(f"[Embedding] Initializing FastEmbed with {settings.FASTEMBED_MODEL}...")
cache_path = os.path.join(settings.DATA_DIR, "models_cache")
os.makedirs(cache_path, exist_ok=True)
embedding_model = TextEmbedding(model_name=settings.FASTEMBED_MODEL, cache_dir=cache_path)
print("[Embedding] FastEmbed initialized successfully.")


def generate_embeddings(texts: list[str], batch_size: int = 32) -> Optional[list[list[float]]]:
    """
    Generate embeddings for a list of texts using FastEmbed.
    
    Args:
        texts: List of text strings to embed
        batch_size: Number of texts to embed per batch
        
    Returns:
        List of embedding vectors, or None on failure
    """
    if not texts:
        return []

    start = time.perf_counter()

    try:
        # FastEmbed handles batching natively and uses parallel workers
        # We cast the generator to a list to force execution
        embeddings_generator = embedding_model.embed(texts, batch_size=batch_size)
        all_embeddings = [list(emb) for emb in embeddings_generator]

        elapsed = (time.perf_counter() - start) * 1000
        dim = len(all_embeddings[0]) if all_embeddings else 0
        print(f"[Embedding] Generated {len(all_embeddings)} embeddings (dim={dim}) in {elapsed:.0f}ms")

        return all_embeddings

    except Exception as e:
        print(f"[Embedding] Error: {e}")
        return None


def generate_single_embedding(text: str) -> Optional[list[float]]:
    """Generate embedding for a single text string."""
    result = generate_embeddings([text])
    return result[0] if result else None


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def get_embedding_dimension() -> Optional[int]:
    """Get the dimension of the embedding model."""
    try:
        # FastEmbed model_name is accessible, but we can just embed a test string
        result = generate_single_embedding("dimension test")
        return len(result) if result else None
    except Exception as e:
        print(f"[Embedding] Cannot get dimension: {e}")
        return None
