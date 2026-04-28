"""
Codex One v2 — LLM Handler

Async interface to Ollama with streaming support for real-time
token-by-token generation. Includes enterprise prompt engineering.
"""

import time
import ollama
from typing import AsyncGenerator, Optional
from app.config import settings

# Initialize client using URL from settings (allows overriding for Docker)
ollama_client = ollama.Client(host=settings.OLLAMA_BASE_URL)

# ============================================================
# Enterprise Prompt Templates
# ============================================================

SYSTEM_PROMPT = """You are Codex One, a highly precise document analysis assistant.

## ABSOLUTE RULES:
1. Answer ONLY using the provided CONTEXT. Never use prior knowledge.
2. If the context does not contain enough information, say: "The provided documents do not contain sufficient information to answer this question."
3. ALWAYS cite the source: include the filename and page/section number.
4. Be concise, structured, and direct.
5. **CRITICAL — LANGUAGE RULE**: You MUST respond in the SAME LANGUAGE as the user's QUESTION. If the user asks in English, respond in English. If the user asks in Portuguese, respond in Portuguese. The language of the context documents is IRRELEVANT — only the question language matters.

## RESPONSE FORMAT:
- Start with a direct answer to the question.
- Support with specific details from the context.
- End with source citations in format: [Source: filename, Page/Section: X]"""


def build_rag_prompt(query: str, context: str) -> list[dict]:
    """
    Build a structured prompt using enterprise RAG patterns.
    
    Uses separate system/user roles for better instruction adherence,
    rather than stuffing everything into a single prompt string.
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"""## CONTEXT (Retrieved Documents):
{context}

---

## QUESTION:
{query}

## ANSWER:""",
        },
    ]


# ============================================================
# Generation Functions
# ============================================================

def generate_response(query: str, context: str) -> dict:
    """
    Synchronous generation — returns the full response.
    
    Returns:
        dict with 'response', 'tokens_in', 'tokens_out', 'latency_ms'
    """
    messages = build_rag_prompt(query, context)
    start = time.perf_counter()

    try:
        result = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": settings.LLM_TEMPERATURE,
                "top_p": settings.LLM_TOP_P,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
                "num_predict": settings.LLM_MAX_TOKENS,
            },
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            "response": result["message"]["content"].strip(),
            "tokens_in": result.get("prompt_eval_count", 0),
            "tokens_out": result.get("eval_count", 0),
            "latency_ms": round(elapsed_ms, 2),
        }

    except ollama.ResponseError as e:
        return {
            "response": f"LLM Error: {e.error} (status {e.status_code})",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
        }
    except ConnectionRefusedError:
        return {
            "response": "Error: Cannot connect to Ollama. Is it running?",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
        }


async def generate_response_stream(query: str, context: str) -> AsyncGenerator[dict, None]:
    """
    Streaming generation — yields tokens one at a time for SSE.
    
    Each yield is a dict with:
        - 'token': the text fragment
        - 'done': whether generation is complete
        - 'tokens_in': (only on final) input token count
        - 'tokens_out': (only on final) output token count
        - 'latency_ms': (only on final) total latency
    """
    messages = build_rag_prompt(query, context)
    start = time.perf_counter()
    tokens_out = 0

    try:
        stream = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=messages,
            stream=True,
            options={
                "temperature": settings.LLM_TEMPERATURE,
                "top_p": settings.LLM_TOP_P,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
                "num_predict": settings.LLM_MAX_TOKENS,
            },
        )

        for chunk in stream:
            token_text = chunk["message"]["content"]
            tokens_out += 1
            is_done = chunk.get("done", False)

            event = {"token": token_text, "done": is_done}

            if is_done:
                elapsed_ms = (time.perf_counter() - start) * 1000
                event["tokens_in"] = chunk.get("prompt_eval_count", 0)
                event["tokens_out"] = chunk.get("eval_count", tokens_out)
                event["latency_ms"] = round(elapsed_ms, 2)

            yield event

    except Exception as e:
        yield {"token": f"\n\n[Error: {str(e)}]", "done": True, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0}


# ============================================================
# Utility: LLM-as-Judge (Context Grading)
# ============================================================

GRADING_PROMPT = """You are a relevance grader. Given a user QUESTION and a DOCUMENT chunk, determine if the document is relevant to answering the question.

Respond with ONLY "yes" or "no". Nothing else.

QUESTION: {question}

DOCUMENT: {document}

RELEVANT (yes/no):"""


def grade_chunk_relevance(question: str, chunk_text: str) -> bool:
    """
    Uses LLM-as-Judge to determine if a chunk is relevant.
    Returns True if relevant, False otherwise.
    """
    try:
        result = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": GRADING_PROMPT.format(question=question, document=chunk_text)}],
            options={"temperature": 0.0, "num_predict": 5},
        )
        answer = result["message"]["content"].strip().lower()
        return "yes" in answer
    except Exception:
        return True  # Fail-open: include chunk if grading fails

