"""
Codex One v2 — Audit Log (LGPD Compliance)

Provides a persistent, append-only JSONL log of all critical
system events to comply with LGPD requirements:
- Data ingestion (what was ingested and when)
- PII redaction (what was scrubbed for Privacy by Design)
- Data erasure (Right to Erasure compliance)
"""

import os
import json
from datetime import datetime, timezone
from typing import Any
from app.config import settings

AUDIT_LOG_FILE = os.path.join(settings.DATA_DIR, "audit_log.jsonl")


def record_event(
    event_type: str,
    doc_id: str,
    details: dict[str, Any],
    user_id: str = "system",
):
    """
    Append an event to the persistent audit log.
    
    Event types:
    - DOCUMENT_INGESTED: When a new document enters the system.
    - PII_REDACTED: Details about anonymization applied.
    - DOCUMENT_DELETED: When a document is completely purged from ChromaDB.
    """
    # Ensure data directory exists
    os.makedirs(settings.DATA_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "doc_id": doc_id,
        "details": details,
    }

    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[AuditLog] Failed to write event {event_type} for {doc_id}: {e}")

