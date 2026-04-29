"""
Codex One v2 — Documents API Routes

Handles document upload, ingestion with SSE streaming progress,
listing, and deletion (LGPD compliance).
"""

import os
import uuid
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.data import vector_db
from app.data.models import DocumentInfo, DocumentListResponse
from app.processing.parser import parse_document
from app.processing.semantic_chunker import chunk_document
from app.processing.pii_scrubber import anonymize_text
from app.processing.threat_scanner import scan_document_pages, summarize_findings
from app.core.embedding import generate_embeddings
from app.observability import audit_log
from app.observability.metrics_store import metrics_store
import concurrent.futures

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all indexed documents with metadata."""
    docs = vector_db.get_all_documents()
    total = vector_db.get_total_chunks()

    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total_chunks=total,
    )


@router.post("/upload")
async def upload_and_ingest(file: UploadFile = File(...)):
    """
    Upload a document and return a stream of ingestion progress events.
    
    Returns SSE stream with stages: saving → parsing → chunking → embedding → storing → complete
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".pdf", ".epub"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use PDF or ePub.")

    # Save uploaded file
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file.filename}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    async def ingest_stream():
        """Generator that processes the document and yields SSE events."""
        try:
            # Stage 1: Parsing
            yield _sse({"stage": "parsing", "status": "running", "message": f"Parsing {file.filename}...", "progress": 0.1})
            start = time.perf_counter()

            pages = parse_document(save_path)
            if not pages:
                yield _sse({"stage": "error", "status": "error", "message": "No text extracted from document"})
                return

            parse_time = (time.perf_counter() - start) * 1000
            yield _sse({
                "stage": "parsing", "status": "done",
                "message": f"Extracted {len(pages)} pages/sections",
                "progress": 0.2,
                "detail": {"pages": len(pages), "latency_ms": round(parse_time)}
            })

            # Stage 1.5: Threat Scanning
            yield _sse({"stage": "scanning", "status": "running", "message": "Scanning for security threats (SQLi, XSS, Prompt Injection)...", "progress": 0.2})
            start = time.perf_counter()

            threat_findings = scan_document_pages(pages, doc_id=doc_id, filename=file.filename)
            threat_summary = summarize_findings(threat_findings)

            scan_time = (time.perf_counter() - start) * 1000

            if threat_findings:
                metrics_store.record_threats(threat_findings)
                audit_log.record_event(
                    "THREATS_DETECTED",
                    doc_id,
                    {
                        "total_threats": threat_summary["total_threats"],
                        "by_severity": threat_summary["by_severity"],
                        "by_category": threat_summary["by_category"],
                        "risk_score": threat_summary["risk_score"],
                    }
                )

                if settings.ENABLE_THREAT_QUARANTINE and threat_summary["risk_score"] > 50:
                    yield _sse({
                        "stage": "scanning", "status": "error",
                        "message": f"QUARANTINE BLOCKED: Document contains {threat_summary['total_threats']} threats with critical risk score.",
                        "progress": 0.25
                    })
                    # Cleanup the uploaded file
                    try:
                        os.remove(save_path)
                    except OSError:
                        pass
                    return

            yield _sse({
                "stage": "scanning", "status": "done",
                "message": f"Found {threat_summary['total_threats']} threats (Risk Score: {threat_summary['risk_score']})",
                "progress": 0.25,
                "detail": {
                    "total_threats": threat_summary["total_threats"],
                    "by_severity": threat_summary.get("by_severity", {}),
                    "by_category": threat_summary.get("by_category", {}),
                    "risk_score": threat_summary["risk_score"],
                    "latency_ms": round(scan_time),
                }
            })

            # Stage 2: Chunking & PII Redaction (Parallel)
            yield _sse({"stage": "chunking", "status": "running", "message": "Applying PII redaction and semantic chunking (Multi-worker)...", "progress": 0.3})
            start = time.perf_counter()

            all_chunks = []
            total_redactions = {}

            def process_page(i, page_data):
                # 1. PII Redaction
                scrubbed_text, redactions = anonymize_text(page_data["text"])
                
                # 2. Chunking
                page_meta = page_data["metadata"].copy()
                page_meta["doc_id"] = doc_id
                page_meta["indexed_at"] = datetime.now(timezone.utc).isoformat()
                
                chunks = chunk_document(
                    scrubbed_text,
                    metadata_base=page_meta,
                    strategy="recursive",
                )
                return i, chunks, redactions

            # Use ThreadPoolExecutor to process pages in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                future_to_page = {executor.submit(process_page, i, p): i for i, p in enumerate(pages)}
                
                completed = 0
                for future in concurrent.futures.as_completed(future_to_page):
                    idx, page_chunks, redactions = future.result()
                    all_chunks.extend(page_chunks)
                    
                    for k, v in redactions.items():
                        total_redactions[k] = total_redactions.get(k, 0) + v
                        
                    completed += 1
                    progress = 0.25 + (0.25 * completed / len(pages))
                    
                    # Yield progress (only occasionally to avoid flooding SSE)
                    if completed % max(1, len(pages) // 5) == 0 or completed == len(pages):
                        yield _sse({
                            "stage": "chunking", "status": "running",
                            "message": f"Processed page {completed}/{len(pages)} ({len(all_chunks)} chunks so far)",
                            "progress": round(progress, 3),
                        })

            chunk_time = (time.perf_counter() - start) * 1000
            yield _sse({
                "stage": "chunking", "status": "done",
                "message": f"Created {len(all_chunks)} chunks",
                "progress": 0.5,
                "detail": {"total_chunks": len(all_chunks), "latency_ms": round(chunk_time)}
            })

            if not all_chunks:
                yield _sse({"stage": "complete", "status": "done", "message": "No chunks generated", "progress": 1.0})
                return

            # Stage 3: Embedding
            yield _sse({"stage": "embedding", "status": "running", "message": f"Generating embeddings for {len(all_chunks)} chunks...", "progress": 0.55})
            start = time.perf_counter()

            texts = [c["text"] for c in all_chunks]
            embeddings = generate_embeddings(texts)

            embed_time = (time.perf_counter() - start) * 1000
            if not embeddings or len(embeddings) != len(texts):
                yield _sse({"stage": "error", "status": "error", "message": "Embedding generation failed"})
                return

            yield _sse({
                "stage": "embedding", "status": "done",
                "message": f"Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})",
                "progress": 0.85,
                "detail": {"dimension": len(embeddings[0]), "latency_ms": round(embed_time)}
            })

            # Stage 4: Storing in Vector DB
            yield _sse({"stage": "storing", "status": "running", "message": "Storing in ChromaDB...", "progress": 0.9})
            start = time.perf_counter()

            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(all_chunks))]
            metadatas = [c["metadata"] for c in all_chunks]

            success = vector_db.add_chunks(texts, embeddings, metadatas, chunk_ids)
            store_time = (time.perf_counter() - start) * 1000

            if not success:
                yield _sse({"stage": "error", "status": "error", "message": "Failed to store in vector DB"})
                return

            yield _sse({
                "stage": "storing", "status": "done",
                "message": f"Stored {len(chunk_ids)} chunks",
                "progress": 0.95,
                "detail": {"latency_ms": round(store_time)}
            })

            # Complete
            
            # Log to Audit Log
            audit_log.record_event(
                "DOCUMENT_INGESTED", 
                doc_id, 
                {"filename": file.filename, "pages": len(pages), "chunks": len(all_chunks)}
            )
            if total_redactions:
                audit_log.record_event(
                    "PII_REDACTED",
                    doc_id,
                    {"redaction_counts": total_redactions}
                )

            yield _sse({
                "stage": "complete", "status": "done",
                "message": f"✅ '{file.filename}' indexed successfully! (PII scrubbed)",
                "progress": 1.0,
                "detail": {
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "pages": len(pages),
                    "chunks": len(all_chunks),
                    "total_time_ms": round(parse_time + chunk_time + embed_time + store_time),
                    "pii_redacted": total_redactions,
                }
            })

        except Exception as e:
            yield _sse({"stage": "error", "status": "error", "message": f"Ingestion failed: {str(e)}"})

    return StreamingResponse(ingest_stream(), media_type="text/event-stream")


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks (LGPD Right to Erasure)."""
    success = vector_db.delete_document_chunks(doc_id)
    if not success:
        raise HTTPException(500, "Failed to delete document chunks")

    # Clear threats from memory so dashboard updates
    metrics_store.remove_threats_for_doc(doc_id)

    # Log deletion to Audit Log
    audit_log.record_event(
        "DOCUMENT_DELETED",
        doc_id,
        {"reason": "Right to Erasure (User Request)"}
    )

    return {
        "status": "deleted",
        "doc_id": doc_id,
        "message": "Document and all associated chunks have been permanently removed.",
        "lgpd_compliance": "Right to Erasure fulfilled",
    }


def _sse(data: dict) -> str:
    """Format a dict as an SSE event string."""
    return f"data: {json.dumps(data)}\n\n"
