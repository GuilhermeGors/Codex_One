from app.processing.pii_scrubber import anonymize_text
from app.observability import audit_log
import os

print("Testing PII Scrubber...")
text = "O João da Silva enviou um e-mail para joao.silva@empresa.com.br informando o CPF 123.456.789-00."
scrubbed, redactions = anonymize_text(text, language="pt")

print(f"Original: {text}")
print(f"Scrubbed: {scrubbed}")
print(f"Redactions: {redactions}")

print("\nTesting Audit Log...")
audit_log.record_event("TEST_EVENT", "doc_test", {"scrubbed": scrubbed, "redactions": redactions})
print("Audit log recorded.")

with open("data/audit_log.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()
    print(f"Last log line: {lines[-1]}")
