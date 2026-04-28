"""
Codex One v2 — Threat Scanner (Security Intelligence)

Pattern-based threat detection engine that scans document content
for embedded security threats before vectorization:
- SQL Injection patterns
- XSS (Cross-Site Scripting) payloads
- Prompt Injection attempts
- Command Injection / Shell commands
- Credential exposure (API keys, tokens)
- Base64 encoded suspicious payloads

Runs entirely on CPU — zero VRAM usage, blazingly fast.
"""

import re
from typing import Any
from datetime import datetime, timezone


# ============================================================
# Threat Signature Database
# ============================================================

THREAT_SIGNATURES: list[dict[str, Any]] = [
    # --- SQL Injection ---
    {
        "id": "SQLI-001",
        "name": "SQL Injection (UNION SELECT)",
        "category": "SQL Injection",
        "severity": "CRITICAL",
        "pattern": r"(?i)(union\s+(all\s+)?select|select\s+.*\s+from\s+.*\s+where|drop\s+table|insert\s+into|delete\s+from|update\s+.*\s+set)",
        "description": "Classic SQL injection using UNION SELECT, DROP TABLE, or data manipulation statements.",
    },
    {
        "id": "SQLI-002",
        "name": "SQL Injection (Boolean/Error-based)",
        "category": "SQL Injection",
        "severity": "HIGH",
        "pattern": r"(?i)(\bor\b\s+1\s*=\s*1|'\s*or\s*'1'\s*=\s*'1|;\s*--\s*$|'\s*;\s*drop\s|having\s+1\s*=\s*1|waitfor\s+delay)",
        "description": "Boolean-based or error-based SQL injection, including tautology and time-based attacks.",
    },
    {
        "id": "SQLI-003",
        "name": "SQL Injection (Comment/Escape)",
        "category": "SQL Injection",
        "severity": "MEDIUM",
        "pattern": r"(/\*.*\*/|--\s+.*|#\s+.*(?:select|drop|union|insert|delete|update))",
        "description": "SQL injection using comment delimiters to bypass filters.",
    },
    # --- XSS ---
    {
        "id": "XSS-001",
        "name": "XSS (Script Tag Injection)",
        "category": "Cross-Site Scripting",
        "severity": "CRITICAL",
        "pattern": r"(?i)(<script[^>]*>.*?</script>|<script[^>]*>|javascript\s*:|on(load|error|click|mouseover)\s*=)",
        "description": "Script tag or inline JavaScript event handler injection.",
    },
    {
        "id": "XSS-002",
        "name": "XSS (HTML Injection)",
        "category": "Cross-Site Scripting",
        "severity": "HIGH",
        "pattern": r"(?i)(<iframe[^>]*>|<img[^>]+onerror\s*=|<svg[^>]+onload\s*=|<body[^>]+onload\s*=|<embed[^>]*>|<object[^>]*>)",
        "description": "HTML element injection for XSS via iframes, images with error handlers, or SVG payloads.",
    },
    # --- Prompt Injection ---
    {
        "id": "PI-001",
        "name": "Prompt Injection (Role Override)",
        "category": "Prompt Injection",
        "severity": "CRITICAL",
        "pattern": r"(?i)(ignore\s+(all\s+)?previous\s+instructions|you\s+are\s+now\s+a|forget\s+(everything|all|your)\s+(you|previous)|disregard\s+(all|your)\s+instructions|new\s+instructions?\s*:)",
        "description": "Attempt to override the LLM's system prompt by injecting new role instructions.",
    },
    {
        "id": "PI-002",
        "name": "Prompt Injection (Data Exfiltration)",
        "category": "Prompt Injection",
        "severity": "HIGH",
        "pattern": r"(?i)(print\s+your\s+(system\s+)?prompt|reveal\s+your\s+instructions|show\s+me\s+your\s+(system|initial)\s+(prompt|message)|what\s+are\s+your\s+rules)",
        "description": "Attempt to extract the system prompt or internal configuration of the LLM.",
    },
    # --- Command Injection ---
    {
        "id": "CMDi-001",
        "name": "OS Command Injection",
        "category": "Command Injection",
        "severity": "CRITICAL",
        "pattern": r"(?i)(;\s*(ls|cat|rm|wget|curl|nc|bash|sh|python|perl|ruby|powershell)\b|\|\|\s*(ls|cat|rm)|`[^`]+`|\$\(.*\))",
        "description": "Shell command injection via semicolons, pipes, backticks, or subshell execution.",
    },
    {
        "id": "CMDi-002",
        "name": "Path Traversal",
        "category": "Command Injection",
        "severity": "HIGH",
        "pattern": r"(\.\./\.\./|\.\.\\\.\.\\|/etc/passwd|/etc/shadow|C:\\Windows\\System32)",
        "description": "Directory traversal attempt to access sensitive system files.",
    },
    # --- Credential Exposure ---
    {
        "id": "CRED-001",
        "name": "API Key / Token Exposure",
        "category": "Credential Exposure",
        "severity": "HIGH",
        "pattern": r"(?i)(api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,}|bearer\s+[a-zA-Z0-9_\-\.]{20,}|token\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{20,})",
        "description": "Hardcoded API keys, bearer tokens, or authentication tokens found in document text.",
    },
    {
        "id": "CRED-002",
        "name": "Password in Plaintext",
        "category": "Credential Exposure",
        "severity": "CRITICAL",
        "pattern": r"(?i)(password\s*[:=]\s*['\"]?[^\s'\"]{6,}|passwd\s*[:=]\s*[^\s]{6,}|secret\s*[:=]\s*['\"]?[^\s'\"]{6,})",
        "description": "Plaintext passwords or secrets embedded in document content.",
    },
    # --- Encoded Payloads ---
    {
        "id": "ENC-001",
        "name": "Base64 Encoded Payload",
        "category": "Obfuscation",
        "severity": "MEDIUM",
        "pattern": r"(?i)(eval\s*\(\s*atob\s*\(|base64[_\s]*decode|frombase64string)",
        "description": "Base64 decoding functions that may hide malicious payloads.",
    },
]


# ============================================================
# Scanner Engine
# ============================================================

def scan_text(text: str, doc_id: str = "", filename: str = "") -> list[dict[str, Any]]:
    """
    Scan a text block for all known threat signatures.
    
    Returns a list of threat findings, each containing:
    - signature details (id, name, category, severity)
    - matched text snippet
    - location (approximate character offset)
    """
    if not text:
        return []

    findings = []

    for sig in THREAT_SIGNATURES:
        try:
            matches = list(re.finditer(sig["pattern"], text))
            for match in matches:
                # Extract a snippet around the match for context
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                snippet = text[start:end].replace("\n", " ").strip()

                findings.append({
                    "threat_id": sig["id"],
                    "name": sig["name"],
                    "category": sig["category"],
                    "severity": sig["severity"],
                    "description": sig["description"],
                    "matched_text": match.group()[:100],
                    "context_snippet": f"...{snippet}...",
                    "char_offset": match.start(),
                    "doc_id": doc_id,
                    "filename": filename,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
        except re.error:
            continue

    return findings


def scan_document_pages(pages: list[dict], doc_id: str = "", filename: str = "") -> list[dict[str, Any]]:
    """
    Scan all pages/sections of a parsed document.
    Returns aggregated findings across all pages.
    """
    all_findings = []
    for page in pages:
        text = page.get("text", "")
        page_findings = scan_text(text, doc_id=doc_id, filename=filename)
        
        # Add page context to each finding
        meta = page.get("metadata", {})
        for f in page_findings:
            f["page"] = meta.get("page", meta.get("section", "unknown"))
        
        all_findings.extend(page_findings)
    
    return all_findings


def get_severity_score(severity: str) -> int:
    """Convert severity string to numeric score for sorting/aggregation."""
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(severity, 0)


def summarize_findings(findings: list[dict]) -> dict[str, Any]:
    """
    Create a summary of all threat findings for dashboard display.
    """
    if not findings:
        return {
            "total_threats": 0,
            "by_severity": {},
            "by_category": {},
            "risk_score": 0,
            "findings": [],
        }

    by_severity = {}
    by_category = {}
    
    for f in findings:
        sev = f["severity"]
        cat = f["category"]
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1

    # Risk score: weighted sum (CRITICAL=10, HIGH=5, MEDIUM=2, LOW=1)
    weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1}
    risk_score = sum(weights.get(f["severity"], 0) for f in findings)

    return {
        "total_threats": len(findings),
        "by_severity": by_severity,
        "by_category": by_category,
        "risk_score": risk_score,
        "findings": findings,
    }
