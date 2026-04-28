"""
Codex One v2 — Vector Database (ChromaDB + BM25 Hybrid)

Implements hybrid search combining dense (semantic) and sparse (BM25)
retrieval with Reciprocal Rank Fusion for optimal RAG results.
"""

import chromadb
from typing import Optional, Any
from rank_bm25 import BM25Okapi

from app.config import settings

_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None


def get_client() -> Optional[chromadb.ClientAPI]:
    """Get or create the ChromaDB persistent client."""
    global _client
    if _client is None:
        try:
            _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            print(f"[VectorDB] Client initialized at {settings.CHROMA_PERSIST_DIR}")
        except Exception as e:
            print(f"[VectorDB] Client error: {e}")
    return _client


def get_collection() -> Optional[chromadb.Collection]:
    """Get or create the document collection."""
    global _collection
    if _collection is None:
        client = get_client()
        if client:
            try:
                _collection = client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                print(f"[VectorDB] Collection error: {e}")
    return _collection


def add_chunks(
    chunk_texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
    chunk_ids: list[str],
) -> bool:
    """Add chunks with embeddings and metadata to the collection."""
    collection = get_collection()
    if not collection:
        return False
    if not chunk_texts:
        return True

    try:
        collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )
        return True
    except Exception as e:
        print(f"[VectorDB] Add error: {e}")
        return False


def dense_search(
    query_embedding: list[float],
    top_k: int = 20,
    filter_metadata: Optional[dict] = None,
) -> list[dict[str, Any]]:
    """Dense (semantic) search using ChromaDB."""
    collection = get_collection()
    if not collection or collection.count() == 0:
        return []

    actual_k = min(top_k, collection.count())
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where=filter_metadata,
            include=["metadatas", "documents", "distances"],
        )

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                chunks.append({
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 1.0,
                    "score": 1.0 - (results["distances"][0][i] if results["distances"] else 1.0),
                })
        return chunks
    except Exception as e:
        print(f"[VectorDB] Dense search error: {e}")
        return []


def bm25_search(query: str, top_k: int = 20) -> list[dict[str, Any]]:
    """Sparse (BM25) search across all documents in the collection."""
    collection = get_collection()
    if not collection or collection.count() == 0:
        return []

    try:
        all_docs = collection.get(include=["documents", "metadatas"])
        if not all_docs["documents"]:
            return []

        # Tokenize for BM25
        tokenized_corpus = [doc.lower().split() for doc in all_docs["documents"]]
        bm25 = BM25Okapi(tokenized_corpus)

        query_tokens = query.lower().split()
        scores = bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "chunk_id": all_docs["ids"][idx],
                    "text": all_docs["documents"][idx],
                    "metadata": all_docs["metadatas"][idx] if all_docs["metadatas"] else {},
                    "distance": 0.0,
                    "score": float(scores[idx]),
                })
        return results
    except Exception as e:
        print(f"[VectorDB] BM25 search error: {e}")
        return []


def hybrid_search(
    query: str,
    query_embedding: list[float],
    top_k: int = 20,
    alpha: float = 0.7,  # Weight for dense vs sparse (0.7 = 70% dense)
) -> list[dict[str, Any]]:
    """
    Hybrid search combining dense + BM25 with Reciprocal Rank Fusion.
    
    Alpha controls the balance: higher = more weight on semantic search.
    """
    dense_results = dense_search(query_embedding, top_k=top_k)
    sparse_results = bm25_search(query, top_k=top_k)

    # Reciprocal Rank Fusion (k=60 is standard)
    k = 60
    rrf_scores: dict[str, float] = {}
    chunk_data: dict[str, dict] = {}

    for rank, chunk in enumerate(dense_results):
        cid = chunk["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + alpha * (1.0 / (k + rank + 1))
        chunk_data[cid] = chunk

    for rank, chunk in enumerate(sparse_results):
        cid = chunk["chunk_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + (1 - alpha) * (1.0 / (k + rank + 1))
        if cid not in chunk_data:
            chunk_data[cid] = chunk

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]

    results = []
    for cid in sorted_ids:
        entry = chunk_data[cid].copy()
        entry["rrf_score"] = rrf_scores[cid]
        results.append(entry)

    return results


def delete_document_chunks(doc_id: str) -> bool:
    """Delete all chunks for a specific document (LGPD compliance)."""
    collection = get_collection()
    if not collection:
        return False
    try:
        collection.delete(where={"doc_id": doc_id})
        return True
    except Exception as e:
        print(f"[VectorDB] Delete error: {e}")
        return False


def get_all_documents() -> list[dict[str, Any]]:
    """Get metadata for all indexed documents."""
    collection = get_collection()
    if not collection or collection.count() == 0:
        return []

    try:
        all_items = collection.get(include=["metadatas"])
        doc_map: dict[str, dict] = {}

        for meta in (all_items["metadatas"] or []):
            if not meta:
                continue
            doc_id = meta.get("doc_id", "")
            if doc_id and doc_id not in doc_map:
                doc_map[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta.get("filename", "unknown"),
                    "title": meta.get("title"),
                    "author": meta.get("author"),
                    "chunk_count": 0,
                    "indexed_at": meta.get("indexed_at"),
                }
            if doc_id:
                doc_map[doc_id]["chunk_count"] += 1

        return list(doc_map.values())
    except Exception as e:
        print(f"[VectorDB] List error: {e}")
        return []


def get_total_chunks() -> int:
    """Get total number of chunks in the collection."""
    collection = get_collection()
    return collection.count() if collection else 0


def reset_collection():
    """Delete and recreate the collection (for testing)."""
    global _collection
    client = get_client()
    if client:
        try:
            client.delete_collection(settings.CHROMA_COLLECTION_NAME)
        except Exception:
            pass
        _collection = None
        return get_collection()
    return None
