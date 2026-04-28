"""
Codex One v2 — Precise Token Counter

Uses tiktoken for accurate token counting independent of
the Ollama response metadata. Provides cost estimation.
"""

import tiktoken
from typing import Optional

# Use cl100k_base as a reasonable approximation for most models
_encoder: Optional[tiktoken.Encoding] = None


def get_encoder() -> tiktoken.Encoding:
    """Get or create the tiktoken encoder singleton."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string."""
    if not text:
        return 0
    return len(get_encoder().encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    """
    Count tokens in a list of chat messages.
    
    Accounts for message formatting overhead (~4 tokens per message).
    """
    total = 0
    for msg in messages:
        total += 4  # Every message has role/content overhead
        total += count_tokens(msg.get("content", ""))
        total += count_tokens(msg.get("role", ""))
    total += 2  # Priming tokens
    return total


def estimate_cost(
    tokens_in: int,
    tokens_out: int,
    model: str = "local",
) -> dict:
    """
    Estimate the equivalent API cost if this were a cloud model.
    
    Useful for demonstrating cost savings of local inference.
    Returns cost comparison: local ($0) vs equivalent cloud API.
    """
    # Approximate cloud pricing per 1M tokens (USD)
    cloud_pricing = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    }

    comparisons = {}
    for model_name, prices in cloud_pricing.items():
        cost_in = (tokens_in / 1_000_000) * prices["input"]
        cost_out = (tokens_out / 1_000_000) * prices["output"]
        comparisons[model_name] = round(cost_in + cost_out, 6)

    return {
        "local_cost": 0.0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "cloud_equivalent": comparisons,
        "savings_vs_gpt4o": comparisons.get("gpt-4o", 0),
    }
