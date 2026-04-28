"""
Codex One v2 — Semantic Chunker

Multi-strategy chunking pipeline:
1. Recursive Character Splitter (structure-aware)
2. Semantic Boundary Detection (embedding similarity)
3. Contextual Enrichment (prepend document context)

This replaces the naive fixed-size splitting from v1.
"""

from typing import Optional, Any
from app.config import settings
from app.core.embedding import generate_embeddings, cosine_similarity


def recursive_split(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
    separators: Optional[list[str]] = None,
) -> list[str]:
    """
    Recursive character splitter with hierarchical separators.
    
    Tries to split by paragraph first, then sentence, then word.
    This preserves logical units of text much better than fixed-size.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    separators = separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    # Find the best separator that creates chunks within size limit
    for sep in separators:
        parts = text.split(sep)
        if len(parts) > 1:
            chunks = []
            current = ""

            for part in parts:
                candidate = (current + sep + part) if current else part

                if len(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    # If part itself exceeds chunk_size, recurse with next separator
                    if len(part) > chunk_size:
                        sub_chunks = recursive_split(
                            part, chunk_size, chunk_overlap,
                            separators[separators.index(sep) + 1:] if sep in separators else [" "]
                        )
                        chunks.extend(sub_chunks)
                        current = ""
                    else:
                        current = part

            if current.strip():
                chunks.append(current.strip())

            if chunks:
                # Apply overlap
                return _apply_overlap(chunks, chunk_overlap)

    # Fallback: hard split by character
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Apply overlap between consecutive chunks for context continuity."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for i in range(1, len(chunks)):
        # Prepend the tail of the previous chunk
        prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
        overlapped.append(prev_tail + " " + chunks[i])

    return overlapped


def semantic_split(
    text: str,
    threshold: float = None,
    base_chunk_size: int = 200,
) -> list[str]:
    """
    Semantic chunking: splits text based on embedding similarity.
    
    Process:
    1. Split text into sentences
    2. Embed each sentence
    3. When similarity between consecutive sentences drops below
       threshold, create a new chunk boundary
    """
    threshold = threshold or settings.SEMANTIC_CHUNK_THRESHOLD

    # Split into sentences first
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

    if len(sentences) <= 1:
        return [text.strip()] if text.strip() else []

    # Generate embeddings for all sentences
    embeddings = generate_embeddings(sentences)
    if not embeddings or len(embeddings) != len(sentences):
        # Fallback to recursive split if embedding fails
        return recursive_split(text)

    # Find semantic boundaries
    chunks = []
    current_chunk_sentences = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = cosine_similarity(embeddings[i - 1], embeddings[i])

        if similarity < threshold:
            # Semantic boundary detected — start new chunk
            chunks.append(" ".join(current_chunk_sentences))
            current_chunk_sentences = [sentences[i]]
        else:
            current_chunk_sentences.append(sentences[i])

            # Also split if current chunk is getting too large
            current_text = " ".join(current_chunk_sentences)
            if len(current_text) > settings.CHUNK_SIZE * 2:
                chunks.append(current_text)
                current_chunk_sentences = []

    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    return [c for c in chunks if c.strip()]


def chunk_document(
    text: str,
    metadata_base: Optional[dict[str, Any]] = None,
    strategy: str = "recursive",  # "recursive" | "semantic" | "hybrid"
) -> list[dict[str, Any]]:
    """
    Main chunking entry point. Returns list of dicts with text + metadata.
    
    Strategies:
    - recursive: Fast, structure-aware (good for most cases)
    - semantic: Embedding-based boundary detection (higher quality, slower)
    - hybrid: Recursive first, then validate with semantic similarity
    """
    if not text or not text.strip():
        return []

    if strategy == "semantic":
        raw_chunks = semantic_split(text)
    elif strategy == "hybrid":
        # First pass: recursive split
        raw_chunks = recursive_split(text)
        # Second pass: merge chunks that are semantically similar
        raw_chunks = _merge_similar_chunks(raw_chunks)
    else:
        raw_chunks = recursive_split(text)

    # Build output with metadata
    results = []
    for i, chunk_text in enumerate(raw_chunks):
        meta = (metadata_base or {}).copy()
        meta["chunk_index"] = i
        meta["chunk_length"] = len(chunk_text)
        meta["chunking_strategy"] = strategy

        results.append({
            "text": chunk_text,
            "metadata": meta,
        })

    return results


def _merge_similar_chunks(chunks: list[str], threshold: float = 0.85) -> list[str]:
    """Merge consecutive chunks that are highly similar (redundancy removal)."""
    if len(chunks) <= 1:
        return chunks

    embeddings = generate_embeddings(chunks)
    if not embeddings:
        return chunks

    merged = [chunks[0]]
    for i in range(1, len(chunks)):
        sim = cosine_similarity(embeddings[i - 1], embeddings[i])
        if sim > threshold:
            # Merge with previous
            merged[-1] = merged[-1] + " " + chunks[i]
        else:
            merged.append(chunks[i])

    return merged
